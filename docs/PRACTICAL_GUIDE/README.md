# Parametric Process Practical Guide

**Companion to the [Academic Reference Manual](../REFERENCE_MANUAL.html).**

The Reference Manual explains the theory and the literature. This guide shows
how to *drive* the plugin: every chapter is one real question, answered with
the real plugin on the real Tire İlçesi planning master.

Nothing here is a mock-up. Every map panel is a QGIS render of a layer the
plugin actually produced, every parameter panel is the literal parameter
dictionary handed to the algorithm, and every browser panel is a Playwright
capture of the plugin's own web studio — driven with the same selectors the
repository's browser acceptance tests use.

---

## 📁 Structure

```text
parametric_process/docs/PRACTICAL_GUIDE/
├── practical_guide.html            # ← interactive guide (English, browser)
├── practical_guide_static.html     # ← print/PDF guide (Turkish)
├── practical_guide_static_en.html  # ← print/PDF guide (English)
├── practical_guide_runner.py       # QGIS-side capture harness
├── serve_real_data.py              # starts the plugin's server on real data
├── capture_ui.mjs                  # Playwright capture of the web studio
├── extract_registry.py             # live Processing registry → JSON
├── build_guide.py                  # content + manifest → HTML
├── optimize_images.py              # web-sized JPEG copies
├── run_practical_guide.bat         # Windows launcher
├── manifest/
│   ├── guide_content.json          # authored copy, EN + TR, per chapter
│   ├── algorithms.json             # live registry metadata (auto-generated)
│   └── screenshots.json            # what was captured, and with which parameters
├── screenshots/
│   ├── <chapter>/<chapter>_4panel.png
│   ├── ui/                         # real browser captures
│   └── web/                        # optimised JPEG copies used by the HTML
```

---

## 🚀 Quick start

### Prerequisites

- QGIS 3.28+ (tested on 3.44 LTR and 4.2) via OSGeo4W
- Node.js with Playwright (`npm i -g playwright && npx playwright install chromium`)
- Python with Pillow for the image optimisation step

### The real data the harness uses

| Purpose | File | Contents |
|---|---|---|
| Design parcels | `PLN3113_Tire_Saha_Master_Nihai_Odev10_Birlesik.gpkg` → `PLN3113_Tire_Kadastro_Tapu_Master` | 1 362 real Tire cadastral blocks with land use, dominant building type, average floors and area |
| Zoning context | same file → `PLN3113_Tire_Ada_NIP_Master` | 1 210 real NIP lots; green space and destinations are filtered from it |
| Street network | same file → `PLN3113_Tire_Yol_Agi_Master` | 3 074 real streets with type, width and sidewalk status |
| Existing buildings | `tire_yapi_bina_taban.gpkg` | 28 442 real building footprints |

The harness looks in `~/Downloads` and `C:/Users/YE/Downloads`.

### Run

```cmd
run_practical_guide.bat                                  REM everything
run_practical_guide.bat --module parametric_optimization  REM one chapter
```

Then rebuild the HTML by hand if you only changed the copy:

```cmd
python build_guide.py
python optimize_images.py
python build_guide.py
```

---

## 📸 The 4-panel composite

Every algorithmic chapter produces the same four-panel image:

```text
┌──────────────────────┬──────────────────────┐
│ 1 · INPUT DATA       │ 2 · PARAMETERS USED  │
│ the real site        │ the exact run + how  │
│                      │ to read the result   │
├──────────────────────┼──────────────────────┤
│ 3 · RESULT           │ 4 · IN CONTEXT       │
│ what the engine made │ the result over the  │
│                      │ real street network  │
└──────────────────────┴──────────────────────┘
```

The browser chapters are captured from the running studio: the 3D cockpit,
the parcel inspector, the Evolutionary Studio, the six Pareto analytics
sub-tabs, the workflow modeler and the academic study workspace.

---

## 🧬 Chapters

| Workspace | Chapters |
|---|---|
| Getting started | The Studio dock, preparing a parcel layer for the engines |
| Evolutionary Engine | Parametric multi-objective optimization, four solvers compared on real numbers |
| Physics & Microclimate | Urban physics & microclimate evaluator, urban morphology & canyon analytics |
| Generative Geometry | Procedural shape grammar, multi-parcel district coupling, PPUD pipeline |
| Research Protocol | Academic urban design study |
| The browser studio | 3D cockpit, Evolutionary Studio & Pareto Analytics, visual rule workflow modeler, academic study workspace |

---

## 🛠 Extending the guide

### Add a chapter

1. Write a capture function in `practical_guide_runner.py` decorated with
   `@module("<id>", "<group>", "<display>", "<algo id>")`.
2. Return a dict with `inputs`, `result`, `context`, `params` and `extent`.
3. Add the copy for the chapter in `manifest/guide_content.json` under both
   `en` and `tr`.
4. Re-run the runner and `build_guide.py`.

### Add text to an existing chapter

Everything the reader sees lives in `manifest/guide_content.json`:

```json
"ppud_pipeline": {
  "group": "Generative Geometry",
  "algo": "parametric_process:ppud_pipeline",
  "en": {
    "title": "PPUD pipeline — plot, building, fabric",
    "question": "How does a block actually grow, phase by phase?",
    "what": "…",
    "steps": ["…", "…"],
    "interpret": "…",
    "trouble": ["…", "…"]
  },
  "tr": { "…": "…" }
}
```

Parameter tables are **not** authored — they are extracted from the live
Processing registry by `extract_registry.py`, so they cannot drift from the code.

---

## 📄 License

Same as Parametric Process: **GPL-3.0-or-later** © Yusuf Eminoğlu
