# -*- coding: utf-8 -*-
"""Safe, serializable node-graph runtime for Parametric Process.

The web modeler sends a small directed acyclic graph (DAG).  Nodes may only
invoke the operations registered in :data:`NODE_CATALOG`; arbitrary Python or
Processing expressions are deliberately unsupported.  This keeps saved
workflows portable across QGIS 3/4 and safe to execute from the local cockpit.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence


WORKFLOW_SCHEMA_VERSION = 1
MAX_NODES = 64
MAX_EDGES = 128
MAX_FEATURES = 250


class WorkflowValidationError(ValueError):
    """Raised when a workflow cannot be executed safely."""


def _param(kind: str, default: Any, **kwargs: Any) -> Dict[str, Any]:
    spec = {"type": kind, "default": default}
    spec.update(kwargs)
    return spec


NODE_CATALOG: Dict[str, Dict[str, Any]] = {
    "site_input": {
        "label": "QGIS Site Layer",
        "category": "Input",
        "color": "#2563eb",
        "description": "Reads the live polygon layer exported by QGIS.",
        "accepts_input": False,
        "params": {
            "scope": _param("select", "all", options=["all", "selected"]),
        },
    },
    "zoning_rules": {
        "label": "Zoning Envelope",
        "category": "Rules",
        "color": "#f59e0b",
        "description": "Applies BCR, FAR and height constraints to downstream solvers.",
        "accepts_input": True,
        "params": {
            "max_bcr": _param("number", 0.45, min=0.05, max=0.95, step=0.05),
            "max_far": _param("number", 2.5, min=0.1, max=15.0, step=0.1),
            "max_height": _param("number", 18.0, min=3.0, max=300.0, step=1.0),
        },
    },
    "subdivide_block": {
        "label": "Shape Grammar",
        "category": "Generate",
        "color": "#8b5cf6",
        "description": "Subdivides blocks with a frontage, grid, perimeter, organic, radial or hybrid rule.",
        "accepts_input": True,
        "params": {
            "strategy": _param(
                "select", "perimeter",
                options=["frontage", "grid", "perimeter", "organic", "radial", "hybrid"],
            ),
            "target_frontage": _param("number", 18.0, min=4.0, max=100.0, step=1.0),
            "min_lot_area": _param("number", 250.0, min=20.0, max=10000.0, step=10.0),
        },
    },
    "ppud_pipeline": {
        "label": "PPUD Fabric",
        "category": "Generate",
        "color": "#7c3aed",
        "description": "Runs plot layout, building configuration and incremental fabric formation.",
        "accepts_input": True,
        "params": {
            "strategy": _param(
                "select", "perimeter",
                options=["frontage", "grid", "perimeter", "organic", "radial", "hybrid"],
            ),
            "block_typology": _param(
                "select", "PerimeterBlock",
                options=["PerimeterBlock", "UrbanBlock", "Superblock", "Campus", "LinearBlock"],
            ),
            "incremental_steps": _param("integer", 3, min=1, max=12, step=1),
            "climate_feedback": _param("boolean", True),
            "max_features": _param("integer", 5, min=1, max=25, step=1),
            "seed": _param("integer", 42, min=0, max=2147483646, step=1),
        },
    },
    "evolutionary_solver": {
        "label": "Evolutionary Solver",
        "category": "Optimize",
        "color": "#10b981",
        "description": "Executes NSGA-II, SPEA-2, NSGA-III or MOEA/D against active rules.",
        "accepts_input": True,
        "params": {
            "algorithm": _param("select", "nsga2", options=["nsga2", "spea2", "nsga3", "moead"]),
            "population": _param("integer", 24, min=4, max=100, step=2),
            "generations": _param("integer", 8, min=1, max=50, step=1),
            "crossover_rate": _param("number", 0.8, min=0.0, max=1.0, step=0.05),
            "mutation_rate": _param("number", 0.15, min=0.0, max=1.0, step=0.01),
            "seed": _param("integer", 42, min=0, max=2147483646, step=1),
            "objectives": _param(
                "objectives",
                [
                    {"name": "planx_score", "direction": "max"},
                    {"name": "gfa", "direction": "max"},
                    {"name": "carbon_kg", "direction": "min"},
                    {"name": "wind_ventilation", "direction": "max"},
                ],
            ),
        },
    },
    "district_analysis": {
        "label": "District Physics",
        "category": "Analyze",
        "color": "#0891b2",
        "description": "Evaluates shadow, canyon wind, comfort and stormwater coupling.",
        "accepts_input": True,
        "params": {},
    },
    "topsis_ranker": {
        "label": "TOPSIS Ranker",
        "category": "Decide",
        "color": "#db2777",
        "description": "Ranks the Pareto population with multi-criteria ideal-distance scoring.",
        "accepts_input": True,
        "params": {},
    },
    "select_best": {
        "label": "Select Best",
        "category": "Decide",
        "color": "#e11d48",
        "description": "Selects one or more preferred candidates for preview and GIS output.",
        "accepts_input": True,
        "params": {
            "method": _param("select", "topsis", options=["topsis", "planx_score", "lowest_carbon", "max_gfa"]),
            "count": _param("integer", 1, min=1, max=10, step=1),
        },
    },
    "qgis_output": {
        "label": "QGIS Output",
        "category": "Output",
        "color": "#0f766e",
        "description": "Builds attribute updates that can be reviewed and synced to the source layer.",
        "accepts_input": True,
        "params": {
            "apply_mode": _param("select", "all", options=["all", "selected"]),
        },
    },
}


ALLOWED_OBJECTIVES = {
    "gfa", "planx_score", "wind_ventilation", "solar_radiation_kwh",
    "pollution_dispersion", "sky_view_factor", "constraint_penalty",
    "carbon_kg", "daylight_index", "runoff_m3", "utci_score",
    "roi_percentage", "pv_yield_mwh", "open_space_ratio",
    "pedestrian_wind_comfort", "far", "bcr", "height_m",
}


def workflow_catalog() -> Dict[str, Any]:
    """Return a JSON-safe copy of the public node catalog."""
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "nodes": deepcopy(NODE_CATALOG),
    }


def _coerce_param(name: str, value: Any, spec: Mapping[str, Any]) -> Any:
    kind = spec.get("type")
    if kind == "boolean":
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if kind in {"number", "integer"}:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise WorkflowValidationError(f"Parameter '{name}' must be numeric") from exc
        minimum = float(spec.get("min", number))
        maximum = float(spec.get("max", number))
        if number < minimum or number > maximum:
            raise WorkflowValidationError(
                f"Parameter '{name}' must be between {minimum:g} and {maximum:g}"
            )
        return int(round(number)) if kind == "integer" else number
    if kind == "select":
        result = str(value)
        if result not in spec.get("options", []):
            raise WorkflowValidationError(f"Unsupported value '{result}' for parameter '{name}'")
        return result
    if kind == "objectives":
        if not isinstance(value, list) or not value:
            raise WorkflowValidationError("At least one optimization objective is required")
        objectives = []
        seen = set()
        for item in value:
            if not isinstance(item, Mapping):
                raise WorkflowValidationError("Objective entries must be objects")
            objective_name = str(item.get("name", ""))
            direction = str(item.get("direction", "max")).lower()
            if objective_name not in ALLOWED_OBJECTIVES or direction not in {"min", "max"}:
                raise WorkflowValidationError(f"Invalid objective '{objective_name}'")
            if objective_name not in seen:
                objectives.append({"name": objective_name, "direction": direction})
                seen.add(objective_name)
        return objectives
    return value


def _normalized_params(node: Mapping[str, Any]) -> Dict[str, Any]:
    node_type = str(node.get("type", ""))
    catalog_spec = NODE_CATALOG[node_type]
    supplied = node.get("params", {})
    if supplied is None:
        supplied = {}
    if not isinstance(supplied, Mapping):
        raise WorkflowValidationError(f"Node '{node.get('id')}' parameters must be an object")
    result = {}
    for name, spec in catalog_spec["params"].items():
        value = supplied.get(name, deepcopy(spec.get("default")))
        result[name] = _coerce_param(name, value, spec)
    return result


def validate_workflow(graph: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate and normalize a workflow, returning its topological order."""
    if not isinstance(graph, Mapping):
        raise WorkflowValidationError("Workflow must be a JSON object")
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not isinstance(nodes, list) or not nodes:
        raise WorkflowValidationError("Workflow must contain at least one node")
    if not isinstance(edges, list):
        raise WorkflowValidationError("Workflow edges must be a list")
    if len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        raise WorkflowValidationError(
            f"Workflow exceeds the limit of {MAX_NODES} nodes and {MAX_EDGES} edges"
        )

    normalized_nodes = []
    node_by_id: Dict[str, Dict[str, Any]] = {}
    for raw_node in nodes:
        if not isinstance(raw_node, Mapping):
            raise WorkflowValidationError("Every workflow node must be an object")
        node_id = str(raw_node.get("id", "")).strip()
        node_type = str(raw_node.get("type", "")).strip()
        if not node_id or len(node_id) > 80:
            raise WorkflowValidationError("Every node needs a short, non-empty id")
        if node_id in node_by_id:
            raise WorkflowValidationError(f"Duplicate node id '{node_id}'")
        if node_type not in NODE_CATALOG:
            raise WorkflowValidationError(f"Unknown node type '{node_type}'")
        normalized = {
            "id": node_id,
            "type": node_type,
            "params": _normalized_params(raw_node),
        }
        normalized_nodes.append(normalized)
        node_by_id[node_id] = normalized

    adjacency: Dict[str, List[str]] = {node_id: [] for node_id in node_by_id}
    indegree: Dict[str, int] = {node_id: 0 for node_id in node_by_id}
    incoming: Dict[str, str] = {}
    normalized_edges = []
    seen_edges = set()
    for raw_edge in edges:
        if not isinstance(raw_edge, Mapping):
            raise WorkflowValidationError("Every edge must be an object")
        source = str(raw_edge.get("source", "")).strip()
        target = str(raw_edge.get("target", "")).strip()
        if source not in node_by_id or target not in node_by_id:
            raise WorkflowValidationError(f"Edge '{source} -> {target}' references a missing node")
        if source == target:
            raise WorkflowValidationError(f"Node '{source}' cannot connect to itself")
        if (source, target) in seen_edges:
            continue
        if target in incoming:
            raise WorkflowValidationError(
                f"Node '{target}' has multiple inputs; insert separate branches instead"
            )
        if not NODE_CATALOG[node_by_id[target]["type"]]["accepts_input"]:
            raise WorkflowValidationError(f"Input node '{target}' cannot accept a connection")
        seen_edges.add((source, target))
        incoming[target] = source
        adjacency[source].append(target)
        indegree[target] += 1
        normalized_edges.append({"source": source, "target": target})

    roots = [node_id for node_id, degree in indegree.items() if degree == 0]
    if not roots:
        raise WorkflowValidationError("Workflow has no input root")
    for node_id in roots:
        if node_by_id[node_id]["type"] != "site_input":
            raise WorkflowValidationError(f"Disconnected node '{node_id}' must be connected to a site input")

    queue = deque(roots)
    order = []
    while queue:
        node_id = queue.popleft()
        order.append(node_id)
        for target in adjacency[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(order) != len(normalized_nodes):
        raise WorkflowValidationError("Workflow contains a cycle")

    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "name": str(graph.get("name", "Untitled Workflow"))[:120],
        "nodes": normalized_nodes,
        "edges": normalized_edges,
        "order": order,
        "incoming": incoming,
        "adjacency": adjacency,
    }


def _ring_area(ring: Sequence[Mapping[str, Any]]) -> float:
    if len(ring) < 3:
        return 0.0
    total = 0.0
    for index, point in enumerate(ring):
        nxt = ring[(index + 1) % len(ring)]
        total += float(point["x"]) * float(nxt["y"]) - float(nxt["x"]) * float(point["y"])
    return abs(total) * 0.5


def _extract_ring(feature: Mapping[str, Any]) -> List[Dict[str, float]]:
    geometry = feature.get("geometry", {})
    coords = geometry.get("coordinates", []) if isinstance(geometry, Mapping) else []
    geom_type = geometry.get("type") if isinstance(geometry, Mapping) else None
    if geom_type == "Polygon" and coords:
        source_ring = coords[0]
    elif geom_type == "MultiPolygon" and coords and coords[0]:
        source_ring = coords[0][0]
    else:
        return []
    ring = []
    for point in source_ring:
        if not isinstance(point, Sequence) or len(point) < 2:
            continue
        try:
            ring.append({"x": float(point[0]), "y": float(point[1])})
        except (TypeError, ValueError):
            continue
    if len(ring) > 3 and ring[0] == ring[-1]:
        ring.pop()
    return ring if len(ring) >= 3 else []


def _site_state(geojson: Mapping[str, Any], scope: str, selected_fid: Any) -> Dict[str, Any]:
    if scope == 'selected' and selected_fid is None:
        raise WorkflowValidationError('Select a parcel in the 3D cockpit before using selected scope')
    raw_features = geojson.get("features", []) if isinstance(geojson, Mapping) else []
    if not isinstance(raw_features, list):
        raise WorkflowValidationError("GeoJSON features must be a list")
    features = []
    for index, feature in enumerate(raw_features[:MAX_FEATURES]):
        if not isinstance(feature, Mapping):
            continue
        feature_id = feature.get("id", feature.get("properties", {}).get("id", index))
        if scope == "selected" and selected_fid is not None and str(feature_id) != str(selected_fid):
            continue
        ring = _extract_ring(feature)
        area = _ring_area(ring)
        if area <= 0:
            continue
        features.append({"id": feature_id, "ring": ring, "area": area})
    if not features:
        if scope == "selected":
            raise WorkflowValidationError("The selected parcel was not found in the live QGIS layer")
        raise WorkflowValidationError("The live QGIS layer contains no valid polygon features")
    total_area = sum(feature["area"] for feature in features)
    return {
        "features": features,
        "feature_count": len(features),
        "site_area": total_area,
        "parcel_area": total_area / len(features),
        "zoning": {"max_bcr": 0.45, "max_far": 2.5, "max_height": 18.0},
        "objective_specs": None,
    }


def _node_site_input(_: Dict[str, Any], params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return _site_state(context["geojson"], params["scope"], context.get("selected_fid"))


def _node_zoning_rules(state: Dict[str, Any], params: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(state)
    result["zoning"] = {
        "max_bcr": params["max_bcr"],
        "max_far": params["max_far"],
        "max_height": params["max_height"],
    }
    return result


def _node_subdivide_block(state: Dict[str, Any], params: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    from .procedural_grammar import subdivide_parcel_block_strategy

    subdivisions = []
    total_lots = 0
    for feature in state["features"]:
        lots = subdivide_parcel_block_strategy(
            feature["ring"],
            strategy=params["strategy"],
            target_frontage=params["target_frontage"],
            min_lot_area=params["min_lot_area"],
        )
        subdivisions.append({"feature_id": feature["id"], "lots": lots, "lot_count": len(lots)})
        total_lots += len(lots)
    result = dict(state)
    result["subdivisions"] = subdivisions
    result["subdivision_summary"] = {
        "strategy": params["strategy"],
        "lot_count": total_lots,
    }
    return result


def _node_ppud_pipeline(state: Dict[str, Any], params: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    from .ppud_pipeline import PpudPipeline

    zoning = state["zoning"]
    results = []
    max_features = min(params["max_features"], len(state["features"]))
    for index, feature in enumerate(state["features"][:max_features]):
        pipeline = PpudPipeline(seed=params["seed"] + index)
        results.append(pipeline.run_full_pipeline(feature["ring"], {
            "strategy": params["strategy"],
            "block_typology": params["block_typology"],
            "max_bcr": zoning["max_bcr"],
            "max_far": zoning["max_far"],
            "max_height": zoning["max_height"],
            "incremental_steps": params["incremental_steps"],
            "climate_feedback": params["climate_feedback"],
            "parent_block_id": str(feature["id"]),
        }))
    result = dict(state)
    result["ppud_results"] = results
    result["ppud_summary"] = {
        "processed_features": len(results),
        "plot_count": sum(item["summary"]["plot_count"] for item in results),
        "total_gfa_m2": round(sum(item["summary"]["total_gfa_m2"] for item in results), 1),
    }
    return result


def _node_evolutionary_solver(state: Dict[str, Any], params: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    from . import nsga2_engine

    solvers = {
        "nsga2": nsga2_engine.run_nsga2_optimization,
        "spea2": nsga2_engine.run_spea2_optimization,
        "nsga3": nsga2_engine.run_nsga3_optimization,
        "moead": nsga2_engine.run_moead_optimization,
    }
    zoning = state["zoning"]
    objectives = params["objectives"]
    optimization = solvers[params["algorithm"]](
        parcel_area=state["parcel_area"],
        objective_specs=objectives,
        pop_size=params["population"],
        generations=params["generations"],
        crossover_rate=params["crossover_rate"],
        mutation_rate=params["mutation_rate"],
        max_bcr=zoning["max_bcr"],
        max_far=zoning["max_far"],
        max_height=zoning["max_height"],
        seed=params["seed"],
    )
    result = dict(state)
    result["optimization"] = optimization
    result["objective_specs"] = objectives
    result["pareto_solutions"] = optimization.get("pareto_solutions", [])
    result["all_solutions"] = optimization.get("all_solutions", [])
    return result


def _solutions_from_state(state: Mapping[str, Any]) -> List[Dict[str, Any]]:
    solutions = state.get("ranked_solutions") or state.get("pareto_solutions") or state.get("all_solutions")
    return list(solutions or [])


def _node_district_analysis(state: Dict[str, Any], _: Dict[str, Any], __: Dict[str, Any]) -> Dict[str, Any]:
    from .district_engine import evaluate_district_coupling

    solutions = _solutions_from_state(state)
    if solutions:
        buildings = solutions[: min(len(state["features"]), len(solutions), 25)]
    else:
        buildings = [
            {
                "id": feature["id"],
                "metrics": {
                    "height_m": 12.0,
                    "footprint_area": feature["area"] * 0.45,
                    "gfa": feature["area"] * 1.8,
                    "planx_score": 75.0,
                },
            }
            for feature in state["features"]
        ]
    result = dict(state)
    result["district_metrics"] = evaluate_district_coupling(buildings, state["site_area"])
    return result


def _node_topsis_ranker(state: Dict[str, Any], _: Dict[str, Any], __: Dict[str, Any]) -> Dict[str, Any]:
    from .nsga2_engine import topsis_rank_solutions

    solutions = state.get("pareto_solutions") or state.get("all_solutions") or []
    if not solutions:
        raise WorkflowValidationError("TOPSIS requires an upstream evolutionary solver")
    ranked = topsis_rank_solutions(solutions, objective_specs=state.get("objective_specs"))
    result = dict(state)
    result["ranked_solutions"] = ranked
    return result


def _node_select_best(state: Dict[str, Any], params: Dict[str, Any], _: Dict[str, Any]) -> Dict[str, Any]:
    solutions = _solutions_from_state(state)
    if not solutions:
        raise WorkflowValidationError("Select Best requires upstream candidate solutions")
    method = params["method"]
    if method == "topsis":
        if not state.get("ranked_solutions"):
            from .nsga2_engine import topsis_rank_solutions
            solutions = topsis_rank_solutions(solutions, objective_specs=state.get("objective_specs"))
        ordered = solutions
    elif method == "lowest_carbon":
        ordered = sorted(solutions, key=lambda item: float(item.get("metrics", {}).get("carbon_kg", 0.0)))
    elif method == "max_gfa":
        ordered = sorted(solutions, key=lambda item: float(item.get("metrics", {}).get("gfa", 0.0)), reverse=True)
    else:
        ordered = sorted(solutions, key=lambda item: float(item.get("metrics", {}).get("planx_score", 0.0)), reverse=True)
    result = dict(state)
    result["selected_solutions"] = ordered[: params["count"]]
    return result


def _solution_update(feature_id: Any, solution: Mapping[str, Any], zoning: Mapping[str, Any]) -> Dict[str, Any]:
    genotype = solution.get("genotype", {})
    metrics = solution.get("metrics", {})
    return {
        "id": feature_id,
        "far": metrics.get("far", 0.0),
        "bcr": metrics.get("bcr", 0.0),
        "gfa": metrics.get("gfa", 0.0),
        "setback": genotype.get("setback", 0.0),
        "scale_x": genotype.get("scale_x", 1.0),
        "scale_y": genotype.get("scale_y", 1.0),
        "floors": genotype.get("floors", 1),
        "usage": genotype.get("usage", "MixedUse"),
        "floor_h": genotype.get("floor_height", 3.0),
        "typology": genotype.get("typology", "Tower"),
        "max_bcr": zoning.get('max_bcr', 0.45),
        "max_far": zoning.get('max_far', 2.5),
        "max_height": zoning.get('max_height', 18.0),
        "roof_style": genotype.get("roof_style", "Flat"),
        "height_m": metrics.get("height_m", 0.0),
        "z_base": 0.0,
        "z_top": metrics.get("height_m", 0.0),
        "plan_score": metrics.get("planx_score", 0.0),
        "const_load": metrics.get("constraint_penalty", 0.0),
        "pop_est": round(float(metrics.get('gfa', 0.0)) / 35.0),
        "carbon": metrics.get("carbon_kg", 0.0),
        "runoff": metrics.get("runoff_m3", 0.0),
        "open_space": metrics.get("open_space_ratio", 0.0),
        "wind_score": metrics.get("wind_ventilation", 0.0),
        "solar_kwh": metrics.get("solar_radiation_kwh", 0.0),
        "poll_disp": metrics.get("pollution_dispersion", 0.0),
        "svf_ratio": metrics.get("sky_view_factor", 0.0),
        "canyon_hw": metrics.get("street_canyon_hw", 0.0),
        "roi_yield": metrics.get("roi_percentage", 0.0),
        "mrt_temp": metrics.get("mrt_temp_celsius", 0.0),
        "utci_score": metrics.get("utci_score", 0.0),
        "pv_kwh": metrics.get("pv_yield_mwh", 0.0),
        "pareto_rank": solution.get("rank", solution.get("topsis_rank", 1)),
        "wallacei_id": solution.get("id", "workflow_solution"),
    }


def _node_qgis_output(state: Dict[str, Any], params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    solutions = state.get("selected_solutions") or _solutions_from_state(state)
    if not solutions:
        raise WorkflowValidationError("QGIS Output requires an upstream solution selection")
    features = state["features"]
    if params["apply_mode"] == "selected" and context.get("selected_fid") is not None:
        features = [feature for feature in features if str(feature["id"]) == str(context["selected_fid"])]
    updates = [
        _solution_update(feature["id"], solutions[index % len(solutions)], state['zoning'])
        for index, feature in enumerate(features)
    ]
    result = dict(state)
    result["qgis_updates"] = updates
    return result


NODE_EXECUTORS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
    "site_input": _node_site_input,
    "zoning_rules": _node_zoning_rules,
    "subdivide_block": _node_subdivide_block,
    "ppud_pipeline": _node_ppud_pipeline,
    "evolutionary_solver": _node_evolutionary_solver,
    "district_analysis": _node_district_analysis,
    "topsis_ranker": _node_topsis_ranker,
    "select_best": _node_select_best,
    "qgis_output": _node_qgis_output,
}


def _node_summary(node_type: str, state: Mapping[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"type": node_type, "status": "completed"}
    if node_type == "site_input":
        summary.update(feature_count=state["feature_count"], site_area=round(state["site_area"], 2))
    elif node_type == "subdivide_block":
        summary.update(state.get("subdivision_summary", {}))
    elif node_type == "ppud_pipeline":
        summary.update(state.get("ppud_summary", {}))
    elif node_type == "evolutionary_solver":
        summary.update(
            population=len(state.get("all_solutions", [])),
            pareto_count=len(state.get("pareto_solutions", [])),
        )
    elif node_type == "district_analysis":
        summary["metrics"] = state.get("district_metrics", {})
    elif node_type == "topsis_ranker":
        summary["ranked_count"] = len(state.get("ranked_solutions", []))
    elif node_type == "select_best":
        summary["selected_count"] = len(state.get("selected_solutions", []))
    elif node_type == "qgis_output":
        summary["update_count"] = len(state.get("qgis_updates", []))
    return summary


def _compact_result(states: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {}
    for state in states:
        for key in (
            "feature_count", "site_area", "zoning", "subdivision_summary", "ppud_summary",
            "district_metrics", "objective_specs", "pareto_solutions", "ranked_solutions",
            "selected_solutions", "qgis_updates",
        ):
            if key in state:
                if key == "qgis_updates":
                    merged.setdefault(key, []).extend(state[key])
                else:
                    merged[key] = state[key]
    merged.setdefault("qgis_updates", [])
    merged.setdefault("selected_solutions", [])
    merged.setdefault("pareto_solutions", [])
    return merged


def execute_workflow(
    graph: Mapping[str, Any],
    geojson: Mapping[str, Any],
    selected_fid: Any = None,
) -> Dict[str, Any]:
    """Validate and execute a workflow against live GeoJSON data."""
    normalized = validate_workflow(graph)
    nodes = {node["id"]: node for node in normalized["nodes"]}
    states: Dict[str, Dict[str, Any]] = {}
    node_results = []
    context = {"geojson": geojson, "selected_fid": selected_fid}

    for node_id in normalized["order"]:
        node = nodes[node_id]
        source_id = normalized["incoming"].get(node_id)
        input_state = states[source_id] if source_id else {}
        try:
            output_state = NODE_EXECUTORS[node["type"]](input_state, node["params"], context)
        except WorkflowValidationError:
            raise
        except Exception as exc:
            label = NODE_CATALOG[node["type"]]["label"]
            raise WorkflowValidationError(f"{label} failed: {exc}") from exc
        states[node_id] = output_state
        summary = _node_summary(node["type"], output_state)
        summary["node_id"] = node_id
        node_results.append(summary)

    sinks = [node_id for node_id in normalized["order"] if not normalized["adjacency"][node_id]]
    return {
        "status": "ok",
        "workflow": {"name": normalized["name"], "schema_version": WORKFLOW_SCHEMA_VERSION},
        "execution_order": normalized["order"],
        "node_results": node_results,
        "result": _compact_result(states[node_id] for node_id in sinks),
    }
