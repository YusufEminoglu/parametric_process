"""Deterministic 400-parcel server for sustained browser acceptance testing."""
from __future__ import annotations

import json
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from parametric_process.server import ParametricProcessServer

features = []
for row in range(20):
    for column in range(20):
        x = column * 54
        y = row * 46
        feature_id = row * 20 + column + 1
        features.append({
            "type": "Feature", "id": feature_id,
            "properties": {"name": f"Block {feature_id}", "max_bcr": 0.45, "max_far": 2.5, "hmax": 24},
            "geometry": {"type": "Polygon", "coordinates": [[[x, y], [x + 42, y], [x + 42, y + 34], [x, y + 34], [x, y]]]},
        })

server = ParametricProcessServer(18101, str(ROOT / "parametric_process" / "web"))
server.update_geojson(json.dumps({"type": "FeatureCollection", "features": features}))
server.start()
running = True

def stop(_signum, _frame):
    global running
    running = False

signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
print(f"LARGE_DEMO_URL=http://127.0.0.1:{server.port}/index.html parcels={len(features)}", flush=True)
try:
    while running:
        time.sleep(0.2)
finally:
    server.stop()
