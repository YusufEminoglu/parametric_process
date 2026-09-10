# -*- coding: utf-8 -*-
"""Integrated QGIS workflow for reproducible block and neighborhood studies."""
from __future__ import annotations

import json
import math

from qgis.core import (
    QgsFeature, QgsFeatureSink, QgsField, QgsFields, QgsGeometry, QgsPointXY,
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingException,
    QgsProcessingParameterFeatureSink, QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField, QgsProcessingParameterNumber,
    QgsProcessingParameterString, QgsRectangle, QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from .academic_engine import (
    DEFAULT_ASSUMPTIONS, MODEL_VERSION, accessibility_indicators,
    aggregate_robustness, blue_green_indicators, constraint_diagnostics,
    create_study, financial_and_carbon, resolve_zoning,
)
from .nsga2_engine import run_nsga2_optimization


def _scaled_rectangle(bounds: QgsRectangle, ratio: float) -> QgsGeometry:
    ratio = min(1.0, max(0.02, ratio))
    factor = math.sqrt(ratio)
    center = bounds.center()
    half_width = bounds.width() * factor / 2.0
    half_height = bounds.height() * factor / 2.0
    return QgsGeometry.fromRect(QgsRectangle(
        center.x() - half_width, center.y() - half_height,
        center.x() + half_width, center.y() + half_height,
    ))


def parcel_conforming_footprints(parcel: QgsGeometry, target_area: float, typology: str,
                                 rotation_deg: float, setback_m: float) -> list[QgsGeometry]:
    """Generate valid planning massing constrained to the parcel setback envelope."""
    if parcel is None or parcel.isEmpty() or parcel.area() <= 0:
        return []
    buildable = parcel.buffer(-max(0.0, setback_m), 8)
    if buildable.isEmpty():
        return []
    if buildable.isMultipart():
        parts = buildable.asGeometryCollection()
        buildable = max(parts, key=lambda part: part.area()) if parts else buildable
    desired = min(max(1.0, float(target_area)), buildable.area())
    ratio = desired / max(1e-9, buildable.boundingBox().area())
    candidate = _scaled_rectangle(buildable.boundingBox(), ratio)
    candidate.rotate(float(rotation_deg), QgsPointXY(buildable.centroid().asPoint()))
    candidate = candidate.intersection(buildable)

    if typology == "Courtyard" and candidate.area() > 100.0:
        depth = max(2.0, min(candidate.boundingBox().width(), candidate.boundingBox().height()) * 0.22)
        inner = candidate.buffer(-depth, 8)
        if not inner.isEmpty():
            candidate = candidate.difference(inner)
    elif typology in {"LShape", "UShape"} and candidate.area() > 80.0:
        box = candidate.boundingBox()
        cut = QgsGeometry.fromRect(QgsRectangle(
            box.center().x(), box.center().y(), box.xMaximum(), box.yMaximum()
        ))
        if typology == "UShape":
            cut = QgsGeometry.fromRect(QgsRectangle(
                box.xMinimum() + box.width() * 0.3, box.center().y(),
                box.xMaximum() - box.width() * 0.3, box.yMaximum()
            ))
        candidate = candidate.difference(cut).intersection(buildable)
    elif typology == "MultiBuildingBlock" and candidate.area() > 120.0:
        box = candidate.boundingBox()
        gap = min(4.0, box.width() * 0.12)
        left = QgsGeometry.fromRect(QgsRectangle(
            box.xMinimum(), box.yMinimum(), box.center().x() - gap / 2.0, box.yMaximum()
        )).intersection(buildable)
        right = QgsGeometry.fromRect(QgsRectangle(
            box.center().x() + gap / 2.0, box.yMinimum(), box.xMaximum(), box.yMaximum()
        )).intersection(buildable)
        return [geometry for geometry in (left, right) if not geometry.isEmpty() and geometry.area() > 1.0]

    candidate = candidate.makeValid().intersection(buildable)
    if candidate.isEmpty() or candidate.area() <= 1.0:
        return []
    return [candidate]


def _field_value(feature: QgsFeature, field_name: str) -> object:
    return feature.attribute(field_name) if field_name and feature.fields().indexOf(field_name) >= 0 else None


def _parse_seeds(text: str) -> list[int]:
    try:
        seeds = [int(value.strip()) for value in str(text).split(",") if value.strip()]
    except ValueError as exc:
        raise QgsProcessingException("Seeds must be comma-separated integers") from exc
    if not seeds or len(seeds) > 50 or len(set(seeds)) != len(seeds):
        raise QgsProcessingException("Provide between 1 and 50 unique seeds")
    if any(seed < 0 or seed > 2147483646 for seed in seeds):
        raise QgsProcessingException("Seeds must be between 0 and 2147483646")
    return seeds


class AcademicUrbanDesignStudyAlgorithm(QgsProcessingAlgorithm):
    """End-to-end reproducible study runner with multiple spatial outputs."""

    def name(self):
        return "academic_urban_design_study"

    def displayName(self):
        return "7. Academic Urban Design Study"

    def group(self):
        return "Urban Analytics"

    def groupId(self):
        return "urban_analytics"

    def shortHelpString(self):
        return (
            "Runs a reproducible block-and-neighborhood design study. It validates a projected "
            "site layer, resolves parcel-specific zoning from optional fields with explicit "
            "defaults, performs deterministic multi-seed NSGA-II screening, creates building "
            "massing inside setback envelopes, evaluates accessibility, blue-green, carbon and "
            "financial indicators, and writes provenance to every output. Environmental results "
            "are screening-level proxies and require domain validation before predictive use."
        )

    def createInstance(self):
        return AcademicUrbanDesignStudyAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            "SITE", "Site parcels", [QgsProcessing.SourceType.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            "ID_FIELD", "Unique parcel ID field", parentLayerParameterName="SITE", optional=True))
        for parameter, label in (
            ("BCR_FIELD", "Maximum BCR field"), ("FAR_FIELD", "Maximum FAR field"),
            ("HEIGHT_FIELD", "Maximum height field"), ("FRONT_FIELD", "Front setback field"),
            ("SIDE_FIELD", "Side setback field"), ("REAR_FIELD", "Rear setback field"),
        ):
            self.addParameter(QgsProcessingParameterField(
                parameter, label, parentLayerParameterName="SITE", optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "STREETS", "Street network (optional)", [QgsProcessing.SourceType.TypeVectorLine], optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "DESTINATIONS", "Destinations or transit stops (optional)",
            [QgsProcessing.SourceType.TypeVectorPoint], optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            "GREEN_SPACE", "Green space or canopy polygons (optional)",
            [QgsProcessing.SourceType.TypeVectorPolygon], optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            "POP_SIZE", "Population size", QgsProcessingParameterNumber.Type.Integer, 24, minValue=4, maxValue=500))
        self.addParameter(QgsProcessingParameterNumber(
            "GENERATIONS", "Generations", QgsProcessingParameterNumber.Type.Integer, 8, minValue=1, maxValue=500))
        self.addParameter(QgsProcessingParameterString(
            "SEEDS", "Unique random seeds (comma-separated)", "42,31415,271828"))
        for parameter, label, default, maximum in (
            ("MAX_BCR", "Default maximum BCR", 0.45, 1.0),
            ("MAX_FAR", "Default maximum FAR", 2.5, None),
            ("MAX_HEIGHT", "Default maximum height (m)", 18.0, None),
            ("SETBACK", "Default setback (m)", 3.0, None),
            ("RAINFALL", "Design rainfall event (mm)", 50.0, None),
            ("CANOPY_TARGET", "Target canopy ratio", 0.25, 1.0),
        ):
            minimum = 0.0 if parameter not in {"MAX_BCR", "MAX_FAR", "MAX_HEIGHT"} else 0.01
            if maximum is None:
                number_parameter = QgsProcessingParameterNumber(
                    parameter, label, QgsProcessingParameterNumber.Type.Double, default,
                    minValue=minimum)
            else:
                number_parameter = QgsProcessingParameterNumber(
                    parameter, label, QgsProcessingParameterNumber.Type.Double, default,
                    minValue=minimum, maxValue=maximum)
            self.addParameter(number_parameter)
        self.addParameter(QgsProcessingParameterFeatureSink("ALTERNATIVES", "Alternative records"))
        self.addParameter(QgsProcessingParameterFeatureSink("BUILDINGS", "Generated building massing"))
        self.addParameter(QgsProcessingParameterFeatureSink("OPEN_SPACE", "Residual open space"))
        self.addParameter(QgsProcessingParameterFeatureSink("REJECTED", "Rejected alternatives"))
        self.addParameter(QgsProcessingParameterFeatureSink("SUMMARY", "Parcel robustness summary"))

    def processAlgorithm(self, parameters, context, feedback):
        site = self.parameterAsSource(parameters, "SITE", context)
        if site is None:
            raise QgsProcessingException("Site parcels are required")
        if site.sourceCrs().isGeographic():
            raise QgsProcessingException("Site CRS must be a projected CRS measured in metres")
        features = list(site.getFeatures())
        if not features:
            raise QgsProcessingException("Site layer contains no features")
        seeds = _parse_seeds(self.parameterAsString(parameters, "SEEDS", context))
        pop_size = self.parameterAsInt(parameters, "POP_SIZE", context)
        generations = self.parameterAsInt(parameters, "GENERATIONS", context)
        defaults = dict(DEFAULT_ASSUMPTIONS)
        defaults.update({
            "max_bcr": self.parameterAsDouble(parameters, "MAX_BCR", context),
            "max_far": self.parameterAsDouble(parameters, "MAX_FAR", context),
            "max_height_m": self.parameterAsDouble(parameters, "MAX_HEIGHT", context),
            "front_setback_m": self.parameterAsDouble(parameters, "SETBACK", context),
            "side_setback_m": self.parameterAsDouble(parameters, "SETBACK", context),
            "rear_setback_m": self.parameterAsDouble(parameters, "SETBACK", context),
            "rainfall_event_mm": self.parameterAsDouble(parameters, "RAINFALL", context),
            "target_canopy_ratio": self.parameterAsDouble(parameters, "CANOPY_TARGET", context),
        })
        mapping = {
            "max_bcr": self.parameterAsString(parameters, "BCR_FIELD", context),
            "max_far": self.parameterAsString(parameters, "FAR_FIELD", context),
            "max_height_m": self.parameterAsString(parameters, "HEIGHT_FIELD", context),
            "front_setback_m": self.parameterAsString(parameters, "FRONT_FIELD", context),
            "side_setback_m": self.parameterAsString(parameters, "SIDE_FIELD", context),
            "rear_setback_m": self.parameterAsString(parameters, "REAR_FIELD", context),
        }
        study = create_study("QGIS Academic Urban Design Study", site.sourceCrs().authid(),
                             field_mapping=mapping, assumptions=defaults, seeds=seeds)
        streets = self.parameterAsSource(parameters, "STREETS", context)
        destinations = self.parameterAsSource(parameters, "DESTINATIONS", context)
        green_space = self.parameterAsSource(parameters, "GREEN_SPACE", context)
        for label, source in (("Street", streets), ("Destination", destinations), ("Green space", green_space)):
            if source and source.sourceCrs() != site.sourceCrs():
                raise QgsProcessingException(
                    f"{label} layer CRS must match the site CRS; reproject it before analysis")

        common = QgsFields()
        for name, field_type in (
            ("parcel_id", QVariant.String), ("source_fid", QVariant.LongLong),
            ("solution_id", QVariant.String), ("run_id", QVariant.String),
            ("study_id", QVariant.String), ("scenario", QVariant.String),
            ("seed", QVariant.Int), ("model_ver", QVariant.String),
            ("typology", QVariant.String), ("floors", QVariant.Int),
            ("height_m", QVariant.Double), ("bcr", QVariant.Double),
            ("far", QVariant.Double), ("gfa_m2", QVariant.Double),
            ("feasible", QVariant.Bool), ("violation", QVariant.Double),
            ("walk_score", QVariant.Double), ("int_density", QVariant.Double),
            ("runoff_m3", QVariant.Double), ("canopy_rt", QVariant.Double),
            ("npv", QVariant.Double), ("irr", QVariant.Double),
            ("carbon_kg", QVariant.Double), ("status", QVariant.String),
        ):
            common.append(QgsField(name, field_type))
        summary_fields = QgsFields()
        for name, field_type in (
            ("parcel_id", QVariant.String), ("study_id", QVariant.String),
            ("runs", QVariant.Int), ("feasible_rt", QVariant.Double),
            ("gfa_median", QVariant.Double), ("gfa_iqr", QVariant.Double),
            ("score_med", QVariant.Double), ("score_iqr", QVariant.Double),
        ):
            summary_fields.append(QgsField(name, field_type))

        alt_sink, alt_id = self.parameterAsSink(parameters, "ALTERNATIVES", context, common,
                                                site.wkbType(), site.sourceCrs())
        building_sink, building_id = self.parameterAsSink(parameters, "BUILDINGS", context, common,
                                                          QgsWkbTypes.Type.MultiPolygon, site.sourceCrs())
        open_sink, open_id = self.parameterAsSink(parameters, "OPEN_SPACE", context, common,
                                                  QgsWkbTypes.Type.MultiPolygon, site.sourceCrs())
        rejected_sink, rejected_id = self.parameterAsSink(parameters, "REJECTED", context, common,
                                                          site.wkbType(), site.sourceCrs())
        summary_sink, summary_id = self.parameterAsSink(parameters, "SUMMARY", context, summary_fields,
                                                        QgsWkbTypes.Type.NoGeometry, site.sourceCrs())
        if any(sink is None for sink in (alt_sink, building_sink, open_sink, rejected_sink, summary_sink)):
            raise QgsProcessingException("One or more output sinks could not be created")

        id_field = self.parameterAsString(parameters, "ID_FIELD", context)
        total_steps = len(features) * len(seeds)
        completed = 0
        for feature_index, source_feature in enumerate(features):
            if feedback.isCanceled():
                break
            geometry = source_feature.geometry()
            parcel_id = str(_field_value(source_feature, id_field) if id_field else source_feature.id())
            if geometry is None or geometry.isEmpty() or geometry.area() <= 1.0 or not geometry.isGeosValid():
                self._write_common(rejected_sink, common, geometry, parcel_id, source_feature.id(),
                                   "", study, 0, {}, {}, {}, {}, False, "invalid_site_geometry")
                continue
            attributes = {field.name(): source_feature[field.name()] for field in source_feature.fields()}
            zoning = resolve_zoning(attributes, mapping, defaults)
            parcel_runs = []
            for seed in seeds:
                result = run_nsga2_optimization(
                    geometry.area(), pop_size=pop_size, generations=generations, seed=seed,
                    max_bcr=zoning["max_bcr"], max_far=zoning["max_far"],
                    max_height=zoning["max_height_m"],
                    bounds={"min_setback": max(zoning["front_setback_m"], zoning["side_setback_m"], zoning["rear_setback_m"]),
                            "max_setback": max(zoning["front_setback_m"], zoning["side_setback_m"], zoning["rear_setback_m"]) + 8.0,
                            "min_floors": 1, "max_floors": max(1, int(zoning["max_height_m"] / defaults["floor_height_m"]))},
                )
                run_id = result["run_manifest"]["run_id"]
                for solution in result["pareto_solutions"]:
                    genotype, metrics = solution["genotype"], solution["metrics"]
                    diagnostics = constraint_diagnostics(metrics, zoning)
                    footprints = parcel_conforming_footprints(
                        geometry, metrics["footprint_area"], genotype["typology"],
                        float(genotype.get("orientation", seed % 180)), float(genotype["setback"]))
                    if not footprints:
                        self._write_common(rejected_sink, common, geometry, parcel_id, source_feature.id(),
                                           solution["id"], study, seed, genotype, metrics, {}, {}, False,
                                           "empty_buildable_envelope", run_id)
                        continue
                    union = QgsGeometry.unaryUnion(footprints)
                    context_metrics = self._context_metrics(geometry, streets, destinations)
                    green_metrics = self._green_metrics(geometry, union, green_space, defaults)
                    finance = financial_and_carbon(metrics["gfa"], defaults)
                    self._write_common(alt_sink, common, geometry, parcel_id, source_feature.id(),
                                       solution["id"], study, seed, genotype, metrics, context_metrics,
                                       {**green_metrics, **finance, "_violation": diagnostics["total_violation"]},
                                       diagnostics["feasible"], "accepted", run_id)
                    for footprint in footprints:
                        self._write_common(building_sink, common, footprint, parcel_id, source_feature.id(),
                                           solution["id"], study, seed, genotype, metrics, context_metrics,
                                           {**green_metrics, **finance, "_violation": diagnostics["total_violation"]},
                                           diagnostics["feasible"], "massing", run_id)
                    residual = geometry.difference(union)
                    if not residual.isEmpty():
                        self._write_common(open_sink, common, residual, parcel_id, source_feature.id(),
                                           solution["id"], study, seed, genotype, metrics, context_metrics,
                                           {**green_metrics, **finance, "_violation": diagnostics["total_violation"]},
                                           diagnostics["feasible"], "residual_open_space", run_id)
                    parcel_runs.append({"feasible": diagnostics["feasible"], "metrics": {
                        "gfa": metrics["gfa"], "planx_score": metrics["planx_score"]}})
                completed += 1
                feedback.setProgress(completed / max(1, total_steps) * 100.0)
            if parcel_runs:
                robustness = aggregate_robustness(parcel_runs, ["gfa", "planx_score"])
                summary_feature = QgsFeature(summary_fields)
                summary_feature.setAttributes([
                    parcel_id, study["study_id"], robustness["run_count"], robustness["feasible_run_rate"],
                    robustness["metrics"]["gfa"]["median"], robustness["metrics"]["gfa"]["iqr"],
                    robustness["metrics"]["planx_score"]["median"], robustness["metrics"]["planx_score"]["iqr"],
                ])
                summary_sink.addFeature(summary_feature, QgsFeatureSink.Flag.FastInsert)
        return {"ALTERNATIVES": alt_id, "BUILDINGS": building_id, "OPEN_SPACE": open_id,
                "REJECTED": rejected_id, "SUMMARY": summary_id, "STUDY_ID": study["study_id"]}

    @staticmethod
    def _context_metrics(site_geometry, streets, destinations):
        search = site_geometry.buffer(800.0, 8)
        street_length = sum(feature.geometry().intersection(search).length() for feature in streets.getFeatures()
                            if streets and feature.geometry() and feature.geometry().intersects(search)) if streets else 0.0
        intersections = 0
        distances = []
        centroid = site_geometry.centroid()
        if destinations:
            distances = [centroid.distance(feature.geometry()) for feature in destinations.getFeatures()
                         if feature.geometry() and not feature.geometry().isEmpty()]
        return accessibility_indicators(site_geometry.area(), street_length, intersections, distances)

    @staticmethod
    def _green_metrics(site_geometry, buildings, green_space, defaults):
        canopy_area = 0.0
        patches = []
        if green_space:
            for feature in green_space.getFeatures():
                geom = feature.geometry()
                if geom and geom.intersects(site_geometry):
                    area = geom.intersection(site_geometry).area()
                    canopy_area += area
                    patches.append({"area_m2": area})
        return blue_green_indicators(site_geometry.area(), buildings.area(), 0.0,
                                     canopy_area, patches, defaults)

    @staticmethod
    def _write_common(sink, fields, geometry, parcel_id, source_fid, solution_id, study,
                      seed, genotype, metrics, context_metrics, extra_metrics, feasible,
                      status, run_id=""):
        feature = QgsFeature(fields)
        if geometry is not None and not geometry.isEmpty():
            feature.setGeometry(geometry)
        feature.setAttributes([
            parcel_id, int(source_fid), str(solution_id), run_id, study["study_id"], "baseline",
            int(seed), MODEL_VERSION, str(genotype.get("typology", "")), int(genotype.get("floors", 0)),
            float(metrics.get("height_m", 0.0)), float(metrics.get("bcr", 0.0)),
            float(metrics.get("far", 0.0)), float(metrics.get("gfa", 0.0)), bool(feasible),
            float(extra_metrics.get("_violation", 0.0)), float(context_metrics.get("walk_access_score", 0.0)),
            float(context_metrics.get("intersection_density", 0.0)),
            float(extra_metrics.get("runoff_volume_m3", 0.0)), float(extra_metrics.get("tree_canopy_ratio", 0.0)),
            float(extra_metrics.get("npv", 0.0)), float(extra_metrics.get("irr") or 0.0),
            float(extra_metrics.get("lifecycle_carbon_kgco2e", 0.0)), status,
        ])
        sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)
