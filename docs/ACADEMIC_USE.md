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

## Interpretation limits

- Output geometries retain the source parcel geometry. Each feature is an **alternative record**, not a construction-ready building footprint.
- Wind, daylight, pollution, thermal comfort and solar outputs are screening-level proxy indicators intended for relative comparison.
- Carbon factors and financial assumptions are scenario defaults, not certified inventories or market forecasts.
- Correlation-based sensitivity metrics describe the sampled population and do not establish causality.
- A Pareto front demonstrates non-dominance only for the chosen variables, bounds, objectives and equations.

## Reproducibility record

The Processing output includes `source_fid`, deterministic `seed`, a stable SHA-256-derived `run_id`, and `model_ver`. The same data, feature order, parameters, solver and seed must reproduce the same result. A changed model version defines a different experiment and should be archived separately.

## External engine contract

External validation is optional. The executable receives a strict JSON study package on standard input and returns `parametric-process-engine-result/1.0` JSON on standard output. Each result must match a requested solution ID and every metric must include a finite `value` and `unit`. Parametric Process launches the approved executable directly without a command shell, limits execution time and output size, and invalidates approval when the executable fingerprint changes. External failures remain visible and do not silently fall back to proxy values.
