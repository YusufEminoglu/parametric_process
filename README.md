<div align="center">

<img src="icons/icon.png" width="96" alt="Parametric Process icon"/>

# Parametric Process

**Parametric Generative Design & Multi-Objective Urban Optimization Studio for QGIS**

[![QGIS](https://img.shields.io/badge/QGIS-3.28%2B-93b023?logo=qgis&logoColor=white)](https://plugins.qgis.org/plugins/parametric_process/)
[![Version](https://img.shields.io/github/v/tag/YusufEminoglu/parametric_process?label=version&color=blue)](https://github.com/YusufEminoglu/parametric_process/releases)
[![License](https://img.shields.io/badge/license-GPL--3.0-orange)](LICENSE)

</div>

---

## ✨ Overview

**Parametric Process** brings generative parametric design and multi-objective evolutionary optimization (NSGA-II) into QGIS. Planners can select parcel boundaries, launch the interactive 3D Web Cockpit, execute evolutionary design trade-offs (maximizing density/GFA & daylight while minimizing carbon, runoff, and zoning constraint penalties), explore Pareto-optimal solutions with Parallel Coordinates (PCP) and Radar charts, preview 3D phenotypes in real time, and write selected optimal design attributes back to QGIS vector layers.

## 🚀 Key Features

- **NSGA-II Multi-Objective Engine**: Pure Python non-dominated sorting genetic algorithm running locally with zero external dependencies.
- **Interactive 3D Web Cockpit**: Three.js procedural building massing, setback controls, animated traffic, and solar shadow orbits.
- **Pareto Analytics Dashboard**:
  - **Pareto Front Scatter Plot**: Interactive 2D trade-off visualization between any 2 objectives.
  - **Parallel Coordinate Plot (PCP)**: Multi-axis filter mapping decision variables and metrics across all solutions.
  - **Diamond / Radar Chart**: Individual phenotype performance profile across active objectives.
  - **Generation Convergence Graph**: Track population fitness evolution over generations.
- **Two-Way QGIS Sync**: Write optimal Pareto phenotype parameters (`pareto_rank`, `wallacei_id`, `gfa`, `far`, `bcr`, `height_m`, `plan_score`, `carbon`, `runoff`) directly back into QGIS layer fields.

## 📖 Quick Start

1. Load a parcel or block polygon vector layer in QGIS.
2. Click the **Parametric Process** toolbar button.
3. Select layer and click **Launch Cockpit**.
4. In the browser cockpit, switch to **🧬 Evolutionary Studio** tab, select objectives, and press **🧬 Run Evolutionary Optimization**.
5. Click any Pareto Rank 1 solution in the Scatter or PCP plot to preview its 3D phenotype model.
6. Click **⚡ Sync Pareto Solution to QGIS** to update feature attributes in QGIS.

## 📜 License & Author

GPL-3.0-or-later © [Yusuf Eminoğlu](https://github.com/YusufEminoglu)
