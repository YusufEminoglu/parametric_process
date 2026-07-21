# Parametric Process: Generative Urban Design Studio for QGIS (v0.8.0 Showcase)

> **Parametric Process** is a standalone, GIS-native generative urban design, procedural shape grammar, microclimate physics, and multi-objective evolutionary optimization studio for QGIS.

---

## 🌟 Key Highlights & Architectural Features

- 🧬 **Multi-Objective Solvers:** NSGA-II, NSGA-III (Das & Dennis reference points), MOEA/D (Tchebycheff decomposition), and SPEA-2.
- 🤖 **Pure-Python AI Surrogate Engine:** Distance-weighted k-NN / Ensemble regressor predicting physics metrics in $<0.1\text{ms}$ with active learning uncertainty refinement.
- 📐 **Procedural Shape Grammar:** Block-to-lot subdivision, frontage lot splitting, setback terracing, and courtyard allocation rules.
- 🏢 **Urban Morphology & Connectivity Suite:** Street canyon height-to-width ratio ($H/W$), Sky View Factor ($SVF$), Street Enclosure Index, $SA/V$ Building Compactness, and Shannon Entropy typological diversity.
- 🌤️ **Real-Time 3D Physics Shaders:** Sol-Air surface heatmaps ($30^\circ\text{C} \rightarrow 70^\circ\text{C}$), Solar Irradiance ramps, animated CFD wind vector particles, and sun azimuth/shadow engine.
- 🏢 **Multi-Parcel District Coupling:** Inter-building mutual solar shadow loss, canyon wind tunnel wake acceleration, and district-wide green infrastructure stormwater balancing.
- ✂️ **3D Interactive Section Cut Planes:** Real-time Three.js WebGL clipping planes for floor plate, courtyard, and podium inspection.
- 📊 **Wallacei-Grade Analytics Studio:** 2D Pareto Front Scatter, Parallel Coordinates Plot (PCP) Brushing, Diamond Radar, K-Means Clustering, and Phenotype Genome Gallery View.
- ⚖️ **TOPSIS MCDA Ranker:** Multi-criteria decision analysis ranking Pareto solutions based on weighted user priorities.
- 📦 **3D Digital Twin Exporters:** CityJSON 1.1, Wavefront OBJ 3D Mesh, 3D GeoPackage vector layer sync, and Executive HTML Reports.

---

## 📖 Operational Workflow Summary

1. **Pre-Processing:** Load polygon parcel vector layer in QGIS (Projected CRS, e.g. EPSG:3857).
2. **Launch Cockpit:** Click Parametric Process toolbar icon -> Launch Web Cockpit.
3. **Configure & Optimize:** Select NSGA-III / MOEA/D, toggle AI Surrogate Acceleration, and click Run Optimization.
4. **Post-Processing & Decision Support:** Filter solutions via PCP brushing or TOPSIS ranker, inspect in Genome Gallery.
5. **Export & Sync:** Export CityJSON, Wavefront OBJ, or Executive HTML Report, and click Sync to QGIS to write parameters back to vector layers.
