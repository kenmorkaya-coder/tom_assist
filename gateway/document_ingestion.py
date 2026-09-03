"""Explicit project-document chunking and local MiniLM embedding boundary."""
from __future__ import annotations

import base64
import binascii
import json
import math
import os
from pathlib import Path
import selectors
import struct
import subprocess
import threading
import uuid

from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
)
from gateway.structure_provider import isolated_worker_environment


DOCUMENT_CHUNKING_VERSION = "minilm-document-token-sentence-max192-overlap32/1.0"
DOCUMENT_EMBEDDING_VERSION = EMBEDDING_VERSION
DOCUMENT_WORKER_PROTOCOL = "tom-assist-document-embedding/1.0"
MAX_DOCUMENT_SOURCE_CHARS = 400_000
MAX_DOCUMENT_CHUNKS = 4_096
ALLOWED_DOCUMENT_MEDIA_TYPES = frozenset({
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/html",
    "text/xml",
    "application/xml",
    "application/json",
})


def validate_document_input(display_name, content, media_type):
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("document display_name is required")
    if len(display_name) > 512:
        raise ValueError("document display_name exceeds 512 characters")
    if not isinstance(content, str):
        raise ValueError("document content must be UTF-8 text, not binary")
    try:
        encoded = content.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("document content must be valid UTF-8") from None
    if not content.strip():
        raise ValueError("document content is empty")
    if len(content) > MAX_DOCUMENT_SOURCE_CHARS:
        raise ValueError(
            f"document content exceeds {MAX_DOCUMENT_SOURCE_CHARS} characters"
        )
    if media_type not in ALLOWED_DOCUMENT_MEDIA_TYPES:
        raise ValueError(
            "document media_type must be plain text or UTF-8 markup; binary formats are unsupported"
        )
    return display_name.strip(), content, media_type, len(encoded)


def encode_vector_f32(values):
    vector = _validate_vector(values)
    raw = struct.pack(f"<{EMBEDDING_DIMENSION}f", *vector)
    return base64.b64encode(raw).decode("ascii")


def decode_vector_f32(value):
    if not isinstance(value, str):
        raise ValueError("document passage vector must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("document passage vector is not canonical base64") from None
    if len(raw) != 4 * EMBEDDING_DIMENSION:
        raise ValueError("document passage vector has the wrong float32 dimension")
    canonical = base64.b64encode(raw).decode("ascii")
    if canonical != value:
        raise ValueError("document passage vector is not canonical base64")
    return _validate_vector(list(struct.unpack(f"<{EMBEDDING_DIMENSION}f", raw)))


def _validate_vector(values):
    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSION:
        raise ValueError(f"document vector must contain {EMBEDDING_DIMENSION} values")
    result = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError("document vector values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("document vector values must be finite numbers")
        result.append(number)
    norm = math.sqrt(sum(number * number for number in result))
    if abs(norm - 1.0) > 2e-3:
        raise ValueError(f"document vector must be unit normalized, got norm {norm}")
    return result


def validate_embedding_result(source_text, payload):
    if not isinstance(payload, dict) or set(payload) != {
        "model", "revision", "chunks",
    }:
        raise ValueError("document embedding result fields mismatch")
    if not isinstance(payload["model"], str) or not payload["model"].strip():
        raise ValueError("document embedding model is required")
    if not isinstance(payload["revision"], str) or not payload["revision"].strip():
        raise ValueError("document embedding revision is required")
    chunks = payload["chunks"]
    if not isinstance(chunks, list) or not 1 <= len(chunks) <= MAX_DOCUMENT_CHUNKS:
        raise ValueError(
            f"document embedding must contain 1..{MAX_DOCUMENT_CHUNKS} chunks"
        )
    validated = []
    previous_end = 0
    for index, row in enumerate(chunks):
        if not isinstance(row, dict) or set(row) != {"index", "start", "end", "values"}:
            raise ValueError(f"document chunk {index} fields mismatch")
        start, end = row["start"], row["end"]
        if row["index"] != index or type(start) is not int or type(end) is not int:
            raise ValueError("document chunk index/offset types are invalid")
        if not (0 <= start < end <= len(source_text)):
            raise ValueError("document chunk offsets are invalid")
        if index == 0 and start != 0:
            raise ValueError("document chunks must begin at source offset zero")
        if index and (start >= previous_end or end <= previous_end):
            raise ValueError("document chunks must overlap and advance")
        if index == len(chunks) - 1 and end != len(source_text):
            raise ValueError("document chunks must cover the source ending")
        validated.append({
            "index": index,
            "start": start,
            "end": end,
            "vector_f32_le_base64": encode_vector_f32(row["values"]),
        })
        previous_end = end
    return {
        "model": payload["model"].strip(),
        "revision": payload["revision"].strip(),
        "chunks": validated,
    }


class DocumentEmbeddingWorkerClient:
    """Persistent, local-only MiniLM client; it never starts Gemma."""

    def __init__(self, command, timeout_seconds=600.0):
        if not command or not all(isinstance(value, str) and value for value in command):
            raise ValueError("document embedding worker command is required")
        self.command = list(command)
        self.timeout_seconds = float(timeout_seconds)
        self._process = None
        self._lock = threading.Lock()

    @classmethod
    def from_environment(cls):
        python = os.environ.get("TOM_ASSIST_STRUCTURE_PYTHON", "")
        model = os.environ.get("TOM_ASSIST_MINILM_MODEL", "")
        missing = [name for name, value in (
            ("TOM_ASSIST_STRUCTURE_PYTHON", python),
            ("TOM_ASSIST_MINILM_MODEL", model),
        ) if not value]
        if missing:
            raise ValueError(
                "local document embedding is not configured: " + ", ".join(missing)
            )
        paths = [Path(python).expanduser(), Path(model).expanduser()]
        if any(not path.is_absolute() or not path.exists() for path in paths):
            raise ValueError("document embedding paths must be existing absolute paths")
        script = Path(__file__).with_name("document_embedding_worker.py").resolve()
        return cls([str(paths[0].resolve()), str(script), "--model", str(paths[1].resolve())])

    def _start(self):
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

    def embed_document(self, source_text):
        request_id = str(uuid.uuid4())
        request = {
            "protocol": DOCUMENT_WORKER_PROTOCOL,
            "request_id": request_id,
            "source_text": source_text,
        }
        with self._lock:
            process = self._start()
            if process.stdin is None or process.stdout is None:
                raise ValueError("document embedding worker has no pipes")
            try:
                process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                self.close()
                raise ValueError("document embedding worker stopped before accepting input") from None
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(self.timeout_seconds):
                    self.close()
                    raise ValueError("document embedding worker timed out")
                line = process.stdout.readline()
            finally:
                selector.close()
            if not line:
                self.close()
                raise ValueError("document embedding worker ended unexpectedly")
            response = json.loads(line)
            if response.get("protocol") != DOCUMENT_WORKER_PROTOCOL:
                raise ValueError("document embedding worker protocol mismatch")
            if response.get("request_id") != request_id:
                raise ValueError("document embedding worker response ID mismatch")
            if "error" in response:
                raise ValueError(str(response["error"])[:500])
            if set(response) != {"protocol", "request_id", "model", "revision", "chunks"}:
                raise ValueError("document embedding worker response shape mismatch")
            return {key: response[key] for key in ("model", "revision", "chunks")}

    def close(self):
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

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
