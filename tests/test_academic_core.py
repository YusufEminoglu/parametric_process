import math
import unittest

from parametric_process.nsga2_engine import (
    _irr,
    evaluate_phenotype,
    run_nsga2_optimization,
)


class AcademicCoreTests(unittest.TestCase):
    def test_irr_matches_closed_form_one_period_case(self):
        self.assertAlmostEqual(_irr([-100.0, 110.0]), 0.10, places=7)

    def test_model_rejects_dimensionally_invalid_inputs(self):
        invalid_cases = (
            {"parcel_area": 0},
            {"parcel_area": float("nan")},
            {"parcel_area": 1000, "max_bcr": 1.2},
            {"parcel_area": 1000, "sim_params": {"latitude": 91}},
        )
        for kwargs in invalid_cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                evaluate_phenotype({"floors": 4}, **kwargs)

    def test_seeded_experiment_has_stable_identity_and_results(self):
        kwargs = dict(parcel_area=2400, pop_size=12, generations=4, seed=20260910)
        first = run_nsga2_optimization(**kwargs)
        second = run_nsga2_optimization(**kwargs)
        self.assertEqual(first["pareto_solutions"], second["pareto_solutions"])
        self.assertEqual(first["run_manifest"], second["run_manifest"])
        manifest = first["run_manifest"]
        self.assertEqual(manifest["seed"], 20260910)
        self.assertEqual(len(manifest["run_id"]), 16)
        self.assertEqual(manifest["model_scope"], "screening-level deterministic surrogate")

    def test_mutation_respects_declared_research_bounds(self):
        result = run_nsga2_optimization(
            parcel_area=1800,
            pop_size=20,
            generations=6,
            seed=7,
            mutation_rate=1.0,
            bounds={"min_setback": 4.0, "max_setback": 5.0, "min_floors": 3, "max_floors": 5},
        )
        for solution in result["all_solutions"]:
            genotype = solution["genotype"]
            self.assertTrue(4.0 <= genotype["setback"] <= 5.0)
            self.assertTrue(3 <= genotype["floors"] <= 5)
            self.assertTrue(all(math.isfinite(float(value)) for value in solution["metrics"].values()))


if __name__ == "__main__":
    unittest.main()
