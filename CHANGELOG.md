# Changelog - Parametric Process

## [0.8.0] - 2026-07-21

### Added
- **Multi-Parcel District Coupling Engine (`district_engine.py`)**: Inter-building mutual solar shadow masking, wind canyon wake acceleration, and district-wide stormwater retention balancing.
- **3D WebGL Interactive Section Cutting Planes**: Dynamic clipping planes in Three.js WebGL viewport allowing real-time floor plate, courtyard, and podium inspection.
- **District Evaluation API Endpoint (`/api/district/evaluate`)**: HTTP handler returning unified multi-parcel microclimate, shadow loss, and pedestrian comfort metrics.
- **District HUD Toolbar Controls**: Section Cut and District Coupling buttons integrated into 3D Web Cockpit HUD.

## [0.7.0] - 2026-07-21

### Added
- **Procedural Urban Shape Grammar Engine (`procedural_grammar.py`)**: Block-to-parcel frontage subdivision grammar, courtyard allocation, and stepped terracing rules.
- **Urban Morphology & Topological Connectivity Suite (`morphology_engine.py`)**: Street canyon height-to-width ratio ($H/W$), Sky View Factor ($SVF$), Street Enclosure Index, Building Surface-to-Volume Compactness ($SA/V$), and Shannon Entropy typological diversity.
- **Wallacei-Grade Phenotype Genome Gallery View**: Grid view for side-by-side visual phenotype analysis, sorting, and direct 3D preview.
- **Enhanced Feature Vector Sync**: Direct QGIS 2-way sync for enclosure index, compactness SA/V, and shape grammar attributes.

## [0.6.0] - 2026-07-21

### Added
- **Pure-Python AI & Machine Learning Surrogate Engine**: Distance-weighted k-NN / Ensemble surrogate regressor for ultra-fast physics predictions (<0.1ms) with active learning uncertainty refinement.
- **CityJSON 3D Urban Digital Twin Exporter**: Native export of Pareto solution building massings into standard CityJSON 1.0/1.1 digital twin format.
- **Wavefront OBJ 3D Mesh Exporter**: Real-time browser export of 3D building massings into `.obj`/`.mtl` format for Blender, Rhino, SketchUp, and 3D printing.
- **AI Surrogate UI Toggle**: Toggle switch in Evolutionary Studio to activate/deactivate AI Surrogate Acceleration.

## [0.4.0] - 2026-07-21

### Added
- **NSGA-III Reference-Point Solver Engine**: Das & Dennis systematic reference points for Many-Objective Optimization (>4 objectives).
- **MOEA/D Decomposition Solver Engine**: Tchebycheff scalarization and Euclidean neighborhood structure for subproblem updates.
- **Adaptive Genotype Repair Engine**: Dynamic projection of building footprints and floor counts onto feasible zoning bounds during crossover and mutation.
- **Real-Time 3D Physics Heatmaps**: Sol-Air surface heatmaps (30°C to 70°C) and Solar Irradiance ramps in WebGL cockpit.
- **Animated CFD Wind Particle Stream**: Instanced vector arrows visualizing wind velocity flow, canyon acceleration, and stagnation shadows.
- **TOPSIS MCDA Ranker**: Multi-criteria decision analysis ranking Pareto front solutions based on custom objective weights.
- **Executive HTML Report Generator**: One-click export of interactive publication-ready executive summary reports with TOPSIS rank tables and KPI metrics.

## [0.2.1] - 2026-07-21

- Add elite brand icon and comprehensive showcase documentation

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
