# -*- coding: utf-8 -*-
"""Approved JSON-in/JSON-out external research engine adapter."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, Mapping, Sequence

from qgis.PyQt.QtCore import QProcess, QSettings


class ExternalEngineError(RuntimeError):
    pass


def executable_fingerprint(path: str) -> str:
    canonical = os.path.realpath(path)
    if not os.path.isfile(canonical):
        raise ExternalEngineError("External engine executable does not exist")
    digest = hashlib.sha256()
    with open(canonical, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ExternalEngineAdapter:
    SETTINGS_GROUP = "parametric_process/external_engines"
    MAX_OUTPUT_BYTES = 20 * 1024 * 1024

    def __init__(self, settings: QSettings | None = None):
        self.settings = settings or QSettings()

    def approve(self, executable: str) -> str:
        path = os.path.realpath(executable)
        fingerprint = executable_fingerprint(path)
        self.settings.setValue(f"{self.SETTINGS_GROUP}/{hashlib.sha256(path.encode('utf-8')).hexdigest()}", fingerprint)
        return fingerprint

    def is_approved(self, executable: str) -> bool:
        path = os.path.realpath(executable)
        try:
            current = executable_fingerprint(path)
        except ExternalEngineError:
            return False
        key = f"{self.SETTINGS_GROUP}/{hashlib.sha256(path.encode('utf-8')).hexdigest()}"
        return self.settings.value(key, "") == current

    def run(self, executable: str, arguments: Sequence[str], payload: Mapping[str, Any],
            timeout_ms: int = 300000) -> Dict[str, Any]:
        path = os.path.realpath(executable)
        if not self.is_approved(path):
            raise ExternalEngineError("External engine is not approved or its executable has changed")
        request = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")
        process = QProcess()
        process.setProgram(path)
        process.setArguments([str(argument) for argument in arguments])
        process.start()
        if not process.waitForStarted(min(timeout_ms, 30000)):
            raise ExternalEngineError(f"External engine could not start: {process.errorString()}")
        process.write(request)
        process.closeWriteChannel()
        if not process.waitForFinished(timeout_ms):
            process.kill()
            process.waitForFinished(5000)
            raise ExternalEngineError("External engine timed out")
        stdout = bytes(process.readAllStandardOutput())
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        if len(stdout) > self.MAX_OUTPUT_BYTES:
            raise ExternalEngineError("External engine output exceeds the configured size limit")
        if process.exitCode() != 0:
            raise ExternalEngineError(f"External engine failed with exit code {process.exitCode()}: {stderr[:1000]}")
        try:
            response = json.loads(stdout.decode("utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Non-finite JSON value: {value}")))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ExternalEngineError("External engine returned invalid strict JSON") from exc
        return validate_external_response(payload, response)


def validate_external_response(request: Mapping[str, Any], response: Any) -> Dict[str, Any]:
    if not isinstance(response, dict) or response.get("schema") != "parametric-process-engine-result/1.0":
        raise ExternalEngineError("External response schema is missing or unsupported")
    requested_ids = {str(item.get("solution_id")) for item in request.get("alternatives", [])}
    results = response.get("results")
    if not isinstance(results, list):
        raise ExternalEngineError("External response results must be a list")
    seen = set()
    for item in results:
        solution_id = str(item.get("solution_id"))
        if solution_id not in requested_ids or solution_id in seen:
            raise ExternalEngineError("External response contains an unknown or duplicate solution ID")
        seen.add(solution_id)
        metrics = item.get("metrics")
        if not isinstance(metrics, dict):
            raise ExternalEngineError("Every external result requires a metrics object")
        for name, metric in metrics.items():
            if not isinstance(metric, dict) or "value" not in metric or "unit" not in metric:
                raise ExternalEngineError(f"External metric '{name}' requires value and unit")
            value = metric["value"]
            if not isinstance(value, (int, float)) or not math_isfinite(value):
                raise ExternalEngineError(f"External metric '{name}' must be finite")
    response["validation_status"] = "validated"
    return response


def math_isfinite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
