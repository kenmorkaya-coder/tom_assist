"""Isolated persistent client for the local Gemma matrix-event worker."""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any


MATRIX_EVENT_WORKER_PROTOCOL = "tom-assist-matrix-event-worker/0.1-shadow"
_SAFE_ENVIRONMENT_NAMES = {
    "PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE",
    "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "TOKENIZERS_PARALLELISM",
    "OMP_NUM_THREADS", "MKL_NUM_THREADS",
}


def isolated_matrix_event_environment() -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items()
        if name in _SAFE_ENVIRONMENT_NAMES
    }
    environment.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_OFFLINE": "1",
        "TOM_FEELING_WHEEL_ENABLED": "0",
    })
    return environment


class MatrixEventProviderError(RuntimeError):
    pass


class MatrixEventWorkerClient:
    def __init__(self, command: list[str], *, timeout_seconds: float = 600.0) -> None:
        if not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("matrix event worker command is required")
        self.command = list(command)
        self.timeout_seconds = float(timeout_seconds)
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def _start(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        try:
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=isolated_matrix_event_environment(),
            )
        except OSError as error:
            raise MatrixEventProviderError(
                f"unable to start local matrix event worker: {error}"
            ) from None
        return self._process

    def parse(self, source_text: str) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        request = {
            "protocol": MATRIX_EVENT_WORKER_PROTOCOL,
            "request_id": request_id,
            "source_text": source_text,
        }
        with self._lock:
            process = self._start()
            if process.stdin is None or process.stdout is None:
                raise MatrixEventProviderError("local matrix event worker has no pipes")
            try:
                process.stdin.write(json.dumps(
                    request, ensure_ascii=False, separators=(",", ":"),
                ) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                self.close()
                raise MatrixEventProviderError(
                    "local matrix event worker stopped before accepting input"
                ) from None
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(self.timeout_seconds):
                    self.close()
                    raise MatrixEventProviderError("local matrix event worker timed out")
                line = process.stdout.readline()
            finally:
                selector.close()
            if not line:
                code = process.poll()
                self.close()
                raise MatrixEventProviderError(
                    f"local matrix event worker ended unexpectedly ({code})"
                )
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                self.close()
                raise MatrixEventProviderError(
                    "local matrix event worker returned invalid JSON"
                ) from None
            if (
                not isinstance(response, dict)
                or response.get("protocol") != MATRIX_EVENT_WORKER_PROTOCOL
                or response.get("request_id") != request_id
            ):
                raise MatrixEventProviderError("local matrix event worker protocol mismatch")
            if "error" in response:
                if set(response) != {"protocol", "request_id", "error", "stage"}:
                    raise MatrixEventProviderError("local matrix event error shape mismatch")
                raise MatrixEventProviderError(
                    f"{response['stage']}: {response['error']}"
                )
            if set(response) != {
                "protocol", "request_id", "candidate", "parser_model", "telemetry",
            }:
                raise MatrixEventProviderError("local matrix event response shape mismatch")
            return {
                "candidate": response["candidate"],
                "parser_model": response["parser_model"],
                "telemetry": response["telemetry"],
            }

    def close(self) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
