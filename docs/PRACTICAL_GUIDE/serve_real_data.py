# -*- coding: utf-8 -*-
"""
Serve the real Parametric Process web interface on real Tire İlçesi data.

Starts the plugin's own HTTP server (``parametric_process.server``) and pushes
the real cadastral master into it, exactly the way the studio dock does when
you press "Launch 3D Cockpit". The browser then connects to
http://127.0.0.1:<port>/index.html and renders the actual plugin UI.

Run:
    C:\\OSGeo4W\\bin\\python-qgis-ltr.bat serve_real_data.py --port 18111
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from contextlib import suppress
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent.parent
REPO_ROOT = PLUGIN_ROOT.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from qgis.core import QgsApplication  # noqa: E402

qgs = QgsApplication([], True)
qgs.initQgis()

import qgis  # noqa: E402

for _plugins_dir in (
    os.path.abspath(os.path.join(os.path.dirname(qgis.__file__), "..", "plugins")),
    "/usr/share/qgis/python/plugins",
):
    if os.path.isdir(os.path.join(_plugins_dir, "processing")):
        if _plugins_dir in sys.path:
            sys.path.remove(_plugins_dir)
        sys.path.insert(0, _plugins_dir)
        break

from qgis.core import QgsJsonExporter, QgsVectorLayer  # noqa: E402

from parametric_process.server import ParametricProcessServer  # noqa: E402

WEB_DIR = PLUGIN_ROOT / "web"
MASTER = "PLN3113_Tire_Saha_Master_Nihai_Odev10_Birlesik.gpkg"


def find_master():
    for root in (Path.home() / "Downloads", Path("C:/Users/YE/Downloads")):
        candidate = root / MASTER
        if candidate.exists():
            return candidate
    return None


def build_geojson(limit: int | None = None) -> str:
    """Export the real cadastral blocks with the attributes the cockpit reads."""
    master = find_master()
    if master is None:
        raise SystemExit(f"planning master not found: {MASTER}")

    layer = QgsVectorLayer(
        f"{master}|layername=PLN3113_Tire_Kadastro_Tapu_Master", "ada", "ogr")
    if not layer.isValid():
        raise SystemExit("could not open the cadastral master")

    exporter = QgsJsonExporter(layer)
    exporter.setPrecision(3)
    exporter.setIncludeAttributes(True)
    # Export in the layer's own CRS, exactly as the studio dock does. The
    # GeoJSON exporter defaults to WGS84, which would both misplace the
    # scene (the cockpit renders planar metres) and collapse small parcels
    # into degenerate rings at 3-decimal degree precision.
    exporter.setDestinationCrs(layer.crs())
    features = list(layer.getFeatures())
    if limit:
        features = features[:limit]
    payload = json.loads(exporter.exportFeatures(features))

    # The cockpit reads the design envelope from the feature attributes.
    for feature in payload.get("features", []):
        props = feature.setdefault("properties", {})
        props.setdefault("name", props.get("adano") or props.get("ada_kimlik") or "")
        props.setdefault("max_bcr", 0.45)
        props.setdefault("max_far", 2.5)
        props.setdefault("max_height", 18.0)
        props.setdefault("floors", 4)
        props.setdefault("typology", "Courtyard")
        props.setdefault("usage", "Residential")
        props.setdefault("setback", 3.0)
    payload["crs_is_geographic"] = layer.crs().isGeographic()
    return json.dumps(payload)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18111)
    ap.add_argument("--limit", type=int, default=None,
                    help="only export the first N blocks (faster cockpit start)")
    args = ap.parse_args()

    geojson = build_geojson(args.limit)
    server = ParametricProcessServer(args.port, str(WEB_DIR))
    server.update_geojson(geojson)
    server.start()
    print(f"REAL_DATA_URL=http://127.0.0.1:{server.port}/index.html", flush=True)
    print(f"features: {geojson.count('\"type\": \"Feature\"')}", flush=True)

    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while running:
            time.sleep(0.2)
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    with suppress(Exception):
        sys.stdout.reconfigure(line_buffering=True)
    raise SystemExit(main())
