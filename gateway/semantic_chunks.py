"""Deterministic token-window planning and multi-vector semantic profiles."""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Mapping, Sequence


PROFILE_VERSION = "tom-assist-semantic-multivector/1.0"
CHUNKING_VERSION = "minilm-token-sentence-max192-overlap32/1.0"
EMBEDDING_VERSION = "minilm-l6-v2/384d-multivector/2.0"
EMBEDDING_DIMENSION = 384
MAX_CHUNK_TOKENS = 192
OVERLAP_TOKENS = 32
MIN_BOUNDARY_TOKENS = 96
MAX_CHUNKS = 128
MAX_SOURCE_CHARS = 48_000


def _text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sentence_boundary(source_text: str, char_end: int, next_char_start: int) -> bool:
    before = source_text[:char_end].rstrip()
    between = source_text[char_end:next_char_start]
    if "\n\n" in between:
        return True
    return bool(re.search(r"[.!?…][\"')\]}]*$", before))


def build_token_chunks(
    source_text: str,
    token_offsets: Sequence[Sequence[int]],
    *,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
    min_boundary_tokens: int = MIN_BOUNDARY_TOKENS,
) -> list[dict[str, int]]:
    """Plan overlapping chunks, preferring sentence/paragraph boundaries.

    Offsets come from the configured MiniLM tokenizer without special tokens.
    Character spans are stored so the gateway can bind every chunk back to the
    exact original passage without importing the tokenizer.
    """
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("source text is required for chunking")
    if len(source_text) > MAX_SOURCE_CHARS:
        raise ValueError(f"source text exceeds {MAX_SOURCE_CHARS} characters")
    if not (8 <= max_tokens <= 256):
        raise ValueError("max_tokens must be in [8,256]")
    if not (0 < overlap_tokens < max_tokens // 2):
        raise ValueError("overlap_tokens must be positive and below half the window")
    if not (1 <= min_boundary_tokens <= max_tokens):
        raise ValueError("min_boundary_tokens is invalid")
    offsets: list[tuple[int, int]] = []
    previous_end = 0
    for index, value in enumerate(token_offsets):
        if not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError(f"token offset {index} must contain start/end")
        start, end = value
        if type(start) is not int or type(end) is not int:
            raise ValueError(f"token offset {index} must contain integers")
        if start < previous_end or end <= start or end > len(source_text):
            raise ValueError(f"token offset {index} is invalid or unordered")
        offsets.append((start, end))
        previous_end = end
    if not offsets:
        raise ValueError("tokenizer returned no source offsets")

    chunks: list[dict[str, int]] = []
    token_start = 0
    while token_start < len(offsets):
        hard_end = min(token_start + max_tokens, len(offsets))
        token_end = hard_end
        if hard_end < len(offsets):
            lower = min(hard_end, token_start + min_boundary_tokens)
            for candidate_end in range(hard_end, lower - 1, -1):
                char_end = offsets[candidate_end - 1][1]
                next_start = offsets[candidate_end][0]
                if _sentence_boundary(source_text, char_end, next_start):
                    token_end = candidate_end
                    break
        char_start = 0 if not chunks else offsets[token_start][0]
        char_end = len(source_text) if token_end == len(offsets) else offsets[token_end - 1][1]
        if chunks and char_start >= chunks[-1]["end"]:
            raise ValueError("chunk plan lost its overlap bridge")
        if chunks and char_end <= chunks[-1]["end"]:
            raise ValueError("chunk plan did not advance")
        chunks.append({
            "index": len(chunks),
            "token_start": token_start,
            "token_end": token_end,
            "start": char_start,
            "end": char_end,
        })
        if len(chunks) > MAX_CHUNKS:
            raise ValueError(f"source requires more than {MAX_CHUNKS} chunks")
        if token_end == len(offsets):
            break
        token_start = max(token_start + 1, token_end - overlap_tokens)
    return chunks


def _unit_vector(values: Any, name: str) -> list[float]:
    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSION:
        raise ValueError(f"{name} must contain {EMBEDDING_DIMENSION} values")
    vector = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError(f"{name} values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name} values must be finite numbers")
        vector.append(number)
    norm = math.sqrt(sum(value * value for value in vector))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError(f"{name} must be unit normalized, got norm {norm}")
    return vector


def _normalize(values: Sequence[float], name: str) -> list[float]:
    norm = math.sqrt(sum(float(value) * float(value) for value in values))
    if norm < 1e-12:
        raise ValueError(f"{name} collapsed to a zero vector")
    return [float(value) / norm for value in values]


def build_semantic_profile(
    source_text: str,
    chunks: Sequence[Mapping[str, Any]],
    *,
    model: str,
    revision: str,
) -> dict[str, Any]:
    """Bind chunk vectors to exact source spans and build an audit centroid."""
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("source text is required")
    if len(source_text) > MAX_SOURCE_CHARS:
        raise ValueError(f"source text exceeds {MAX_SOURCE_CHARS} characters")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("semantic profile model is required")
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("semantic profile revision is required")
    if not isinstance(chunks, Sequence) or isinstance(chunks, (str, bytes)):
        raise ValueError("semantic chunks must be an array")
    if not 1 <= len(chunks) <= MAX_CHUNKS:
        raise ValueError(f"semantic profile must contain 1..{MAX_CHUNKS} chunks")

    normalized = []
    previous_end = 0
    centroid = [0.0] * EMBEDDING_DIMENSION
    total_weight = 0
    for index, item in enumerate(chunks):
        if not isinstance(item, Mapping) or set(item) != {"start", "end", "values"}:
            raise ValueError(f"semantic chunk {index} shape mismatch")
        start, end = item["start"], item["end"]
        if type(start) is not int or type(end) is not int:
            raise ValueError(f"semantic chunk {index} offsets must be integers")
        if start < 0 or end <= start or end > len(source_text):
            raise ValueError(f"semantic chunk {index} offsets are invalid")
        if index == 0 and start != 0:
            raise ValueError("semantic chunks must begin at source offset zero")
        if index and (start >= previous_end or end <= previous_end):
            raise ValueError("semantic chunks must overlap and advance")
        if index == len(chunks) - 1 and end != len(source_text):
            raise ValueError("semantic chunks must cover the source ending")
        vector = _unit_vector(item["values"], f"semantic chunk {index}")
        unique_chars = end - (start if index == 0 else previous_end)
        if unique_chars <= 0:
            raise ValueError("semantic chunk adds no new source coverage")
        for axis, value in enumerate(vector):
            centroid[axis] += value * unique_chars
        total_weight += unique_chars
        chunk_text = source_text[start:end]
        normalized.append({
            "index": index,
            "start": start,
            "end": end,
            "text_sha256": _text_digest(chunk_text),
            "values": vector,
        })
        previous_end = end
    if previous_end != len(source_text) or total_weight != len(source_text):
        raise ValueError("semantic chunks do not provide exact source coverage")
    passage = _normalize(centroid, "passage centroid")
    return {
        "version": PROFILE_VERSION,
        "embedding_version": EMBEDDING_VERSION,
        "chunking_version": CHUNKING_VERSION,
        "model": model.strip(),
        "revision": revision.strip(),
        "dimension": EMBEDDING_DIMENSION,
        "chunks": normalized,
        "passage_vector": passage,
    }


def validate_semantic_profile(payload: Any, source_text: str) -> dict[str, Any]:
    fields = {
        "version", "embedding_version", "chunking_version", "model", "revision",
        "dimension", "chunks", "passage_vector",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("semantic profile fields mismatch")
    if payload["version"] != PROFILE_VERSION:
        raise ValueError("semantic profile version is not supported")
    if payload["embedding_version"] != EMBEDDING_VERSION:
        raise ValueError("semantic embedding version is not supported")
    if payload["chunking_version"] != CHUNKING_VERSION:
        raise ValueError("semantic chunking version is not supported")
    if payload["dimension"] != EMBEDDING_DIMENSION:
        raise ValueError("semantic profile dimension is not supported")
    raw_chunks = payload["chunks"]
    if not isinstance(raw_chunks, list):
        raise ValueError("semantic profile chunks must be an array")
    chunks = []
    for index, item in enumerate(raw_chunks):
        if not isinstance(item, Mapping):
            raise ValueError(f"semantic chunk {index} must be an object")
        if set(item) != {"index", "start", "end", "text_sha256", "values"}:
            raise ValueError(f"semantic chunk {index} fields mismatch")
        if item["index"] != index:
            raise ValueError("semantic chunk indices must be contiguous")
        start, end = item["start"], item["end"]
        if type(start) is not int or type(end) is not int:
            raise ValueError("semantic chunk offsets must be integers")
        if not (0 <= start < end <= len(source_text)):
            raise ValueError("semantic chunk offsets are invalid")
        if item["text_sha256"] != _text_digest(source_text[start:end]):
            raise ValueError("semantic chunk is not bound to its source span")
        chunks.append({"start": start, "end": end, "values": item["values"]})
    rebuilt = build_semantic_profile(
        source_text, chunks, model=payload["model"], revision=payload["revision"]
    )
    supplied_passage = _unit_vector(payload["passage_vector"], "passage vector")
    if rebuilt["passage_vector"] != supplied_passage:
        raise ValueError("semantic passage vector does not replay exactly")
    return rebuilt


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("semantic vector dimension mismatch")
    score = sum(float(x) * float(y) for x, y in zip(left, right))
    return max(0.0, min(1.0, score))


def profile_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Compare every chunk pair; no passage is collapsed before matching."""
    left_chunks = left.get("chunks")
    right_chunks = right.get("chunks")
    if not isinstance(left_chunks, list) or not left_chunks:
        raise ValueError("left semantic profile has no chunks")
    if not isinstance(right_chunks, list) or not right_chunks:
        raise ValueError("right semantic profile has no chunks")
    matrix = [
        [_cosine(a["values"], b["values"]) for b in right_chunks]
        for a in left_chunks
    ]
    left_best = [max(row) for row in matrix]
    right_best = [max(matrix[i][j] for i in range(len(matrix))) for j in range(len(matrix[0]))]
    best_score = max(max(row) for row in matrix)
    best_pair = min(
        (i, j) for i, row in enumerate(matrix) for j, score in enumerate(row)
        if score == best_score
    )
    left_coverage = sum(left_best) / len(left_best)
    right_coverage = sum(right_best) / len(right_best)
    symmetric = 0.5 * best_score + 0.25 * left_coverage + 0.25 * right_coverage
    query_relevance = 0.7 * left_coverage + 0.3 * best_score
    return {
        "best_chunk_score": best_score,
        "left_coverage": left_coverage,
        "right_coverage": right_coverage,
        "symmetric_score": symmetric,
        "query_relevance_score": query_relevance,
        "best_left_chunk_index": best_pair[0],
        "best_right_chunk_index": best_pair[1],
        "pair_count": len(left_chunks) * len(right_chunks),
    }
