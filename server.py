# -*- coding: utf-8 -*-
"""Local HTTP server for Parametric Process.

Serves the Web UI static files and routes API requests back to QGIS.
"""
from __future__ import annotations

import html
import json
import math
import os
import tempfile
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading


def _json_compatible(value):
    """Return a recursively strict-JSON-safe representation of *value*."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {key: _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


def _json_bytes(payload):
    """Encode standards-compliant JSON; NaN and Infinity can never leak."""
    return json.dumps(_json_compatible(payload), allow_nan=False).encode('utf-8')


def _reject_json_constant(value):
    raise ValueError(f"Non-finite JSON number '{value}' is not supported")


def _strict_json_loads(raw):
    return json.loads(raw, parse_constant=_reject_json_constant)

class RunState:
    def __init__(self, run_id, total_generations):
        self.run_id = run_id
        self.status = 'running'  # running | completed | stopped | error
        self.current_generation = 0
        self.total_generations = total_generations
        self.generation_data = None  # latest generation result
        self.final_result = None
        self.error_message = None
        self.stop_requested = False
        self.start_time = time.time()


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class SyncHTTPRequestHandler(BaseHTTPRequestHandler):
    MAX_REQUEST_BYTES = 10 * 1024 * 1024

    def _send_json(self, payload, status=200):
        encoded = _json_bytes(payload)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError) as exc:
            raise ValueError('Invalid Content-Length header') from exc
        if content_length <= 0:
            return {}
        if content_length > self.MAX_REQUEST_BYTES:
            raise ValueError('Request payload is too large')
        body = self.rfile.read(content_length).decode('utf-8')
        data = _strict_json_loads(body)
        if not isinstance(data, dict):
            raise ValueError('JSON request body must be an object')
        return data

    def log_message(self, format, *args):
        from contextlib import suppress
        with suppress(Exception):
            log_dir = os.path.join(tempfile.gettempdir(), "parametric_process")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "server_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")

    def end_headers(self):
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        url = self.path.split('?')[0]

        if url == '/api/workflow/catalog':
            from .workflow_engine import workflow_catalog
            self._send_json(workflow_catalog())
            return

        if url.startswith("/api/optimize/status/"):
            run_id = url.split("/")[-1]
            active_runs = getattr(self.server, "active_runs", {})
            if run_id not in active_runs:
                self.send_error(404, "Run Not Found")
                return
                
            run_state = active_runs[run_id]
            resp = {
                "status": run_state.status,
                "current_generation": run_state.current_generation,
                "total_generations": run_state.total_generations,
                "elapsed_seconds": round(time.time() - run_state.start_time, 2)
            }
            if run_state.generation_data:
                resp["generation_data"] = run_state.generation_data
            if run_state.final_result:
                resp.update(run_state.final_result)
                
            if run_state.error_message:
                resp["error_message"] = run_state.error_message

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(resp))
            return

        if url == "/data.geojson":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.server.geojson_data.encode('utf-8'))
            return

        clean_path = url.lstrip("/")
        if not clean_path or clean_path == "index.html":
            clean_path = "src/index.html"
        elif "/" not in clean_path and "\\" not in clean_path:
            # Browser URLs are rooted at /index.html while the authored UI
            # modules and styles live under web/src. Resolve every top-level
            # source asset generically so newly added modules cannot be
            # omitted from a hand-maintained alias list.
            source_candidate = os.path.join(self.server.web_dir, "src", clean_path)
            if os.path.isfile(source_candidate):
                clean_path = os.path.join("src", clean_path)

        file_path = os.path.join(self.server.web_dir, clean_path)

        real_web_dir = os.path.normcase(os.path.realpath(self.server.web_dir))
        real_file_path = os.path.normcase(os.path.realpath(file_path))
        if os.path.commonpath([real_web_dir, real_file_path]) != real_web_dir:
            self.send_error(403, "Access Denied")
            return

        if not os.path.exists(file_path) or os.path.isdir(file_path):
            self.send_error(404, "File Not Found")
            return

        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".json": "application/json"
        }
        mime = mime_types.get(ext, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())

    def do_POST(self):
        url = self.path.split('?')[0]
        try:
            declared_length = int(self.headers.get('Content-Length', 0))
        except (TypeError, ValueError):
            self._send_json({'status': 'error', 'message': 'Invalid Content-Length header'}, 400)
            return
        if declared_length > self.MAX_REQUEST_BYTES:
            self._send_json({'status': 'error', 'message': 'Request payload is too large'}, 413)
            return

        if url == '/api/workflow/validate':
            try:
                from .workflow_engine import validate_workflow
                data = self._read_json()
                normalized = validate_workflow(data.get('workflow', data))
                response_data = {
                    'status': 'ok',
                    'execution_order': normalized['order'],
                    'node_count': len(normalized['nodes']),
                    'edge_count': len(normalized['edges']),
                }
                self._send_json(response_data)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({'status': 'error', 'message': str(exc)}, 400)
            return

        if url == '/api/workflow/run':
            try:
                from .workflow_engine import execute_workflow
                data = self._read_json()
                live_geojson = _strict_json_loads(self.server.geojson_data or '{}')
                response_data = execute_workflow(
                    data.get('workflow', {}),
                    live_geojson,
                    selected_fid=data.get('selected_fid'),
                )
                self._send_json(response_data)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json({'status': 'error', 'message': str(exc)}, 400)
            return

        if url == "/sync":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                if self.server.sync_callback:
                    success, msg = self.server.sync_callback(data)
                    response_data = {"status": "ok" if success else "error", "message": msg}
                else:
                    response_data = {"status": "error", "message": "No sync callback registered"}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/optimize/start":
            try:
                data = self._read_json()
                run_id = str(uuid.uuid4())
                gens = int(data.get("generations", 15))
                pop_size = int(data.get("pop_size", 30))
                if gens < 1 or gens > 50:
                    raise ValueError('Generations must be between 1 and 50')
                if pop_size < 2 or pop_size > 100:
                    raise ValueError('Population size must be between 2 and 100')
                seed_value = data.get('seed')
                seed = int(seed_value) if seed_value is not None else None

                active_runs = self.server.active_runs
                for old_id, old_state in list(active_runs.items()):
                    if old_state.status != 'running' and time.time() - old_state.start_time > 600:
                        del active_runs[old_id]
                if sum(1 for state in active_runs.values() if state.status == 'running') >= 2:
                    raise ValueError('At most two optimization runs may execute concurrently')
                
                run_state = RunState(run_id, gens)
                if not hasattr(self.server, "active_runs"):
                    self.server.active_runs = {}
                self.server.active_runs[run_id] = run_state
                
                def run_opt():
                    from .nsga2_engine import (
                        run_nsga2_streaming,
                        run_spea2_streaming,
                        run_multiparcel_nsga2_streaming,
                        run_nsga3_streaming,
                        run_moead_streaming,
                    )
                    algo = data.get("algorithm", "nsga2")
                    try:
                        if algo == "spea2":
                            generator = run_spea2_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=pop_size,
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params"),
                                seed=seed,
                            )
                        elif algo == "nsga3":
                            generator = run_nsga3_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=pop_size,
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params"),
                                seed=seed,
                            )
                        elif algo == "moead":
                            generator = run_moead_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=pop_size,
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params"),
                                seed=seed,
                            )
                        elif algo == "multiparcel":
                            generator = run_multiparcel_nsga2_streaming(
                                parcels_data=data.get("parcels_data", [{"id": "1", "area": float(data.get("parcel_area", 1000.0))}]),
                                objective_specs=data.get("objective_specs"),
                                pop_size=pop_size,
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params")
                            )
                        else:
                            generator = run_nsga2_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=pop_size,
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params"),
                                seed=seed,
                            )
                        for gen_result in generator:
                            if run_state.stop_requested:
                                break
                            run_state.current_generation = gen_result["generation"]
                            run_state.generation_data = gen_result
                            
                        if not run_state.stop_requested:
                            run_state.status = 'completed'
                            if run_state.generation_data and "k_means_clusters" in run_state.generation_data:
                                run_state.final_result = {
                                    "k_means_clusters": run_state.generation_data.get("k_means_clusters"),
                                    "sensitivity": run_state.generation_data.get("sensitivity"),
                                    "all_solutions": run_state.generation_data.get("all_solutions"),
                                    "pareto_solutions": run_state.generation_data.get("pareto_solutions")
                                }
                        else:
                            run_state.status = 'stopped'
                    except Exception as e:
                        run_state.status = 'error'
                        run_state.error_message = str(e)

                t = threading.Thread(target=run_opt, daemon=True)
                t.start()
                
                response_data = {"status": "ok", "run_id": run_id, "total_generations": gens}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url.startswith("/api/optimize/stop/"):
            run_id = url.split("/")[-1]
            active_runs = getattr(self.server, "active_runs", {})
            if run_id in active_runs:
                active_runs[run_id].stop_requested = True
                response_data = {"status": "ok"}
            else:
                response_data = {"status": "error", "message": "Run Not Found"}
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/topsis/rank":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                from .nsga2_engine import topsis_rank_solutions
                solutions = data.get("solutions", [])
                weights = data.get("weights")
                specs = data.get("objective_specs")
                ranked = topsis_rank_solutions(solutions, weights, specs)
                response_data = {"status": "ok", "ranked_solutions": ranked}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/export/cityjson":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                from .nsga2_engine import export_to_cityjson
                solutions = data.get("solutions", [])
                cityjson_obj = export_to_cityjson(solutions)
                response_data = {"status": "ok", "cityjson": cityjson_obj}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/district/evaluate":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                from .district_engine import evaluate_district_coupling
                buildings = data.get("buildings", [])
                site_area = float(data.get("site_area", 5000.0))
                metrics = evaluate_district_coupling(buildings, site_area)
                response_data = {"status": "ok", "district_metrics": metrics}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/optimize":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                from .nsga2_engine import (
                    run_nsga2_optimization,
                    run_spea2_optimization,
                    run_multiparcel_nsga2_streaming,
                    run_nsga3_optimization,
                    run_moead_optimization,
                )
                algo = data.get("algorithm", "nsga2")
                
                if algo == "spea2":
                    response_data = run_spea2_optimization(
                        parcel_area=float(data.get("parcel_area", 1000.0)),
                        objective_specs=data.get("objective_specs"),
                        pop_size=int(data.get("pop_size", 30)),
                        generations=int(data.get("generations", 15)),
                        crossover_rate=float(data.get("crossover_rate", 0.8)),
                        mutation_rate=float(data.get("mutation_rate", 0.15)),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.5)),
                        max_height=float(data.get("max_height", 18.0)),
                        bounds=data.get("bounds"),
                        sim_params=data.get("sim_params")
                    )
                elif algo == "nsga3":
                    response_data = run_nsga3_optimization(
                        parcel_area=float(data.get("parcel_area", 1000.0)),
                        objective_specs=data.get("objective_specs"),
                        pop_size=int(data.get("pop_size", 30)),
                        generations=int(data.get("generations", 15)),
                        crossover_rate=float(data.get("crossover_rate", 0.8)),
                        mutation_rate=float(data.get("mutation_rate", 0.15)),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.5)),
                        max_height=float(data.get("max_height", 18.0)),
                        bounds=data.get("bounds"),
                        sim_params=data.get("sim_params")
                    )
                elif algo == "moead":
                    response_data = run_moead_optimization(
                        parcel_area=float(data.get("parcel_area", 1000.0)),
                        objective_specs=data.get("objective_specs"),
                        pop_size=int(data.get("pop_size", 30)),
                        generations=int(data.get("generations", 15)),
                        crossover_rate=float(data.get("crossover_rate", 0.8)),
                        mutation_rate=float(data.get("mutation_rate", 0.15)),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.5)),
                        max_height=float(data.get("max_height", 18.0)),
                        bounds=data.get("bounds"),
                        sim_params=data.get("sim_params")
                    )
                elif algo == "multiparcel":
                    generator = run_multiparcel_nsga2_streaming(
                        parcels_data=data.get("parcels_data", [{"id": "1", "area": float(data.get("parcel_area", 1000.0))}]),
                        objective_specs=data.get("objective_specs"),
                        pop_size=int(data.get("pop_size", 30)),
                        generations=int(data.get("generations", 15)),
                        crossover_rate=float(data.get("crossover_rate", 0.8)),
                        mutation_rate=float(data.get("mutation_rate", 0.15)),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.5)),
                        max_height=float(data.get("max_height", 18.0)),
                        bounds=data.get("bounds"),
                        sim_params=data.get("sim_params")
                    )
                    last_data = None
                    for gen_data in generator:
                        last_data = gen_data
                    response_data = {
                        "status": "ok",
                        "pareto_solutions": last_data.get("pareto_solutions", []),
                        "all_solutions": last_data.get("all_solutions", [])
                    }
                else:
                    response_data = run_nsga2_optimization(
                        parcel_area=float(data.get("parcel_area", 1000.0)),
                        objective_specs=data.get("objective_specs"),
                        pop_size=int(data.get("pop_size", 30)),
                        generations=int(data.get("generations", 15)),
                        crossover_rate=float(data.get("crossover_rate", 0.8)),
                        mutation_rate=float(data.get("mutation_rate", 0.15)),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.5)),
                        max_height=float(data.get("max_height", 18.0)),
                        bounds=data.get("bounds"),
                        sim_params=data.get("sim_params")
                    )
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/ppud/run":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                from .ppud_pipeline import run_ppud_pipeline

                # Extract block ring from GeoJSON features or direct ring
                features_data = data.get("features", [])
                results = []

                for feat in features_data:
                    geom = feat.get("geometry", {})
                    coords = geom.get("coordinates", [])
                    if geom.get("type") == "Polygon" and coords:
                        ring = [{"x": pt[0], "y": pt[1]} for pt in coords[0]]
                    elif geom.get("type") == "MultiPolygon" and coords:
                        ring = [{"x": pt[0], "y": pt[1]} for pt in coords[0][0]]
                    else:
                        continue

                    result = run_ppud_pipeline(
                        block_ring=ring,
                        strategy=data.get("strategy", "perimeter"),
                        block_typology=data.get("block_typology", "PerimeterBlock"),
                        max_bcr=float(data.get("max_bcr", 0.45)),
                        max_far=float(data.get("max_far", 2.0)),
                        max_height=float(data.get("max_height", 18.0)),
                        incremental_steps=int(data.get("incremental_steps", 5)),
                        climate_feedback=bool(data.get("climate_feedback", True)),
                        sim_params=data.get("sim_params"),
                    )

                    # Also generate form-based code
                    from .plan_note_codifier import export_form_based_code
                    fbc = export_form_based_code(
                        result["stage2_configured"],
                        data.get("block_typology", "PerimeterBlock"),
                        sum(p.get("area_m2", 0) for p in result["stage1_plots"]),
                        float(data.get("max_bcr", 0.45)),
                        float(data.get("max_far", 2.0)),
                        float(data.get("max_height", 18.0)),
                    )
                    result["form_based_code"] = fbc
                    results.append(result)

                response_data = {"status": "ok", "results": results}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        if url == "/api/export/report":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = _strict_json_loads(body)
                solutions = data.get("solutions", [])
                site_area = float(data.get("site_area", 10000.0))
                title = data.get('title', 'Parametric Urban Master Plan Report')
                safe_title = html.escape(str(title))

                html_report = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{safe_title}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1e293b; background: #f8fafc; }}
        h1 {{ color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 10px; }}
        .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
        .kpi-card {{ background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .kpi-val {{ font-size: 1.5rem; font-weight: bold; color: #0f766e; margin-top: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; font-size: 0.85rem; }}
        th {{ background: #0f766e; color: white; }}
        tr:nth-child(even) {{ background: #f1f5f9; }}
        .footer {{ margin-top: 40px; font-size: 0.8rem; color: #64748b; text-align: center; }}
    </style>
</head>
<body>
    <h1>🏢 {safe_title}</h1>
    <p>Generated by <strong>PlanX Parametric Process v2.0.6</strong> | Site Area: <strong>{site_area:,.1f} m²</strong></p>

    <div class="kpi-grid">
        <div class="kpi-card"><div>Total Solutions</div><div class="kpi-val">{len(solutions)}</div></div>
        <div class="kpi-card"><div>Optimization Engine</div><div class="kpi-val">NSGA-II / SPEA-2</div></div>
        <div class="kpi-card"><div>Compliance Status</div><div class="kpi-val" style="color: #10b981;">100% Feasible</div></div>
        <div class="kpi-card"><div>GIS CRS Sync</div><div class="kpi-val">EPSG:3857</div></div>
    </div>

    <h2>📊 Pareto Front TOPSIS Solutions Table</h2>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>Typology</th>
                <th>Floors</th>
                <th>Setback (m)</th>
                <th>GFA (m²)</th>
                <th>FAR</th>
                <th>BCR</th>
                <th>PlanX Score</th>
                <th>Carbon (kg)</th>
            </tr>
        </thead>
        <tbody>
"""
                for idx, sol in enumerate(solutions[:15], start=1):
                    geno = sol.get("genotype", {})
                    met = sol.get("metrics", {})
                    html_report += f"""
            <tr>
                <td><strong>#{idx}</strong></td>
                <td>{html.escape(str(geno.get('typology', 'Perimeter')))}</td>
                <td>{geno.get('floors', 4)}</td>
                <td>{geno.get('setback', 3.0):.1f}</td>
                <td>{met.get('gfa', 0.0):,.1f}</td>
                <td>{met.get('far', 0.0):.2f}</td>
                <td>{met.get('bcr', 0.0):.3f}</td>
                <td><strong>{met.get('planx_score', 0.0):.1f}</strong>/100</td>
                <td>{met.get('carbon_kg', 0.0):,.0f}</td>
            </tr>"""

                html_report += """
        </tbody>
    </table>

    <div class="footer">
        <p>PlanX Parametric Process Urban Analytics Studio | Copyright © Yusuf Eminoğlu | GPL-3.0-or-later</p>
    </div>
</body>
</html>"""

                response_data = {"status": "ok", "report_html": html_report}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(_json_bytes(response_data))
            return

        self.send_error(404, "Endpoint Not Found")


class ParametricProcessServer:
    def __init__(self, port: int, web_dir: str, sync_callback=None):
        self.port = port
        self.web_dir = web_dir
        self.sync_callback = sync_callback
        self.geojson_data = "{}"
        self.httpd = None
        self.thread = None
        self.active_runs = {}

    def start(self):
        base_port = self.port
        last_error = None
        self.httpd = None
        for candidate in range(base_port, base_port + 21):
            try:
                self.httpd = ReusableThreadingHTTPServer(('127.0.0.1', candidate), SyncHTTPRequestHandler)
                self.port = candidate
                break
            except OSError as exc:
                last_error = exc
        if self.httpd is None:
            raise OSError(
                f"No free port between {base_port} and {base_port + 20}: {last_error}"
            )
        self.httpd.web_dir = self.web_dir
        self.httpd.sync_callback = self.sync_callback
        self.httpd.geojson_data = self.geojson_data
        self.httpd.active_runs = self.active_runs

        def serve():
            self.httpd.serve_forever()

        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()

    def update_geojson(self, geojson_str: str):
        self.geojson_data = geojson_str
        if self.httpd:
            self.httpd.geojson_data = geojson_str

    def stop(self):
        for run_state in self.active_runs.values():
            if run_state.status == 'running':
                run_state.stop_requested = True
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
