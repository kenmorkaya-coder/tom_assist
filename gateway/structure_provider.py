"""Isolated local semantic/Gemma worker client.

The worker is a subprocess so torch/transformers and Gemma's MLX version never
enter the pinned tom_master gateway interpreter.
"""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any


WORKER_PROTOCOL = "tom-assist-structure-worker/1.0"
_SAFE_ENVIRONMENT_NAMES = {
    "PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE",
    "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH", "TOKENIZERS_PARALLELISM",
    "OMP_NUM_THREADS", "MKL_NUM_THREADS",
}


def isolated_worker_environment() -> dict[str, str]:
    """Return the minimal local-model environment; credentials never cross."""
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


class StructureProviderError(RuntimeError):
    pass


class StructureWorkerClient:
    def __init__(self, command: list[str], *, timeout_seconds: float = 300.0) -> None:
        if not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("structure worker command is required")
        self.command = list(command)
        self.timeout_seconds = float(timeout_seconds)
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls) -> "StructureWorkerClient":
        names = {
            "structure_python": "TOM_ASSIST_STRUCTURE_PYTHON",
            "embedding_model": "TOM_ASSIST_MINILM_MODEL",
            "gemma_python": "TOM_ASSIST_GEMMA_PYTHON",
            "gemma_model": "TOM_ASSIST_GEMMA_MODEL",
        }
        values = {key: os.environ.get(name, "") for key, name in names.items()}
        missing = [names[key] for key, value in values.items() if not value]
        if missing:
            raise StructureProviderError(
                "local structure worker is not configured: " + ", ".join(sorted(missing))
            )
        for key, value in values.items():
            path = Path(value).expanduser()
            if not path.is_absolute() or not path.exists():
                raise StructureProviderError(f"{names[key]} must be an existing absolute path")
        script = Path(__file__).with_name("structure_worker.py").resolve()
        try:
            timeout = float(os.environ.get("TOM_ASSIST_STRUCTURE_TIMEOUT_SECONDS", "600"))
        except ValueError:
            raise StructureProviderError(
                "TOM_ASSIST_STRUCTURE_TIMEOUT_SECONDS must be numeric"
            ) from None
        if not 30.0 <= timeout <= 1800.0:
            raise StructureProviderError(
                "TOM_ASSIST_STRUCTURE_TIMEOUT_SECONDS must be in [30,1800]"
            )
        return cls([
            str(Path(values["structure_python"]).resolve()), str(script),
            "--embedding-model", str(Path(values["embedding_model"]).resolve()),
            "--gemma-python", str(Path(values["gemma_python"]).resolve()),
            "--gemma-model", str(Path(values["gemma_model"]).resolve()),
        ], timeout_seconds=timeout)

    def _start(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=isolated_worker_environment(),
        )
        return self._process

    def analyze(self, source_text: str) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        request = {
            "protocol": WORKER_PROTOCOL,
            "request_id": request_id,
            "source_text": source_text,
        }
        with self._lock:
            process = self._start()
            if process.stdin is None or process.stdout is None:
                raise StructureProviderError("local structure worker has no pipes")
            try:
                process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                self.close()
                raise StructureProviderError("local structure worker stopped before accepting input") from None
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(self.timeout_seconds):
                    self.close()
                    raise StructureProviderError("local structure worker timed out")
                line = process.stdout.readline()
            finally:
                selector.close()
            if not line:
                code = process.poll()
                self.close()
                raise StructureProviderError(f"local structure worker ended unexpectedly ({code})")
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                self.close()
                raise StructureProviderError("local structure worker returned invalid JSON") from None
            if not isinstance(response, dict) or response.get("protocol") != WORKER_PROTOCOL:
                raise StructureProviderError("local structure worker protocol mismatch")
            if response.get("request_id") != request_id:
                raise StructureProviderError("local structure worker response ID mismatch")
            if "error" in response:
                raise StructureProviderError(str(response["error"])[:500])
            if set(response) != {
                "protocol", "request_id", "chunk_candidates", "semantic_profile",
                "parser_model",
            }:
                raise StructureProviderError("local structure worker response shape mismatch")
            return {
                "chunk_candidates": response["chunk_candidates"],
                "semantic_profile": response["semantic_profile"],
                "parser_model": response["parser_model"],
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
