# -*- coding: utf-8 -*-
"""
02CartoLab-style Practical Guide runner for **Parametric Process**.

Runs the real plugin — real Processing algorithms, the real studio dock and
the real web cockpit — in a real QGIS runtime against real urban data, and
captures publication-grade panel composites for the Practical Guide.

The data is the Tire İlçesi planning master (Tire, İzmir Province): 1 362
real cadastral blocks, 1 210 real zoning (NIP) lots and 3 074 real streets,
plus 28 442 real buildings. Nothing is synthesised.

Because the plugin works in *design* space, the harness first prepares the
raw cadastral attributes into the schema the engines read (`floors`,
`typology`, `setback`, `height_m`, `max_bcr`, `max_far`, ...). That mapping
is itself one of the guide's chapters — it is the step every user needs.

Run:
    C:\\OSGeo4W\\bin\\python-qgis-ltr.bat docs\\PRACTICAL_GUIDE\\practical_guide_runner.py --all
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from contextlib import suppress
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

with suppress(Exception):
    sys.stdout.reconfigure(line_buffering=True)

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent.parent
REPO_ROOT = PLUGIN_ROOT.parent
SHOTS = HERE / "screenshots"
MANIFEST = HERE / "manifest"

# ── QGIS bootstrap ──────────────────────────────────────────────────────────
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

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Headless OSGeo4W does not always discover system fonts — without this the
# panel labels render as empty boxes.
from qgis.PyQt.QtGui import QFontDatabase  # noqa: E402

for _font_root in (Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts",
                   Path("/usr/share/fonts/truetype/dejavu")):
    for _font_name in ("segoeui.ttf", "segoeuib.ttf", "arial.ttf", "arialbd.ttf",
                       "consola.ttf", "DejaVuSans.ttf"):
        _fp = _font_root / _font_name
        if _fp.exists():
            QFontDatabase.addApplicationFont(str(_fp))

from qgis.PyQt.QtCore import QRectF, QSize, Qt, QVariant  # noqa: E402
from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter, QPen  # noqa: E402
from qgis.core import (  # noqa: E402
    QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsGeometry,
    QgsMapRendererParallelJob, QgsMapSettings, QgsProcessingContext,
    QgsProcessingFeedback, QgsProcessingUtils, QgsProject, QgsRectangle,
    QgsVectorLayer,
)

import processing  # noqa: E402
from processing.core.Processing import Processing  # noqa: E402

Processing.initialize()

from parametric_process.processing_provider import ParametricProcessProvider  # noqa: E402

_PROVIDER = ParametricProcessProvider()
QgsApplication.processingRegistry().addProvider(_PROVIDER)

print(f"QGIS {qgis.core.Qgis.QGIS_VERSION} — Parametric Process provider registered "
      f"({len(list(_PROVIDER.algorithms()))} algorithms)", flush=True)

# ── Brand palette ──────────────────────────────────────────────────────────
INK = "#0f172a"
INK_SOFT = "#334155"
PAPER = "#ffffff"
CANVAS = "#f1f5f9"
ACCENT = "#0f766e"          # the plugin's own teal
ACCENT_DARK = "#115e59"
ACCENT_LIGHT = "#5eead4"
GOLD = "#f59e0b"
HEADER_BG = "#0b1220"

PANEL_W, PANEL_H, HEADER_H = 900, 620, 58


# ══════════════════════════════════════════════════════════════════════════
#  DATA — the real Tire İlçesi planning master
# ══════════════════════════════════════════════════════════════════════════
DATA_ROOTS = [
    Path.home() / "Downloads",
    Path("C:/Users/YE/Downloads"),
]

MASTER = "PLN3113_Tire_Saha_Master_Nihai_Odev10_Birlesik.gpkg"
BUILDINGS = "tire_yapi_bina_taban.gpkg"

# Turkish planning norms used to translate the cadastral land-use class into
# the design envelope the evolutionary solver works inside.
DENSITY_NORMS = {
    "Konut (Düşük Yoğunluk)":      (0.25, 0.60, 9.0, "Courtyard"),
    "Konut (Orta Yoğunluk)":       (0.30, 1.20, 15.0, "Slab"),
    "Konut (Yüksek Yoğunluk)":     (0.40, 2.20, 24.0, "Tower"),
    "Konut (Çok Yüksek Yoğunluk)": (0.45, 3.20, 33.0, "PodiumTower"),
    "Karma Kullanım (Ticaret + Konut)": (0.40, 2.50, 24.0, "Slab"),
    "Ticaret Alanı (Çarşı / İş Merkezi)": (0.50, 3.00, 24.0, "PodiumTower"),
    "Genel Otopark Alanı":        (0.65, 0.40, 6.0, "MultiBuildingBlock"),
    "Boş Arsa / Yapılaşmamış Parsel": (0.35, 1.20, 12.0, "Courtyard"),
}
DEFAULT_NORM = (0.30, 1.00, 12.0, "Courtyard")

GREEN_FUNCTIONS = ("Park ve Çocuk Oyun Alanı", "Refüj ve Yol Boyu Yeşil Alan",
                   "Ağaçlandırılacak Alan")
DESTINATION_FUNCTIONS = ("İlkokul Alanı", "Sağlık Tesisleri Alanı",
                         "Resmi Kurum Alanı", "Ticaret Alanı",
                         "İbadet Alanı", "Eğitim Tesisleri Alanı")


def _find(name: str):
    for root in DATA_ROOTS:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


class DataBundle:
    """Real Tire planning data, prepared into the schema the plugin reads."""

    def __init__(self):
        self.notes = []
        self.master_path = _find(MASTER)
        self.buildings_path = _find(BUILDINGS)
        self.parcels = None        # prepared design parcels (plugin schema)
        self.nip = None            # zoning lots
        self.streets = None        # street network
        self.green = None          # green space polygons
        self.destinations = None   # destination polygons
        self.buildings = None      # existing building footprints
        self.raw_parcels = None    # untouched cadastral blocks

    def resolve(self) -> bool:
        if not self.master_path:
            self.notes.append("Tire planning master NOT FOUND — expected "
                              f"{MASTER} under ~/Downloads")
            return False
        self.notes.append(f"Planning master: {self.master_path.name} "
                          "(Tire İlçesi cadastral + NIP + street master)")
        if self.buildings_path:
            self.notes.append(f"Existing buildings: {self.buildings_path.name}")
        return True

    def build(self) -> None:
        master = self.master_path
        self.raw_parcels = QgsVectorLayer(
            f"{master}|layername=PLN3113_Tire_Kadastro_Tapu_Master", "ada", "ogr")
        self.nip = QgsVectorLayer(
            f"{master}|layername=PLN3113_Tire_Ada_NIP_Master", "nip", "ogr")
        self.streets = QgsVectorLayer(
            f"{master}|layername=PLN3113_Tire_Yol_Agi_Master", "yol", "ogr")
        if self.buildings_path:
            self.buildings = QgsVectorLayer(str(self.buildings_path), "binalar", "ogr")

        self.parcels = self._prepare_parcels()
        self.green = self._filter_nip(GREEN_FUNCTIONS, "yesil")
        self.destinations = self._filter_nip(DESTINATION_FUNCTIONS, "hedef")

    # ------------------------------------------------------------------
    def _prepare_parcels(self):
        """Translate the cadastral attributes into the plugin's design schema."""
        src = self.raw_parcels
        if not src.isValid():
            return None

        mem = QgsVectorLayer("MultiPolygon?crs=EPSG:5253", "Tire parseller", "memory")
        dp = mem.dataProvider()
        dp.addAttributes([
            QgsField("parcel_id", QVariant.String),
            QgsField("mahalle", QVariant.String),
            QgsField("adano", QVariant.String),
            QgsField("land_use", QVariant.String),
            QgsField("building_type", QVariant.String),
            QgsField("area_m2", QVariant.Double),
            QgsField("floors", QVariant.Int),
            QgsField("height_m", QVariant.Double),
            QgsField("typology", QVariant.String),
            QgsField("usage", QVariant.String),
            QgsField("setback", QVariant.Double),
            QgsField("roof_style", QVariant.String),
            QgsField("max_bcr", QVariant.Double),
            QgsField("max_far", QVariant.Double),
            QgsField("gfa", QVariant.Double),
        ])
        mem.updateFields()

        feats = []
        counts = {"residential": 0, "green": 0, "other": 0}
        dropped = 0
        for f in src.getFeatures():
            geom = QgsGeometry(f.geometry())
            if geom.isEmpty():
                dropped += 1
                continue
            # The cadastral master contains a handful of degenerate blocks whose
            # exterior ring encloses no area. The PPUD block splitter cannot
            # subdivide them, so they are repaired or dropped here.
            if not geom.isGeosValid():
                repaired = geom.makeValid()
                if repaired is not None and not repaired.isEmpty():
                    geom = repaired
            if geom.area() < 1.0:
                dropped += 1
                continue
            if not geom.isMultipart():
                geom.convertToMultiType()
            land_use = str(f["arazi_kullanim_tanimi"] or "")
            btype = str(f["baskin_yapi_tipi"] or "")
            area = float(f["ada_alani_m2"] or geom.area())
            floors = _safe_int(f["ortalama_kat"])
            if floors <= 0:
                floors = 4
            bcr_cap, far_cap, height_cap, typology = DENSITY_NORMS.get(
                land_use, DEFAULT_NORM)

            if land_use in GREEN_FUNCTIONS or "Park" in land_use:
                counts["green"] += 1
                usage, floors = "Green", 1
                bcr_cap, far_cap, height_cap = 0.05, 0.0, 4.5
                typology = "Courtyard"
            elif "Konut" in land_use or "Karma" in land_use:
                counts["residential"] += 1
                usage = "Residential"
            else:
                counts["other"] += 1
                usage = "Commercial" if ("Ticaret" in land_use or "Ofis" in land_use) else "Civic"

            height = round(floors * 3.0, 1)   # 3.0 m storey height
            setback = 3.0 if usage == "Residential" else 5.0
            nf = QgsFeature(mem.fields())
            nf.setGeometry(geom)
            nf.setAttributes([
                str(f["ada_kimlik"] or f["adano"] or ""),
                str(f["mahalle_adi"] or ""),
                str(f["adano"] or ""),
                land_use, btype, round(area, 1), floors, height,
                typology, usage, setback,
                "Flat" if usage == "Residential" else "Mixed",
                bcr_cap, far_cap, round(area * far_cap, 1),
            ])
            feats.append(nf)
        dp.addFeatures(feats)
        mem.updateExtents()
        self.notes.append(
            f"Prepared {len(feats)} design parcels "
            f"({counts['residential']} residential, {counts['green']} green, "
            f"{counts['other']} other) from the cadastral master; "
            f"{dropped} degenerate blocks dropped")
        return mem

    # ------------------------------------------------------------------
    def _filter_nip(self, functions, label):
        mem = QgsVectorLayer("MultiPolygon?crs=EPSG:5253", label, "memory")
        dp = mem.dataProvider()
        dp.addAttributes([
            QgsField("parcel_id", QVariant.String),
            QgsField("district", QVariant.String),
            QgsField("function", QVariant.String),
            QgsField("area_m2", QVariant.Double),
        ])
        mem.updateFields()
        feats = []
        for f in self.nip.getFeatures():
            func = str(f["plan_fonksiyon"] or "")
            if func not in functions:
                continue
            geom = QgsGeometry(f.geometry())
            if geom.isEmpty():
                continue
            if not geom.isMultipart():
                geom.convertToMultiType()
            nf = QgsFeature(mem.fields())
            nf.setGeometry(geom)
            nf.setAttributes([str(f["grup_no"] or f["paket_adi"] or ""),
                              str(f["paket_adi"] or ""), func,
                              round(geom.area(), 1)])
            feats.append(nf)
        dp.addFeatures(feats)
        mem.updateExtents()
        if feats:
            self.notes.append(f"{label}: {len(feats)} real zoning lots")
        return mem if feats else None


def _safe_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


# ══════════════════════════════════════════════════════════════════════════
#  RENDER + COMPOSITE
# ══════════════════════════════════════════════════════════════════════════
def _render(layers, extent, size, background="#ffffff"):
    valid = [l for l in layers if l is not None and l.isValid()]
    if not valid or extent is None or extent.isEmpty():
        return QImage()
    settings = QgsMapSettings()
    settings.setLayers(list(reversed(valid)))
    settings.setExtent(extent)
    settings.setOutputSize(size)
    settings.setBackgroundColor(QColor(background))
    settings.setDestinationCrs(valid[0].crs())
    settings.setOutputDpi(96)
    job = QgsMapRendererParallelJob(settings)
    job.start()
    job.waitForFinished()
    return job.renderedImage()


def _extent_of(layers, pad=1.10):
    extent = None
    for lyr in layers:
        if lyr is None or not lyr.isValid():
            continue
        e = lyr.extent()
        if e.isEmpty():
            continue
        extent = QgsRectangle(e) if extent is None else extent
        extent.combineExtentWith(e)
    if extent is None or extent.isEmpty():
        return None
    extent.scale(pad)
    return extent


def _streets_layer(data):
    """The real street network, drawn as a thin context layer."""
    if data.streets is None:
        return None
    from qgis.core import QgsLineSymbol, QgsSingleSymbolRenderer
    clone = data.streets.clone()
    sym = QgsLineSymbol.createSimple({
        "line_color": "#94a3b8", "line_width": "0.25"})
    clone.setRenderer(QgsSingleSymbolRenderer(sym))
    return clone


def _neutral(layer, color="#d7dde5"):
    clone = layer.clone()
    from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer
    sym = QgsFillSymbol.createSimple({
        "color": color, "outline_color": "#94a3b8", "outline_width": "0.2",
        "outline_style": "solid"})
    clone.setRenderer(QgsSingleSymbolRenderer(sym))
    return clone


def _band_label(painter, x, y, w, text, sub=""):
    painter.fillRect(QRectF(x, y, w, 36), QColor(ACCENT))
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
    painter.drawText(QRectF(x + 12, y + 3, w - 24, 30),
                     Qt.AlignLeft | Qt.AlignVCenter, text)
    if sub:
        painter.fillRect(QRectF(x, y + 36, w, 20), QColor(255, 255, 255, 235))
        painter.setPen(QColor(INK_SOFT))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(x + 12, y + 37, w - 24, 18),
                         Qt.AlignLeft | Qt.AlignVCenter, sub)


def _draw_map_panel(painter, x, y, w, h, layers, extent, label, sub):
    if not layers:
        painter.fillRect(QRectF(x, y, w, h), QColor(CANVAS))
        painter.setPen(QColor("#94a3b8"))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, "no layer")
    else:
        img = _render(layers, extent, QSize(int(w), int(h)))
        if not img.isNull():
            painter.drawImage(int(x), int(y), img)
        else:
            painter.fillRect(QRectF(x, y, w, h), QColor(CANVAS))
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, "render unavailable")
    _band_label(painter, x, y, w, label, sub)


def _draw_params_panel(painter, x, y, w, h, title, sub, param_text, notes=""):
    painter.fillRect(QRectF(x, y, w, h), QColor("#fbfbfd"))
    margin = 18
    body_top = y + 72
    notes_h = min(190.0, h * 0.34) if notes else 0
    params_h = (h - (body_top - y) - 18) - (notes_h + 14 if notes else 0)

    painter.setPen(QPen(QColor(ACCENT_LIGHT), 1.4))
    painter.drawRect(QRectF(x + margin, body_top, w - 2 * margin, params_h))
    painter.setPen(QColor(INK))
    painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
    painter.drawText(int(x + margin + 10), int(body_top + 18), title)
    painter.setFont(QFont("Consolas", 8))
    painter.setPen(QColor(INK_SOFT))
    yy = body_top + 36
    for line in param_text.splitlines()[:30]:
        painter.drawText(int(x + margin + 10), int(yy), line)
        yy += 12.0

    if notes:
        ny = body_top + params_h + 14
        painter.setPen(QPen(QColor(GOLD), 1.4))
        painter.drawRect(QRectF(x + margin, ny, w - 2 * margin, notes_h))
        painter.setPen(QColor("#92400e"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(int(x + margin + 10), int(ny + 18), "READ THE OUTPUT")
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#334155"))
        ny2 = ny + 36
        for line in notes.splitlines()[:12]:
            painter.drawText(int(x + margin + 10), int(ny2), line)
            ny2 += 12.0

    _band_label(painter, x, y, w, "2 · PARAMETERS USED", sub)


def compose_4panel(module_id, display, inputs, result, context, param_text,
                   out_path, subtitle="", notes="", extent=None):
    img = QImage(QSize(PANEL_W * 2, PANEL_H * 2 + HEADER_H), QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(PAPER))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    if extent is None:
        extent = _extent_of(inputs + result + context, 1.08)

    _draw_map_panel(p, 0, HEADER_H, PANEL_W, PANEL_H, inputs, extent,
                    "1 · INPUT DATA", "the real site the engine worked on")
    _draw_params_panel(p, PANEL_W, HEADER_H, PANEL_W, PANEL_H, display, subtitle,
                       param_text, notes)
    _draw_map_panel(p, 0, HEADER_H + PANEL_H, PANEL_W, PANEL_H, result, extent,
                    "3 · RESULT", "what the engine produced")
    _draw_map_panel(p, PANEL_W, HEADER_H + PANEL_H, PANEL_W, PANEL_H, context, extent,
                    "4 · IN CONTEXT", "the result over the real site")

    p.fillRect(QRectF(0, 0, PANEL_W * 2, HEADER_H), QColor(HEADER_BG))
    p.setPen(QColor(ACCENT_LIGHT))
    p.setFont(QFont("Segoe UI", 15, QFont.Bold))
    p.drawText(18, 30, f"Parametric Process — {display}")
    p.setPen(QColor("#94a3b8"))
    p.setFont(QFont("Segoe UI", 9))
    p.drawText(18, 47, f"{module_id}  ·  real QGIS {qgis.core.Qgis.QGIS_VERSION} run  ·  "
                       f"real Tire İlçesi planning data, no mock-ups")
    p.end()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG")
    return out_path


# ══════════════════════════════════════════════════════════════════════════
#  ALGORITHM RUNS
# ══════════════════════════════════════════════════════════════════════════
def run_algo(algo_id, params):
    ctx = QgsProcessingContext()
    ctx.setProject(QgsProject.instance())
    algo = QgsApplication.processingRegistry().algorithmById(algo_id)
    res = processing.run(algo_id, params, context=ctx, feedback=QgsProcessingFeedback())
    outputs = {}
    for key, value in res.items():
        layer = None
        if isinstance(value, str):
            layer = QgsProcessingUtils.mapLayerFromString(value, ctx)
            if layer is None:
                matches = QgsProject.instance().mapLayersByName(value.replace("memory:", ""))
                if matches:
                    layer = matches[0]
        if layer is None and hasattr(value, "isValid"):
            layer = value
        outputs[key] = layer if layer is not None else value
    return outputs


def fmt_params(params, skip=("OUTPUT", "OUTPUT_PLOTS", "OUTPUT_FBC")):
    lines = []
    for k, v in params.items():
        if k in skip:
            continue
        if isinstance(v, str) and len(v) > 40:
            v = "…" + v[-38:]
        if hasattr(v, "name"):
            v = v.name()
        lines.append(f"{k:<16} = {v}")
    return "\n".join(lines) if lines else "(algorithm defaults)"


MODULES = []
NOTES = {}


def module(module_id, group, display, algo_id=None):
    def deco(fn):
        MODULES.append({"id": module_id, "group": group, "display": display,
                        "algo_id": algo_id, "fn": fn})
        return fn
    return deco


@module("parametric_optimization", "Evolutionary Engine",
        "Parametric Multi-Objective Optimization", "parametric_process:parametric_optimization")
def run_optimization(data):
    params = {
        "INPUT": data.parcels, "POP_SIZE": 40, "GENERATIONS": 12, "ALGORITHM": 0,
        "MAX_BCR": 0.45, "MAX_FAR": 2.5, "MAX_HEIGHT": 18.0, "SEED": 42,
        "OUTPUT": "memory:",
    }
    out = run_algo("parametric_process:parametric_optimization", params)
    result = out.get("OUTPUT")
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [result],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), result],
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


def _solver_stats(layer):
    """Summarise a solver output with the metrics the engines actually write."""
    if layer is None:
        return "n/a"
    names = layer.fields().names()
    rows = list(layer.getFeatures())
    n = len(rows)
    if not n:
        return "no designs"
    sums = {k: 0.0 for k in ("plan_score", "pop_est", "carbon", "utci_score", "canyon_hw")}
    counts = {k: 0 for k in sums}
    rank1 = 0
    for f in rows:
        if "pareto_rank" in names:
            with suppress(Exception):
                if int(f["pareto_rank"]) == 1:
                    rank1 += 1
        for key in sums:
            if key in names:
                with suppress(Exception):
                    sums[key] += float(f[key] or 0)
                    counts[key] += 1

    def mean(key):
        return sums[key] / counts[key] if counts[key] else 0.0

    return (f"designs={n}  rank-1={rank1}  "
            f"score={mean('plan_score'):.1f}  pop={mean('pop_est'):,.0f}  "
            f"CO2={mean('carbon'):,.0f} kg  UTCI={mean('utci_score'):.1f}  "
            f"canyon H/W={mean('canyon_hw'):.2f}")


@module("algorithm_compare", "Evolutionary Engine",
        "NSGA-II vs SPEA-2 vs NSGA-III vs MOEA/D", "parametric_process:parametric_optimization")
def run_algorithm_compare(data):
    """Same seed, same site, four solvers — compared on their real numbers."""
    texts = []
    layers = []
    for idx, name in enumerate(["NSGA-II", "SPEA-2", "NSGA-III", "MOEA/D"]):
        params = {
            "INPUT": data.parcels, "POP_SIZE": 30, "GENERATIONS": 8, "ALGORITHM": idx,
            "MAX_BCR": 0.45, "MAX_FAR": 2.5, "MAX_HEIGHT": 18.0, "SEED": 42,
            "OUTPUT": "memory:",
        }
        out = run_algo("parametric_process:parametric_optimization", params)
        layer = out.get("OUTPUT")
        if layer is not None:
            layers.append(layer)
        texts.append(f"{name:<10} {_solver_stats(layer)}")
    if not layers:
        return None
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [layers[0]],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), layers[-1]],
        "params": ("Same site, same seed 42, POP 30 x 8 generations.\n"
                   "Each solver proposes a different design set for the same\n"
                   "1 362 real Tire blocks. Compare the numbers:\n\n"
                   + "\n".join(texts)),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("prepare_input", "Getting started",
        "Preparing a parcel layer for the engines")
def run_prepare_input(data):
    """The design envelope the engines read, derived from the real cadastre."""
    from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory
    layer = data.parcels
    if layer is None:
        return None
    names = layer.fields().names()

    groups = {}
    for f in layer.getFeatures():
        key = str(f["typology"])
        groups.setdefault(key, []).append(f)
    colours = ["#0d9488", "#14b8a6", "#f59e0b", "#8b5cf6", "#ef4444",
               "#22c55e", "#3b82f6", "#a855f7"]
    categories = []
    for i, (key, feats) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
        from qgis.core import QgsFillSymbol
        sym = QgsFillSymbol.createSimple({
            "color": colours[i % len(colours)],
            "outline_color": "#ffffff", "outline_width": "0.1"})
        categories.append(QgsRendererCategory(key, sym, f"{key} ({len(feats)})"))
    styled = layer.clone()
    styled.setRenderer(QgsCategorizedSymbolRenderer("typology", categories))

    schema = "\n".join(f"{n:<14} {t}" for n, t in zip(names, [f.typeName() for f in layer.fields()]))
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [styled],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), styled],
        "params": ("Derived from the Tire cadastral master (1 362 real ada).\n"
                   "The engines read this schema:\n\n" + schema),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("urban_physics", "Physics & Microclimate",
        "Urban Physics & Microclimate Evaluator", "parametric_process:urban_physics_evaluator")
def run_physics(data):
    params = {"INPUT": data.parcels, "OUTPUT": "memory:"}
    out = run_algo("parametric_process:urban_physics_evaluator", params)
    result = out.get("OUTPUT")
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [result],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), result],
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("urban_morphology", "Physics & Microclimate",
        "Urban Morphology & Canyon Analytics", "parametric_process:urban_morphology_analytics")
def run_morphology(data):
    params = {"INPUT": data.parcels, "OUTPUT": "memory:"}
    out = run_algo("parametric_process:urban_morphology_analytics", params)
    result = out.get("OUTPUT")
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [result],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), result],
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("shape_grammar", "Generative Geometry",
        "Procedural Shape Grammar Block Subdivider",
        "parametric_process:procedural_shape_grammar")
def run_shape_grammar(data):
    params = {"INPUT": data.parcels, "FRONTAGE": 18.0, "OUTPUT": "memory:"}
    out = run_algo("parametric_process:procedural_shape_grammar", params)
    result = out.get("OUTPUT")
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [result],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), result],
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("district_coupling", "Generative Geometry",
        "Multi-Parcel District Environmental Coupling",
        "parametric_process:district_environmental_coupling")
def run_district(data):
    params = {"INPUT": data.parcels, "OUTPUT": "memory:"}
    out = run_algo("parametric_process:district_environmental_coupling", params)
    result = out.get("OUTPUT")
    return {
        "inputs": [_neutral(data.parcels)],
        "result": [result],
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data), result],
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("ppud_pipeline", "Generative Geometry",
        "PPUD Sequential Pipeline (Plot → Building → Fabric)",
        "parametric_process:ppud_pipeline")
def run_ppud(data):
    params = {
        "INPUT": data.parcels, "BLOCK_TYPOLOGY": 0, "STRATEGY": 2,
        "MAX_BCR": 0.45, "MAX_FAR": 2.0, "MAX_HEIGHT": 18.0,
        "INCREMENTAL_STEPS": 5, "CLIMATE_FEEDBACK": 0,
        "OUTPUT_PLOTS": "memory:", "OUTPUT_FBC": "memory:",
    }
    out = run_algo("parametric_process:ppud_pipeline", params)
    plots = out.get("OUTPUT_PLOTS")
    fbc = out.get("OUTPUT_FBC")
    result = [lyr for lyr in (plots, fbc) if lyr is not None]
    return {
        "inputs": [_neutral(data.parcels)],
        "result": result,
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data)] + result,
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


@module("academic_study", "Research Protocol",
        "Academic Urban Design Study", "parametric_process:academic_urban_design_study")
def run_academic(data):
    params = {
        "SITE": data.parcels, "STREETS": data.streets,
        "DESTINATIONS": data.destinations, "GREEN_SPACE": data.green,
        "POP_SIZE": 16, "GENERATIONS": 4, "SEEDS": "42,31415",
        "MAX_BCR": 0.45, "MAX_FAR": 2.5, "MAX_HEIGHT": 18.0, "SETBACK": 3.0,
        "RAINFALL": 50.0, "CANOPY_TARGET": 0.25,
        "ALTERNATIVES": "memory:", "BUILDINGS": "memory:",
        "OPEN_SPACE": "memory:", "REJECTED": "memory:", "SUMMARY": "memory:",
    }
    out = run_algo("parametric_process:academic_urban_design_study", params)
    alts = out.get("ALTERNATIVES")
    blds = out.get("BUILDINGS")
    result = [lyr for lyr in (alts, blds) if lyr is not None]
    return {
        "inputs": [_neutral(data.parcels)],
        "result": result,
        "context": [_neutral(data.parcels, "#e8edf3"), _streets_layer(data)] + result,
        "params": fmt_params(params),
        "extent": _extent_of([data.parcels], 1.06),
    }


# ══════════════════════════════════════════════════════════════════════════
#  STUDIO DOCK (real QGIS widget tree)
# ══════════════════════════════════════════════════════════════════════════
@module("studio_dock", "Getting started", "The Parametric Process Studio dock")
def run_studio_dock(data):
    from parametric_process.studio_dock import ParametricProcessStudioDock

    project = QgsProject.instance()
    for lyr in (data.parcels, data.streets, data.nip):
        if lyr is not None and lyr.isValid():
            project.addMapLayer(lyr, False)

    class _Iface:
        def mainWindow(self):
            return None

        def mapCanvas(self):
            return None

        def layerTreeView(self):
            return None

        def messageBar(self):
            class _Bar:
                def pushWarning(self, *_a, **_k):
                    pass

                def pushCritical(self, *_a, **_k):
                    pass

                def pushInfo(self, *_a, **_k):
                    pass

                def pushSuccess(self, *_a, **_k):
                    pass
            return _Bar()

    dock = ParametricProcessStudioDock(_Iface())
    dock.resize(460, 760)
    dock.show()
    for _ in range(10):
        QgsApplication.processEvents()
    with suppress(Exception):
        idx = dock.layer_combo.findData(data.parcels.id())
        if idx >= 0:
            dock.layer_combo.setCurrentIndex(idx)
        QgsApplication.processEvents()
    for _ in range(6):
        QgsApplication.processEvents()

    out_dir = SHOTS / "studio_dock"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "studio_dock.png"
    dock.grab().save(str(p), "PNG")
    dock.close()
    return {"inputs": [], "result": [], "context": [], "params": "", "single": True,
            "layout_png": str(p.relative_to(HERE)).replace("\\", "/"), "extent": None}


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Parametric Process practical-guide capture")
    ap.add_argument("--module", action="append", default=None)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    selected = MODULES
    if args.module:
        wanted = set(args.module)
        selected = [m for m in MODULES if m["id"] in wanted]

    data = DataBundle()
    data.resolve()
    data.build()
    print("Data notes:", flush=True)
    for note in data.notes:
        print("   -", note, flush=True)
    if data.parcels is None:
        print("FATAL: no real planning master resolved.", flush=True)
        return 2

    manifest = {"generated": "", "qgis_version": qgis.core.Qgis.QGIS_VERSION,
                "data_notes": data.notes, "modules": {}}

    for spec in selected:
        mid = spec["id"]
        out_dir = SHOTS / mid
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            res = spec["fn"](data)
            if res is None:
                print(f"SKIP  {mid}: required real data unavailable", flush=True)
                continue
            entry = {"id": mid, "group": spec["group"], "display": spec["display"],
                     "algo_id": spec["algo_id"], "params": res["params"],
                     "notes": NOTES.get(mid, "")}
            if res.get("single"):
                png = HERE / res["layout_png"]
            else:
                png = out_dir / f"{mid}_4panel.png"
                compose_4panel(mid, spec["display"], res["inputs"], res["result"],
                               res["context"], res["params"], png,
                               subtitle=spec["group"], notes=NOTES.get(mid, ""),
                               extent=res.get("extent"))
            entry["screenshot"] = str(png.relative_to(HERE)).replace("\\", "/")
            entry["status"] = "ok"
            manifest["modules"][mid] = entry
            print(f"OK    {mid:<26} → {png.name}", flush=True)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            manifest["modules"][mid] = {
                "id": mid, "group": spec["group"], "display": spec["display"],
                "algo_id": spec["algo_id"], "status": "failed", "error": str(exc)}
            print(f"FAIL  {mid}: {exc}", flush=True)

    import datetime
    manifest["generated"] = datetime.datetime.now().isoformat(timespec="seconds")
    MANIFEST.mkdir(parents=True, exist_ok=True)
    out_json = MANIFEST / "screenshots.json"
    if out_json.exists():
        try:
            existing = json.loads(out_json.read_text(encoding="utf-8"))
            merged = existing.get("modules", {})
            merged.update(manifest["modules"])
            manifest["modules"] = merged
        except Exception:
            pass
    out_json.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nmanifest → {out_json}", flush=True)
    print(f"modules captured: {len(manifest['modules'])}", flush=True)
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
