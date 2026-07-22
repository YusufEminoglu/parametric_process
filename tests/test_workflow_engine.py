import json
import unittest
import urllib.request

from parametric_process.server import ParametricProcessServer
from parametric_process.workflow_engine import (
    WorkflowValidationError,
    execute_workflow,
    validate_workflow,
    workflow_catalog,
)


SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": 7,
            "properties": {"name": "Test block"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [60, 0], [60, 40], [0, 40], [0, 0]]],
            },
        }
    ],
}


def graph_from_types(*node_types, overrides=None):
    overrides = overrides or {}
    nodes = []
    for index, node_type in enumerate(node_types):
        node_id = f"node_{index}"
        nodes.append({"id": node_id, "type": node_type, "params": overrides.get(node_type, {})})
    edges = [
        {"source": nodes[index]["id"], "target": nodes[index + 1]["id"]}
        for index in range(len(nodes) - 1)
    ]
    return {"name": "Test workflow", "nodes": nodes, "edges": edges}


class WorkflowValidationTests(unittest.TestCase):
    def test_catalog_is_json_serializable(self):
        catalog = workflow_catalog()
        self.assertIn("evolutionary_solver", catalog["nodes"])
        json.dumps(catalog)

    def test_cycle_is_rejected(self):
        graph = graph_from_types("site_input", "zoning_rules")
        graph["edges"].append({"source": "node_1", "target": "node_0"})
        with self.assertRaises(WorkflowValidationError):
            validate_workflow(graph)

    def test_multiple_inputs_are_rejected(self):
        graph = {
            "nodes": [
                {"id": "site_a", "type": "site_input"},
                {"id": "site_b", "type": "site_input"},
                {"id": "rules", "type": "zoning_rules"},
            ],
            "edges": [
                {"source": "site_a", "target": "rules"},
                {"source": "site_b", "target": "rules"},
            ],
        }
        with self.assertRaises(WorkflowValidationError):
            validate_workflow(graph)


class WorkflowExecutionTests(unittest.TestCase):
    def balanced_graph(self, algorithm="nsga2"):
        return graph_from_types(
            "site_input",
            "zoning_rules",
            "evolutionary_solver",
            "topsis_ranker",
            "select_best",
            "qgis_output",
            overrides={
                "evolutionary_solver": {
                    "algorithm": algorithm,
                    "population": 6,
                    "generations": 2,
                    "seed": 17,
                }
            },
        )

    def test_balanced_graph_produces_qgis_updates(self):
        response = execute_workflow(self.balanced_graph(), SAMPLE_GEOJSON)
        result = response["result"]
        self.assertEqual(response["status"], "ok")
        self.assertGreater(len(result["pareto_solutions"]), 0)
        self.assertEqual(len(result["selected_solutions"]), 1)
        self.assertEqual(result["qgis_updates"][0]["id"], 7)

    def test_seeded_runs_are_reproducible(self):
        first = execute_workflow(self.balanced_graph(), SAMPLE_GEOJSON)["result"]
        second = execute_workflow(self.balanced_graph(), SAMPLE_GEOJSON)["result"]
        self.assertEqual(first["selected_solutions"], second["selected_solutions"])

    def test_all_solver_backends_execute(self):
        for algorithm in ("nsga2", "spea2", "nsga3", "moead"):
            with self.subTest(algorithm=algorithm):
                result = execute_workflow(self.balanced_graph(algorithm), SAMPLE_GEOJSON)["result"]
                self.assertGreater(len(result["pareto_solutions"]), 0)

    def test_ppud_rule_chain_executes(self):
        graph = graph_from_types(
            "site_input",
            "zoning_rules",
            "subdivide_block",
            "ppud_pipeline",
            overrides={
                "ppud_pipeline": {"incremental_steps": 1, "max_features": 1, "seed": 5},
            },
        )
        result = execute_workflow(graph, SAMPLE_GEOJSON)["result"]
        self.assertGreater(result["subdivision_summary"]["lot_count"], 0)
        self.assertGreater(result["ppud_summary"]["plot_count"], 0)

    def test_selected_scope_requires_selection(self):
        graph = graph_from_types("site_input")
        graph["nodes"][0]["params"] = {"scope": "selected"}
        with self.assertRaises(WorkflowValidationError):
            execute_workflow(graph, SAMPLE_GEOJSON)


class WorkflowHttpTests(unittest.TestCase):
    def setUp(self):
        self.server = ParametricProcessServer(18090, "parametric_process/web")
        self.server.update_geojson(json.dumps(SAMPLE_GEOJSON))
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.port}"

    def tearDown(self):
        self.server.stop()

    def test_catalog_and_run_endpoints(self):
        with urllib.request.urlopen(f"{self.base_url}/api/workflow/catalog", timeout=5) as response:
            catalog = json.load(response)
        self.assertIn("site_input", catalog["nodes"])

        graph = graph_from_types("site_input", "zoning_rules", "district_analysis")
        request = urllib.request.Request(
            f"{self.base_url}/api/workflow/run",
            data=json.dumps({"workflow": graph}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            result = json.load(response)
        self.assertEqual(result["status"], "ok")
        self.assertIn("district_metrics", result["result"])


if __name__ == "__main__":
    unittest.main()
