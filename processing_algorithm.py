# -*- coding: utf-8 -*-
"""QGIS Processing Algorithms for Parametric Process.

Provides headless evolutionary optimization and multi-domain urban physics evaluation directly in QGIS Processing Toolbox.
"""
from __future__ import annotations

from qgis.core import (
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
)
from qgis.PyQt.QtCore import QVariant

from .nsga2_engine import (
    evaluate_phenotype,
    run_nsga2_optimization,
    run_spea2_optimization,
)


class ParametricOptimizationAlgorithm(QgsProcessingAlgorithm):
    def name(self):
        return 'parametric_optimization'

    def displayName(self):
        return '1. Parametric Multi-Objective Evolutionary Optimization'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def createInstance(self):
        return ParametricOptimizationAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Polygon Layer', types=[QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'POP_SIZE', 'Population Size', QgsProcessingParameterNumber.Integer, 30
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'GENERATIONS', 'Generations', QgsProcessingParameterNumber.Integer, 15
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                'ALGORITHM', 'Algorithm', options=['NSGA-II', 'SPEA-2'], defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_BCR', 'Max BCR', QgsProcessingParameterNumber.Double, 0.45
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_FAR', 'Max FAR', QgsProcessingParameterNumber.Double, 2.5
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_HEIGHT', 'Max Height', QgsProcessingParameterNumber.Double, 18.0
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

        solver_fn = run_spea2_optimization if algorithm_idx == 1 else run_nsga2_optimization
        res = solver_fn(
            parcel_area=avg_area,
            pop_size=pop_size,
            generations=generations,
            max_bcr=max_bcr,
            max_far=max_far,
            max_height=max_height,
        )

        pareto_sols = res.get('pareto_solutions', [])
        ref_geom = features[0].geometry() if features else None

        for idx, sol in enumerate(pareto_sols):
            if feedback.isCanceled():
                break

            g = sol.get('genotype', {})
            m = sol.get('metrics', {})

            new_f = QgsFeature(fields)
            if ref_geom:
                new_f.setGeometry(ref_geom)

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

            sink.addFeature(new_f, QgsFeatureSink.FastInsert)
            feedback.setProgress(int((idx + 1) / max(1, len(pareto_sols)) * 100))

        return {'OUTPUT': dest_id}


class UrbanPhysicsEvaluatorAlgorithm(QgsProcessingAlgorithm):
    def name(self):
        return 'urban_physics_evaluator'

    def displayName(self):
        return '2. Urban Physics & Microclimate Multi-Domain Evaluator'

    def group(self):
        return 'Urban Analytics'

    def groupId(self):
        return 'urban_analytics'

    def createInstance(self):
        return UrbanPhysicsEvaluatorAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Building Footprints', types=[QgsProcessing.TypeVectorPolygon]
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

            sink.addFeature(new_f, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * total))

        return {'OUTPUT': dest_id}
