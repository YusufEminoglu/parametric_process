# Changelog - Parametric Process

## [0.2.0] - 2026-07-21

- WallaceiX-grade evolutionary studio upgrade with SPEA-2, K-Means clustering, streaming engine, PCP brushing, and QGIS Processing algorithms

All notable changes to the **Parametric Process** QGIS plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-21

### Added
- **Initial Release**: Parametric generative urban design suite for QGIS.
- **Embedded NSGA-II Evolutionary Solver**: Multi-objective optimization for density, GFA, PlanX Quality Score, Daylight Index, Carbon Footprint, and Stormwater Runoff.
- **Interactive Web Cockpit**: 3D Three.js scene with procedural building typologies, solar shadow animation, and traffic simulation.
- **Analytics Studio**:
  - **Pareto Front Scatter Plot**: 2D scatter visualization of Rank 1 non-dominated design solutions.
  - **Parallel Coordinate Plot (PCP)**: Multi-dimensional axis filter for decision variables and performance metrics.
  - **Diamond / Radar Chart**: Individual phenotype performance profile.
  - **Generation Convergence Graph**: Line chart tracking fitness trajectory across generations.
- **2-Way QGIS Sync**: Direct attribute write-back for optimal Pareto solution parameters (`pareto_rank`, `wallacei_id`, `gfa`, `far`, `bcr`, `height_m`, `plan_score`, `carbon`, `runoff`).
