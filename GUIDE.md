# Parametric Process: Academic & Methodological Master Guide (v0.8.0)

> **Author:** Yusuf Eminoğlu  
> **Affiliation:** Dokuz Eylül University, Department of Urban and Regional Planning  
> **Software Suite:** Parametric Process QGIS Plugin (v0.8.0)  
> **License:** GPL-3.0-or-later  

---

## 📖 Executive Summary & Theoretical Foundations

**Parametric Process** is a standalone, GIS-native generative urban design, procedural shape grammar, microclimate physics, and multi-objective evolutionary optimization studio developed exclusively for QGIS 3.28+ and QGIS 4.x.

It bridges spatial planning, computational urban morphology, microclimate thermodynamics, and Pareto-optimal decision theory into a unified environment—delivering Grasshopper 3D / Wallacei / CityEngine grade analytical power natively inside QGIS without requiring external proprietary CAD binaries or pip dependencies.

```
+-----------------------------------------------------------------------------------+
|                              PARAMETRIC PROCESS STUDIO                            |
+-----------------------------------------------------------------------------------+
|  1. PRE-PROCESSING    : GIS Layer Prep, CRS EPSG:3857, Polygon Cleaning           |
|  2. SHAPE GRAMMAR     : Block-to-Lot Subdivision, Footprint Setbacks & Terraces   |
|  3. MORPHOLOGY SUITE  : Canyon H/W, Enclosure Index, SA/V Compactness, Entropy    |
|  4. MICROCLIMATE PHY  : Sol-Air Temp, Solar Irradiance, CFD Wind Canyon, UTCI     |
|  5. MOO SOLVER ENGINE : NSGA-II, NSGA-III (Ref Points), MOEA/D (Decomposition)     |
|  6. AI SURROGATE ACCEL: Pure-Python k-NN / Ensemble Regressor (<0.1ms / Eval)      |
|  7. POST-PROCESSING   : TOPSIS MCDA, Wallacei Genome Matrix, 3D CityJSON/OBJ Export|
|  8. GIS SYNC          : 2-Way Vector Attribute Back-Propagation to QGIS Layers    |
+-----------------------------------------------------------------------------------+
```

---

## 1. PRE-PROCESSING WORKFLOW (GIS DATA PREPARATION)

### 1.1 Vector Layer & Coordinate Reference System (CRS) Requirements
Before launching Parametric Process, input vector layers must meet the following GIS criteria:
- **Geometry Type:** `Polygon` or `MultiPolygon` representing urban blocks, parcels, or zoning districts.
- **Coordinate Reference System (CRS):** Projective CRS measured in meters (e.g., **EPSG:3857 - WGS 84 / Pseudo-Mercator** or local UTM zones like **EPSG:32635**). *Geographic CRS (EPSG:4326 in degrees) must be reprojected.*
- **Topological Integrity:** Polygon boundaries must be valid without self-intersections or duplicate nodes. Run `QGIS Processing -> Fix Geometries` if necessary.

### 1.2 Mandatory & Optional Attribute Mapping
The engine automatically detects parcel geometry bounds. Optional vector layer attribute fields:
- `parcel_id` (String / Integer): Unique parcel identifier.
- `max_bcr` (Real): Maximum allowed Taban Alanı Katsayısı (default: 0.45).
- `max_far` (Real): Maximum allowed Kat Alanı Katsayısı (default: 2.50).
- `max_height` (Real): Maximum allowed height in meters (default: 18.0 m).
- `street_w` (Real): Adjoining street width in meters (default: 12.0 m).

---

## 2. IN-PROCESS GENERATIVE & EVOLUTIONARY WORKFLOW

### 2.1 Procedural Shape Grammar Engine (`procedural_grammar.py`)
Urban blocks are procedurally subdivided into sub-lots using perpendicular bisector cuts along frontage edges:
- **Polygon Area (Shoelace Formula):**
  $$A = \frac{1}{2} \left| \sum_{i=1}^{n-1} (x_i y_{i+1} - x_{i+1} y_i) + (x_n y_1 - x_1 y_n) \right|$$
- **Frontage Lot Subdivision:** Large blocks exceeding target frontage $L_{front} > 18\text{ m}$ are split into sub-lots $S_1, S_2, \dots, S_k$ with inward setback offsets.
- **Typological Massing Articulation:**
  - *Perimeter / Courtyard Blocks:* Internal open space ratio $OSR \ge 0.40$.
  - *Stepped Podiums:* Terraced setback steps calculated every $\lfloor \text{Floors} / 4 \rfloor$ levels.

### 2.2 Urban Morphology & Topological Metrics (`morphology_engine.py`)
- **Street Canyon Height-to-Width Ratio ($H/W$):**
  $$\text{Canyon } H/W = \frac{H_{building}}{W_{street}}$$
- **Street Enclosure Index ($E_i$):**
  $$E_i = \min\left(100, \max\left(0, \frac{H}{2 \cdot S_{setback} + 6} \times 45\right)\right)$$
- **Thermal & Volumetric Compactness Ratio ($SA/V$):**
  $$\frac{SA}{V} = \frac{A_{facade} + 2 \cdot A_{roof}}{V_{building}} = \frac{4 \cdot \sqrt{A_{fp}} \cdot H + 2 \cdot A_{fp}}{A_{fp} \cdot H}$$
- **Shannon Entropy Typological Diversity ($H_{shannon}$):**
  $$H_{shannon} = -\sum_{i=1}^{k} p_i \ln(p_i)$$

### 2.3 Microclimate Thermodynamics & CFD Wind Physics
- **Sol-Air Surface Temperature ($T_{sol-air}$):**
  $$T_{sol-air} = T_{ambient} + \frac{\alpha \cdot I_{solar} - \epsilon \cdot \Delta R}{h_c} \quad (30^\circ\text{C} \le T_{sol-air} \le 70^\circ\text{C})$$
- **CFD Wind Canyon Acceleration:**
  $$v_{canyon} = v_\infty \times \sqrt{1 + \left(\frac{H}{W}\right)^2}$$

### 2.4 Multi-Objective Evolutionary Solvers (`nsga2_engine.py`)
1. **NSGA-II:** Non-dominated Sorting & Crowding Distance Selection.
2. **NSGA-III:** Das & Dennis Systematic Reference Points on Unit Simplex for $>4$ objectives:
   $$H = \binom{M + p - 1}{p}$$
3. **MOEA/D:** Multi-Objective Evolutionary Algorithm based on Tchebycheff Decomposition:
   $$\min g^{tch}(x \mid \lambda, z^*) = \max_{1 \le j \le M} \left\{ \lambda_j \left| f_j(x) - z_j^* \right| \right\}$$
4. **Adaptive Genotype Repair:** Projects out-of-bound chromosomes back onto feasible zoning envelopes ($BCR \le max\_bcr$, $FAR \le max\_far$) before fitness assignment.

### 2.5 Pure-Python AI & Machine Learning Surrogate Acceleration
- **Surrogate Regressor (`PurePythonSurrogateModel`):** Distance-weighted $k$-NN regressor ($k=5$) predicting physics metrics in $<0.1\text{ms}$.
- **Active Learning Uncertainty Threshold:** Computes neighbor variance $\sigma(x)$. If $\sigma(x) > \text{threshold}$, triggers exact physics evaluation and updates the training memory.

---

## 3. POST-PROCESSING & DECISION SUPPORT WORKFLOW

### 3.1 Multi-Criteria TOPSIS Decision Support (`topsis_rank_solutions`)
Computes positive ($A^*$) and negative ($A^-$) ideal solutions to determine relative closeness coefficients $C_i^* \in [0, 1]$:
$$C_i^* = \frac{D_i^-}{D_i^+ + D_i^-}$$

### 3.2 3D Spatial Vector & Mesh Exporters
1. **CityJSON 3D Urban Digital Twin (`export_to_cityjson`):**
   Generates standard CityJSON 1.0/1.1 objects (`Building` -> `Solid` LoD2 geometries with attributes).
2. **Wavefront OBJ 3D Mesh (`exportWavefrontObj`):**
   Generates Wavefront `.obj` / `.mtl` mesh strings for Blender, Rhino, SketchUp, and 3D printing.
3. **3D GeoPackage Vector Sync:**
   Writes 3D polygon geometries with $Z$ coordinates (`z_min`, `z_top`, `height_m`, `bcr`, `far`, `planx_score`, `topsis_rank`) directly into QGIS vector layers.

### 3.3 Executive HTML Report Exporter
Generates standalone, publication-ready HTML reports containing KPI summary cards, TOPSIS rank tables, and microclimate performance metrics.

---

## 4. STEP-BY-STEP USER OPERATIONAL GUIDE

```
+-----------------------------------------------------------------------------------+
| STEP 1: Select Polygon Parcel Layer in QGIS Layers Panel                          |
| STEP 2: Click "Parametric Process" Icon on QGIS Toolbar                            |
| STEP 3: Click "Launch Web Cockpit" -> Browser Opens http://localhost:8080         |
| STEP 4: Select Optimization Algorithm (NSGA-II / NSGA-III / MOEA/D)               |
| STEP 5: Check "Enable AI Surrogate Model (<0.1ms Physics)"                        |
| STEP 6: Click "Run Optimization" & Watch Real-Time 3D Convergence                 |
| STEP 7: Click "Genome Gallery" or "PCP" Sub-tab to Filter Solutions              |
| STEP 8: Click "TOPSIS Rank" -> Select Top Solution                                |
| STEP 9: Click "CityJSON 3D" or "OBJ Mesh" to Export 3D Models                     |
| STEP 10: Click "Sync to QGIS" -> Attributes & 3D Geometries Write Back to Layer   |
+-----------------------------------------------------------------------------------+
```

---

## 📚 References & Academic Citations

1. Deb, K., et al. (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." *IEEE Transactions on Evolutionary Computation*, 6(2), 182-197.
2. Deb, K., & Jain, H. (2014). "An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, part I: solving problems with box constraints." *IEEE Transactions on Evolutionary Computation*, 18(4), 577-601.
3. Zhang, Q., & Li, H. (2007). "MOEA/D: A multiobjective evolutionary algorithm based on decomposition." *IEEE Transactions on Evolutionary Computation*, 11(6), 712-731.
4. Hwang, C. L., & Yoon, K. (1981). *Multiple Attribute Decision Making: Methods and Applications*. Springer-Verlag.
5. CityJSON Specification v1.1. Open Geospatial Consortium (OGC).
