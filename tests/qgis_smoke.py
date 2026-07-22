"""Real-QGIS import/provider/dock smoke test (run via python-qgis*.bat)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from qgis.core import QgsApplication


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

    provider = ParametricProcessProvider()
    QgsApplication.processingRegistry().addProvider(provider)
    algorithms = list(provider.algorithms())
    assert len(algorithms) == 6, f"Expected 6 algorithms, got {len(algorithms)}"
    assert all(algorithm.id().startswith("parametric_process:") for algorithm in algorithms)

    dock = ParametricProcessStudioDock(None)
    assert dock.btn_workflow.text() == "Workflow Modeler"
    assert dock.tree.topLevelItemCount() > 0
    assert "evolutionary_solver" in workflow_catalog()["nodes"]
    print("QGIS_SMOKE_OK algorithms=6 workflow_nodes=9")
finally:
    if dock is not None:
        dock.close()
        dock.deleteLater()
    if provider is not None:
        QgsApplication.processingRegistry().removeProvider(provider)
    app.exitQgis()
