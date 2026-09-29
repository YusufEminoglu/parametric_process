"""Algorithm-level tests for the survivor-selection and scalarisation cores.

These pin the defining property of each algorithm rather than a snapshot of
its output: NSGA-III must spread survivors over reference directions,
MOEA/D's Tchebycheff must not depend on an objective's unit, and every
reported metric must actually respond to the design.
"""
import math
import unittest

from parametric_process.nsga2_engine import (
    ProcessIndividual,
    _LCG,
    evaluate_phenotype,
    fast_non_dominated_sort,
    generate_das_dennis_ref_points,
    nsga3_environmental_selection,
    nsga3_normalize,
    perpendicular_distance,
    run_moead_optimization,
    run_nsga3_optimization,
    tchebycheff_normalized,
)


def _ind(name, fitness):
    ind = ProcessIndividual(name, {})
    ind.fitness_vector = list(fitness)
    ind.metrics = {"constraint_penalty": 0.0}
    return ind


def _associations(individuals, refs):
    norm = nsga3_normalize([i.fitness_vector for i in individuals])
    out = []
    for v in norm:
        out.append(min(range(len(refs)), key=lambda j: perpendicular_distance(v, refs[j])))
    return out


class Nsga3Tests(unittest.TestCase):
    def test_normalisation_maps_the_hyperplane_intercepts_to_one(self):
        norm = nsga3_normalize([[2.0, 0.0], [0.0, 4.0], [1.0, 2.0]])
        for got, want in zip(norm, [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]):
            for g, w in zip(got, want):
                self.assertAlmostEqual(g, w, places=9)

    def test_normalisation_is_unit_free(self):
        pts = [[0.1, 0.9], [0.4, 0.55], [0.8, 0.15], [1.0, 0.0], [0.0, 1.0]]
        scaled = [[a * 1_000_000.0, b] for a, b in pts]
        for got, want in zip(nsga3_normalize(scaled), nsga3_normalize(pts)):
            for g, w in zip(got, want):
                self.assertAlmostEqual(g, w, places=9)

    def test_das_dennis_count_and_simplex(self):
        refs = generate_das_dennis_ref_points(3, partitions=4)
        self.assertEqual(len(refs), math.comb(4 + 3 - 1, 3 - 1))
        self.assertTrue(all(abs(sum(r) - 1.0) < 1e-12 for r in refs))

    def test_last_front_is_niched_one_per_reference_direction_first(self):
        # A dense cluster at one end of a linear front and a few lone points:
        # crowding distance keeps the extremes and wide gaps, NSGA-III must
        # first give every represented reference direction one survivor.
        cluster = [(0.02 * i, 1.0 - 0.02 * i) for i in range(10)]
        lone = [(0.5, 0.5), (0.75, 0.25), (1.0, 0.0)]
        front = [_ind(f"p{i}", f) for i, f in enumerate(cluster + lone)]
        refs = generate_das_dennis_ref_points(2, partitions=4)  # 5 directions
        assoc = dict(zip((i.id for i in front), _associations(front, refs)))
        represented = len(set(assoc.values()))
        for size in range(2, represented + 1):
            with self.subTest(pop_size=size):
                chosen = nsga3_environmental_selection([list(front)], size, refs, rng=_LCG(7))
                self.assertEqual(len(chosen), size)
                self.assertEqual(len({assoc[c.id] for c in chosen}), size)

    def test_niching_counts_survivors_from_earlier_fronts(self):
        # Front 1 already fills the left (x2) and right (x1) reference
        # directions; the partial front 2 spans all five. NSGA-III must spend
        # the three free slots on the empty middle directions. Crowding
        # distance looks at front 2 alone and takes its two extremes first.
        first = [_ind("A", (0.0, 0.5)), _ind("B", (0.05, 0.45)), _ind("C", (0.7, 0.0))]
        second = [_ind(f"s{i}", (0.05 + 0.25 * i, 1.0 - 0.25 * i)) for i in range(5)]
        fronts = fast_non_dominated_sort(first + second)
        self.assertEqual({i.id for i in fronts[0]}, {"A", "B", "C"})
        refs = generate_das_dennis_ref_points(2, partitions=4)
        chosen = nsga3_environmental_selection(fronts, 6, refs, rng=_LCG(3))
        self.assertEqual({c.id for c in chosen} - {"A", "B", "C"}, {"s1", "s2", "s3"})

    def test_whole_fronts_are_kept_before_niching(self):
        good = [_ind("a", (0.0, 1.0)), _ind("b", (1.0, 0.0))]
        worse = [_ind(f"w{i}", (0.5 + 0.1 * i, 1.5 - 0.1 * i)) for i in range(5)]
        fronts = fast_non_dominated_sort(good + worse)
        chosen = nsga3_environmental_selection(fronts, 4, generate_das_dennis_ref_points(2, 4), rng=_LCG(1))
        self.assertEqual(len(chosen), 4)
        self.assertTrue({"a", "b"} <= {c.id for c in chosen})

    def test_seeded_nsga3_run_is_reproducible_and_keeps_its_size(self):
        kwargs = dict(parcel_area=2400, pop_size=14, generations=5, seed=20260929)
        first = run_nsga3_optimization(**kwargs)
        second = run_nsga3_optimization(**kwargs)
        self.assertEqual(first["pareto_solutions"], second["pareto_solutions"])
        self.assertEqual(len(first["all_solutions"]), 14)
        self.assertEqual(first["run_manifest"]["algorithm"], "NSGA-III")


class MoeadTests(unittest.TestCase):
    def test_tchebycheff_ranking_does_not_depend_on_units(self):
        cands = [(120.0, 0.30), (80.0, 0.10), (100.0, 0.20), (95.0, 0.45)]
        ideal, nadir = [80.0, 0.10], [120.0, 0.45]
        w = [0.5, 0.5]
        base = sorted(range(4), key=lambda i: tchebycheff_normalized(cands[i], w, ideal, nadir))
        k = 1_000_000.0
        scaled = [(a * k, b) for a, b in cands]
        rank = sorted(range(4), key=lambda i: tchebycheff_normalized(
            scaled[i], w, [ideal[0] * k, ideal[1]], [nadir[0] * k, nadir[1]]))
        self.assertEqual(rank, base)
        # the raw form is dominated by the large-unit objective: a different order
        raw = sorted(range(4), key=lambda i: max(w[0] * abs(scaled[i][0] - ideal[0] * k),
                                                 w[1] * abs(scaled[i][1] - ideal[1])))
        self.assertNotEqual(raw, base)

    def test_zero_weight_objective_is_not_ignored(self):
        worse = tchebycheff_normalized([0.0, 1.0], [1.0, 0.0], [0.0, 0.0], [1.0, 1.0])
        self.assertGreater(worse, 0.0)

    def test_seeded_moead_run_is_reproducible(self):
        kwargs = dict(parcel_area=2400, pop_size=12, generations=4, seed=11)
        self.assertEqual(run_moead_optimization(**kwargs)["pareto_solutions"],
                         run_moead_optimization(**kwargs)["pareto_solutions"])


class MetricResponseTests(unittest.TestCase):
    def test_sol_air_temperature_follows_roof_albedo(self):
        temps = {roof: evaluate_phenotype({"floors": 4, "roof_style": roof}, 2400)["sol_air_temp_celsius"]
                 for roof in ("Flat", "Hipped", "Gable", "Mansard")}
        self.assertEqual(len(set(temps.values())), 4)
        # albedo 0.30 (flat) absorbs most, 0.45 (hipped) least
        self.assertEqual(max(temps, key=temps.get), "Flat")
        self.assertEqual(min(temps, key=temps.get), "Hipped")
        self.assertAlmostEqual(temps["Flat"], round(30.0 + 0.70 * 900.0 / 17.0 - 3.9, 1))


if __name__ == "__main__":
    unittest.main()
