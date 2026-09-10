# -*- coding: utf-8 -*-
"""Research-grade study, indicator, uncertainty, and interoperability core.

The module is deliberately QGIS-free so every equation and schema can be tested on
plain Python. Spatial construction stays in :mod:`academic_processing` where GEOS is
available through QGIS.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence


STUDY_SCHEMA = "parametric-process-study/3.0"
MODEL_VERSION = "3.0"
METRIC_SCHEMA = {
    "walk_access_score": {"unit": "score_0_100", "class": "screening_proxy"},
    "intersection_density": {"unit": "count_per_km2", "class": "measured_geometry"},
    "active_frontage_ratio": {"unit": "ratio", "class": "screening_proxy"},
    "permeability_index": {"unit": "score_0_100", "class": "screening_proxy"},
    "universal_access_score": {"unit": "score_0_100", "class": "screening_proxy"},
    "impervious_ratio": {"unit": "ratio", "class": "screening_proxy"},
    "runoff_volume_m3": {"unit": "m3_event", "class": "screening_proxy"},
    "detention_demand_m3": {"unit": "m3_event", "class": "screening_proxy"},
    "tree_canopy_ratio": {"unit": "ratio", "class": "measured_or_scenario"},
    "canopy_cooling_c": {"unit": "degC", "class": "screening_proxy"},
    "habitat_connectivity": {"unit": "score_0_100", "class": "screening_proxy"},
    "npv": {"unit": "currency", "class": "scenario_model"},
    "irr": {"unit": "ratio", "class": "scenario_model"},
    "discounted_payback_years": {"unit": "years", "class": "scenario_model"},
}

DEFAULT_ASSUMPTIONS = {
    "max_bcr": 0.45,
    "max_far": 2.50,
    "max_height_m": 18.0,
    "front_setback_m": 5.0,
    "side_setback_m": 3.0,
    "rear_setback_m": 3.0,
    "floor_height_m": 3.0,
    "rainfall_event_mm": 50.0,
    "runoff_coefficient_roof": 0.90,
    "runoff_coefficient_hardscape": 0.80,
    "runoff_coefficient_landscape": 0.20,
    "target_canopy_ratio": 0.25,
    "discount_rate": 0.06,
    "analysis_years": 30,
    "construction_cost_per_m2": 750.0,
    "annual_income_per_m2": 132.0,
    "annual_operating_cost_per_m2": 28.0,
    "income_escalation": 0.02,
    "cost_escalation": 0.02,
    "embodied_carbon_kgco2e_m2": 380.0,
    "operational_carbon_kgco2e_m2_year": 45.0,
}


class StudyValidationError(ValueError):
    """Raised when a study cannot support a defensible run."""


def _finite_number(name: str, value: Any, minimum: float | None = None,
                   maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise StudyValidationError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise StudyValidationError(f"{name} must be finite")
    if minimum is not None and number < minimum:
        raise StudyValidationError(f"{name} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise StudyValidationError(f"{name} must be at most {maximum}")
    return number


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: Any, length: int = 16) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]


def create_study(name: str, crs_authid: str, layers: Mapping[str, Any] | None = None,
                 field_mapping: Mapping[str, str] | None = None,
                 assumptions: Mapping[str, Any] | None = None,
                 scenarios: Sequence[Mapping[str, Any]] | None = None,
                 seeds: Sequence[int] | None = None) -> Dict[str, Any]:
    merged = dict(DEFAULT_ASSUMPTIONS)
    merged.update(dict(assumptions or {}))
    study = {
        "schema": STUDY_SCHEMA,
        "name": str(name).strip(),
        "crs": str(crs_authid).strip(),
        "layers": dict(layers or {}),
        "field_mapping": dict(field_mapping or {}),
        "assumptions": merged,
        "scenarios": list(scenarios or [{"id": "baseline", "name": "Baseline", "overrides": {}}]),
        "seeds": [int(seed) for seed in (seeds or [42, 31415, 271828])],
        "model_version": MODEL_VERSION,
    }
    validate_study(study)
    study["study_id"] = content_hash(study)
    return study


def migrate_study(study: Mapping[str, Any]) -> Dict[str, Any]:
    migrated = dict(study)
    schema = migrated.get("schema")
    if schema == STUDY_SCHEMA:
        return migrated
    if schema in (None, "parametric-process-study/2.0"):
        migrated["schema"] = STUDY_SCHEMA
        migrated.setdefault("model_version", MODEL_VERSION)
        migrated.setdefault("layers", {})
        migrated.setdefault("field_mapping", {})
        merged = dict(DEFAULT_ASSUMPTIONS)
        merged.update(migrated.get("assumptions", {}))
        migrated["assumptions"] = merged
        migrated.setdefault("scenarios", [{"id": "baseline", "name": "Baseline", "overrides": {}}])
        migrated.setdefault("seeds", [42, 31415, 271828])
        migrated["study_id"] = content_hash({k: v for k, v in migrated.items() if k != "study_id"})
        return migrated
    raise StudyValidationError(f"Unsupported study schema: {schema}")


def validate_study(study: Mapping[str, Any]) -> None:
    if not isinstance(study, Mapping):
        raise StudyValidationError("Study must be a JSON object")
    if study.get("schema") != STUDY_SCHEMA:
        raise StudyValidationError(f"Study schema must be {STUDY_SCHEMA}")
    if not str(study.get("name", "")).strip():
        raise StudyValidationError("Study name is required")
    crs = str(study.get("crs", ""))
    if not crs or crs.upper() in {"EPSG:4326", "OGC:CRS84"}:
        raise StudyValidationError("A projected study CRS in metres is required")
    seeds = study.get("seeds")
    if not isinstance(seeds, list) or not seeds:
        raise StudyValidationError("At least one deterministic seed is required")
    if len(set(int(seed) for seed in seeds)) != len(seeds):
        raise StudyValidationError("Study seeds must be unique")
    assumptions = study.get("assumptions", {})
    _finite_number("max_bcr", assumptions.get("max_bcr"), 0.01, 1.0)
    _finite_number("max_far", assumptions.get("max_far"), 0.01)
    _finite_number("max_height_m", assumptions.get("max_height_m"), 0.1)
    _finite_number("rainfall_event_mm", assumptions.get("rainfall_event_mm"), 0.0)
    _finite_number("discount_rate", assumptions.get("discount_rate"), -0.99, 10.0)


def apply_scenario(study: Mapping[str, Any], scenario_id: str) -> Dict[str, Any]:
    validate_study(study)
    scenario = next((item for item in study.get("scenarios", [])
                     if item.get("id") == scenario_id), None)
    if scenario is None:
        raise StudyValidationError(f"Unknown scenario: {scenario_id}")
    assumptions = dict(study["assumptions"])
    assumptions.update(scenario.get("overrides", {}))
    resolved = dict(study)
    resolved["assumptions"] = assumptions
    resolved["active_scenario"] = scenario_id
    resolved["run_id"] = content_hash({
        "study_id": study.get("study_id"), "scenario": scenario_id,
        "assumptions": assumptions, "seeds": study["seeds"],
    })
    validate_study(resolved)
    return resolved


def resolve_zoning(attributes: Mapping[str, Any], field_mapping: Mapping[str, str],
                   defaults: Mapping[str, Any]) -> Dict[str, Any]:
    keys = ("max_bcr", "max_far", "max_height_m", "front_setback_m",
            "side_setback_m", "rear_setback_m")
    result = {}
    provenance = {}
    for key in keys:
        field = field_mapping.get(key)
        raw = attributes.get(field) if field else None
        if raw not in (None, ""):
            result[key] = _finite_number(key, raw, 0.0, 1.0 if key == "max_bcr" else None)
            provenance[key] = {"source": "field", "field": field}
        else:
            result[key] = _finite_number(key, defaults[key], 0.0,
                                         1.0 if key == "max_bcr" else None)
            provenance[key] = {"source": "study_default", "field": None}
    result["provenance"] = provenance
    return result


def constraint_diagnostics(metrics: Mapping[str, Any], zoning: Mapping[str, Any]) -> Dict[str, Any]:
    checks = (
        ("bcr", "max_bcr", "ratio"),
        ("far", "max_far", "ratio"),
        ("height_m", "max_height_m", "m"),
    )
    rules = []
    total = 0.0
    for metric_name, limit_name, unit in checks:
        value = float(metrics.get(metric_name, 0.0))
        limit = float(zoning[limit_name])
        violation = max(0.0, value - limit)
        total += violation
        rules.append({"rule": metric_name, "value": value, "limit": limit,
                      "unit": unit, "violation": violation, "feasible": violation == 0.0})
    return {"feasible": total == 0.0, "total_violation": total, "rules": rules}


def accessibility_indicators(site_area_m2: float, street_length_m: float,
                             intersection_count: int, destination_distances_m: Iterable[float],
                             active_frontage_m: float = 0.0, total_frontage_m: float = 0.0,
                             accessible_route_ratio: float = 1.0) -> Dict[str, float]:
    area = _finite_number("site_area_m2", site_area_m2, 1.0)
    street_length = _finite_number("street_length_m", street_length_m, 0.0)
    intersections = int(_finite_number("intersection_count", intersection_count, 0.0))
    distances = [_finite_number("destination_distance", item, 0.0) for item in destination_distances_m]
    access = statistics.fmean(math.exp(-distance / 800.0) for distance in distances) * 100.0 if distances else 0.0
    intersection_density = intersections / (area / 1_000_000.0)
    frontage_ratio = min(1.0, max(0.0, active_frontage_m / total_frontage_m)) if total_frontage_m > 0 else 0.0
    permeability = min(100.0, (street_length / area) * 5000.0 + min(50.0, intersection_density / 4.0))
    return {
        "walk_access_score": round(access, 3),
        "intersection_density": round(intersection_density, 3),
        "active_frontage_ratio": round(frontage_ratio, 4),
        "permeability_index": round(permeability, 3),
        "universal_access_score": round(min(1.0, max(0.0, accessible_route_ratio)) * 100.0, 3),
    }


def blue_green_indicators(site_area_m2: float, roof_area_m2: float,
                          hardscape_area_m2: float, canopy_area_m2: float,
                          green_patches: Sequence[Mapping[str, float]], assumptions: Mapping[str, Any]) -> Dict[str, float]:
    area = _finite_number("site_area_m2", site_area_m2, 1.0)
    roof = _finite_number("roof_area_m2", roof_area_m2, 0.0)
    hardscape = _finite_number("hardscape_area_m2", hardscape_area_m2, 0.0)
    canopy = _finite_number("canopy_area_m2", canopy_area_m2, 0.0)
    landscape = max(0.0, area - roof - hardscape)
    rainfall_m = _finite_number("rainfall_event_mm", assumptions.get("rainfall_event_mm", 50.0), 0.0) / 1000.0
    runoff = rainfall_m * (
        roof * float(assumptions.get("runoff_coefficient_roof", 0.9))
        + hardscape * float(assumptions.get("runoff_coefficient_hardscape", 0.8))
        + landscape * float(assumptions.get("runoff_coefficient_landscape", 0.2))
    )
    canopy_ratio = min(1.0, canopy / area)
    target = max(0.01, float(assumptions.get("target_canopy_ratio", 0.25)))
    detention = max(0.0, runoff - rainfall_m * area * 0.20)
    patch_area = sum(max(0.0, float(item.get("area_m2", 0.0))) for item in green_patches)
    largest_patch = max((max(0.0, float(item.get("area_m2", 0.0))) for item in green_patches), default=0.0)
    connectivity = min(100.0, (patch_area / area) * 60.0 + (largest_patch / area) * 40.0)
    return {
        "impervious_ratio": round(min(1.0, (roof + hardscape) / area), 4),
        "runoff_volume_m3": round(runoff, 3),
        "detention_demand_m3": round(detention, 3),
        "tree_canopy_ratio": round(canopy_ratio, 4),
        "canopy_cooling_c": round(min(3.0, canopy_ratio / target * 2.0), 3),
        "habitat_connectivity": round(connectivity, 3),
    }


def financial_and_carbon(gfa_m2: float, assumptions: Mapping[str, Any]) -> Dict[str, float | None]:
    gfa = _finite_number("gfa_m2", gfa_m2, 0.0)
    years = int(_finite_number("analysis_years", assumptions.get("analysis_years", 30), 1, 100))
    discount = _finite_number("discount_rate", assumptions.get("discount_rate", 0.06), -0.99, 10.0)
    construction = gfa * float(assumptions.get("construction_cost_per_m2", 750.0))
    income = gfa * float(assumptions.get("annual_income_per_m2", 132.0))
    operating = gfa * float(assumptions.get("annual_operating_cost_per_m2", 28.0))
    income_growth = float(assumptions.get("income_escalation", 0.02))
    cost_growth = float(assumptions.get("cost_escalation", 0.02))
    cash_flows = [-construction]
    for year in range(1, years + 1):
        cash_flows.append(income * ((1.0 + income_growth) ** (year - 1))
                          - operating * ((1.0 + cost_growth) ** (year - 1)))
    npv = sum(value / ((1.0 + discount) ** period) for period, value in enumerate(cash_flows))
    cumulative = cash_flows[0]
    payback = None
    for year, cash_flow in enumerate(cash_flows[1:], 1):
        previous = cumulative
        cumulative += cash_flow / ((1.0 + discount) ** year)
        if cumulative >= 0.0:
            discounted = cash_flow / ((1.0 + discount) ** year)
            payback = year - 1 + (-previous / discounted if discounted else 0.0)
            break
    irr = _cashflow_irr(cash_flows)
    embodied = gfa * float(assumptions.get("embodied_carbon_kgco2e_m2", 380.0))
    operational = gfa * float(assumptions.get("operational_carbon_kgco2e_m2_year", 45.0)) * years
    return {
        "construction_cost": round(construction, 2),
        "npv": round(npv, 2),
        "irr": round(irr, 6) if irr is not None else None,
        "discounted_payback_years": round(payback, 3) if payback is not None else None,
        "embodied_carbon_kgco2e": round(embodied, 2),
        "operational_carbon_kgco2e": round(operational, 2),
        "lifecycle_carbon_kgco2e": round(embodied + operational, 2),
    }


def _cashflow_irr(cash_flows: Sequence[float]) -> float | None:
    lower, upper = -0.9999, 10.0
    def value(rate: float) -> float:
        return sum(flow / ((1.0 + rate) ** index) for index, flow in enumerate(cash_flows))
    low_value, high_value = value(lower), value(upper)
    if low_value * high_value > 0:
        return None
    for _ in range(180):
        middle = (lower + upper) / 2.0
        middle_value = value(middle)
        if abs(middle_value) < 1e-8:
            return middle
        if low_value * middle_value <= 0:
            upper = middle
        else:
            lower, low_value = middle, middle_value
    return (lower + upper) / 2.0


def aggregate_robustness(runs: Sequence[Mapping[str, Any]], metrics: Sequence[str]) -> Dict[str, Any]:
    if not runs:
        raise StudyValidationError("At least one completed run is required")
    summary = {}
    for metric in metrics:
        values = [float(run["metrics"][metric]) for run in runs
                  if metric in run.get("metrics", {}) and math.isfinite(float(run["metrics"][metric]))]
        if not values:
            continue
        ordered = sorted(values)
        q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive") if len(ordered) > 1 else (ordered[0], ordered[0], ordered[0])
        mean = statistics.fmean(ordered)
        stdev = statistics.stdev(ordered) if len(ordered) > 1 else 0.0
        margin = 1.96 * stdev / math.sqrt(len(ordered)) if len(ordered) > 1 else 0.0
        summary[metric] = {
            "n": len(ordered), "mean": round(mean, 6), "median": round(statistics.median(ordered), 6),
            "q1": round(q1, 6), "q3": round(q3, 6), "iqr": round(q3 - q1, 6),
            "ci95_low": round(mean - margin, 6), "ci95_high": round(mean + margin, 6),
        }
    feasible = sum(1 for run in runs if run.get("feasible") is True)
    return {"run_count": len(runs), "feasible_run_rate": feasible / len(runs), "metrics": summary}


def consensus_alternatives(runs: Sequence[Mapping[str, Any]], top_fraction: float = 0.20) -> List[Dict[str, Any]]:
    """Rank recurring genotype families across independent seeds."""
    fraction = _finite_number("top_fraction", top_fraction, 0.01, 1.0)
    counts: Dict[str, Dict[str, Any]] = {}
    completed = 0
    for run in runs:
        alternatives = list(run.get("alternatives", []))
        if not alternatives:
            continue
        completed += 1
        ranked = sorted(alternatives, key=lambda item: (
            not bool(item.get("feasible", False)), -float(item.get("score", 0.0))))
        keep = max(1, math.ceil(len(ranked) * fraction))
        seen = set()
        for item in ranked[:keep]:
            genotype = item.get("genotype", {})
            family = content_hash({
                "typology": genotype.get("typology"), "usage": genotype.get("usage"),
                "floors": genotype.get("floors"), "setback": genotype.get("setback"),
            })
            if family in seen:
                continue
            seen.add(family)
            record = counts.setdefault(family, {"family_id": family, "attainment_count": 0,
                                                "representative": item})
            record["attainment_count"] += 1
    if completed == 0:
        return []
    result = []
    for record in counts.values():
        record = dict(record)
        record["attainment_frequency"] = record["attainment_count"] / completed
        result.append(record)
    return sorted(result, key=lambda item: (-item["attainment_frequency"], item["family_id"]))


def compare_scenarios(baseline: Mapping[str, Any], alternative: Mapping[str, Any],
                      metric_directions: Mapping[str, str]) -> Dict[str, Any]:
    """Return transparent metric deltas and improvement direction for two scenarios."""
    comparison = {}
    baseline_metrics = baseline.get("metrics", {})
    alternative_metrics = alternative.get("metrics", {})
    for metric, direction in metric_directions.items():
        if direction not in {"min", "max"}:
            raise StudyValidationError(f"Invalid direction for {metric}")
        old = _finite_number(metric, baseline_metrics.get(metric))
        new = _finite_number(metric, alternative_metrics.get(metric))
        delta = new - old
        comparison[metric] = {
            "baseline": old, "alternative": new, "delta": delta,
            "improved": delta >= 0 if direction == "max" else delta <= 0,
        }
    return {"baseline_id": baseline.get("scenario_id"),
            "alternative_id": alternative.get("scenario_id"), "metrics": comparison}


def rank_stability(rankings: Sequence[Sequence[str]]) -> Dict[str, Any]:
    """Summarize rank ranges and mean positions across preference scenarios."""
    positions: Dict[str, List[int]] = {}
    for ranking in rankings:
        if len(set(ranking)) != len(ranking):
            raise StudyValidationError("A ranking cannot contain duplicate solution IDs")
        for position, solution_id in enumerate(ranking, 1):
            positions.setdefault(str(solution_id), []).append(position)
    rows = []
    for solution_id, values in positions.items():
        rows.append({
            "solution_id": solution_id, "observations": len(values),
            "mean_rank": round(statistics.fmean(values), 4),
            "best_rank": min(values), "worst_rank": max(values),
            "rank_range": max(values) - min(values),
        })
    return {"scenario_count": len(rankings), "solutions": sorted(rows, key=lambda row: (row["mean_rank"], row["solution_id"]))}


def morris_screen(model: Callable[[Mapping[str, float]], Mapping[str, float]],
                  baseline: Mapping[str, float], bounds: Mapping[str, Sequence[float]],
                  output_names: Sequence[str], levels: int = 6) -> Dict[str, Any]:
    """Deterministic one-at-a-time Morris elementary-effects screening."""
    if levels < 4:
        raise StudyValidationError("Morris analysis requires at least four levels")
    effects: Dict[str, Dict[str, List[float]]] = {
        parameter: {output: [] for output in output_names} for parameter in bounds
    }
    fractions = [index / (levels - 1) for index in range(levels - 1)]
    for parameter, limits in bounds.items():
        low, high = map(float, limits)
        if high <= low:
            raise StudyValidationError(f"Invalid Morris bounds for {parameter}")
        delta = (high - low) / (levels - 1)
        for fraction in fractions:
            point = dict(baseline)
            point[parameter] = low + fraction * (high - low)
            shifted = dict(point)
            shifted[parameter] += delta
            before, after = model(point), model(shifted)
            for output in output_names:
                effects[parameter][output].append((float(after[output]) - float(before[output])) / delta)
    result = {}
    for parameter, outputs in effects.items():
        result[parameter] = {}
        for output, values in outputs.items():
            result[parameter][output] = {
                "mu": round(statistics.fmean(values), 6),
                "mu_star": round(statistics.fmean(abs(value) for value in values), 6),
                "sigma": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
            }
    return {"method": "Morris elementary effects", "levels": levels, "effects": result}


def alternatives_csv(alternatives: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    columns = {"solution_id", "run_id", "scenario_id", "seed", "feasible"}
    for alternative in alternatives:
        row = {key: alternative.get(key) for key in columns}
        row.update(alternative.get("genotype", {}))
        row.update(alternative.get("metrics", {}))
        rows.append(row)
        columns.update(row)
    ordered = ["solution_id", "run_id", "scenario_id", "seed", "feasible"] + sorted(
        columns - {"solution_id", "run_id", "scenario_id", "seed", "feasible"})
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=ordered, extrasaction="ignore", lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in ordered})
    return stream.getvalue()
