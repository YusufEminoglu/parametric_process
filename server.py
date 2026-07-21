# -*- coding: utf-8 -*-
"""Local HTTP server for Parametric Process.

Serves the Web UI static files and routes /api/optimize and /sync POST requests back to QGIS.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

class RunState:
    def __init__(self, run_id, total_generations):
        self.run_id = run_id
        self.status = 'running'  # running | completed | error
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
    def log_message(self, format, *args):
        from contextlib import suppress
        with suppress(Exception):
            log_dir = os.path.join(tempfile.gettempdir(), "parametric_process")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "server_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}\n")

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        url = self.path.split('?')[0]

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
            self.wfile.write(json.dumps(resp).encode('utf-8'))
            return

        if url == "/data.geojson":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.server.geojson_data.encode('utf-8'))
            return

        clean_path = url.lstrip("/")
        if not clean_path or clean_path == "" or clean_path == "index.html":
            clean_path = "src/index.html"
        elif clean_path == "app.js":
            clean_path = "src/app.js"
        elif clean_path == "style.css":
            clean_path = "src/style.css"

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
        if url == "/sync":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
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
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        if url == "/api/optimize/start":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                run_id = str(uuid.uuid4())
                gens = int(data.get("generations", 15))
                
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
                                pop_size=int(data.get("pop_size", 30)),
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params")
                            )
                        elif algo == "nsga3":
                            generator = run_nsga3_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=int(data.get("pop_size", 30)),
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params")
                            )
                        elif algo == "moead":
                            generator = run_moead_streaming(
                                parcel_area=float(data.get("parcel_area", 1000.0)),
                                objective_specs=data.get("objective_specs"),
                                pop_size=int(data.get("pop_size", 30)),
                                generations=gens,
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
                                pop_size=int(data.get("pop_size", 30)),
                                generations=gens,
                                crossover_rate=float(data.get("crossover_rate", 0.8)),
                                mutation_rate=float(data.get("mutation_rate", 0.15)),
                                max_bcr=float(data.get("max_bcr", 0.45)),
                                max_far=float(data.get("max_far", 2.5)),
                                max_height=float(data.get("max_height", 18.0)),
                                bounds=data.get("bounds"),
                                sim_params=data.get("sim_params")
                            )
                        for gen_result in generator:
                            if run_state.stop_requested:
                                break
                            run_state.current_generation = gen_result["generation"]
                            run_state.generation_data = gen_result
                            
                        if not run_state.stop_requested:
                            run_state.status = 'completed'
                            if "k_means_clusters" in run_state.generation_data:
                                run_state.final_result = {
                                    "k_means_clusters": run_state.generation_data.get("k_means_clusters"),
                                    "sensitivity": run_state.generation_data.get("sensitivity"),
                                    "all_solutions": run_state.generation_data.get("all_solutions"),
                                    "pareto_solutions": run_state.generation_data.get("pareto_solutions")
                                }
                        else:
                            run_state.status = 'error'
                            run_state.error_message = 'Stopped by user'
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
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
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
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        if url == "/api/topsis/rank":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
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
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        if url == "/api/export/cityjson":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
                from .nsga2_engine import export_to_cityjson
                solutions = data.get("solutions", [])
                cityjson_obj = export_to_cityjson(solutions)
                response_data = {"status": "ok", "cityjson": cityjson_obj}
            except Exception as e:
                response_data = {"status": "error", "message": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            return

        if url == "/api/optimize":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
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
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
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
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
