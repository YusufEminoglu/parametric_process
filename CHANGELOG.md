# Changelog - Parametric Process

## [1.3.1] - 2026-07-21

- Fix: single toolbar icon + Processing Toolbox pattern (removed 6 redundant sub-tool icons)

## [1.3.0] - 2026-07-21

- PPUD Pipeline: 3-stage sequential urban design pipeline (Plot Layout → Building Config → Incremental Fabric), 6 subdivision strategies, 5 block typologies, form-based code export

## [1.2.0] - 2026-07-21

- v1.2.0: AI Code Review enhancements (Real Perimeter Compactness, Directional Solar Shadow Azimuth, and Typology JSON Disk Persistence)

## [1.1.0] - 2026-07-21

- v1.1.0 ULTIMATE FEATURE RELEASE: Complete 5 Processing Toolbox algorithms, Custom Typology Engine, and Morris Spatial Sensitivity Analysis

## [1.0.0] - 2026-07-21

- v1.0.0 MAJOR RELEASE: PlanX-grade multi-tool icon suite, dedicated toolbar actions, and complete academic workflow

## [1.2.0] - 2026-07-21 - AI CODE REVIEW ENHANCEMENTS

### Added & Enhanced
- **Real Geometry Perimeter Compactness (`morphology_engine.py`)**: Enhanced `calculate_compactness_sav` to evaluate real polygon perimeter input for non-square, L-shaped, and U-shaped building footprints.
- **Directional 3D Solar Azimuth Shadowing (`district_engine.py`)**: Enhanced `calculate_mutual_solar_obstruction` with `sun_azimuth_deg` projection factors.
- **JSON Disk Persistence for Custom Typologies (`typologies.py`)**: Added `save_custom_typologies_to_disk` & `load_custom_typologies_from_disk` to preserve custom typologies across QGIS sessions.

## [1.1.1] - 2026-07-21

### Added
- **Multi-Polygon Geometry Guard**: Safe multi-part polygon handling in Processing algorithms.

## [1.1.0] - 2026-07-21 - ULTIMATE FEATURE RELEASE

### Added
- **Full QGIS Processing Toolbox Suite (5 Algorithms)**: `Parametric Optimization`, `Urban Physics Evaluation`, `Urban Morphology Analytics`, `Procedural Shape Grammar Subdivider`, and `Multi-Parcel District Environmental Coupling` algorithms registered in QGIS Processing Provider.
- **Custom Typology Preset Registry Engine (`typologies.py`)**: Custom building typology editor for user-defined footprint ratios, courtyard allocations, and setback profiles.
- **Morris / Sobol Variance-based Spatial Sensitivity Analysis (`calculate_sensitivity_matrix`)**: Elementary Effects matrix computing variable-objective impact.

## [1.0.0] - 2026-07-21 - MAJOR RELEASE

### Added
- **Dedicated Sub-Tool Icon & Toolbar Suite**: Individual PNG icons (`icon_nsga3.png`, `icon_morphology.png`, `icon_grammar.png`, `icon_district.png`, `icon_cityjson.png`) and dedicated QGIS toolbar & menu entry points matching PlanX suite conventions.
- **Multi-Tool Execution Architecture**: 6 discrete action triggers for direct workflow access.

## [0.9.0] - 2026-07-21

### Added
- **PlanX-Grade Native QGIS Dialog Suite (`dialog.py`)**: Multi-tab dialog with Design Strategy Presets (Balanced, High Density, Microclimate Eco-District, Financial ROI, Procedural Courtyard), native QGIS layer selector, evolutionary solver controls (NSGA-III, MOEA/D, NSGA-II, SPEA-2), and AI Surrogate toggle.
- **Wallacei & Discover Grade Phenotype Lineage Features**: Extended evolutionary tree parameters and preset strategy profiles.

## [0.8.1] - 2026-07-21

### Added
- **Master Academic & Methodological User Guide (`GUIDE.md`)**: Comprehensive formulation of pre-processing, shape grammar, morphology metrics, microclimate thermodynamics, MOO solvers, and post-processing decision support.
- **Showcase Documentation (`SHOWCASE.md`)**: Complete architectural summary of generative urban design capabilities.

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
