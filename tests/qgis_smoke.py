"""Real-QGIS import/provider/dock smoke test (run via python-qgis*.bat)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import (
    QgsApplication, QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer,
    QgsProcessingContext, QgsProcessingFeedback,
)


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
