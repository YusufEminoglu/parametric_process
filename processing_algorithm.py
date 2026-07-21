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
        return self.tr(
            "<h3>Parametric Multi-Objective Evolutionary Optimization</h3>"
            "<p><b>Literature context.</b> This tool implements the NSGA-II algorithm "
            "(Deb et al., 2002), NSGA-III with Das & Dennis reference points (Deb & "
            "Jain, 2014), SPEA-2 (Zitzler et al., 2001), and MOEA/D with Tchebycheff "
            "decomposition (Zhang & Li, 2007). These are the four canonical multi-"
            "objective evolutionary algorithms used in generative urban design and "
            "parametric massing studies since the early 2000s. The constrained-"
            "dominance principle follows Deb (2000), enforcing zoning compliance "
            "(BCR, FAR, height caps) as hard feasibility constraints.</p>"
            "<p><b>Usage.</b> Provide a polygon layer of parcels/blocks. Set population "
            "size (recommended 30-100) and generations (15-50). Choose the algorithm: "
            "NSGA-II is the default all-rounder; NSGA-III handles 4+ objectives better; "
            "SPEA-2 gives a finer-grained archive; MOEA/D excels at well-distributed "
            "Pareto fronts. Max BCR/FAR/Height define the zoning envelope — solutions "
            "exceeding these are penalised via constraint violation.</p>"
            "<p><b>Reading the results.</b> The output layer contains Pareto Rank 1 "
            "solutions (non-dominated front). Each feature carries the full genotype "
            "(setback, floors, typology, usage, roof style) and 30+ physics/metrics "
            "columns (GFA, carbon, wind ventilation, UTCI score, ROI %, SVF, canyon H/W, "
            "PV yield). Sort by <i>planx_score</i> for the best-balanced design; use "
            "<i>pareto_rank</i> to filter the non-dominated set. Visualise in the 3D "
            "cockpit by launching the Studio dock panel.</p>"
        )

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
                'ALGORITHM', 'Algorithm', options=['NSGA-II', 'SPEA-2', 'NSGA-III', 'MOEA/D'], defaultValue=0
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

        solver_map = {
            0: run_nsga2_optimization,
            1: run_spea2_optimization,
            2: run_nsga3_optimization,
            3: run_moead_optimization,
        }
        solver_fn = solver_map.get(algorithm_idx, run_nsga2_optimization)
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
        return self.tr(
            "<h3>Urban Physics & Microclimate Multi-Domain Evaluator</h3>"
            "<p><b>Literature context.</b> This evaluator synthesises 15 linked "
            "microclimate and environmental physics models into a single pass. "
            "Wind ventilation uses a porosity-alignment model based on the urban "
            "canopy literature (Oke, 1988; Grimmond & Oke, 1999). Pedestrian wind "
            "comfort follows Lawson criteria (Lawson & Penwarden, 1975). Solar "
            "irradiance is latitude-adjusted (Duffie & Beckman, 2013). MRT and UTCI "
            "thermal comfort indices follow the COST Action 730 standard (Jendritzky "
            "et al., 2012; Brode et al., 2012). Life-cycle carbon assessment uses "
            "embodied + operational carbon factors per building material tier "
            "(timber/concrete/steel) adapted from the ICE database (Hammond & Jones, "
            "2008). Stormwater runoff uses the Rational Method with roof-form "
            "coefficients.</p>"
            "<p><b>Usage.</b> Input a building footprint layer that already has "
            "<i>floors</i>, <i>setback</i>, <i>typology</i>, <i>usage</i>, and "
            "<i>roof_style</i> attributes (from the Evolutionary Optimization output "
            "or manually assigned). The tool evaluates all 15 physics domains in one "
            "run — no additional parameters needed.</p>"
            "<p><b>Reading the results.</b> The enriched output layer adds columns: "
            "<i>carbon</i> (kg CO2eq total LCA), <i>wind_score</i> (0-100 ventilation), "
            "<i>solar_kwh</i> (kWh/m²/yr), <i>utci_score</i> (0-100 thermal comfort), "
            "<i>runoff</i> (m³ stormwater), <i>poll_disp</i> (0-100 pollution dispersion), "
            "<i>mrt_temp</i> (°C mean radiant temperature), <i>pv_kwh</i> (rooftop PV "
            "yield), <i>roi_yield</i> (% return), <i>svf_ratio</i> (0-1 sky view), "
            "<i>canyon_hw</i> (street canyon ratio). Use QGIS graduated symbology on "
            "<i>utci_score</i> or <i>carbon</i> for thermal/carbon hotspot maps.</p>"
        )

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
        return self.tr(
            "<h3>Urban Morphology & Canyon Analytics</h3>"
            "<p><b>Literature context.</b> This tool computes the core urban morphology "
            "indicators used in the space syntax and urban climatology traditions. "
            "Street canyon height-to-width ratio (H/W) follows the urban canopy layer "
            "parameterisation of Oke (1988) — H/W > 1.5 indicates a deep canyon with "
            "reduced turbulent mixing. Sky View Factor (SVF) estimation uses the "
            "geometric approximation from Johnson & Watson (1984), critical for urban "
            "heat island studies (Unger, 2004). Surface-to-volume compactness (SA/V) "
            "follows Ratti et al. (2005) — lower SA/V means lower heating/cooling "
            "energy demand per m². Shannon Entropy of typological diversity adapts "
            "ecological diversity indices to urban morphology (after Batty, 2008).</p>"
            "<p><b>Usage.</b> Provide a polygon layer with <i>floors</i>, <i>setback</i>, "
            "and <i>typology</i> attributes. The tool computes all four indices in one "
            "pass.</p>"
            "<p><b>Reading the results.</b> Output columns: <i>canyon_hw</i> (ratio, "
            "higher = deeper street canyons), <i>enclosure</i> (0-100 street enclosure "
            "index), <i>sav_ratio</i> (surface-to-volume, lower = more energy-compact), "
            "<i>svf_ratio</i> (0-1 sky view factor, lower = less sky visible = warmer "
            "night-time microclimate). In QGIS, use a red-blue diverging ramp on "
            "<i>canyon_hw</i>: red for H/W > 1.5 (deep canyons, potential air-quality "
            "traps), blue for H/W < 0.5 (open, well-ventilated).</p>"
        )

    def createInstance(self):
        return UrbanMorphologyAnalyticsAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Polygon Layer', types=[QgsProcessing.TypeVectorPolygon]
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

            sink.addFeature(new_f, QgsFeatureSink.FastInsert)
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
        return self.tr(
            "<h3>Procedural Shape Grammar Block Subdivider</h3>"
            "<p><b>Literature context.</b> Shape grammars for urban design originate "
            "with Stiny & Gips (1972) and were adapted to urban-scale procedural "
            "modelling by Parish & Muller (2001) in the CityEngine system. The CGA "
            "(Computer Generated Architecture) shape grammar formalises block-to-lot "
            "subdivision as recursive split rules. This tool also draws on plot-based "
            "urbanism theory (Porta & Romice, 2014; Tarbatt, 2012), where the "
            "individual plot is the fundamental unit of urban fabric formation, and "
            "on Mert Akay's METU thesis (2019) 'Algorithmic Design Control for "
            "Plot-Based Urbanism' which formalised parametric subdivision rules for "
            "the Turkish planning context.</p>"
            "<p><b>Usage.</b> Provide an urban block polygon layer. Set the target "
            "frontage width (default 18 m — typical for row housing; use 12-15 m for "
            "denser urban fabric, 22-30 m for suburban lots). Each block is subdivided "
            "along its longest edge.</p>"
            "<p><b>Reading the results.</b> Output columns: <i>sublot_id</i> (sequential "
            "plot number within the block), <i>lot_area</i> (m²). The subdivided "
            "output can be fed into the Evolutionary Optimization tool to assign "
            "building massing to each plot. For visualisation, use categorised symbology "
            "on <i>sublot_id</i> with a qualitative palette to distinguish plots within "
            "each block.</p>"
        )

    def createInstance(self):
        return ProceduralShapeGrammarAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Block Layer', types=[QgsProcessing.TypeVectorPolygon]
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'FRONTAGE', 'Target Frontage Width (m)', type=QgsProcessingParameterNumber.Double, defaultValue=18.0
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
                new_f.setGeometry(geom)
                for field in source.fields():
                    new_f.setAttribute(field.name(), f.attribute(field.name()))

                new_f.setAttribute('sublot_id', s_idx)
                new_f.setAttribute('lot_area', round(lot_area, 1))
                sink.addFeature(new_f, QgsFeatureSink.FastInsert)

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
        return self.tr(
            "<h3>Multi-Parcel District Environmental Coupling</h3>"
            "<p><b>Literature context.</b> Urban buildings do not perform in isolation "
            "— mutual solar obstruction (Knowles, 2003 'Solar Envelope'), inter-building "
            "wind canyon wake acceleration (Blocken et al., 2007; Ai & Mak, 2015), and "
            "district-scale stormwater retention (Berland et al., 2017) are all coupling "
            "effects that emerge only at the district scale. This tool operationalises "
            "these three coupling mechanisms in a single evaluator. The solar obstruction "
            "model uses directional azimuth projection (after Compagnon, 2004), the wind "
            "canyon model uses H/W-ratio acceleration factors from the street canyon "
            "literature (Oke, 1988; Vardoulakis et al., 2003).</p>"
            "<p><b>Usage.</b> Input a district layer with <i>height_m</i> and <i>gfa</i> "
            "attributes. The tool computes pairwise inter-building effects across all "
            "buildings in the district in a single pass.</p>"
            "<p><b>Reading the results.</b> Output columns: <i>shadow_loss</i> (% solar "
            "access lost due to neighbouring massing), <i>canyon_wind</i> (m/s accelerated "
            "wind speed in building gaps), <i>comfort_score</i> (0-100 pedestrian wind "
            "comfort — higher is more comfortable). Map <i>shadow_loss</i> with a red "
            "sequential ramp to identify over-shadowed parcels; map <i>canyon_wind</i> "
            "with a divergent blue-red ramp (blue = calm < 3 m/s, red = uncomfortable "
            "> 8 m/s per Lawson criteria).</p>"
        )

    def createInstance(self):
        return MultiParcelDistrictCouplingAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input District Layer', types=[QgsProcessing.TypeVectorPolygon]
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

            sink.addFeature(new_f, QgsFeatureSink.FastInsert)
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
        return self.tr(
            "<h3>PPUD Sequential Pipeline — Plot Layout → Building Config → Incremental Fabric</h3>"
            "<p><b>Literature context.</b> PPUD (Parametric Plot-based Urban Design) is "
            "a three-stage sequential framework introduced by Mert Akay in his METU MSc "
            "thesis 'Algorithmic Design Control for Plot-Based Urbanism' (2019) and "
            "extended with climate-responsive multi-objective optimisation in Akay & "
            "Caliskan (2025, <i>Urban Design International</i>). The framework bridges "
            "plot-based urbanism theory (Porta, Romice, Tarbatt, 2010-2015) with "
            "generative parametric modelling. The three stages are: (1) plot layout "
            "generation via multi-strategy block subdivision, (2) per-plot building "
            "configuration with zoning-compliant genotype optimisation, and (3) "
            "incremental block fabric formation simulating piecemeal urban development "
            "with climate feedback loops (mutual solar shadowing and wind canyon wake "
            "recalculation at each time step).</p>"
            "<p><b>Usage.</b> Provide an urban block polygon layer. Select a block "
            "typology (PerimeterBlock, LinearBlock, PavilionBlock, OrganicBlock, "
            "HybridBlock) — each prescribes a default subdivision strategy, compatible "
            "building typologies, and zoning envelope. Choose a subdivision strategy "
            "(or use the typology default). Set the zoning envelope (max BCR, FAR, "
            "height). <i>Incremental Steps</i> controls how many development phases "
            "are simulated (3-10 recommended). Enable <i>Climate Feedback</i> to let "
            "later phases adapt to cumulative shadow/wind impacts from earlier "
            "development.</p>"
            "<p><b>Reading the results.</b> Two output layers: (1) <i>PPUD Subdivided "
            "Plots</i> — each plot as an individual polygon with full genotype (typology, "
            "floors, setback, usage), performance metrics (GFA, FAR, BCR, carbon, "
            "planx_score), and <i>fabric_step</i> (which development phase the plot "
            "first appears in). (2) <i>Form-Based Code Diagram</i> — regulating plan "
            "parameters per plot (build-to-line, max floors, max height, setback). "
            "For visualisation: colour plots by <i>fabric_step</i> (temporal sequence "
            "ramp) or <i>typology</i> (qualitative palette to show typological diversity "
            "across the block). The <i>fabric_step</i> attribute enables temporal "
            "animation via QGIS Temporal Controller.</p>"
        )

    def createInstance(self):
        return PpudPipelineAlgorithm()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT', 'Input Block Polygon Layer', types=[QgsProcessing.TypeVectorPolygon]
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
                'MAX_BCR', 'Max BCR', QgsProcessingParameterNumber.Double, 0.45
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_FAR', 'Max FAR', QgsProcessingParameterNumber.Double, 2.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'MAX_HEIGHT', 'Max Height (m)', QgsProcessingParameterNumber.Double, 18.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'INCREMENTAL_STEPS', 'Incremental Development Steps',
                QgsProcessingParameterNumber.Integer, 5
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

                sink_plots.addFeature(new_f, QgsFeatureSink.FastInsert)

                fbc_f = QgsFeature(fbc_fields)
                fbc_f.setGeometry(plot_geom)
                fbc_f.setAttribute('plot_id', int(cp.get('plot_id', 0)))
                fbc_f.setAttribute('build_to_line', 1 if m.get('bcr', 0) > 0.3 else 0)
                fbc_f.setAttribute('max_floors', int(g.get('floors', 4)))
                fbc_f.setAttribute('max_height_m', float(m.get('height_m', 0)))
                fbc_f.setAttribute('setback_m', float(g.get('setback', 3.0)))
                fbc_f.setAttribute('block_type', block_typology_name)
                sink_fbc.addFeature(fbc_f, QgsFeatureSink.FastInsert)

            feedback.setProgress(int(((b_idx + 1) / total_blocks) * 100))

        return {'OUTPUT_PLOTS': dest_plots, 'OUTPUT_FBC': dest_fbc}
