# Changelog - Parametric Process

## [2.0.5] - 2026-07-22

- Added default one-click workflow chaining: palette selection now adds, selects, and connects a component in one action while manual ports remain available.
- Replaced the four-card quick help with a searchable ten-section Turkish analytical guide covering data preparation, node semantics, solver calibration, Pareto/PCP/TOPSIS interpretation, decision governance, improvement loops, QGIS sync, and auditability.
- Added a standalone Turkish user guide for project handover and reproducible decision records.

## [2.0.4] - 2026-07-22

- Fixed an infinite loading screen in both 3D Cockpit and Workflow Modeler by serving all top-level web source assets from the local plugin server.

## [2.0.3] - 2026-07-22

- Added a Grasshopper-style visual Workflow Modeler with draggable rule components, typed inspectors, connection validation, JSON import/export, browser-profile persistence, execution logs, 3D preview, and reviewed QGIS synchronization.
- Added a safe DAG runtime for live QGIS inputs, zoning envelopes, shape grammar subdivision, PPUD fabric generation, NSGA-II/SPEA-2/NSGA-III/MOEA-D, district physics, TOPSIS ranking, solution selection, and GIS output.
- Fixed first-click dock visibility, stopped-run reporting, non-functional phenotype preview, server cleanup on export failure, and stale UI version labels.
- Isolated solver random state per worker thread, added deterministic workflow seeds and bounded server requests, and paused WebGL rendering while the workflow editor or browser tab is inactive.

## [2.0.2] - 2026-07-22

- Parametric Process Studio v2.0.2 Release: Roll back prototype Urban Mobility flow to backlog while preserving IDW Spatial Kernel and Asphalt (+18.5°C) vs Park (-8.5°C) thermal physics

## [2.0.1] - 2026-07-22

- Parametric Process Studio v2.0.1 Release: Animated Urban Mobility Traffic flow (cars, buses, cyclists) and distinct Asphalt (+18.5°C) vs Park/Tree (-8.5°C) surface thermal physics

## [2.0.0] - 2026-07-22

- Parametric Process Studio v2.0.0 Release: Inverse Distance Weighting (IDW) Kernel Interpolation Engine with 1-meter height sensitivity across all heatmaps

## [1.9.9] - 2026-07-22

- Parametric Process Studio v1.9.9 Release: Re-architected Heatmap Legend directly into the Left Tool Drawer to eliminate 3D viewport overlaps

## [1.9.8] - 2026-07-22

- Parametric Process Studio v1.9.8 Release: Fix targetCenter centroid calculation in 1.85m Human POV camera handler

## [1.9.7] - 2026-07-22

- Parametric Process Studio v1.9.7 Release: Sky View Factor (SVF) visualizer, 1.85m human eye-level POV camera, UHI & vegetation canopy cooling simulation, and streamlined aerodynamic wind flows

## [1.9.6] - 2026-07-22

- Parametric Process Studio v1.9.6 Release: Clean plugin scope separation and title alignment (Parametric Process Studio)

## [1.9.5] - 2026-07-22

- Parametric Process Studio v1.9.5 Release: High-contrast typography fix for Heatmap mode dropdowns, Design Parameters dropdowns, and bottom city scorecard stats banner

## [1.9.4] - 2026-07-22

- Parametric Process Studio v1.9.4 Release: Rounded circular architectural icon emblem and warm porcelain academic studio palette matching 00_SAVUNMA_MERKEZI design system

## [1.9.3] - 2026-07-22

- Parametric Process Studio v1.9.3 Release: Classy mechanical architectural studio icon, soft warm classy studio web palette, 7-stop high-divergence heatmaps, and Qt6 graphics fixes

## [1.9.2] - 2026-07-22

- Parametric Process Studio v1.9.2 Release: High-resolution 3D parametric glassmorphic icon, 7-stop high-divergence spectral heatmaps, microclimate heat & CFD wind simulation, and Qt6 graphics fixes

## [1.9.1] - 2026-07-22

- Parametric Process Studio v1.9.1: 7-stop high-divergence spectral heatmaps, Sol-Air surface temp & UTCI heat stress, 3D CFD wind flow vectors, fixed pitched roof rendering, fixed sun sphere sky altitude, and Qt6 node graphics fixes

## [1.9.0] - 2026-07-21

- **Explicit Pairwise 3D Distance District Coupling**: Upgraded `evaluate_district_coupling` in `district_engine.py` to evaluate explicit 3D pairwise centroid distances for directional solar shadow masking %, wind canyon wake acceleration, and pedestrian comfort scores.
- **Bug Fix in ProceduralShapeGrammarAlgorithm**: Fixed sub-lot geometry creation in QGIS Processing Toolbox algorithm (`ProceduralShapeGrammarAlgorithm`) so output features retain their subdivided sub-lot polygon geometry instead of copying parent block bounds.
- **High-Performance Multi-Objective Optimization Engine**: Fully verified NSGA-II, SPEA-2, NSGA-III, and MOEA/D solvers with zero C/C++ external dependencies.

## [1.7.2] - 2026-07-21

- Qt6 compat: getattr-based exec/exec_ dispatch for Processing dialog

## [1.7.1] - 2026-07-21

- Qt6 enum compatibility: fully scoped QgsProcessing.SourceType, QgsFeatureSink.Flag, QgsProcessingParameterNumber.Type, QgsMapLayerProxyModel.Filter

## [1.7.0] - 2026-07-21

- Comprehensive academic shortHelpString for all 6 algorithms: literature context, formulae, parameter guidance, interpretation, visualisation recommendations

## [1.6.6] - 2026-07-21

- Use createAlgorithmDialog+exec_() for parameter dialog; fallback to Processing Toolbox menu trigger

## [1.6.5] - 2026-07-21

- Fix: broader Processing Toolbox search + trigger via Processing menu action if dock not found

## [1.6.4] - 2026-07-21

- Double-click now opens Processing Toolbox and highlights the algorithm for native dialog launch

## [1.6.3] - 2026-07-21

- Clean: dock double-click runs algorithm with defaults. Processing Toolbox for full parameter control. Crash-free.

## [1.6.2] - 2026-07-21

- Fix: auto-fill required sink params with memory: and load result layers into map. Detects sink params from algorithm definition.

## [1.6.1] - 2026-07-21

- Double-click now runs algorithm with runAndLoadResults using current layer. Removed crash-prone execAlgorithmDialog.

## [1.6.0] - 2026-07-21

- Clean stable release: removed experimental 3D-cockpit auto-launch and dialog-opening features. Algorithms run normally via Processing Toolbox. First QGIS Hub upload candidate.

## [1.5.7] - 2026-07-21

- Use QGIS native AlgorithmDialog directly (bypasses execAlgorithmDialog crash)

## [1.5.6] - 2026-07-21

- Double-click now runs algorithm with defaults via processing.runAndLoadResults (crash-free); fallback hint to Processing Toolbox

## [1.5.5] - 2026-07-21

- Fix: removed crash-prone execAlgorithmDialog; double-click now reveals Processing Toolbox with algorithm hint

## [1.5.4] - 2026-07-21

- Fix: pass parent=iface.mainWindow() to execAlgorithmDialog to prevent Windows access violation from dock context

## [1.5.3] - 2026-07-21

- Fix: revert to execAlgorithmDialog with 150ms QTimer delay to prevent crash while keeping Run button functional

## [1.5.2] - 2026-07-21

- Fix: use createAlgorithmDialog+show() instead of execAlgorithmDialog to prevent modal dialog crash from dock tree double-click

## [1.5.1] - 2026-07-21

- Fix: defer Processing dialog open via QTimer to prevent Qt access-violation crash on double-click

## [1.5.0] - 2026-07-21

- Post-algorithm 'View in 3D Cockpit' button: each of 6 algorithms now offers one-click 3D visualization of results via QGIS message bar

## [1.4.7] - 2026-07-21

- Heatmap fix: now tints 3D building massing (not just ground). CFD wind: 3-zone color groups (cyan=fast, orange=canyon, red=wake) with morphology classification.

## [1.4.6] - 2026-07-21

- Web cockpit: minimal pedestrians/cars, morphology-aware CFD wind, grouped export panel, export chip styling

## [1.4.5] - 2026-07-21

- Fix: Evolutionary Optimization now runs per input feature (each parcel gets own optimized solutions with its own geometry)

## [1.4.4] - 2026-07-21

- Fix: remove self.tr() from shortHelpString (not available on bare QgsProcessingAlgorithm)

## [1.4.3] - 2026-07-21

- PPUD per-plot geometry fix + detailed shortHelpString on all 6 algorithms (literature context, usage, reading results, visualization)

## [1.4.2] - 2026-07-21

- Per-algorithm icons in Processing Toolbox: each of 6 tools now has distinct icon in dock tree

## [1.4.1] - 2026-07-21

- Hotfix: repair 52 escaped backtick + 56 escaped dollar-sign corruptions in app.js template literals

## [1.4.0] - 2026-07-21

- PlanX-style docked Studio panel: QDockWidget with algorithm browser + cockpit launcher (replaces floating QDialog)

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
