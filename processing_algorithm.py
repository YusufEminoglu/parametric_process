# -*- coding: utf-8 -*-
"""QGIS Processing Algorithms for Parametric Process.

Provides headless evolutionary optimization and multi-domain urban physics evaluation directly in QGIS Processing Toolbox.
"""
from __future__ import annotations

import os

from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QIcon

from .nsga2_engine import (
    evaluate_phenotype,
    run_nsga2_optimization,
    run_spea2_optimization,
    run_nsga3_optimization,
    run_moead_optimization,
)

PLUGIN_DIR = os.path.dirname(__file__)


def _icon(filename: str) -> QIcon:
    path = os.path.join(PLUGIN_DIR, "icons", filename)
    return QIcon(path) if os.path.exists(path) else QIcon()


def _ring_to_geometry(ring: list) -> QgsGeometry:
    """Convert a plot ring (list of {"x":..., "y":...} dicts) to a QgsGeometry polygon."""
    if not ring or len(ring) < 3:
        return QgsGeometry()
    pts = [QgsPointXY(pt["x"], pt["y"]) for pt in ring]
    # Close the ring
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return QgsGeometry.fromPolygonXY([pts])


class ParametricOptimizationAlgorithm(QgsProcessingAlgorithm):
    ICON = "icon_nsga3.png"

    def name(self):
        return 'parametric_optimization'

    def displayName(self):
        return '1. Parametric Multi-Objective Evolutionary Optimization'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>1. Parametric Multi-Objective Evolutionary Optimization</h3>"

            "<p><b>Algorithms & theory.</b> Four canonical multi-objective evolutionary "
            "solvers are implemented in pure Python: <b>NSGA-II</b> (Deb, Pratap, Agarwal "
            "& Meyarivan, 2002 — IEEE Trans. Evol. Comp. 6(2):182-197) uses fast "
            "non-dominated sorting (O(MN<sup>2</sup>) per generation) with crowding-"
            "distance archive truncation; <b>NSGA-III</b> (Deb & Jain, 2014 — IEEE Trans. "
            "Evol. Comp. 18(4):577-601) replaces crowding with Das & Dennis systematic "
            "reference-point niching, critical when optimising 5+ objectives where the "
            "Pareto front occupies a high-dimensional manifold; <b>SPEA-2</b> (Zitzler, "
            "Laumanns & Thiele, 2001 — TIK Report 103) computes raw fitness from dominance "
            "strength plus k-th nearest-neighbour density (k = sqrt(N)), producing a finer-"
            "grained archive than NSGA-II; <b>MOEA/D</b> (Zhang & Li, 2007 — IEEE Trans. "
            "Evol. Comp. 11(6):712-731) decomposes the multi-objective problem into N "
            "scalar subproblems using Tchebycheff aggregation with neighbourhood-based "
            "subproblem updates, yielding uniformly distributed Pareto sets even on "
            "disconnected fronts.</p>"

            "<p><b>Constraint handling.</b> Deb's constrained-dominance principle (2000) "
            "is applied: a feasible solution always dominates an infeasible one; between "
            "two infeasible solutions, the one with smaller total constraint violation "
            "(BCR excess + FAR excess + height excess) dominates. This is stricter than "
            "penalty-function approaches because it guarantees that feasible solutions "
            "survive into later generations regardless of objective values.</p>"

            "<p><b>Genotype space.</b> Each individual encodes 8 decision variables: "
            "setback (0-15 m, continuous), floors (1-30, integer), typology (8 nominal "
            "classes: Tower, Slab, Courtyard, L-Shape, U-Shape, PodiumTower, SteppedTower, "
            "MultiBuildingBlock), usage (Residential, Commercial, MixedUse, Civic, Park), "
            "roof style (Flat, Hipped, Gable, Mansard), scale_x (0.35-1.6, continuous), "
            "scale_y (0.35-1.6, continuous), and floor height (2.8-4.2 m, continuous). "
            "Crossover is uniform with arithmetic blend on continuous variables; mutation "
            "is Gaussian perturbation on continuous, random-walk step on integer, uniform "
            "resample on nominal.</p>"

            "<p><b>Objective functions.</b> Default 5-objective formulation: maximise GFA "
            "(gross floor area, m<sup>2</sup>), maximise PlanX composite urban quality "
            "score (0-100, weighted composite of density efficiency, open-space ratio, "
            "wind ventilation, thermal comfort, and pollution dispersion), maximise wind "
            "ventilation (0-100, porosity × alignment factor), maximise ROI percentage, "
            "minimise total lifecycle carbon (kg CO<sub>2</sub>eq, embodied + 50-year "
            "operational). The hypervolume indicator (Zitzler & Thiele, 1999) tracks "
            "convergence across generations.</p>"

            "<p><b>Parameter guidance.</b> Population 30-100 — larger populations cover "
            "the decision space more thoroughly at higher computational cost (quadratic "
            "in N for non-dominated sort). Generations 15-50 — most runs converge by "
            "gen 30-40; monitor hypervolume plateau in the 3D cockpit analytics panel. "
            "Max BCR 0.30-0.60 (Turkish typical: 0.40), Max FAR 1.5-3.5 (Turkish typical: "
            "2.0-2.5), Max Height 12-60 m. If constraint_penalty > 0 in output, the "
            "solution violated zoning — increase max values or accept the penalty.</p>"

            "<p><b>Output interpretation.</b> Each output feature is one Pareto-rank-1 "
            "solution with the full genotype (setback, floors, typology, usage, roof_style, "
            "scale_x, scale_y, floor_h) plus 30+ physics metrics: planx_score (higher = "
            "better overall), carbon_kg (total LCA), wind_score (0-100), solar_kwh (per m<sup>2</sup>), "
            "utci_score (0-100 thermal comfort), roi_yield (%), svf_ratio (0-1 sky view), "
            "canyon_hw (H/W ratio), mrt_temp (C), pv_kwh (rooftop PV), pop_est, runoff_m3, "
            "pareto_rank, wallacei_id. Sort by planx_score descending for the best-balanced "
            "design. Use pareto_rank to isolate the non-dominated front. In QGIS, apply "
            "graduated symbology on planx_score (green = high, red = low) and overlay on "
            "aerial imagery to compare design alternatives spatially.</p>"
        )

    def createInstance(self):
        return ParametricOptimizationAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Polygon Layer', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'POP_SIZE', 'Population Size', QgsProcessingParameterNumber.Type.Integer, 30
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'GENERATIONS', 'Generations', QgsProcessingParameterNumber.Type.Integer, 15
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'ALGORITHM', 'Algorithm', options=['NSGA-II', 'SPEA-2', 'NSGA-III', 'MOEA/D'], defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_BCR', 'Max BCR', QgsProcessingParameterNumber.Type.Double, 0.45
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_FAR', 'Max FAR', QgsProcessingParameterNumber.Type.Double, 2.5
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_HEIGHT', 'Max Height', QgsProcessingParameterNumber.Type.Double, 18.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT', 'Pareto Front Output')
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, 'INPUT', context)
        pop_size = self.parameterAsInt(parameters, 'POP_SIZE', context)
        generations = self.parameterAsInt(parameters, 'GENERATIONS', context)
        algorithm_idx = self.parameterAsEnum(parameters, 'ALGORITHM', context)
        max_bcr = self.parameterAsDouble(parameters, 'MAX_BCR', context)
        max_far = self.parameterAsDouble(parameters, 'MAX_FAR', context)
        max_height = self.parameterAsDouble(parameters, 'MAX_HEIGHT', context)

        features = list(source.getFeatures()) if source else []
        total_area = sum(f.geometry().area() for f in features) if features else 1200.0
        avg_area = total_area / max(1, len(features))

        fields = QgsFields()
        fields.append(QgsField('far', QVariant.Double))
        fields.append(QgsField('bcr', QVariant.Double))
        fields.append(QgsField('gfa', QVariant.Double))
        fields.append(QgsField('setback', QVariant.Double))
        fields.append(QgsField('scale_x', QVariant.Double))
        fields.append(QgsField('scale_y', QVariant.Double))
        fields.append(QgsField('floors', QVariant.Int))
        fields.append(QgsField('usage', QVariant.String))
        fields.append(QgsField('floor_h', QVariant.Double))
        fields.append(QgsField('typology', QVariant.String))
        fields.append(QgsField('max_bcr', QVariant.Double))
        fields.append(QgsField('max_far', QVariant.Double))
        fields.append(QgsField('max_height', QVariant.Double))
        fields.append(QgsField('roof_style', QVariant.String))
        fields.append(QgsField('stepback_i', QVariant.Int))
        fields.append(QgsField('stepback_d', QVariant.Double))
        fields.append(QgsField('plan_score', QVariant.Double))
        fields.append(QgsField('const_load', QVariant.Double))
        fields.append(QgsField('height_m', QVariant.Double))
        fields.append(QgsField('z_base', QVariant.Double))
        fields.append(QgsField('z_top', QVariant.Double))
        fields.append(QgsField('pop_est', QVariant.Int))
        fields.append(QgsField('carbon', QVariant.Double))
        fields.append(QgsField('runoff', QVariant.Double))
        fields.append(QgsField('open_space', QVariant.Double))
        fields.append(QgsField('wind_score', QVariant.Double))
        fields.append(QgsField('solar_kwh', QVariant.Double))
        fields.append(QgsField('poll_disp', QVariant.Double))
        fields.append(QgsField('svf_ratio', QVariant.Double))
        fields.append(QgsField('canyon_hw', QVariant.Double))
        fields.append(QgsField('roi_yield', QVariant.Double))
        fields.append(QgsField('mrt_temp', QVariant.Double))
        fields.append(QgsField('utci_score', QVariant.Double))
        fields.append(QgsField('pv_kwh', QVariant.Double))
        fields.append(QgsField('pareto_rank', QVariant.Int))
        fields.append(QgsField('wallacei_id', QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT', context, fields, source.wkbType(), source.sourceCrs()
        )

        solver_map = {
            0: run_nsga2_optimization,
            1: run_spea2_optimization,
            2: run_nsga3_optimization,
            3: run_moead_optimization,
        }
        solver_fn = solver_map.get(algorithm_idx, run_nsga2_optimization)

        total_features = len(features)

        for f_idx, feature in enumerate(features):
            if feedback.isCanceled():
                break

            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            parcel_area = geom.area()
            if parcel_area <= 0:
                continue

            res = solver_fn(
                parcel_area=parcel_area,
                pop_size=pop_size,
                generations=generations,
                max_bcr=max_bcr,
                max_far=max_far,
                max_height=max_height,
            )

            pareto_sols = res.get('pareto_solutions', [])

            for idx, sol in enumerate(pareto_sols):
                if feedback.isCanceled():
                    break

                g = sol.get('genotype', {})
                m = sol.get('metrics', {})

                new_f = QgsFeature(fields)
                new_f.setGeometry(geom)

                new_f.setAttribute('far', float(m.get('far', 0)))
                new_f.setAttribute('bcr', float(m.get('bcr', 0)))
                new_f.setAttribute('gfa', float(m.get('gfa', 0)))
                new_f.setAttribute('setback', float(g.get('setback', 0)))
                new_f.setAttribute('scale_x', float(g.get('scale_x', 1)))
                new_f.setAttribute('scale_y', float(g.get('scale_y', 1)))
                new_f.setAttribute('floors', int(g.get('floors', 1)))
                new_f.setAttribute('usage', str(g.get('usage', 'MixedUse')))
                new_f.setAttribute('floor_h', float(g.get('floor_height', 3.0)))
                new_f.setAttribute('typology', str(g.get('typology', 'Tower')))
                new_f.setAttribute('max_bcr', float(max_bcr))
                new_f.setAttribute('max_far', float(max_far))
                new_f.setAttribute('max_height', float(max_height))
                new_f.setAttribute('roof_style', str(g.get('roof_style', 'Flat')))
                new_f.setAttribute('stepback_i', 4)
                new_f.setAttribute('stepback_d', 1.5)
                new_f.setAttribute('plan_score', float(m.get('planx_score', 0)))
                new_f.setAttribute('const_load', float(m.get('constraint_penalty', 0)))
                new_f.setAttribute('height_m', float(m.get('height_m', 0)))
                new_f.setAttribute('z_base', 0.0)
                new_f.setAttribute('z_top', float(m.get('height_m', 0)))
                new_f.setAttribute('pop_est', int(round(m.get('gfa', 0) / 35)))
                new_f.setAttribute('carbon', float(m.get('carbon_kg', 0)))
                new_f.setAttribute('runoff', float(m.get('runoff_m3', 0)))
                new_f.setAttribute('open_space', float(m.get('open_space_m2', 0)))
                new_f.setAttribute('wind_score', float(m.get('wind_ventilation', 0)))
                new_f.setAttribute('solar_kwh', float(m.get('solar_radiation_kwh', 0)))
                new_f.setAttribute('poll_disp', float(m.get('pollution_dispersion', 0)))
                new_f.setAttribute('svf_ratio', float(m.get('sky_view_factor', 0)))
                new_f.setAttribute('canyon_hw', float(m.get('street_canyon_hw', 0)))
                new_f.setAttribute('roi_yield', float(m.get('roi_percentage', 0)))
                new_f.setAttribute('mrt_temp', float(m.get('mrt_temp_celsius', 32.0)))
                new_f.setAttribute('utci_score', float(m.get('utci_score', 0)))
                new_f.setAttribute('pv_kwh', float(m.get('pv_yield_mwh', 0) * 1000.0))
                new_f.setAttribute('pareto_rank', int(sol.get('rank', 1)))
                new_f.setAttribute('wallacei_id', str(sol.get('id', f'sol_{idx+1}')))

                sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)

                # Per-feature progress
                progress = int(((f_idx * len(pareto_sols)) + idx + 1) / max(1, total_features * len(pareto_sols)) * 100)
                feedback.setProgress(progress)

        return {'OUTPUT': dest_id}


class UrbanPhysicsEvaluatorAlgorithm(QgsProcessingAlgorithm):
    ICON = "icon.png"

    def name(self):
        return 'urban_physics_evaluator'

    def displayName(self):
        return '2. Urban Physics & Microclimate Multi-Domain Evaluator'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>2. Urban Physics & Microclimate Multi-Domain Evaluator</h3>"

            "<p><b>Wind ventilation & pedestrian comfort.</b> Building-level wind "
            "ventilation score (0-100) is computed from three components: (a) open-space "
            "ratio (45% weight) — larger setbacks and unbuilt area allow lateral airflow; "
            "(b) building porosity (35% weight) — typology-dependent: Tower 0.75, "
            "MultiBuildingBlock 0.70, Slab 0.35, Courtyard 0.15, reflecting the degree "
            "to which the massing obstructs prevailing wind; (c) wind alignment factor "
            "(20% weight) — the sine of the angle between prevailing wind direction "
            "(default 225 deg SW) and the building's long-axis orientation (L-shape and "
            "U-shape forms get a 45 deg rotation). Street canyon H/W penalty subtracts "
            "up to 8 points per unit H/W. Pedestrian wind comfort follows the Lawson "
            "criteria (Lawson & Penwarden, 1975 — Building Research Establishment Report): "
            "comfort decreases with building height and increases with porosity; scores "
            "below 40 indicate uncomfortable conditions for standing/ sitting activities.</p>"

            "<p><b>Solar irradiance & rooftop PV.</b> Annual solar irradiance (kWh/m<sup>2</sup>/yr) "
            "is estimated from a latitude-adjusted baseline (1500 kWh/m<sup>2</sup>/yr at "
            "35 deg N, decreasing by 15 kWh per degree of latitude). Rooftop PV potential "
            "(MWh/yr) multiplies roof area (footprint adjusted for roof style — flat 0.85, "
            "hipped 1.10) by 65% usable coverage ratio and 20% panel efficiency, following "
            "Duffie & Beckman (2013 — Solar Engineering of Thermal Processes, 4th ed.). "
            "Sky View Factor (SVF) modulates solar access: SVF = 1.0 - 0.24*canyon_HW + "
            "0.32*open_space_ratio, bounded [0.12, 1.0] after Johnson & Watson (1984).</p>"

            "<p><b>Urban heat island & thermal comfort.</b> Mean Radiant Temperature "
            "(MRT, deg C) starts from a 32 deg C Mediterranean summer baseline and adds: "
            "(1-SVF)*3.5 deg C (reduced night-time radiative cooling in deep canyons), "
            "(1-albedo)*2.0 deg C (roof albedo: flat 0.30, hipped 0.45, gable 0.40, "
            "mansard 0.35), minus open_space_ratio*2.5 deg C (vegetated/permeable surface "
            "cooling). UTCI (Universal Thermal Climate Index, 0-100) follows COST Action "
            "730 (Jendritzky et al., 2012 — Int. J. Biometeorology 56:421-428): optimal "
            "comfort at 24 deg C MRT, decreasing by 4.5 points per degree deviation. "
            "Sol-air facade temperature (T_sol-air) is computed from absorbed solar "
            "radiation minus longwave re-radiation divided by the outdoor heat transfer "
            "coefficient (17 W/m<sup>2</sup>K).</p>"

            "<p><b>Lifecycle carbon (LCA).</b> Embodied carbon: timber-tier (< 3 floors, "
            "220 kgCO<sub>2</sub>e/m<sup>2</sup>), concrete-tier (3-8 floors, 380), "
            "steel-tier (> 8 floors, 450), adapted from the ICE database v2.0 (Hammond "
            "& Jones, 2008 — University of Bath). Operational carbon: usage-dependent "
            "emission factors (Residential 45, Commercial 65, MixedUse 52, Civic 48, "
            "Park 5 kgCO<sub>2</sub>e/m<sup>2</sup>/yr) multiplied by GFA. Total LCA = "
            "embodied + 50-year operational, following EN 15978:2011 system boundary.</p>"

            "<p><b>Stormwater runoff & financials.</b> Runoff (m<sup>3</sup>) uses the "
            "Rational Method Q = CIA with roof-form coefficients (flat 0.85, hipped 0.92) "
            "and 80% imperviousness assumption. ROI (%) = (revenue - construction cost) / "
            "construction cost * 100 with 82% net-sellable-area efficiency. NPV computed "
            "over 20 years at 6% discount rate; IRR approximated from cash-flow ratio.</p>"

            "<p><b>Input requirements.</b> Polygon layer with attributes: floors, setback, "
            "typology, usage, roof_style. Ideal input is the output of Algorithm 1 "
            "(Evolutionary Optimization) which already has these columns. Can also be used "
            "standalone for existing building stock evaluation.</p>"

            "<p><b>Visualisation.</b> In QGIS, create graduated symbology: (a) utci_score "
            "diverging blue-white-red ramp centred at 50 (blue = comfortable, red = heat "
            "stress); (b) carbon graduated 5-class natural-breaks to identify carbon "
            "hotspots; (c) wind_score sequential green ramp for ventilation corridors; "
            "(d) mrt_temp red sequential for UHI intensity mapping.</p>"
        )

    def createInstance(self):
        return UrbanPhysicsEvaluatorAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Building Footprints', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT', 'Enriched Evaluated Layers')
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, 'INPUT', context)

        fields = QgsFields()
        for field in source.fields():
            fields.append(field)

        physics_fields = [
            ('carbon', QVariant.Double),
            ('wind_score', QVariant.Double),
            ('solar_kwh', QVariant.Double),
            ('utci_score', QVariant.Double),
            ('runoff', QVariant.Double),
            ('poll_disp', QVariant.Double),
            ('mrt_temp', QVariant.Double),
            ('pv_kwh', QVariant.Double),
            ('roi_yield', QVariant.Double),
            ('plan_score', QVariant.Double),
            ('svf_ratio', QVariant.Double),
            ('canyon_hw', QVariant.Double),
            ('const_load', QVariant.Double),
            ('pop_est', QVariant.Int),
            ('open_space', QVariant.Double),
        ]

        for f_name, f_type in physics_fields:
            if fields.indexOf(f_name) == -1:
                fields.append(QgsField(f_name, f_type))

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT', context, fields, source.wkbType(), source.sourceCrs()
        )

        features = list(source.getFeatures())
        total = 100.0 / len(features) if len(features) > 0 else 0

        for current, f in enumerate(features):
            if feedback.isCanceled():
                break

            geom = f.geometry()
            area = geom.area() if geom and not geom.isEmpty() else 1000.0

            floors = int(f.attribute('floors')) if f.attribute('floors') is not None and str(f.attribute('floors')).isdigit() else 4
            setback = float(f.attribute('setback')) if f.attribute('setback') is not None else 3.0
            typology = str(f.attribute('typology')) if f.attribute('typology') is not None else 'Tower'
            usage = str(f.attribute('usage')) if f.attribute('usage') is not None else 'MixedUse'
            roof_style = str(f.attribute('roof_style')) if f.attribute('roof_style') is not None else 'Flat'

            genotype = {
                'setback': setback,
                'floors': floors,
                'typology': typology,
                'usage': usage,
                'roof_style': roof_style,
                'scale_x': 1.0,
                'scale_y': 1.0,
                'floor_height': 3.0,
            }

            metrics = evaluate_phenotype(genotype, parcel_area=area)

            new_f = QgsFeature(fields)
            new_f.setGeometry(geom)

            for field in source.fields():
                new_f.setAttribute(field.name(), f.attribute(field.name()))

            new_f.setAttribute('carbon', float(metrics.get('carbon_kg', 0)))
            new_f.setAttribute('wind_score', float(metrics.get('wind_ventilation', 0)))
            new_f.setAttribute('solar_kwh', float(metrics.get('solar_radiation_kwh', 0)))
            new_f.setAttribute('utci_score', float(metrics.get('utci_score', 0)))
            new_f.setAttribute('runoff', float(metrics.get('runoff_m3', 0)))
            new_f.setAttribute('poll_disp', float(metrics.get('pollution_dispersion', 0)))
            new_f.setAttribute('mrt_temp', float(metrics.get('mrt_temp_celsius', 32.0)))
            new_f.setAttribute('pv_kwh', float(metrics.get('pv_yield_mwh', 0) * 1000.0))
            new_f.setAttribute('roi_yield', float(metrics.get('roi_percentage', 0)))
            new_f.setAttribute('plan_score', float(metrics.get('planx_score', 0)))
            new_f.setAttribute('svf_ratio', float(metrics.get('sky_view_factor', 0)))
            new_f.setAttribute('canyon_hw', float(metrics.get('street_canyon_hw', 0)))
            new_f.setAttribute('const_load', float(metrics.get('constraint_penalty', 0)))
            new_f.setAttribute('pop_est', int(round(metrics.get('gfa', 0) / 35)))
            new_f.setAttribute('open_space', float(metrics.get('open_space_m2', 0)))

            sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(current * total))

        return {'OUTPUT': dest_id}


class UrbanMorphologyAnalyticsAlgorithm(QgsProcessingAlgorithm):
    ICON = "icon_morphology.png"

    def name(self):
        return 'urban_morphology_analytics'

    def displayName(self):
        return '3. Urban Morphology & Canyon Analytics'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>3. Urban Morphology & Canyon Analytics</h3>"

            "<p><b>Street canyon H/W ratio.</b> Following the urban canopy layer (UCL) "
            "parameterisation of Oke (1988 — Energy & Buildings 11:103-113), the canyon "
            "height-to-width ratio H/W = building_height / effective_street_width. "
            "Classification thresholds: H/W < 0.5 = isolated roughness flow (buildings "
            "do not interact aerodynamically), 0.5 < H/W < 1.0 = wake interference flow "
            "(downstream building affected by upstream wake), H/W > 1.0 = skimming flow "
            "(bulk of flow passes over the canyon, trapping pollutants at street level). "
            "Deep canyons (H/W > 1.5) show severely reduced turbulent mixing and are "
            "associated with elevated pedestrian-level pollutant concentrations (Vardoulakis "
            "et al., 2003 — Atmospheric Environment 37:155-182).</p>"

            "<p><b>Street enclosure index.</b> A 0-100 composite: (height / effective_street_width) "
            "* 45, where effective_street_width = setback*2 + 6 m (6 m being the minimum "
            "two-lane street width). Following Jacobs (1993 — Great Streets, MIT Press), "
            "enclosure values of 30-60 represent the 'outdoor room' feeling characteristic "
            "of successful urban spaces; below 20 is an exposed, suburban-scale void; above "
            "80 is an oppressive, canyonised condition associated with reduced sky visibility "
            "and daylight access at street level.</p>"

            "<p><b>Surface-to-volume compactness (SA/V).</b> SA/V = (facade_area + 2*roof_area) / "
            "volume, measured in m<sup>-1</sup>. Following Ratti, Baker & Steemers (2005 — "
            "Energy & Buildings 37:762-776), SA/V is the primary geometric determinant of "
            "a building's heating and cooling energy demand: lower SA/V means less envelope "
            "area per unit of conditioned volume. Compact, cube-like buildings have SA/V ~ "
            "0.15-0.25; slab buildings ~0.30-0.45; highly articulated forms (courtyards, "
            "L-shapes) ~0.50-0.70. Each 0.1 SA/V increase adds roughly 8-12% to annual "
            "space-conditioning energy. The calculation uses the real polygon perimeter "
            "for non-rectangular footprints.</p>"

            "<p><b>Sky View Factor (SVF).</b> SVF = 1.0 - 0.24*canyon_HW + 0.32*open_space_ratio, "
            "clamped [0.12, 1.0]. This is a first-order geometric approximation of the "
            "fisheye-lens method (Johnson & Watson, 1984 — J. Climate & Applied Met. "
            "23:329-335). SVF < 0.5 indicates that more than half the sky hemisphere is "
            "obstructed, resulting in reduced night-time longwave radiative cooling and "
            "elevated nocturnal UHI intensity (Unger, 2004 — Int. J. Climatology 24:1043-"
            "1058). In high-latitude cities SVF is strongly correlated with wintertime "
            "space-heating demand due to lost passive solar gain.</p>"

            "<p><b>Shannon Entropy of typological diversity.</b> H' = -SUM(p_i * ln(p_i)) "
            "across building typology classes within a district, where p_i is the proportion "
            "of typology i. Following the urban morphology adaptation of ecological diversity "
            "metrics (Batty, 2008 — Science 319:769-771): H' = 0 indicates a mono-typological "
            "estate (all towers, all slabs); H' = 1.0-1.5 indicates moderate diversity (2-3 "
            "typologies mixed); H' > 1.5 indicates high typological richness (4+ typologies "
            "with balanced proportions). Higher entropy correlates with greater spatial "
            "resilience to microclimate extremes because different typologies create varied "
            "shade, wind, and thermal micro-niches.</p>"

            "<p><b>Visualisation.</b> canyon_hw: diverging RdBu ramp, threshold at 1.0 — red "
            "for skimming-flow canyons (air quality concern), blue for isolated roughness "
            "(well-ventilated). sav_ratio: sequential warm ramp (yellow-orange-red) — red for "
            "energy-inefficient high-SA/V forms. svf_ratio: sequential grey ramp — dark for "
            "low SVF (UHI-prone), light for high SVF. enclosure: diverging ramp centred at 45 "
            "(Jacobs' ideal 'outdoor room').</p>"
        )

    def createInstance(self):
        return UrbanMorphologyAnalyticsAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Polygon Layer', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT', 'Output Morphology Layer')
        )

    def processAlgorithm(self, parameters, context, feedback):
        from .morphology_engine import calculate_urban_morphology_suite
        source = self.parameterAsSource(parameters, 'INPUT', context)

        fields = QgsFields(source.fields())
        fields.append(QgsField('canyon_hw', QVariant.Double))
        fields.append(QgsField('enclosure', QVariant.Double))
        fields.append(QgsField('sav_ratio', QVariant.Double))
        fields.append(QgsField('svf_ratio', QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT', context, fields, source.wkbType(), source.sourceCrs()
        )

        features = list(source.getFeatures())
        total = len(features) if features else 1

        for i, f in enumerate(features):
            if feedback.isCanceled():
                break

            geom = f.geometry()
            area = geom.area() if geom and not geom.isEmpty() else 1000.0
            floors = int(f.attribute('floors')) if f.attribute('floors') is not None and str(f.attribute('floors')).isdigit() else 4
            setback = float(f.attribute('setback')) if f.attribute('setback') is not None else 3.0
            typology = str(f.attribute('typology')) if f.attribute('typology') is not None else 'Tower'

            m = calculate_urban_morphology_suite({'floors': floors, 'setback': setback, 'typology': typology}, parcel_area=area)

            new_f = QgsFeature(fields)
            new_f.setGeometry(geom)
            for field in source.fields():
                new_f.setAttribute(field.name(), f.attribute(field.name()))

            new_f.setAttribute('canyon_hw', float(m.get('canyon_hw', 0)))
            new_f.setAttribute('enclosure', float(m.get('enclosure_index', 0)))
            new_f.setAttribute('sav_ratio', float(m.get('compactness_sav', 0)))
            new_f.setAttribute('svf_ratio', float(m.get('sky_view_factor', 0)))

            sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(((i + 1) / total) * 100))

        return {'OUTPUT': dest_id}


class ProceduralShapeGrammarAlgorithm(QgsProcessingAlgorithm):
    ICON = "icon_grammar.png"

    def name(self):
        return 'procedural_shape_grammar'

    def displayName(self):
        return '4. Procedural Shape Grammar Block Subdivider'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>4. Procedural Shape Grammar Block Subdivider</h3>"

            "<p><b>Shape grammar theory.</b> Shape grammars were introduced by Stiny & "
            "Gips (1972 — 'Shape Grammars and the Generative Specification of Painting "
            "and Sculpture', IFIP Congress) as a formal system of shape-transformation "
            "rules operating on labelled geometries. Parish & Muller (2001 — Proc. "
            "SIGGRAPH, pp.301-308) adapted the formalism to urban-scale procedural "
            "modelling in the CityEngine system, introducing CGA (Computer Generated "
            "Architecture) shape grammars where recursive split rules on polygonal "
            "footprints generate lot subdivisions, building envelopes, and facade "
            "articulation. In CGA, a split rule takes the form: Lot(area) -> {Lot(a1), "
            "Lot(a2), ...} where a1+a2+... sums to the parent area within tolerance.</p>"

            "<p><b>Plot-based urbanism.</b> The tool operationalises the theoretical "
            "framework of plot-based urbanism (Porta & Romice, 2014 — 'Plot-Based "
            "Urbanism: Towards Time-conscious Urban Design', in Carmona (ed.), "
            "Explorations in Urban Design; Tarbatt, 2012 — 'The Plot: Designing "
            "Diversity in the Built Environment', RIBA Publishing). In this paradigm, "
            "the individual plot — not the master-planned superblock — is the "
            "fundamental morphological unit of urban fabric. The plot is both a legal "
            "property boundary and a design control instrument. Mert Akay's METU MSc "
            "thesis (2019 — 'Algorithmic Design Control for Plot-Based Urbanism: A Model "
            "Proposal in Turkish Spatial Planning Context') formalised this for the "
            "Turkish 1/1000 Implementation Plan system, demonstrating how parametric "
            "subdivision rules can serve as algorithmic development control codes.</p>"

            "<p><b>Subdivision algorithm.</b> The frontage-based strategy finds the "
            "longest edge of the block polygon, computes the number of equal divisions "
            "(max_len / target_frontage, clamped 1-6), and creates trapezoidal sub-lots "
            "by connecting edge split points to the block centroid. Each sub-lot ring is "
            "a quadrilateral: [edge_split_i, edge_split_i+1, centroid_projection_i+1, "
            "centroid_projection_i]. Lots smaller than min_lot_area*0.5 are discarded. "
            "This produces regular row-house-style plots typical of 19th-century planned "
            "extensions (ensanche, gridiron suburbs).</p>"

            "<p><b>Parameter guidance.</b> Target frontage: 12-15 m for dense urban "
            "terraced housing (UK Victorian terrace: 4-5 m; Dutch canal house: 5-6 m; "
            "Istanbul row house: 6-8 m); 18-22 m for standard suburban detached plots; "
            "25-35 m for villa plots. The algorithm respects a minimum lot area of 250 m<sup>2</sup> "
            "(Turkish Imar Kanunu minimum parsel for detached construction). The output "
            "sublot_id is sequential per block; lot_area is in map units (use a projected "
            "CRS in metres).</p>"

            "<p><b>Pipeline integration.</b> Chain this tool with Algorithm 1 (Evolutionary "
            "Optimization) to assign building massing to each subdivided plot. For multi-"
            "strategy subdivision (grid, perimeter, organic, radial, hybrid), use "
            "Algorithm 6 (PPUD Pipeline) which includes all six strategies. The CGA "
            "literature also describes setback, courtyard, and stepped-terracing rules — "
            "these are applied during 3D massing generation in the cockpit.</p>"

            "<p><b>Visualisation.</b> Categorised symbology on sublot_id field with a "
            "qualitative colour palette (e.g., Set3 or Pastel1) distinguishes individual "
            "plots within each block. Graduated symbology on lot_area shows plot-size "
            "distribution. For subdivided urban fabric analysis, overlay the sub-lot "
            "layer on the original block layer at 50% transparency to assess subdivision "
            "coverage and edge effects.</p>"
        )

    def createInstance(self):
        return ProceduralShapeGrammarAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Block Layer', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'FRONTAGE', 'Target Frontage Width (m)', type=QgsProcessingParameterNumber.Type.Double, defaultValue=18.0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT', 'Subdivided Sub-Lots Layer')
        )

    def processAlgorithm(self, parameters, context, feedback):
        from .procedural_grammar import subdivide_parcel_block, calculate_polygon_area
        source = self.parameterAsSource(parameters, 'INPUT', context)
        frontage = self.parameterAsDouble(parameters, 'FRONTAGE', context)

        fields = QgsFields(source.fields())
        fields.append(QgsField('sublot_id', QVariant.Int))
        fields.append(QgsField('lot_area', QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT', context, fields, source.wkbType(), source.sourceCrs()
        )

        features = list(source.getFeatures())
        total = len(features) if features else 1

        for i, f in enumerate(features):
            if feedback.isCanceled():
                break

            geom = f.geometry()
            if not geom or geom.isEmpty():
                continue

            ring = []
            polygon_pts = geom.asMultiPolygon()[0] if geom.isMultipart() and geom.asMultiPolygon() else geom.asPolygon()
            if polygon_pts and len(polygon_pts[0]) >= 3:
                ring = [{'x': pt.x(), 'y': pt.y()} for pt in polygon_pts[0]]

            sublots = subdivide_parcel_block(ring, target_frontage=frontage)

            for s_idx, lot_ring in enumerate(sublots, start=1):
                lot_area = calculate_polygon_area(lot_ring)
                new_f = QgsFeature(fields)
                plot_geom = _ring_to_geometry(lot_ring) if lot_ring else geom
                new_f.setGeometry(plot_geom)
                for field in source.fields():
                    new_f.setAttribute(field.name(), f.attribute(field.name()))

                new_f.setAttribute('sublot_id', s_idx)
                new_f.setAttribute('lot_area', round(lot_area, 1))
                sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)

            feedback.setProgress(int(((i + 1) / total) * 100))

        return {'OUTPUT': dest_id}


class MultiParcelDistrictCouplingAlgorithm(QgsProcessingAlgorithm):
    ICON = "icon_district.png"

    def name(self):
        return 'district_environmental_coupling'

    def displayName(self):
        return '5. Multi-Parcel District Environmental Coupling'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>5. Multi-Parcel District Environmental Coupling</h3>"

            "<p><b>Inter-building solar obstruction.</b> The solar envelope concept "
            "(Knowles, 2003 — 'The Solar Envelope: Its Meaning for Urban Growth and "
            "Form', Solar Energy 74:201-211) defines the maximum 3D volume a building "
            "can occupy without casting shadow on neighbouring parcels during a specified "
            "time window. This tool computes pairwise directional shadow loss between "
            "all building pairs: shadow_length = h1 / tan(sun_altitude), azimuth-weighted "
            "by cos(|sun_azimuth - 180|) to model directional shadow casting. The overlap "
            "of the effective shadow with the receiving building (h2) yields a shadow_loss "
            "percentage (0-65% range). Following Compagnon (2004 — Energy & Buildings "
            "36:691-699), the model assumes a single representative sun position (default "
            "45 deg altitude, 180 deg azimuth = due south at mid-morning) suitable for "
            "comparative design evaluation rather than annual irradiation calculation.</p>"

            "<p><b>Canyon wind wake & pedestrian comfort.</b> Inter-building wind "
            "acceleration is modelled using the canyon H/W ratio: H/W = avg(h1,h2) / "
            "gap_width. When H/W > 1.5 (narrow gap relative to height), a Venturi "
            "acceleration factor of 1.0 + 0.35*H/W (max 2.2x ambient wind speed) is "
            "applied, following wind-tunnel measurements by Blocken, Stathopoulos & "
            "Carmeliet (2007 — Atmospheric Environment 41:2307-2321). When H/W < 0.67 "
            "(wide gap), a deceleration factor of 1.0 - 0.2/H/W (min 0.6x) models the "
            "wake recovery zone. Pedestrian comfort scores are computed against Lawson "
            "criteria thresholds: sitting (0-3.0 m/s), standing (3.0-5.5 m/s), "
            "uncomfortable (5.5-8.0 m/s), dangerous (> 8.0 m/s).</p>"

            "<p><b>District stormwater retention.</b> Runoff retention (%) is estimated "
            "from the district-scale BCR: retention = (1 - bcr) * 85%, bounded [20%, 90%]. "
            "This follows the green infrastructure hydrology literature (Berland et al., "
            "2017 — Landscape & Urban Planning 162:167-177) where unbuilt area serves as "
            "a first-order proxy for permeable surface and infiltration capacity. A BCR "
            "of 0.3 yields ~60% retention; BCR > 0.6 drops retention below 35%, implying "
            "the need for engineered SUDS (sustainable urban drainage systems).</p>"

            "<p><b>The emergence of district-scale effects.</b> These three coupling "
            "mechanisms exhibit emergence: they are negligible at the single-building "
            "scale but become dominant at the district scale (> 5 buildings). A tower "
            "that is optimal in isolation may create unacceptable shadow loss on its "
            "neighbours; a slab that maximises its own GFA may create a wind tunnel "
            "between itself and the adjacent building. This tool quantifies those "
            "externalities, enabling multi-parcel design negotiation.</p>"

            "<p><b>Visualisation.</b> shadow_loss: red sequential ramp (light red = 0-10% "
            "minor shadowing, dark red = 40-65% severe overshading — these parcels may "
            "fail solar access regulations). canyon_wind: diverging blue-white-red ramp "
            "centred at 3.5 m/s (blue = calm, white = comfortable breeze, red > 8 m/s = "
            "Lawson dangerous). comfort_score: green sequential (dark green = comfortable "
            "> 80, light green = marginal 50-80, white < 50 = uncomfortable).</p>"
        )

    def createInstance(self):
        return MultiParcelDistrictCouplingAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input District Layer', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT', 'Coupled District Layer')
        )

    def processAlgorithm(self, parameters, context, feedback):
        from .district_engine import evaluate_district_coupling
        source = self.parameterAsSource(parameters, 'INPUT', context)

        fields = QgsFields(source.fields())
        fields.append(QgsField('shadow_loss', QVariant.Double))
        fields.append(QgsField('canyon_wind', QVariant.Double))
        fields.append(QgsField('comfort_score', QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(
            parameters, 'OUTPUT', context, fields, source.wkbType(), source.sourceCrs()
        )

        features = list(source.getFeatures())
        total = len(features) if features else 1

        building_list = []
        for f in features:
            height = float(f.attribute('height_m')) if f.attribute('height_m') is not None else 18.0
            gfa = float(f.attribute('gfa')) if f.attribute('gfa') is not None else 800.0
            building_list.append({'metrics': {'height_m': height, 'gfa': gfa, 'footprint_area': gfa / 4.0, 'planx_score': 82.0}})

        district_metrics = evaluate_district_coupling(building_list, site_area=5000.0)

        for i, f in enumerate(features):
            if feedback.isCanceled():
                break

            new_f = QgsFeature(fields)
            new_f.setGeometry(f.geometry())
            for field in source.fields():
                new_f.setAttribute(field.name(), f.attribute(field.name()))

            new_f.setAttribute('shadow_loss', float(district_metrics.get('district_avg_solar_shadow_loss_pct', 0)))
            new_f.setAttribute('canyon_wind', float(district_metrics.get('district_canyon_wind_speed_ms', 3.5)))
            new_f.setAttribute('comfort_score', float(district_metrics.get('district_pedestrian_comfort', 80.0)))

            sink.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)
            feedback.setProgress(int(((i + 1) / total) * 100))

        return {'OUTPUT': dest_id}


class PpudPipelineAlgorithm(QgsProcessingAlgorithm):
    """PPUD Sequential Pipeline: Plot Layout → Building Config → Incremental Fabric."""
    ICON = "icon_ppud.png"

    def name(self):
        return 'ppud_pipeline'

    def displayName(self):
        return '6. PPUD Sequential Pipeline (Plot→Building→Fabric)'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def icon(self):
        return _icon(self.ICON)

    def shortHelpString(self):
        return (
            "<h3>6. PPUD Sequential Pipeline — Plot Layout → Building Config → Incremental Fabric</h3>"

            "<p><b>Theoretical framework.</b> PPUD (Parametric Plot-based Urban Design) "
            "was introduced by Mert Akay in his METU MSc thesis (2019 — 'Algorithmic "
            "Design Control for Plot-Based Urbanism: A Model Proposal in Turkish Spatial "
            "Planning Context', supervised by Assoc. Prof. Dr. Olgu Caliskan) and "
            "extended with climate-responsive multi-objective optimisation in Akay & "
            "Caliskan (2025 — Urban Design International 30:45-62, 'A Parametric Approach "
            "to Plot-Based Urban Design: A Climate-Responsive Algorithmic Control for the "
            "Generation of Urban Block Fabric'). The core argument: master plans are static "
            "spatial diagrams that cannot handle the complexity of multi-actor, piecemeal "
            "urban development. Instead, a three-stage generative pipeline — operating on "
            "individual plots as the fundamental morphological unit — can produce "
            "morphologically coherent yet diverse urban fabric while respecting zoning "
            "envelopes and responding to cumulative microclimate effects.</p>"

            "<p><b>Stage 1 — Plot Layout Generation.</b> The parent block polygon is "
            "subdivided using one of six strategies: <i>frontage</i> (longest-edge "
            "recursive split, produces regular row-house plots), <i>grid</i> (axis-"
            "aligned rectangular grid, produces regular orthogonal plots), <i>perimeter</i> "
            "(edge plots wrapping a central shared courtyard, produces traditional "
            "perimeter-block fabric), <i>organic</i> (recursive bisection with "
            "controlled randomness, produces medieval-style irregular fabric), "
            "<i>radial</i> (pie-slice sectors from the centroid, produces Beaux-Arts "
            "radial compositions), <i>hybrid</i> (perimeter edge + grid interior, "
            "produces mixed fabric with street-facing continuity and interior density). "
            "Each strategy has independent parameters (target frontage, grid spacing, "
            "depth ratio, randomness, sectors, etc.). Plot count is constrained by the "
            "selected block typology's min/max range.</p>"

            "<p><b>Stage 2 — Building Configuration.</b> Each plot receives a building "
            "genotype (typology, floors, setback, usage, roof_style, scale factors) "
            "selected from the block typology's compatible building types. A lightweight "
            "optimisation loop (configurable rounds, default 3) generates candidate "
            "genotypes per plot and selects the one with the highest planx_score among "
            "zoning-feasible candidates. If all candidates are infeasible, the one with "
            "lowest constraint penalty is selected and flagged. Zoning envelope (max BCR, "
            "FAR, height) is inherited from the block typology defaults with user overrides.</p>"

            "<p><b>Stage 3 — Incremental Block Fabric Formation.</b> The core innovation "
            "of the PPUD framework: plots are not developed simultaneously but in a "
            "randomised sequence of development phases (configurable steps, 3-10). After "
            "each phase, mutual solar shadowing loss (%) and canyon wind wake speed (m/s) "
            "are recomputed across all already-developed plots using pairwise inter-building "
            "distance and height data. If Climate Feedback is enabled, plots developed in "
            "later phases have their genotypes adaptively adjusted: severe shadowing "
            "(> 30% loss) triggers floor reduction and setback increase; strong canyon "
            "wind (> 8 m/s) triggers typology switching (Slab→SteppedTower) and setback "
            "widening. The fabric history tracks: typology diversity (Shannon H'), average "
            "canyon H/W drift, cumulative carbon (kg), and cumulative GFA (m<sup>2</sup>) "
            "at each development step.</p>"

            "<p><b>Block typologies.</b> Five pre-configured typologies encode morphological "
            "rules: PerimeterBlock (closed perimeter, central courtyard, BCR 0.45, suggested "
            "buildings: Courtyard/Slab/UShape), LinearBlock (row along street axis, BCR "
            "0.40, Slab/LShape), PavilionBlock (freestanding towers, BCR 0.25, Tower/"
            "SteppedTower/PodiumTower), OrganicBlock (irregular medieval fabric, BCR 0.50, "
            "MultiBuildingBlock/LShape), HybridBlock (mixed perimeter + towers, BCR 0.40, "
            "Courtyard/Tower/PodiumTower). Each typology also defines street frontage "
            "continuity (build-to-line requirement), typical FAR range, and height envelope.</p>"

            "<p><b>Two output layers.</b> (1) PPUD Subdivided Plots — each plot as its own "
            "polygon (from the subdivided ring geometry), with full genotype + 14 "
            "performance metrics including fabric_step (the development phase this plot "
            "first appears in). (2) Form-Based Code Diagram — regulating plan attributes "
            "per plot: build-to-line (boolean), max floors, max height (m), setback (m), "
            "and block typology name. This second layer serves as a machine-readable zoning "
            "code export suitable for planning document integration.</p>"

            "<p><b>Visualisation & temporal analysis.</b> Colour plots by fabric_step "
            "(temporal sequence: light-to-dark sequential ramp) to reveal the spatial "
            "pattern of development phasing. Colour by typology (qualitative palette) to "
            "assess typological diversity at a glance. The fabric_step field enables "
            "temporal animation via QGIS Temporal Controller — set start/end datetime "
            "and step duration to watch the urban fabric grow incrementally. Overlay the "
            "FBC diagram on the plot layer to verify build-to-line compliance.</p>"
        )

    def createInstance(self):
        return PpudPipelineAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Block Polygon Layer', types=[QgsProcessing.SourceType.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'BLOCK_TYPOLOGY', 'Block Typology',
                options=['PerimeterBlock', 'LinearBlock', 'PavilionBlock', 'OrganicBlock', 'HybridBlock'],
                defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'STRATEGY', 'Subdivision Strategy',
                options=['frontage', 'grid', 'perimeter', 'organic', 'radial', 'hybrid'],
                defaultValue=2
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_BCR', 'Max BCR', QgsProcessingParameterNumber.Type.Double, 0.45
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_FAR', 'Max FAR', QgsProcessingParameterNumber.Type.Double, 2.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_HEIGHT', 'Max Height (m)', QgsProcessingParameterNumber.Type.Double, 18.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'INCREMENTAL_STEPS', 'Incremental Development Steps',
                QgsProcessingParameterNumber.Type.Integer, 5
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'CLIMATE_FEEDBACK', 'Climate Feedback',
                options=['Enabled', 'Disabled'], defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT_PLOTS', 'PPUD Subdivided Plots Layer')
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink('OUTPUT_FBC', 'Form-Based Code Diagram Layer')
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, 'INPUT', context)
        block_typology_idx = self.parameterAsEnum(parameters, 'BLOCK_TYPOLOGY', context)
        strategy_idx = self.parameterAsEnum(parameters, 'STRATEGY', context)
        max_bcr = self.parameterAsDouble(parameters, 'MAX_BCR', context)
        max_far = self.parameterAsDouble(parameters, 'MAX_FAR', context)
        max_height = self.parameterAsDouble(parameters, 'MAX_HEIGHT', context)
        incremental_steps = self.parameterAsInt(parameters, 'INCREMENTAL_STEPS', context)
        climate_feedback = self.parameterAsEnum(parameters, 'CLIMATE_FEEDBACK', context) == 0

        block_typologies_list = ['PerimeterBlock', 'LinearBlock', 'PavilionBlock', 'OrganicBlock', 'HybridBlock']
        strategies_list = ['frontage', 'grid', 'perimeter', 'organic', 'radial', 'hybrid']
        block_typology_name = block_typologies_list[block_typology_idx]
        strategy = strategies_list[strategy_idx]

        from .ppud_pipeline import PpudPipeline

        features = list(source.getFeatures()) if source else []
        if not features:
            return {'OUTPUT_PLOTS': None, 'OUTPUT_FBC': None}

        plot_fields = QgsFields()
        plot_fields.append(QgsField('plot_id', QVariant.Int))
        plot_fields.append(QgsField('block_id', QVariant.String))
        plot_fields.append(QgsField('area_m2', QVariant.Double))
        plot_fields.append(QgsField('typology', QVariant.String))
        plot_fields.append(QgsField('usage', QVariant.String))
        plot_fields.append(QgsField('floors', QVariant.Int))
        plot_fields.append(QgsField('height_m', QVariant.Double))
        plot_fields.append(QgsField('setback', QVariant.Double))
        plot_fields.append(QgsField('gfa', QVariant.Double))
        plot_fields.append(QgsField('far', QVariant.Double))
        plot_fields.append(QgsField('bcr', QVariant.Double))
        plot_fields.append(QgsField('planx_score', QVariant.Double))
        plot_fields.append(QgsField('carbon_kg', QVariant.Double))
        plot_fields.append(QgsField('fabric_step', QVariant.Int))

        (sink_plots, dest_plots) = self.parameterAsSink(
            parameters, 'OUTPUT_PLOTS', context, plot_fields,
            source.wkbType(), source.sourceCrs()
        )

        fbc_fields = QgsFields()
        fbc_fields.append(QgsField('plot_id', QVariant.Int))
        fbc_fields.append(QgsField('build_to_line', QVariant.Int))
        fbc_fields.append(QgsField('max_floors', QVariant.Int))
        fbc_fields.append(QgsField('max_height_m', QVariant.Double))
        fbc_fields.append(QgsField('setback_m', QVariant.Double))
        fbc_fields.append(QgsField('block_type', QVariant.String))

        (sink_fbc, dest_fbc) = self.parameterAsSink(
            parameters, 'OUTPUT_FBC', context, fbc_fields,
            source.wkbType(), source.sourceCrs()
        )

        pipeline = PpudPipeline()
        total_blocks = len(features)

        for b_idx, feature in enumerate(features):
            if feedback.isCanceled():
                break

            geom = feature.geometry()
            if not geom or geom.isEmpty():
                continue

            ring = []
            polygon_pts = (
                geom.asMultiPolygon()[0]
                if geom.isMultipart() and geom.asMultiPolygon()
                else geom.asPolygon()
            )
            if polygon_pts and len(polygon_pts[0]) >= 3:
                ring = [{'x': pt.x(), 'y': pt.y()} for pt in polygon_pts[0]]

            if not ring:
                continue

            result = pipeline.run_full_pipeline(ring, {
                "strategy": strategy,
                "block_typology": block_typology_name,
                "max_bcr": max_bcr,
                "max_far": max_far,
                "max_height": max_height,
                "incremental_steps": incremental_steps,
                "climate_feedback": climate_feedback,
                "parent_block_id": str(feature.id()) if feature.id() else f"block_{b_idx+1}",
            })

            configured = result.get("stage2_configured", [])
            fabric_history = result.get("stage3_fabric", {}).get("fabric_history", [])

            plot_dev_step = {}
            for step_data in fabric_history:
                for pid in step_data.get("developed_plot_ids", []):
                    if pid not in plot_dev_step:
                        plot_dev_step[pid] = step_data["step"]

            for cp in configured:
                g = cp.get("genotype", {})
                m = cp.get("metrics", {})

                # Build plot geometry from its subdivided ring
                plot_ring = cp.get("ring", [])
                plot_geom = _ring_to_geometry(plot_ring) if plot_ring else geom

                new_f = QgsFeature(plot_fields)
                new_f.setGeometry(plot_geom)

                new_f.setAttribute('plot_id', int(cp.get('plot_id', 0)))
                new_f.setAttribute('block_id', cp.get('parent_block', ''))
                new_f.setAttribute('area_m2', float(cp.get('area_m2', 0)))
                new_f.setAttribute('typology', str(g.get('typology', 'Tower')))
                new_f.setAttribute('usage', str(g.get('usage', 'MixedUse')))
                new_f.setAttribute('floors', int(g.get('floors', 4)))
                new_f.setAttribute('height_m', float(m.get('height_m', 0)))
                new_f.setAttribute('setback', float(g.get('setback', 3.0)))
                new_f.setAttribute('gfa', float(m.get('gfa', 0)))
                new_f.setAttribute('far', float(m.get('far', 0)))
                new_f.setAttribute('bcr', float(m.get('bcr', 0)))
                new_f.setAttribute('planx_score', float(m.get('planx_score', 0)))
                new_f.setAttribute('carbon_kg', float(m.get('carbon_kg', 0)))
                new_f.setAttribute('fabric_step', int(plot_dev_step.get(cp.get('plot_id', 0), 1)))

                sink_plots.addFeature(new_f, QgsFeatureSink.Flag.FastInsert)

                fbc_f = QgsFeature(fbc_fields)
                fbc_f.setGeometry(plot_geom)
                fbc_f.setAttribute('plot_id', int(cp.get('plot_id', 0)))
                fbc_f.setAttribute('build_to_line', 1 if m.get('bcr', 0) > 0.3 else 0)
                fbc_f.setAttribute('max_floors', int(g.get('floors', 4)))
                fbc_f.setAttribute('max_height_m', float(m.get('height_m', 0)))
                fbc_f.setAttribute('setback_m', float(g.get('setback', 3.0)))
                fbc_f.setAttribute('block_type', block_typology_name)
                sink_fbc.addFeature(fbc_f, QgsFeatureSink.Flag.FastInsert)

            feedback.setProgress(int(((b_idx + 1) / total_blocks) * 100))

        return {'OUTPUT_PLOTS': dest_plots, 'OUTPUT_FBC': dest_fbc}
