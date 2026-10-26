"""Property tests for the 3.3.0 model and solver corrections.

Each test pins the property a defect violated, so it fails on the code that
had the defect: the documented direction of a model term, the continuity of
a score at a zoning limit, the unit-independence of a distance, the validity
of an exported file format, and the origin check of the local server.
"""
import json
import math
import unittest
import urllib.error
import urllib.request

from parametric_process.district_engine import evaluate_building_coupling
from parametric_process.nsga2_engine import (
    ProcessIndividual,
    TYPOLOGIES,
    _LCG,
    _rng,
    create_random_genotype,
    environmental_selection_spea2,
    evaluate_phenotype,
    export_to_cityjson,
    mutate_genotype,
    repair_genotype,
    run_moead_optimization,
    run_spea2_optimization,
)
from parametric_process.server import ParametricProcessServer


def _ind(name, fitness):
    ind = ProcessIndividual(name, {})
    ind.fitness_vector = list(fitness)
    ind.metrics = {"constraint_penalty": 0.0}
    return ind


class RandomGeneratorTests(unittest.TestCase):
    def test_random_never_reaches_one(self):
        # Put the generator one step before its largest state; random() used
        # to return exactly 1.0 there and choice() indexed past the end.
        a, c, m = 1103515245, 12345, 2 ** 31
        rng = _LCG(1)
        rng._state = ((0x7FFFFFFF - c) * pow(a, -1, m)) % m
        value = rng.random()
        self.assertLess(value, 1.0)
        rng._state = ((0x7FFFFFFF - c) * pow(a, -1, m)) % m
        self.assertIn(rng.choice(["a", "b", "c"]), ["a", "b", "c"])


class PhenotypeDirectionTests(unittest.TestCase):
    def test_wind_along_the_axis_ventilates_better_than_across_it(self):
        genotype = {"setback": 3.0, "floors": 4, "typology": "Slab", "usage": "MixedUse",
                    "roof_style": "Flat", "scale_x": 1.0, "scale_y": 1.0, "floor_height": 3.0}
        aligned = evaluate_phenotype(genotype, 1200.0, sim_params={"wind_deg": 0.0})
        across = evaluate_phenotype(genotype, 1200.0, sim_params={"wind_deg": 90.0})
        self.assertGreater(aligned["wind_ventilation"], across["wind_ventilation"])

    def test_breaking_the_far_never_raises_the_composite_score(self):
        for typology in TYPOLOGIES:
            genotype = {"setback": 2.0, "floors": 6, "typology": typology, "usage": "MixedUse",
                        "roof_style": "Flat", "scale_x": 1.0, "scale_y": 1.0, "floor_height": 3.0}
            far = evaluate_phenotype(genotype, 1000.0, max_bcr=1.0, max_far=100.0,
                                     max_height=100.0)["far"]
            compliant = evaluate_phenotype(genotype, 1000.0, max_bcr=1.0, max_far=far + 0.02,
                                           max_height=100.0)
            violating = evaluate_phenotype(genotype, 1000.0, max_bcr=1.0, max_far=far - 0.02,
                                           max_height=100.0)
            self.assertGreater(violating["constraint_penalty"], 0.0)
            self.assertLessEqual(violating["planx_score"], compliant["planx_score"], typology)


class OperatorTests(unittest.TestCase):
    def test_floor_height_is_mutated(self):
        _rng.seed(7)
        genotype = create_random_genotype()
        seen = {mutate_genotype(genotype, mutation_rate=1.0)["floor_height"] for _ in range(40)}
        self.assertGreater(len(seen), 1)
        self.assertTrue(all(2.8 <= value <= 4.2 for value in seen))

    def test_repair_satisfies_every_zoning_limit(self):
        _rng.seed(11)
        for _ in range(200):
            genotype = create_random_genotype()
            repaired = repair_genotype(genotype, 1500.0, max_bcr=0.4, max_far=1.6, max_height=15.0)
            metrics = evaluate_phenotype(repaired, 1500.0, max_bcr=0.4, max_far=1.6, max_height=15.0)
            self.assertLessEqual(metrics["height_m"], 15.0)
            self.assertLessEqual(metrics["bcr"], 0.4)
            self.assertLessEqual(metrics["far"], 1.6)
            self.assertEqual(metrics["constraint_penalty"], 0.0)

    def test_unknown_objective_is_an_error_not_a_zero(self):
        ind = ProcessIndividual("x", create_random_genotype())
        with self.assertRaises(ValueError):
            ind.evaluate(1000.0, [{"name": "gfaa", "direction": "max"}])


class SolverOutputTests(unittest.TestCase):
    def test_spea2_truncation_does_not_depend_on_units(self):
        # A non-dominated set larger than the archive: truncation must keep the
        # same members whether the second objective is in units or millions.
        xs = [0.0, 10.0, 20.0, 30.0, 60.0, 90.0, 100.0]
        ys = [1.0, 0.9, 0.5, 0.45, 0.4, 0.05, 0.0]

        def kept(scale):
            pop = [_ind(f"p{i}", (x, y * scale)) for i, (x, y) in enumerate(zip(xs, ys))]
            return sorted(ind.id for ind in environmental_selection_spea2(pop, 4))

        self.assertEqual(kept(1.0), kept(1e3))
        self.assertEqual(kept(1.0), kept(1e6))

    def test_spea2_reports_pareto_ranks(self):
        result = run_spea2_optimization(1200.0, pop_size=10, generations=3, seed=5)
        self.assertTrue(result["pareto_solutions"])
        self.assertTrue(all(sol["rank"] >= 1 for sol in result["all_solutions"]))
        self.assertTrue(all(sol["rank"] == 1 for sol in result["pareto_solutions"]))

    def test_moead_reports_each_design_once(self):
        result = run_moead_optimization(1200.0, pop_size=16, generations=6, seed=3)
        ids = [sol["id"] for sol in result["pareto_solutions"]]
        self.assertEqual(len(ids), len(set(ids)))
        all_ids = [sol["id"] for sol in result["all_solutions"]]
        self.assertEqual(len(all_ids), len(set(all_ids)))


class CityJsonTests(unittest.TestCase):
    def test_export_is_valid_cityjson_1_1(self):
        result = run_spea2_optimization(1200.0, pop_size=6, generations=2, seed=9)
        doc = export_to_cityjson(result["pareto_solutions"])
        self.assertEqual(doc["version"], "1.1")
        self.assertIn("transform", doc)
        self.assertTrue(all(isinstance(c, int) for v in doc["vertices"] for c in v))
        n = len(doc["vertices"])
        for obj in doc["CityObjects"].values():
            geometry = obj["geometry"][0]
            self.assertEqual(geometry["lod"], "1")
            for shell in geometry["boundaries"]:
                for surface in shell:
                    for ring in surface:
                        self.assertTrue(all(0 <= i < n for i in ring))
        # alternatives are laid out side by side, not stacked on one origin
        xs = sorted({v[0] for v in doc["vertices"]})
        if len(doc["CityObjects"]) > 1:
            self.assertGreater(len(xs), 2)


class BuildingCouplingTests(unittest.TestCase):
    def test_shadow_falls_north_of_a_tall_building_at_noon(self):
        buildings = [
            {"x": 0.0, "y": 0.0, "height_m": 6.0},    # low, north
            {"x": 0.0, "y": -20.0, "height_m": 40.0},  # tall, south
        ]
        result = evaluate_building_coupling(buildings, sun_altitude_deg=30.0, sun_azimuth_deg=180.0)
        self.assertGreater(result[0]["shadow_loss_pct"], 0.0)
        self.assertEqual(result[1]["shadow_loss_pct"], 0.0)

    def test_values_are_per_building(self):
        buildings = [
            {"x": 0.0, "y": 0.0, "height_m": 9.0},
            {"x": 8.0, "y": 0.0, "height_m": 30.0},
            {"x": 200.0, "y": 0.0, "height_m": 9.0},
        ]
        result = evaluate_building_coupling(buildings)
        self.assertNotEqual(result[0]["nearest_gap_m"], result[2]["nearest_gap_m"])
        self.assertNotEqual(result[0]["canyon_wind_speed_ms"], result[2]["canyon_wind_speed_ms"])


class ServerOriginTests(unittest.TestCase):
    def setUp(self):
        self.server = ParametricProcessServer(18120, "parametric_process/web")
        self.server.start()
        self.base = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self):
        self.server.stop()

    def _status(self, path, method="GET", headers=None, body=None):
        request = urllib.request.Request(self.base + path, data=body, headers=headers or {},
                                         method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_cross_site_simple_post_is_refused(self):
        body = json.dumps({"updates": [{"id": 1}]}).encode()
        self.assertEqual(self._status("/sync", "POST", {"Content-Type": "text/plain"}, body), 415)
        self.assertEqual(self._status("/sync", "POST", {
            "Content-Type": "application/json", "Origin": "https://example.com"}, body), 403)

    def test_rebinding_host_is_refused(self):
        self.assertEqual(self._status("/data.geojson", headers={"Host": "attacker.example:80"}), 403)

    def test_own_page_is_served(self):
        self.assertEqual(self._status("/data.geojson"), 200)
        self.assertEqual(self._status("/api/workflow/catalog", headers={
            "Origin": f"http://127.0.0.1:{self.server.port}"}), 200)


if __name__ == "__main__":
    unittest.main()
