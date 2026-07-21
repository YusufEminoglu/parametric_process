# Parametric Process — Generative Urban Design & Evolutionary Multi-Objective Optimization Studio

<p align="center">
  <img src="icons/icon.png" width="160" height="160" alt="Parametric Process Icon" />
</p>

<p align="center">
  <strong>Parametric Urban Massing, Microclimate Physics & WallaceiX-Grade Evolutionary Studio for QGIS</strong>
</p>

<p align="center">
  <a href="https://qgis.org"><img src="https://img.shields.io/badge/QGIS-3.28%2B%20%7C%204.x-589632.svg?logo=qgis&logoColor=white" alt="QGIS"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg" alt="License"></a>
  <a href="metadata.txt"><img src="https://img.shields.io/badge/Version-0.2.0-0f766e.svg?style=flat" alt="Version"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-Pure%20Stdlib-3776AB.svg?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/YusufEminoglu/parametric_process"><img src="https://img.shields.io/badge/Engine-NSGA--II%20%2F%20SPEA--2-10b981.svg" alt="Engine"></a>
</p>

---

## 🌟 Overview

**Parametric Process** is an elite, standalone generative urban design and multi-objective evolutionary optimization lab natively built for **QGIS**. It brings **Grasshopper WallaceiX-grade (and beyond)** evolutionary analytics, interactive 3D WebGL cockpit simulation, multi-domain microclimate physics, and bidirectional GIS vector layer synchronization directly into your spatial planning workspace.

Unlike traditional CAD-bound tools, **Parametric Process** is **GIS-native**—it operates on real spatial coordinate reference systems (CRS), real parcel boundaries, and real-world urban context while enforcing strict zoning laws (BCR, FAR, height caps) with zero third-party C/C++ dependencies.

---

## 🔥 Key Feature Highlights

### 🧬 Evolutionary Solver Suite (NSGA-II & SPEA-2)
- **NSGA-II (Elitist Non-dominated Sorting):** Fast non-dominated sorting with crowding distance archive truncation.
- **SPEA-2 (Strength Pareto Evolutionary Algorithm 2):** Fine-grained raw fitness based on dominance strength combined with $k$-th nearest neighbor density estimation.
- **Deb's Constrained Dominance Principle:** Native feasibility-first sorting rule. Infeasible design candidates are penalized according to exact constraint violation magnitudes ($BCR$, $FAR$, Height), ensuring zoning compliance.
- **Multi-Parcel Master-Plan Engine:** Optimizes heterogeneous multi-building neighborhood blocks simultaneously, evaluating site-wide density, wind corridors, and typology diversity.

### 📊 6-Subtab Pareto Analytics Studio (WallaceiX-Grade)
1. **Pareto Front Scatter (2D):** Configurable $X/Y$ metric axes, custom coloring modes (*Pareto Rank*, *K-Means Cluster*, *Generation Trajectory*), real-time 3D phenotype click-selection.
2. **Parallel Coordinates Plot (PCP):** Multi-dimensional polyline visualization with **Interactive Click-Drag Brush Filtering** across decision variables and physics metrics.
3. **Fitness Convergence & SD Trajectory:** Real-time trajectory of Min (red), Mean (yellow), and Max (green) fitness values accompanied by a shaded **Standard Deviation (SD)** variance band across generations.
4. **Diamond / Radar Fitness Profile:** Individual multi-axis polygon performance profile (GFA, Score, Wind, Solar, Air, SVF, UTCI, ROI%).
5. **K-Means Clustering Studio:** Unsupervised machine learning clustering of Pareto solutions with 2D PCA projection, automatic $K$ heuristic (Elbow method), cluster centroids, and summary statistics.
6. **Population Browser Data Table:** Sortable, filterable (*All Solutions*, *Rank 1 Only*, *Top 10%*) tabular browser with direct 3D scene preview and CSV/JSON export.

### 🔬 15 Multi-Domain Microclimate & Financial Engines
- **CFD Wind Ventilation & Pedestrian Comfort:** Lawson wind comfort criteria and directional wind flushing efficiency.
- **Solar Irradiance & Rooftop PV Energy:** Latitude-adjusted solar irradiance ($kWh/m^2/yr$) and rooftop solar PV yield ($MWh/yr$).
- **Sol-Air Facade Temperature:** Peak solar radiation thermal loading calculation ($T_{sol-air}$).
- **Air Pollution Dispersion (AQI):** Street canyon pollutant trapping penalty vs. green open-space flushing.
- **Outdoor Thermal Comfort (UTCI / MRT):** Urban Heat Island ($UHI$) temperature rise and Universal Thermal Climate Index ($UTCI$).
- **Life-Cycle Carbon Assessment (LCA):** Embodied Carbon ($kgCO_2e/m^2$ by material selection: Timber/Concrete/Steel) + 50-year Operational Carbon footprint.
- **Real Estate Financial Pro-Forma:** Net Present Value ($NPV$), Internal Rate of Return ($IRR\%$), and Return on Investment ($ROI\%$).

---

## 🧮 Mathematical & Physics Engine Formulations

### 1. Sol-Air Facade Temperature ($T_{sol-air}$)
$$T_{sol-air} = T_a + \frac{\alpha \cdot I - \epsilon \cdot \Delta R}{h_o}$$
*where $T_a$ is ambient air temperature ($30^\circ C$), $\alpha$ is facade solar absorptance ($0.7$), $I$ is incident solar irradiance ($W/m^2$), and $h_o$ is outdoor heat transfer coefficient ($17\,W/m^2K$).*

### 2. SPEA-2 Density Estimation ($D_i$)
$$D(i) = \frac{1}{\sigma_i^k + 2}$$
*where $\sigma_i^k$ is the Euclidean distance in objective space to the $k$-th nearest neighbor ($k = \lfloor\sqrt{N}\rfloor$).*

### 3. Shannon Typology Diversity Index ($H'$)
$$H' = -\sum_{i=1}^{S} p_i \ln p_i$$
*where $p_i$ represents the proportion of building typology $i$ across the master-plan site.*

---

## 🛠️ QGIS Processing Toolbox Integration

**Parametric Process** registers natively under the **Urban Analytics** group in the QGIS Processing Toolbox:

1. **`1. Parametric Multi-Objective Evolutionary Optimization`**
   - Headless batch evolutionary simulation (NSGA-II / SPEA-2) for QGIS Graphical Modeler pipelines.
   - Outputs a vector polygon layer containing all Pareto Rank 1 design candidates populated with genotype attributes and physics metrics.
2. **`2. Urban Physics & Microclimate Multi-Domain Evaluator`**
   - Evaluates existing building footprint vector layers and populates all 15 microclimate, financial, carbon, and UTCI attributes.

---

## 🖥️ User Interface Preview & Workflow

```
┌────────────────────────────────────────────────────────────────────────┐
│                          QGIS MAIN WINDOW                              │
│ ┌──────────────────────────┐  ┌──────────────────────────────────────┐ │
│ │ Vector Layer Selector    │  │ Local WebGL 3D Cockpit (Port 8090)  │ │
│ │ • Parcel Boundaries      │──│ • Three.js Procedural Massing        │ │
│ │ • Urban Block Geometries │  │ • Real-time Shadows & Pedestrians    │ │
│ └──────────────────────────┘  └──────────────────────────────────────┘ │
│                                                  │                     │
│                                                  ▼                     │
│                               ┌──────────────────────────────────────┐ │
│                               │ Pareto Analytics Studio              │ │
│                               │ ├── 📊 Pareto Front 2D Scatter       │ │
│                               │ ├── 🔀 PCP with Brush Filtering      │ │
│                               │ ├── 📈 Fitness & SD Band Trajectory  │ │
│                               │ ├── 💎 Diamond Fitness Radar         │ │
│                               │ ├── 🧮 K-Means Clustering Studio     │ │
│                               │ └── 🔬 Population Browser Table      │ │
│                               └──────────────────────────────────────┘ │
│                                                  │                     │
│                                                  ▼                     │
│                               ┌──────────────────────────────────────┐ │
│                               │ ⚡ Bidirectional QGIS Vector Sync    │ │
│                               └──────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation & Setup

1. **Environment Variable / Directory:**
   Copy the `parametric_process` folder into your QGIS plugin directory:
   ```bash
   C:\Users\<User>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\parametric_process
   ```
2. **Enable Plugin:**
   Open QGIS → **Plugins** → **Manage and Install Plugins** → Enable **Parametric Process**.
3. **Launch Studio:**
   Click the **Parametric Process** toolbar icon or select it from the menu, pick your target parcel vector layer, and launch the local 3D cockpit!

---

## 📄 License & Attribution

- **Author:** Yusuf Eminoğlu ([yusuf.eminoglu@deu.edu.tr](mailto:yusuf.eminoglu@deu.edu.tr))
- **License:** GPL-3.0-or-later
- **Repository:** [YusufEminoglu/parametric_process](https://github.com/YusufEminoglu/parametric_process)
