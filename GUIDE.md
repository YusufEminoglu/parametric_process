# Parametric Process — Academic User and Methodology Guide

Parametric Process is a QGIS-native environment for generating, screening, and comparing urban design alternatives. It supports research and early-stage planning decisions; it does not turn proxy indicators into measurements or replace statutory review and specialist simulation.

## 1. Frame the study before opening the solver

Predeclare the decision question, scale, data sources and dates, legal constraints, design variables and ranges, objectives and units, uncertainty factors, scenarios, fixed seeds, run budget, and validation methods. Treat constraints and objectives differently: a legal height limit is a feasibility condition, not a performance value that can be traded away.

## 2. Prepare defensible spatial inputs

Use valid Polygon or MultiPolygon parcels in an appropriate local projected CRS measured in metres. Preserve immutable unique parcel IDs and the unmodified source. Record geometry repairs, omissions, field mappings, and every default used for missing zoning values. Pilot a small area and inspect buildings, open space, rejected alternatives, units, nulls, and outliers in QGIS.

## 3. Build a transparent workflow graph

A defensible flow normally follows:

`QGIS Site Layer → Zoning Envelope → Generator → Analysis → Evolutionary Solver → Decision Review → QGIS Output`

The graph is an executable hypothesis about how inputs become evidence. Give nodes meaningful names, expose assumptions, keep constraints separate from objectives, validate the graph, and preserve its exported JSON.

## 4. Design the computational experiment

Run a diagnostic first, then freeze the experimental design. Compare scenarios with the same population, generations, bounds, objectives and seed set unless the changed item is the declared treatment. Use at least three predeclared seeds for exploratory work and add replication until conclusions, Pareto coverage and ranks are adequately stable. A seed provides repeatability; it is not uncertainty analysis. Preserve failed and infeasible runs.

Use NSGA-II as a general baseline for a modest objective count. Consider NSGA-III or MOEA/D when many objectives make dominance less discriminating. Algorithm choice belongs in the protocol, not in post-hoc attempts to obtain a preferred plan.

## 5. Interpret the Pareto set

Check input completeness and feasibility first, then convergence and cross-seed consistency, Pareto coverage and spacing, raw objective values and units, spatial plausibility, and sensitivity. Pareto rank means non-dominated under the declared model only. It does not mean legally compliant, safe, socially preferred, or optimal in an absolute sense.

## 6. Use TOPSIS as an explicit preference model

Apply TOPSIS only after feasibility screening. Publish criterion directions, normalization, weights, and the ranked alternative set. Repeat the ranking across plausible weights and report rank reversals. Record stakeholder weight elicitation and disagreement. A top-ranked candidate is a conditional recommendation, not validated truth.

## 7. Analyse uncertainty and sensitivity

Separate data, parameter, model-form and preference uncertainty. Use scenarios for structural assumptions and multiple seeds for search variability. Use Morris elementary effects for economical factor screening, then a global variance-based method where interactions and quantitative attribution matter. Do not present one-factor-at-a-time checks as global sensitivity analysis.

Bootstrap intervals describe variability in supplied results; they do not remove bias or validate a proxy. Archive their seed and sample count. Define a robustness rule before seeing the results, such as the proportion of seeds and scenarios in which a candidate remains feasible and within a declared performance band.

## 8. Validate claims at the right fidelity

Built-in wind, solar, thermal comfort, pollution, carbon, and financial outputs are screening indicators. Validate shortlisted claims using observations or an appropriate specialist method: for example, calibrated CFD, validated radiation or energy simulation, an accepted UTCI implementation with defensible weather inputs, a declared LCA database and system boundary, or a dated cost model.

Agreement between two proxies is not field validation. Report validation data, calibration choices, errors, applicability limits, and discrepancies. For external engines, archive the executable fingerprint and version and require explicit units and matching solution IDs.

## 9. Preserve a reproducible research package

Archive source snapshots and licences; CRS and boundary; field mappings, defaults, exclusions and repairs; workflow and study JSON; software and engine versions; solver settings and seeds; objectives, constraints and scenarios; complete alternatives, buildings, open space, rejected records and summaries; robustness, sensitivity and ranking outputs; external validation; selection rationale; and the SHA-256 manifest.

Stable fields such as `source_fid`, `seed`, `run_id`, and `model_ver` support traceability. Re-run an archived sample before publication. A changed model version or manifest hash identifies a materially different experiment and must not overwrite the original.

## 10. Minimum reporting checklist

Report the research question, data provenance, CRS, scale, variables and bounds, equations or engine versions, objectives and directions, constraints, solver and budget, all seeds, feasibility rate, Pareto diagnostics, uncertainty and sensitivity design, TOPSIS weights and stability, external validation, limitations, and access to the research package.

## Verified academic references

Each DOI link was checked against its publisher record or DOI registry.

1. Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation, 6*(2), 182–197. [https://doi.org/10.1109/4235.996017](https://doi.org/10.1109/4235.996017)
2. Deb, K., & Jain, H. (2014). An evolutionary many-objective optimization algorithm using reference-point-based nondominated sorting approach, Part I. *IEEE Transactions on Evolutionary Computation, 18*(4), 577–601. [https://doi.org/10.1109/TEVC.2013.2281535](https://doi.org/10.1109/TEVC.2013.2281535)
3. Zhang, Q., & Li, H. (2007). MOEA/D: A multiobjective evolutionary algorithm based on decomposition. *IEEE Transactions on Evolutionary Computation, 11*(6), 712–731. [https://doi.org/10.1109/TEVC.2007.892759](https://doi.org/10.1109/TEVC.2007.892759)
4. Shih, H.-S., & Olson, D. L. (2022). *TOPSIS and Its Extensions: A Distance-Based MCDM Approach*. Springer. [https://doi.org/10.1007/978-3-031-09577-1](https://doi.org/10.1007/978-3-031-09577-1)
5. Morris, M. D. (1991). Factorial sampling plans for preliminary computational experiments. *Technometrics, 33*(2), 161–174. [https://doi.org/10.1080/00401706.1991.10484804](https://doi.org/10.1080/00401706.1991.10484804)
6. Saltelli, A., Annoni, P., Azzini, I., Campolongo, F., Ratto, M., & Tarantola, S. (2010). Variance based sensitivity analysis of model output. *Computer Physics Communications, 181*(2), 259–270. [https://doi.org/10.1016/j.cpc.2009.09.018](https://doi.org/10.1016/j.cpc.2009.09.018)
7. Pianosi, F., Beven, K., Freer, J., Hall, J. W., Rougier, J., Stephenson, D. B., & Wagener, T. (2016). Sensitivity analysis of environmental models: A systematic review with practical workflow. *Environmental Modelling & Software, 79*, 214–232. [https://doi.org/10.1016/j.envsoft.2016.02.008](https://doi.org/10.1016/j.envsoft.2016.02.008)
8. Bröde, P., Fiala, D., Błażejczyk, K., Holmér, I., Jendritzky, G., Kampmann, B., Tinz, B., & Havenith, G. (2012). Deriving the operational procedure for the Universal Thermal Climate Index (UTCI). *International Journal of Biometeorology, 56*, 481–494. [https://doi.org/10.1007/s00484-011-0454-1](https://doi.org/10.1007/s00484-011-0454-1)
