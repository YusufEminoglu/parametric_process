"""Real-QGIS import/provider/dock smoke test (run via python-qgis*.bat)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    QgsApplication, QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsVectorLayer,
    QgsProcessingContext, QgsProcessingFeedback,
)
from qgis.PyQt.QtCore import QVariant


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

app = QgsApplication([], True)
app.initQgis()
provider = None
dock = None
try:
    from parametric_process.processing_provider import ParametricProcessProvider
    from parametric_process.studio_dock import ParametricProcessStudioDock
    from parametric_process.workflow_engine import workflow_catalog
    from parametric_process.external_adapter import validate_external_response

    provider = ParametricProcessProvider()
    QgsApplication.processingRegistry().addProvider(provider)
    algorithms = list(provider.algorithms())
    assert len(algorithms) == 7, f"Expected 7 algorithms, got {len(algorithms)}"
    assert all(algorithm.id().startswith("parametric_process:") for algorithm in algorithms)

    parcels = QgsVectorLayer("Polygon?crs=EPSG:32635", "academic_test_parcel", "memory")
    feature = QgsFeature()
    feature.setGeometry(QgsGeometry.fromPolygonXY([[
        QgsPointXY(500000, 4200000), QgsPointXY(500040, 4200000),
        QgsPointXY(500040, 4200030), QgsPointXY(500000, 4200030),
        QgsPointXY(500000, 4200000),
    ]]))
    parcels.dataProvider().addFeature(feature)
    algorithm = QgsApplication.processingRegistry().algorithmById(
        "parametric_process:parametric_optimization"
    ).createInstance()
    context = QgsProcessingContext()
    result, ok = algorithm.run({
        "INPUT": parcels,
        "POP_SIZE": 8,
        "GENERATIONS": 2,
        "ALGORITHM": 0,
        "MAX_BCR": 0.45,
        "MAX_FAR": 2.5,
        "MAX_HEIGHT": 18.0,
        "SEED": 1234,
        "OUTPUT": "memory:",
    }, context, QgsProcessingFeedback())
    assert ok, "Optimization Processing algorithm failed"
    output = context.getMapLayer(result["OUTPUT"])
    assert output.featureCount() > 0
    output_fields = output.fields().names()
    for required in ("source_fid", "seed", "run_id", "model_ver"):
        assert required in output_fields, f"Missing provenance field: {required}"
    first = next(output.getFeatures())
    assert first["seed"] == 1234
    assert len(first["run_id"]) == 16

    # every selectable solver runs end to end through Processing
    for algo_index, algo_name in ((1, "SPEA-2"), (2, "NSGA-III"), (3, "MOEA/D")):
        algo_context = QgsProcessingContext()
        algo_result, algo_ok = algorithm.run({
            "INPUT": parcels, "POP_SIZE": 8, "GENERATIONS": 3,
            "ALGORITHM": algo_index, "MAX_BCR": 0.45, "MAX_FAR": 2.5,
            "MAX_HEIGHT": 18.0, "SEED": 1234, "OUTPUT": "memory:",
        }, algo_context, QgsProcessingFeedback())
        assert algo_ok, f"{algo_name} Processing run failed"
        algo_layer = algo_context.getMapLayer(algo_result["OUTPUT"])
        assert algo_layer is not None and algo_layer.featureCount() > 0, f"{algo_name}: empty output"

    registry = QgsApplication.processingRegistry()

    def run_alg(alg_id, params):
        alg_context = QgsProcessingContext()
        alg_result, alg_ok = registry.algorithmById(
            f"parametric_process:{alg_id}").createInstance().run(
                params, alg_context, QgsProcessingFeedback())
        assert alg_ok, f"{alg_id} failed"
        return alg_context, alg_result

    def polygon_layer(name, rings, fields=()):
        layer = QgsVectorLayer("Polygon?crs=EPSG:32635", name, "memory")
        if fields:
            layer.dataProvider().addAttributes([QgsField(n, t) for n, t in fields])
            layer.updateFields()
        for ring, values in rings:
            feat = QgsFeature(layer.fields())
            feat.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in ring]]))
            for key, value in values.items():
                feat[key] = value
            layer.dataProvider().addFeature(feat)
        return layer

    def box(x0, y0, w, h):
        return [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h), (x0, y0)]

    # Evaluators accept a layer with none of the genotype fields (used to
    # raise KeyError) and read the genotype Algorithm 1 wrote, floor_h included.
    for alg_id in ("urban_physics_evaluator", "urban_morphology_analytics"):
        ctx, res = run_alg(alg_id, {"INPUT": parcels, "OUTPUT": "memory:"})
        assert ctx.getMapLayer(res["OUTPUT"]).featureCount() == 1, alg_id
    ctx, res = run_alg("urban_physics_evaluator", {"INPUT": output, "OUTPUT": "memory:"})
    from parametric_process.nsga2_engine import evaluate_phenotype
    for evaluated, original in zip(ctx.getMapLayer(res["OUTPUT"]).getFeatures(), output.getFeatures()):
        genotype = {
            "setback": original["setback"], "floors": original["floors"],
            "typology": original["typology"], "usage": original["usage"],
            "roof_style": original["roof_style"], "scale_x": original["scale_x"],
            "scale_y": original["scale_y"], "floor_height": original["floor_h"],
        }
        expected = evaluate_phenotype(genotype, original.geometry().area(),
                                      original["max_bcr"], original["max_far"], original["max_height"])
        assert abs(evaluated["plan_score"] - expected["planx_score"]) < 1e-6, "evaluator ignored the genotype"

    # floors stored as a real number (8.0) is 8 storeys, not the old default 4
    real_floors = polygon_layer("real_floors", [(box(0, 0, 40, 30), {"floors": 8.0, "setback": 3.0})],
                                (("floors", QVariant.Double), ("setback", QVariant.Double)))
    ctx, res = run_alg("urban_morphology_analytics", {"INPUT": real_floors, "OUTPUT": "memory:"})
    morph = next(ctx.getMapLayer(res["OUTPUT"]).getFeatures())
    assert abs(morph["canyon_hw"] - 2.0) < 1e-9, morph["canyon_hw"]

    # Shape grammar on a concave block: every sub-lot stays inside the block
    l_block = [(0, 0), (120, 0), (120, 40), (40, 40), (40, 120), (0, 120), (0, 0)]
    blocks = polygon_layer("l_block", [(l_block, {})])
    ctx, res = run_alg("procedural_shape_grammar", {"INPUT": blocks, "FRONTAGE": 18.0, "OUTPUT": "memory:"})
    lots = ctx.getMapLayer(res["OUTPUT"])
    block_geom = next(blocks.getFeatures()).geometry()
    assert lots.featureCount() > 1
    for lot in lots.getFeatures():
        outside = lot.geometry().difference(block_geom).area()
        assert outside < 1e-6, f"sub-lot reaches {outside:.1f} m2 outside its block"
        assert abs(lot["lot_area"] - lot.geometry().area()) < 0.1

    # District coupling is per building: a tall block south of a low one
    # shades it at noon; the tall one is not shaded; values differ by feature.
    district = polygon_layer("district", [
        (box(0, 0, 20, 20), {"height_m": 6.0}),
        (box(0, -45, 20, 20), {"height_m": 45.0}),
        (box(400, 0, 20, 20), {"height_m": 6.0}),
    ], (("height_m", QVariant.Double),))
    ctx, res = run_alg("district_environmental_coupling", {
        "INPUT": district, "SUN_ALTITUDE": 30.0, "SUN_AZIMUTH": 180.0,
        "WIND_SPEED": 3.5, "OUTPUT": "memory:"})
    coupled = {f.id(): f for f in ctx.getMapLayer(res["OUTPUT"]).getFeatures()}
    values = list(coupled.values())
    assert values[0]["shadow_loss"] > 0.0, values[0]["shadow_loss"]
    assert values[1]["shadow_loss"] == 0.0
    assert values[2]["shadow_loss"] == 0.0
    assert values[0]["nn_gap_m"] != values[2]["nn_gap_m"]

    from parametric_process.academic_processing import parcel_conforming_footprints
    parcel_geometry = feature.geometry()
    for typology in ("Tower", "Courtyard", "LShape", "UShape", "MultiBuildingBlock"):
        generated = parcel_conforming_footprints(parcel_geometry, 450.0, typology, 17.0, 3.0)
        assert generated, f"No geometry generated for {typology}"
        assert all(item.isGeosValid() and parcel_geometry.contains(item) for item in generated)

    academic = QgsApplication.processingRegistry().algorithmById(
        "parametric_process:academic_urban_design_study"
    ).createInstance()
    academic_context = QgsProcessingContext()
    academic_result, academic_ok = academic.run({
        "SITE": parcels,
        "POP_SIZE": 6,
        "GENERATIONS": 2,
        "SEEDS": "17,23",
        "MAX_BCR": 0.45,
        "MAX_FAR": 2.5,
        "MAX_HEIGHT": 18.0,
        "SETBACK": 3.0,
        "RAINFALL": 50.0,
        "CANOPY_TARGET": 0.25,
        "ALTERNATIVES": "memory:",
        "BUILDINGS": "memory:",
        "OPEN_SPACE": "memory:",
        "REJECTED": "memory:",
        "SUMMARY": "memory:",
    }, academic_context, QgsProcessingFeedback())
    assert academic_ok, "Academic study Processing algorithm failed"
    for output_name in ("ALTERNATIVES", "BUILDINGS", "OPEN_SPACE", "SUMMARY"):
        layer = academic_context.getMapLayer(academic_result[output_name])
        assert layer is not None and layer.featureCount() > 0, f"Empty academic output: {output_name}"

    dock = ParametricProcessStudioDock(None)
    assert dock.btn_workflow.text() == "Workflow Modeler"
    assert dock.tree.topLevelItemCount() > 0
    assert dock.btn_engine_approve.text() == "Approve executable"
    external = validate_external_response(
        {"alternatives": [{"solution_id": "a1"}]},
        {"schema": "parametric-process-engine-result/1.0", "results": [
            {"solution_id": "a1", "metrics": {"wind_speed": {"value": 2.5, "unit": "m/s"}}}
        ]},
    )
    assert external["validation_status"] == "validated"
    assert "evolutionary_solver" in workflow_catalog()["nodes"]
    print("QGIS_SMOKE_OK algorithms=7 workflow_nodes=9 academic_study=ok")
finally:
    if dock is not None:
        dock.close()
        dock.deleteLater()
    if provider is not None:
        QgsApplication.processingRegistry().removeProvider(provider)
    app.exitQgis()
