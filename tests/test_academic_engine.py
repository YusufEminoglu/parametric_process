import csv
import io
import json
import math
import unittest

from parametric_process.academic_engine import (
    STUDY_SCHEMA, StudyValidationError, accessibility_indicators,
    aggregate_robustness, alternatives_csv, apply_scenario,
    blue_green_indicators, constraint_diagnostics, create_study,
    financial_and_carbon, migrate_study, morris_screen, resolve_zoning,
    compare_scenarios, consensus_alternatives, rank_stability,
    audit_manifest, bootstrap_robustness, data_quality_report, pareto_quality,
)


class AcademicStudyTests(unittest.TestCase):
    def test_study_round_trip_and_scenario_identity(self):
        study = create_study(
            "Campus alternatives", "EPSG:32635",
            scenarios=[
                {"id": "baseline", "name": "Baseline", "overrides": {}},
                {"id": "green", "name": "Green", "overrides": {"target_canopy_ratio": 0.4}},
            ], seeds=[11, 22, 33],
        )
        self.assertEqual(study["schema"], STUDY_SCHEMA)
        self.assertEqual(json.loads(json.dumps(study)), study)
        baseline = apply_scenario(study, "baseline")
        green = apply_scenario(study, "green")
        self.assertNotEqual(baseline["run_id"], green["run_id"])
        self.assertEqual(green["assumptions"]["target_canopy_ratio"], 0.4)

    def test_legacy_study_migration(self):
        migrated = migrate_study({"name": "Legacy", "crs": "EPSG:32635", "seeds": [1]})
        self.assertEqual(migrated["schema"], STUDY_SCHEMA)
        self.assertIn("rainfall_event_mm", migrated["assumptions"])

    def test_geographic_crs_and_duplicate_seeds_are_rejected(self):
        with self.assertRaises(StudyValidationError):
            create_study("Invalid", "EPSG:4326")
        with self.assertRaises(StudyValidationError):
            create_study("Invalid", "EPSG:32635", seeds=[4, 4])

    def test_zoning_field_mapping_has_provenance_and_fallback(self):
        study = create_study("Zoning", "EPSG:32635")
        zoning = resolve_zoning(
            {"kaks": 3.0, "hmax": None},
            {"max_far": "kaks", "max_height_m": "hmax"}, study["assumptions"])
        self.assertEqual(zoning["max_far"], 3.0)
        self.assertEqual(zoning["provenance"]["max_far"]["source"], "field")
        self.assertEqual(zoning["provenance"]["max_height_m"]["source"], "study_default")

    def test_constraint_diagnostics_preserves_violation_units(self):
        result = constraint_diagnostics(
            {"bcr": 0.6, "far": 2.0, "height_m": 21.0},
            {"max_bcr": 0.5, "max_far": 2.5, "max_height_m": 18.0})
        self.assertFalse(result["feasible"])
        self.assertEqual([rule["unit"] for rule in result["rules"]], ["ratio", "ratio", "m"])
        self.assertAlmostEqual(result["total_violation"], 3.1)


class IndicatorTests(unittest.TestCase):
    def test_accessibility_reference_values(self):
        result = accessibility_indicators(1_000_000, 20_000, 100, [0, 800], 500, 1000, 0.8)
        self.assertAlmostEqual(result["walk_access_score"], (1 + math.exp(-1)) * 50, places=3)
        self.assertEqual(result["intersection_density"], 100.0)
        self.assertEqual(result["active_frontage_ratio"], 0.5)
        self.assertEqual(result["universal_access_score"], 80.0)

    def test_rational_method_event_runoff(self):
        assumptions = create_study("Water", "EPSG:32635")["assumptions"]
        result = blue_green_indicators(1000, 400, 200, 250, [{"area_m2": 250}], assumptions)
        expected = 0.05 * (400 * 0.9 + 200 * 0.8 + 400 * 0.2)
        self.assertAlmostEqual(result["runoff_volume_m3"], expected, places=3)
        self.assertEqual(result["tree_canopy_ratio"], 0.25)

    def test_finance_uses_discounted_cashflow_and_separate_carbon(self):
        assumptions = create_study("Finance", "EPSG:32635")["assumptions"]
        result = financial_and_carbon(1000, assumptions)
        self.assertTrue(math.isfinite(result["npv"]))
        self.assertGreater(result["irr"], 0)
        self.assertAlmostEqual(
            result["lifecycle_carbon_kgco2e"],
            result["embodied_carbon_kgco2e"] + result["operational_carbon_kgco2e"])

    def test_morris_linear_reference_model(self):
        result = morris_screen(
            lambda values: {"y": 2 * values["x"] + 3 * values["z"]},
            {"x": 0.0, "z": 0.0}, {"x": [0, 1], "z": [0, 1]}, ["y"])
        self.assertAlmostEqual(result["effects"]["x"]["y"]["mu_star"], 2.0)
        self.assertAlmostEqual(result["effects"]["z"]["y"]["mu_star"], 3.0)
        self.assertAlmostEqual(result["effects"]["x"]["y"]["sigma"], 0.0)

    def test_robustness_and_csv_contract(self):
        summary = aggregate_robustness([
            {"feasible": True, "metrics": {"gfa": 100}},
            {"feasible": False, "metrics": {"gfa": 120}},
            {"feasible": True, "metrics": {"gfa": 140}},
        ], ["gfa"])
        self.assertEqual(summary["feasible_run_rate"], 2 / 3)
        self.assertEqual(summary["metrics"]["gfa"]["median"], 120)
        output = alternatives_csv([{"solution_id": "a,1", "metrics": {"gfa": 120}}])
        row = next(csv.DictReader(io.StringIO(output)))
        self.assertEqual(row["solution_id"], "a,1")
        self.assertEqual(row["gfa"], "120")

    def test_consensus_scenario_delta_and_rank_stability(self):
        genotype = {"typology": "Tower", "usage": "MixedUse", "floors": 6, "setback": 4}
        consensus = consensus_alternatives([
            {"alternatives": [{"feasible": True, "score": 80, "genotype": genotype}]},
            {"alternatives": [{"feasible": True, "score": 82, "genotype": genotype}]},
        ])
        self.assertEqual(consensus[0]["attainment_frequency"], 1.0)
        comparison = compare_scenarios(
            {"scenario_id": "base", "metrics": {"gfa": 100, "carbon": 50}},
            {"scenario_id": "green", "metrics": {"gfa": 110, "carbon": 40}},
            {"gfa": "max", "carbon": "min"})
        self.assertTrue(comparison["metrics"]["gfa"]["improved"])
        self.assertTrue(comparison["metrics"]["carbon"]["improved"])
        stability = rank_stability([["a", "b"], ["b", "a"]])
        self.assertEqual(stability["solutions"][0]["rank_range"], 1)

    def test_bootstrap_is_reproducible_and_distribution_free(self):
        runs = [{"feasible": True, "metrics": {"gfa": value}} for value in (80, 100, 120, 160)]
        first = bootstrap_robustness(runs, ["gfa"], seed=91, samples=500)
        second = bootstrap_robustness(runs, ["gfa"], seed=91, samples=500)
        self.assertEqual(first, second)
        interval = first["metrics"]["gfa"]
        self.assertLess(interval["bootstrap_mean_low"], interval["mean"])
        self.assertGreater(interval["bootstrap_mean_high"], interval["mean"])

    def test_data_quality_and_pareto_quality(self):
        quality = data_quality_report(
            [{"id": "a", "far": 2.0}, {"id": "a", "far": 9.0}, {"id": "c", "far": None}],
            ["id", "far"], "id", {"far": [0, 5]})
        self.assertFalse(quality["passed"])
        self.assertEqual(quality["duplicate_id_count"], 1)
        self.assertEqual(quality["out_of_range"]["far"], 1)
        pareto = pareto_quality([
            {"metrics": {"cost": 10, "quality": 5}},
            {"metrics": {"cost": 20, "quality": 9}},
            {"metrics": {"cost": 20, "quality": 9}},
        ], ["cost", "quality"])
        self.assertEqual(pareto["unique_count"], 2)
        self.assertAlmostEqual(pareto["duplicate_rate"], 1 / 3, places=6)

    def test_audit_manifest_detects_any_material_change(self):
        study = create_study("Audit", "EPSG:32635")
        first = audit_manifest(study, {"parcels": [{"id": 1}]}, {"population": 40})
        second = audit_manifest(study, {"parcels": [{"id": 2}]}, {"population": 40})
        self.assertEqual(first, audit_manifest(study, {"parcels": [{"id": 1}]}, {"population": 40}))
        self.assertNotEqual(first["manifest_hash"], second["manifest_hash"])


if __name__ == "__main__":
    unittest.main()
