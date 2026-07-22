"""Local demo server used for browser QA of the workflow modeler."""
from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parametric_process.server import ParametricProcessServer


WEB_DIR = ROOT / "parametric_process" / "web"
SAMPLE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": 7,
            "properties": {"name": "Browser QA block", "max_bcr": 0.45, "max_far": 2.5},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [60, 0], [60, 40], [0, 40], [0, 0]]],
            },
        },
        {
            "type": "Feature",
            "id": 8,
            "properties": {"name": "Second block", "max_bcr": 0.4, "max_far": 2.0},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[72, 0], [112, 0], [112, 40], [72, 40], [72, 0]]],
            },
        },
    ],
}


server = ParametricProcessServer(18100, str(WEB_DIR))
server.update_geojson(json.dumps(SAMPLE))
server.start()
running = True


def stop(_signum, _frame):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
print(f"WORKFLOW_DEMO_URL=http://127.0.0.1:{server.port}/index.html#workflow", flush=True)
try:
    while running:
        time.sleep(0.2)
finally:
    server.stop()
