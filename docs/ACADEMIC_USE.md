# Academic Use Protocol

Parametric Process is suitable for reproducible **comparative screening** of urban design alternatives. It does not claim predictive equivalence to field measurements or specialist simulation software.

## Minimum defensible workflow

1. Repair input geometries and reproject parcels to an appropriate local projected CRS in metres.
2. State the study boundary, parcel source, CRS, zoning limits, objectives and objective directions.
3. Choose and report a fixed seed. For robustness, repeat each scenario with multiple pre-declared seeds.
4. Keep population size and generation count constant when comparing planning scenarios.
5. Preserve `run_id`, `model_ver`, `seed`, and `source_fid` with the study data.
6. Report the entire non-dominated set. If TOPSIS is used, publish its weights and a sensitivity analysis.
7. Validate shortlisted alternatives using the domain method appropriate to the claim.

## Pre-registration and comparison design

Before production, freeze the question, data snapshot, variable bounds, objective
directions, constraints, scenario matrix, solver budget, seed list, robustness rule
and validation methods. Compare scenarios under an identical budget and seed set.
Preserve failed and infeasible runs. A fixed seed provides repeatability, but it is
not an uncertainty analysis.

## Interpretation limits

- Output geometries retain the source parcel geometry. Each feature is an **alternative record**, not a construction-ready building footprint.
- Wind, daylight, pollution, thermal comfort and solar outputs are screening-level proxy indicators intended for relative comparison.
- Carbon factors and financial assumptions are scenario defaults, not certified inventories or market forecasts.
- Correlation-based sensitivity metrics describe the sampled population and do not establish causality.
- A Pareto front demonstrates non-dominance only for the chosen variables, bounds, objectives and equations.

## Uncertainty, quality and audit record

Use the academic robustness endpoint with `bootstrap: true` to obtain deterministic,
distribution-free percentile intervals. Archive its seed and sample count. The audit
endpoint can check required-field completeness, identifier uniqueness and declared
numeric ranges; characterize Pareto-set coverage and spacing; and produce a SHA-256
chain-of-custody manifest over inputs, parameters and outputs. A changed manifest hash
means the experiment package is materially different.

Distinguish data, parameter, model-form and preference uncertainty. Use scenarios
for structural assumptions, Morris elementary effects for economical screening, and
a global variance-based method when interactions matter. Do not describe
one-factor-at-a-time checks as global sensitivity analysis.

## Decision and validation protocol

Apply TOPSIS after feasibility screening. Publish directions, normalization, weights
and rank changes across plausible weight sets. Shortlist different Pareto regions.
Built-in wind, solar, UTCI, carbon and financial values are screening indicators,
not calibrated CFD, certified LCA, market forecasts or field measurements.

## Reproducibility record

The Processing output includes `source_fid`, deterministic `seed`, a stable SHA-256-derived `run_id`, and `model_ver`. The same data, feature order, parameters, solver and seed must reproduce the same result. A changed model version defines a different experiment and should be archived separately.

## External engine contract

External validation is optional. The executable receives a strict JSON study package on standard input and returns `parametric-process-engine-result/1.0` JSON on standard output. Each result must match a requested solution ID and every metric must include a finite `value` and `unit`. Parametric Process launches the approved executable directly without a command shell, limits execution time and output size, and invalidates approval when the executable fingerprint changes. External failures remain visible and do not silently fall back to proxy values.

## Methodology references

See the verified bibliography and reporting checklist in [`../GUIDE.md`](../GUIDE.md).
Core methods include NSGA-II ([DOI](https://doi.org/10.1109/4235.996017)), NSGA-III
([DOI](https://doi.org/10.1109/TEVC.2013.2281535)), MOEA/D
([DOI](https://doi.org/10.1109/TEVC.2007.892759)), Morris screening
([DOI](https://doi.org/10.1080/00401706.1991.10484804)), and Pianosi et al.'s
sensitivity workflow ([DOI](https://doi.org/10.1016/j.envsoft.2016.02.008)).
