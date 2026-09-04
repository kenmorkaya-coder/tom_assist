"""Explicit project-document chunking and local MiniLM embedding boundary."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import struct
import subprocess
import threading
import uuid

from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
    build_semantic_profile,
    profile_similarity,
)
from gateway.declared_structure import MAX_DECLARED_STRUCTURE_SOURCE_CHARS
from gateway.structure_provider import isolated_worker_environment


DOCUMENT_CHUNKING_VERSION = "minilm-document-token-sentence-max188-overlap32/1.1"
SUPPORTED_DOCUMENT_CHUNKING_VERSIONS = frozenset({
    "minilm-document-token-sentence-max192-overlap32/1.0",
    DOCUMENT_CHUNKING_VERSION,
})
DOCUMENT_EMBEDDING_VERSION = EMBEDDING_VERSION
DOCUMENT_WORKER_PROTOCOL = "tom-assist-document-embedding/1.0"
DOCUMENT_PACKET_ADMISSION_VERSION = "minilm-document-hybrid-packet-admission/1.0"
MAX_DOCUMENT_SOURCE_CHARS = MAX_DECLARED_STRUCTURE_SOURCE_CHARS
MAX_DOCUMENT_CHUNKS = 4_096
MAX_DOCUMENT_PACKET_CANDIDATES = 4
MAX_DOCUMENT_PACKET_EXCERPT_CHARS = 680
DOCUMENT_MAX_CHUNK_TOKENS = 188
DOCUMENT_DENSE_RRF_WEIGHT = 0.50
DOCUMENT_LEXICAL_RRF_WEIGHT = 0.50
DOCUMENT_RRF_K = 60
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


def build_document_query_profile(source_text, provider):
    """Embed a draft without mutating document, tree, or memory state."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("document retrieval query is required")
    embedded = validate_embedding_result(
        source_text, provider.embed_document(source_text),
    )
    return build_semantic_profile(
        source_text,
        [
            {
                "start": row["start"],
                "end": row["end"],
                "values": decode_vector_f32(row["vector_f32_le_base64"]),
            }
            for row in embedded["chunks"]
        ],
        model=embedded["model"],
        revision=embedded["revision"],
    )


def rank_document_chunks_for_packet(
    query_text, query_profile, document_chunks, *, k, max_chars,
):
    """Return bounded, exact source excerpts from immutable active chunks."""
    if type(k) is not int or k <= 0:
        raise ValueError("document packet k must be a positive integer")
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("document packet max_chars must be a positive integer")
    ranked = []
    query_terms = _retrieval_terms(query_text)
    for row in document_chunks:
        text = row.get("text")
        if not isinstance(text, str) or not text:
            raise ValueError("document chunk text is required for packet admission")
        vector = decode_vector_f32(row["passage_vector"])
        scores = profile_similarity(
            query_profile, {"chunks": [{"values": vector}]},
        )
        document_id = str(row["document_id"])
        chunk_index = int(row["chunk_index"])
        ranked.append({
            "id": f"{document_id}:chunk:{chunk_index}",
            "document_id": document_id,
            "display_name": str(row["display_name"]),
            "chunk_index": chunk_index,
            "start": int(row["start"]),
            "end": int(row["end"]),
            "text": text,
            "text_sha256": str(row["text_sha256"]),
            "semantic_score": float(scores["query_relevance_score"]),
            "best_chunk_score": float(scores["best_chunk_score"]),
            "lexical_score": _lexical_query_coverage(query_terms, text),
            "score_space": "minilm_dense_plus_exact_term_rrf",
            "packet_eligible": True,
            "structural_signature": None,
        })
    ranked.sort(
        key=lambda row: (
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        )
    )
    for dense_rank, row in enumerate(ranked, 1):
        row["dense_rank"] = dense_rank
    lexical_rows = sorted(
        (row for row in ranked if row["lexical_score"] > 0.0),
        key=lambda row: (
            -row["lexical_score"],
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        ),
    )
    lexical_ranks = {row["id"]: rank for rank, row in enumerate(lexical_rows, 1)}
    for row in ranked:
        lexical_rank = lexical_ranks.get(row["id"])
        row["lexical_rank"] = lexical_rank
        row["rrf_score"] = (
            DOCUMENT_DENSE_RRF_WEIGHT / (DOCUMENT_RRF_K + row["dense_rank"])
            + (
                DOCUMENT_LEXICAL_RRF_WEIGHT / (DOCUMENT_RRF_K + lexical_rank)
                if lexical_rank is not None else 0.0
            )
        )
    ranked.sort(
        key=lambda row: (
            -row["rrf_score"],
            -row["lexical_score"],
            -row["semantic_score"],
            row["document_id"],
            row["chunk_index"],
        )
    )
    admitted = []
    used_chars = 0
    limit = min(k, MAX_DOCUMENT_PACKET_CANDIDATES)
    for packet_rank, row in enumerate(ranked, 1):
        if len(admitted) >= limit or used_chars >= max_chars:
            break
        excerpt_length = min(
            len(row["text"]),
            MAX_DOCUMENT_PACKET_EXCERPT_CHARS,
            max_chars - used_chars,
        )
        if excerpt_length <= 0:
            break
        relative_start = _evidence_excerpt_start(
            row["text"], query_text, excerpt_length,
        )
        relative_end = relative_start + excerpt_length
        clause_pattern = re.compile(r"(?m)^[ \t]*\d+(?:\.\d+)+(?:[ \t]|$)")
        if clause_pattern.match(row["text"], relative_start):
            next_clause = next(
                (
                    match.start() for match in clause_pattern.finditer(
                        row["text"], relative_start + 1, relative_end,
                    )
                ),
                None,
            )
            if next_clause is not None:
                relative_end = next_clause
        excerpt = row["text"][relative_start:relative_end].rstrip()
        relative_end = relative_start + len(excerpt)
        admitted.append({
            **{key: value for key, value in row.items() if key != "text"},
            "text": excerpt,
            "rank": packet_rank,
            "excerpt_start": row["start"] + relative_start,
            "excerpt_end": row["start"] + relative_end,
            "excerpt_sha256": "sha256:" + hashlib.sha256(
                excerpt.encode("utf-8")
            ).hexdigest(),
            "truncated": relative_start > 0 or relative_end < len(row["text"]),
        })
        used_chars += excerpt_length
    return admitted


def _evidence_excerpt_start(text, query_text, limit):
    """Centre an exact excerpt on the densest shared-term window after dense rank."""
    if len(text) <= limit:
        return 0
    terms = _retrieval_terms(query_text)
    folded = text.casefold()
    occurrences = []
    for term in terms:
        occurrences.extend(
            (match.start(), term)
            for match in re.finditer(re.escape(term), folded)
        )
    if not occurrences:
        return 0
    starts = {
        min(max(0, position - limit // 3), len(text) - limit)
        for position, _ in occurrences
    }
    best = None
    for start in sorted(starts):
        end = start + limit
        within = [(position, term) for position, term in occurrences if start <= position < end]
        score = (len({term for _, term in within}), len(within), -start)
        if best is None or score > best[0]:
            best = (score, start)
    start = best[1]
    within = [
        (position, term) for position, term in occurrences
        if start <= position < start + limit
    ]
    focus, _ = min(within, key=lambda item: (-len(item[1]), item[0]))
    boundaries = [
        match.start()
        for match in re.finditer(
            r"(?m)^[ \t]*\d+(?:\.\d+)+(?:[ \t]|$)", text,
        )
        if match.start() <= focus
    ]
    if boundaries and focus - boundaries[-1] <= limit // 2:
        return min(boundaries[-1], len(text) - limit)
    return start


def _retrieval_terms(query_text):
    return sorted({
        term.casefold()
        for term in re.findall(r"[\w'-]+", str(query_text), flags=re.UNICODE)
        if len(term) >= 4
    })


def _lexical_query_coverage(query_terms, text):
    if not query_terms:
        return 0.0
    folded = text.casefold()
    return sum(term in folded for term in query_terms) / len(query_terms)


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
