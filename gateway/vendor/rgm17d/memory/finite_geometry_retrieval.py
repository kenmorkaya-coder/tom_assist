"""
Finite Geometry Retriever (FGR) — Covering-Design Memory Selection.

Applies Cushing-Stewart (arXiv:2307.12430v2) covering-design decomposition
principles to maximize concept coverage in memory retrieval while minimizing
redundancy.

Key ideas from the paper:
1. Decomposition Principle (Lemma 3.1): Optimal coverage decomposes into
   disjoint covering designs over balanced partitions.
2. Excess Function E(X): Measures redundant coverage — minimized by FGR.
3. Per-query quality gate: FGR output only used when it beats baseline.

Algorithm phases:
  0. Build hybrid union pool (top N vector, dedupe)
  1. Multi-channel concept extraction (hash + DSI + SEI)
  2. Axis partition (L/S/T — Lemma 3.1 analog)
  3. Greedy weighted set cover per partition
  4. Cross-partition merge + fill
  5. Per-query quality gate with automatic fallback
  6. Coverage telemetry

All operations are deterministic. Tie-breaking by memory_id (lexicographic).

Subsystem: memory
Owns: post-retrieval coverage-optimized selection
Must Not: modify memory state, enforce policy, or introduce non-determinism
"""

from __future__ import annotations

import hashlib
import re
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


# ============================================================================
# TELEMETRY TYPES
# ============================================================================

@dataclass(frozen=True)
class FgrTelemetry:
    """Telemetry emitted per FGR selection cycle."""
    candidate_count: int              # N candidates in union pool
    selected_count: int               # K chunks output
    coverage_ratio: float             # |covered query concepts| / |total query concepts|
    redundancy_score: float           # Excess E(X) analog
    axis_distribution: Dict[str, int] # {"L": 2, "S": 1, "T": 2}
    partition_groups: List[List[str]]  # IDs grouped by L/S/T partition
    channel_coverage: Dict[str, float]  # {"hash": 0.7, "dsi": 0.9, "heading": 0.5}
    fallback_used: bool
    fallback_reason: Optional[str]
    latency_ms: float


@dataclass(frozen=True)
class GraphNode:
    """Node in the retrieval graph (for future GraphRAG 3D)."""
    id: str
    type: str          # "source" | "doc" | "chunk" | "anchor" | "query"
    label: str
    axis_hint: Optional[str]
    partition_group: Optional[str]


@dataclass(frozen=True)
class GraphEdge:
    """Edge in the retrieval graph."""
    source_id: str
    target_id: str
    type: str          # "ingested_from" | "indexed_as" | "retrieved_in" | "cited_by"
    weight: float


@dataclass(frozen=True)
class GraphTelemetryEvent:
    """Graph telemetry emitted per retrieval cycle."""
    timestamp: float
    query_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ============================================================================
# ADAPTIVE K COMPUTATION
# ============================================================================

import math


def compute_adaptive_k(
    dataset_size: int,
    *,
    k_base: int = 5,
    k_max: int = 12,
    k_scale_threshold: int = 50,
) -> int:
    """
    Compute optimal K (chunks to select) based on memory store size.

    Uses logarithmic scaling: once the dataset exceeds k_scale_threshold,
    K grows by 1 for each doubling of the dataset size, capped at k_max.

    Formula: K = min(k_max, k_base + floor(log2(dataset_size / threshold)))

    Examples (with defaults k_base=5, k_max=12, threshold=50):
        dataset_size < 50  -> K = 5
        dataset_size = 50  -> K = 5
        dataset_size = 100 -> K = 6
        dataset_size = 200 -> K = 7
        dataset_size = 400 -> K = 8
        dataset_size = 800 -> K = 9
        dataset_size = 2000+ -> K = 12 (capped)

    Args:
        dataset_size: Total records in the memory store.
        k_base: Minimum K (floor).
        k_max: Maximum K (ceiling, limited by token budget).
        k_scale_threshold: Dataset size at which scaling begins.

    Returns:
        Computed K value, always in [k_base, k_max].
    """
    if dataset_size <= k_scale_threshold or k_scale_threshold <= 0:
        return max(1, min(k_base, k_max))

    ratio = dataset_size / k_scale_threshold
    k = k_base + int(math.log2(ratio))
    return min(max(k_base, k), k_max)


# ============================================================================
# CONCEPT EXTRACTION
# ============================================================================

# Channel weights (configurable via TOM_FGR_CHANNEL_WEIGHTS)
_DEFAULT_CHANNEL_WEIGHTS = {"hash": 1.0, "dsi": 1.5, "heading": 1.2}

# Stop words for topic extraction
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "and", "but", "or",
    "not", "no", "if", "then", "than", "that", "this", "these", "those",
    "it", "its", "i", "me", "my", "we", "our", "you", "your", "he",
    "she", "they", "them", "their", "what", "which", "who", "how", "when",
    "where", "why", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "so", "very",
})

_TOKEN_PATTERN = re.compile(r'\b[a-zA-Z0-9]+\b')


def _encode_hash_buckets(text: str, dim: int = 256) -> Set[int]:
    """
    Deterministic hash-bucket encoding matching VectorStore._encode().
    Returns the set of non-zero bucket indices.
    """
    tokens = text.lower().split()
    buckets: Set[int] = set()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        buckets.add(bucket)
    return buckets


def _extract_topic_tokens(text: str) -> Set[str]:
    """Extract topic tokens from text (tokenize, remove stops)."""
    tokens = _TOKEN_PATTERN.findall(text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) >= 2}


def _get_dsi_topics(candidate: Dict[str, Any]) -> Set[str]:
    """Extract DSI topic tags from a candidate's semantic_tags."""
    tags = candidate.get("semantic_tags", [])
    topics: Set[str] = set()
    for tag in tags:
        tag_str = str(tag)
        if tag_str.startswith("TOPIC:"):
            topics.add(tag_str[6:].lower())
    # Also check metadata for dsi_topics
    meta = candidate.get("metadata", {})
    if isinstance(meta, dict):
        for topic in meta.get("dsi_topics", []):
            topics.add(str(topic).lower())
    return topics


def _get_heading_ids(candidate: Dict[str, Any]) -> Set[str]:
    """Extract SEI/heading tags from a candidate's semantic_tags."""
    tags = candidate.get("semantic_tags", [])
    headings: Set[str] = set()
    for tag in tags:
        tag_str = str(tag)
        if tag_str.startswith("SECTION:") or tag_str.startswith("HEADING:"):
            headings.add(tag_str)
    return headings


def _build_concept_set(
    candidate: Dict[str, Any],
    channel_weights: Dict[str, float],
) -> Tuple[Set[Tuple[str, str]], Dict[Tuple[str, str], float]]:
    """
    Build multi-channel concept set for a candidate.

    Returns:
        (concept_set, concept_weights) where concept_set is the set of
        (channel, id) tuples and concept_weights maps each to its weight.
    """
    concepts: Set[Tuple[str, str]] = set()
    weights: Dict[Tuple[str, str], float] = {}

    # Channel A: Hash buckets
    content = candidate.get("content", "")
    hash_buckets = _encode_hash_buckets(content)
    hash_weight = channel_weights.get("hash", 1.0)
    for b in hash_buckets:
        key = ("hash", str(b))
        concepts.add(key)
        weights[key] = hash_weight

    # Channel B: DSI topics
    dsi_topics = _get_dsi_topics(candidate)
    dsi_weight = channel_weights.get("dsi", 1.5)
    for t in dsi_topics:
        key = ("dsi", t)
        concepts.add(key)
        weights[key] = dsi_weight

    # Channel C: SEI/Heading IDs
    heading_ids = _get_heading_ids(candidate)
    heading_weight = channel_weights.get("heading", 1.2)
    for h in heading_ids:
        key = ("heading", h)
        concepts.add(key)
        weights[key] = heading_weight

    return concepts, weights


def _build_query_concepts(
    query: str,
    channel_weights: Dict[str, float],
) -> Tuple[Set[Tuple[str, str]], Dict[Tuple[str, str], float]]:
    """Build multi-channel concept set for the query."""
    concepts: Set[Tuple[str, str]] = set()
    weights: Dict[Tuple[str, str], float] = {}

    # Channel A: Hash buckets
    hash_buckets = _encode_hash_buckets(query)
    hash_weight = channel_weights.get("hash", 1.0)
    for b in hash_buckets:
        key = ("hash", str(b))
        concepts.add(key)
        weights[key] = hash_weight

    # Channel B: DSI topic tokens
    dsi_weight = channel_weights.get("dsi", 1.5)
    for t in _extract_topic_tokens(query):
        key = ("dsi", t)
        concepts.add(key)
        weights[key] = dsi_weight

    return concepts, weights


# ============================================================================
# COVERAGE AND REDUNDANCY METRICS
# ============================================================================

def compute_coverage(
    selected: List[Dict[str, Any]],
    query_concepts: Set[Tuple[str, str]],
) -> float:
    """
    Compute coverage ratio: fraction of query concepts covered by selected chunks.
    """
    if not query_concepts:
        return 1.0
    covered: Set[Tuple[str, str]] = set()
    for chunk in selected:
        chunk_concepts = chunk.get("_concepts", set())
        covered |= (chunk_concepts & query_concepts)
    return len(covered) / len(query_concepts)


def compute_redundancy(
    selected: List[Dict[str, Any]],
    query_concepts: Set[Tuple[str, str]],
) -> float:
    """
    Excess-based redundancy (paper's E(X) analog).

    For each query concept, counts how many selected chunks cover it.
    Ideal = 1 (each concept covered once).
    Excess = sum of (count - 1) for concepts covered more than once.
    """
    if not query_concepts:
        return 0.0
    concept_counts: Counter = Counter()
    for chunk in selected:
        chunk_concepts = chunk.get("_concepts", set())
        for c in chunk_concepts & query_concepts:
            concept_counts[c] += 1
    return float(sum(max(0, count - 1) for count in concept_counts.values()))


def compute_channel_coverage(
    selected: List[Dict[str, Any]],
    query_concepts: Set[Tuple[str, str]],
) -> Dict[str, float]:
    """Compute per-channel coverage ratios."""
    channel_totals: Dict[str, int] = Counter()
    channel_covered: Dict[str, Set[str]] = {"hash": set(), "dsi": set(), "heading": set()}

    for channel, cid in query_concepts:
        channel_totals[channel] += 1

    for chunk in selected:
        chunk_concepts = chunk.get("_concepts", set())
        for channel, cid in chunk_concepts & query_concepts:
            channel_covered.setdefault(channel, set()).add(cid)

    result: Dict[str, float] = {}
    for channel in ("hash", "dsi", "heading"):
        total = channel_totals.get(channel, 0)
        covered = len(channel_covered.get(channel, set()))
        result[channel] = covered / total if total > 0 else 1.0

    return result


# ============================================================================
# CORE FGR ALGORITHM
# ============================================================================

def _parse_channel_weights(weights_str: str) -> Dict[str, float]:
    """Parse channel weights from config string 'hash,dsi,heading'."""
    try:
        parts = [float(x.strip()) for x in weights_str.split(",")]
        if len(parts) >= 3:
            return {"hash": parts[0], "dsi": parts[1], "heading": parts[2]}
    except (ValueError, IndexError):
        pass
    return dict(_DEFAULT_CHANNEL_WEIGHTS)


def _get_axis_hint(candidate: Dict[str, Any]) -> Optional[str]:
    """Extract axis hint from candidate, normalizing to L/S/T."""
    hint = candidate.get("axis_hint")
    if hint is None:
        return None
    hint_str = str(hint).upper().strip()
    if hint_str in ("L", "S", "T"):
        return hint_str
    # Handle dict-style axis hints
    if isinstance(hint, dict):
        max_axis = max(hint, key=lambda k: hint.get(k, 0), default=None)
        if max_axis and str(max_axis).upper() in ("L", "S", "T"):
            return str(max_axis).upper()
    return None


def finite_geometry_select(
    candidates: List[Dict[str, Any]],
    query: str,
    K: int = 5,
    axis_balance: bool = True,
    channel_weights_str: str = "1.0,1.5,1.2",
    latency_budget_ms: float = 50.0,
) -> Tuple[List[Dict[str, Any]], FgrTelemetry]:
    """
    Select K chunks from N candidates maximizing concept coverage.

    Uses covering-design decomposition (Cushing-Stewart Lemma 3.1):
    1. Extract multi-channel concept vectors (hash + DSI + SEI)
    2. Partition candidates by L/S/T axis hint
    3. Greedy weighted set cover per partition
    4. Cross-partition merge with redundancy trimming
    5. Per-query quality gate with automatic fallback

    All operations are fully deterministic. Tie-breaking by memory_id
    (lexicographic) ensures reproducible output.

    Args:
        candidates: List of candidate dicts with 'content', 'memory_id',
                   'hybrid_score', 'semantic_tags', 'axis_hint' fields.
        query: The user's query string.
        K: Number of chunks to select.
        axis_balance: Whether to partition by L/S/T axis.
        channel_weights_str: Comma-separated hash,dsi,heading weights.
        latency_budget_ms: Max allowed processing time before fallback.

    Returns:
        (selected_chunks, telemetry) tuple.
    """
    start_time = time.monotonic()
    channel_weights = _parse_channel_weights(channel_weights_str)

    # Handle edge cases
    if not candidates:
        return [], FgrTelemetry(
            candidate_count=0, selected_count=0,
            coverage_ratio=1.0, redundancy_score=0.0,
            axis_distribution={"L": 0, "S": 0, "T": 0},
            partition_groups=[[], [], []],
            channel_coverage={"hash": 1.0, "dsi": 1.0, "heading": 1.0},
            fallback_used=False, fallback_reason=None,
            latency_ms=0.0,
        )

    if len(candidates) <= K:
        # Return all candidates, still compute telemetry
        query_concepts, _ = _build_query_concepts(query, channel_weights)
        for c in candidates:
            c_concepts, _ = _build_concept_set(c, channel_weights)
            c["_concepts"] = c_concepts

        elapsed = (time.monotonic() - start_time) * 1000
        return candidates, FgrTelemetry(
            candidate_count=len(candidates),
            selected_count=len(candidates),
            coverage_ratio=compute_coverage(candidates, query_concepts),
            redundancy_score=compute_redundancy(candidates, query_concepts),
            axis_distribution=_count_axes(candidates),
            partition_groups=_build_partition_groups(candidates),
            channel_coverage=compute_channel_coverage(candidates, query_concepts),
            fallback_used=False, fallback_reason=None,
            latency_ms=elapsed,
        )

    # ---- PHASE 1: Multi-Channel Concept Extraction ----
    query_concepts, query_weights = _build_query_concepts(query, channel_weights)

    for c in candidates:
        c_concepts, c_weights = _build_concept_set(c, channel_weights)
        c["_concepts"] = c_concepts
        c["_concept_weights"] = c_weights
        c["_query_overlap"] = c_concepts & query_concepts

    # ---- Compute baseline top-K (for quality gate) ----
    baseline_topk = sorted(
        candidates,
        key=lambda c: (c.get("hybrid_score", 0.0), c.get("memory_id", "")),
        reverse=True,
    )[:K]
    baseline_coverage = compute_coverage(baseline_topk, query_concepts)
    baseline_redundancy = compute_redundancy(baseline_topk, query_concepts)

    # ---- PHASE 2: Axis Partition ----
    if axis_balance:
        result = _axis_partitioned_select(candidates, query_concepts, query_weights, K, channel_weights)
    else:
        result = _greedy_select(candidates, query_concepts, query_weights, K, channel_weights)

    # ---- PHASE 5: Per-Query Quality Gate ----
    elapsed_ms = (time.monotonic() - start_time) * 1000

    fgr_coverage = compute_coverage(result, query_concepts)
    fgr_redundancy = compute_redundancy(result, query_concepts)

    fallback_used = False
    fallback_reason = None

    # Check gates
    gate_failures = []
    if fgr_coverage < baseline_coverage:
        gate_failures.append(f"coverage({fgr_coverage:.3f}<{baseline_coverage:.3f})")
    if fgr_redundancy > baseline_redundancy:
        gate_failures.append(f"redundancy({fgr_redundancy:.1f}>{baseline_redundancy:.1f})")
    if elapsed_ms > latency_budget_ms:
        gate_failures.append(f"latency({elapsed_ms:.1f}ms>{latency_budget_ms}ms)")

    if gate_failures:
        fallback_used = True
        fallback_reason = "; ".join(gate_failures)
        result = baseline_topk
        fgr_coverage = baseline_coverage
        fgr_redundancy = baseline_redundancy

    # ---- PHASE 6: Coverage Telemetry ----
    final_elapsed = (time.monotonic() - start_time) * 1000

    telemetry = FgrTelemetry(
        candidate_count=len(candidates),
        selected_count=len(result),
        coverage_ratio=fgr_coverage,
        redundancy_score=fgr_redundancy,
        axis_distribution=_count_axes(result),
        partition_groups=_build_partition_groups(result),
        channel_coverage=compute_channel_coverage(result, query_concepts),
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        latency_ms=final_elapsed,
    )

    return result, telemetry


# ============================================================================
# INTERNAL HELPERS
# ============================================================================

def _axis_partitioned_select(
    candidates: List[Dict[str, Any]],
    query_concepts: Set[Tuple[str, str]],
    query_weights: Dict[Tuple[str, str], float],
    K: int,
    channel_weights: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Axis-partitioned greedy set cover (Lemma 3.1 analog).

    Partitions candidates into L/S/T pools, allocates K//3 slots per axis,
    then runs greedy set cover within each pool.
    """
    # Partition by axis
    pools: Dict[str, List[Dict[str, Any]]] = {"L": [], "S": [], "T": []}
    untagged: List[Dict[str, Any]] = []

    for c in candidates:
        axis = _get_axis_hint(c)
        if axis in pools:
            pools[axis].append(c)
        else:
            untagged.append(c)

    # Distribute untagged to smallest pool (round-robin by size)
    untagged_sorted = sorted(untagged, key=lambda c: c.get("memory_id", ""))
    for c in untagged_sorted:
        smallest = min(pools, key=lambda a: len(pools[a]))
        pools[smallest].append(c)

    # Allocate slots: K//3 per axis, remainder to largest pool
    base_slots = K // 3
    remainder = K - base_slots * 3
    slot_alloc = {"L": base_slots, "S": base_slots, "T": base_slots}
    # Give remainder to axis with most candidates
    largest = max(pools, key=lambda a: len(pools[a]))
    slot_alloc[largest] += remainder

    # Greedy set cover per partition
    all_selected: List[Dict[str, Any]] = []
    global_covered: Set[Tuple[str, str]] = set()

    for axis in ("L", "S", "T"):
        pool = pools[axis]
        slots = slot_alloc[axis]
        selected = _greedy_select(pool, query_concepts, query_weights, slots, channel_weights, global_covered)
        all_selected.extend(selected)
        for s in selected:
            global_covered |= s.get("_query_overlap", set())

    # Fill remaining slots if under K
    if len(all_selected) < K:
        selected_ids = {c.get("memory_id") for c in all_selected}
        remaining = [c for c in candidates if c.get("memory_id") not in selected_ids]
        remaining.sort(key=lambda c: (-c.get("hybrid_score", 0.0), c.get("memory_id", "")))
        all_selected.extend(remaining[:K - len(all_selected)])

    # Trim if over K (shouldn't happen, but safety)
    if len(all_selected) > K:
        # Trim highest-redundancy chunks
        for c in all_selected:
            c["_redundancy"] = sum(
                len(c.get("_concepts", set()) & other.get("_concepts", set()))
                for other in all_selected if other is not c
            )
        all_selected.sort(key=lambda c: (-c.get("hybrid_score", 0.0), c.get("_redundancy", 0)))
        all_selected = all_selected[:K]

    return all_selected


def _greedy_select(
    pool: List[Dict[str, Any]],
    query_concepts: Set[Tuple[str, str]],
    query_weights: Dict[Tuple[str, str], float],
    K: int,
    channel_weights: Dict[str, float],
    pre_covered: Optional[Set[Tuple[str, str]]] = None,
) -> List[Dict[str, Any]]:
    """
    Greedy weighted set cover within a single pool.

    Selects chunks that maximize:
        cover_score = sum(weight for new concepts) * hybrid_score

    Deterministic tie-break: lowest memory_id (lexicographic).
    """
    if not pool or K <= 0:
        return []

    covered = set(pre_covered) if pre_covered else set()
    selected: List[Dict[str, Any]] = []
    available = list(pool)

    while len(selected) < K and available:
        best_score = -1.0
        best_idx = -1

        for i, c in enumerate(available):
            overlap = c.get("_query_overlap", set())
            new_concepts = overlap - covered
            # Weighted coverage gain * hybrid relevance
            gain = sum(
                c.get("_concept_weights", {}).get(concept, 1.0)
                for concept in new_concepts
            )
            hybrid_score = c.get("hybrid_score", 0.0)
            cover_score = gain * max(hybrid_score, 0.001)  # avoid zero

            # Deterministic tie-break: higher cover_score wins,
            # then lower memory_id (lexicographic)
            memory_id = c.get("memory_id", "")
            if (cover_score > best_score or
                    (cover_score == best_score and best_idx >= 0 and
                     memory_id < available[best_idx].get("memory_id", ""))):
                best_score = cover_score
                best_idx = i

        if best_idx < 0:
            break

        best = available.pop(best_idx)
        selected.append(best)
        covered |= best.get("_query_overlap", set())

    return selected


def _count_axes(selected: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count axis distribution in selected chunks."""
    counts = {"L": 0, "S": 0, "T": 0}
    for c in selected:
        axis = _get_axis_hint(c)
        if axis in counts:
            counts[axis] += 1
    return counts


def _build_partition_groups(selected: List[Dict[str, Any]]) -> List[List[str]]:
    """Build partition groups [L_ids, S_ids, T_ids] for telemetry."""
    groups: Dict[str, List[str]] = {"L": [], "S": [], "T": []}
    for c in selected:
        axis = _get_axis_hint(c) or "L"
        groups.setdefault(axis, []).append(c.get("memory_id", ""))
    return [groups.get("L", []), groups.get("S", []), groups.get("T", [])]


# ============================================================================
# HYBRID POOL BUILDER
# ============================================================================

def build_hybrid_pool(
    candidates: List[Dict[str, Any]],
    query: str,
    text_index: Any = None,
    vector_store: Any = None,
    limit_per_source: int = 15,
) -> List[Dict[str, Any]]:
    """
    Build hybrid union pool from vector candidates.

    When vector_store is provided, queries it and merges with candidates.
    Otherwise, treats the candidates list as the pre-built pool.

    Args:
        candidates: Existing candidate list (used as fallback pool).
        query: Query string.
        text_index: DEPRECATED — ignored, kept for API compat.
        vector_store: VectorStore instance (optional).
        limit_per_source: Max candidates per retrieval source.

    Returns:
        Deduplicated pool with hybrid_score annotations.
    """
    pool: Dict[str, Dict[str, Any]] = {}

    # Vector from VectorStore
    if vector_store is not None:
        try:
            vector_results = vector_store.query(query, k=limit_per_source)
            for record_id, similarity in vector_results:
                if record_id not in pool:
                    pool[record_id] = {
                        "memory_id": record_id,
                        "content": "",
                        "vector_score": similarity,
                    }
                else:
                    pool[record_id]["vector_score"] = max(
                        pool[record_id].get("vector_score", 0.0), similarity
                    )
        except Exception:
            pass

    # If no external indices available, use the candidates as-is
    if not pool:
        for c in candidates:
            mid = c.get("memory_id", c.get("anchor_id", c.get("id", "")))
            if mid:
                entry = dict(c)
                entry["memory_id"] = mid
                if "hybrid_score" not in entry:
                    entry["hybrid_score"] = entry.get("relevance_score", 0.0)
                pool[mid] = entry

    # Compute hybrid scores — vector-only (BM25 removed)
    result = []
    for mid, entry in pool.items():
        vector = entry.get("vector_score", 0.0)
        entry["hybrid_score"] = vector

        # Merge with original candidate data if available
        for c in candidates:
            c_mid = c.get("memory_id", c.get("anchor_id", c.get("id", "")))
            if c_mid == mid:
                for key in ("content", "semantic_tags", "axis_hint", "metadata",
                             "source_ref", "anchor_type", "section_id"):
                    if key in c and key not in entry:
                        entry[key] = c[key]
                    elif key in c and not entry.get(key):
                        entry[key] = c[key]
                break

        result.append(entry)

    return result


# ============================================================================
# GRAPH TELEMETRY BUILDER
# ============================================================================

def build_graph_telemetry(
    query: str,
    query_id: str,
    selected: List[Dict[str, Any]],
) -> GraphTelemetryEvent:
    """
    Build graph telemetry event from FGR selection results.

    Creates nodes for the query and each selected chunk,
    plus edges for retrieval relationships.
    """
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    # Query node
    nodes.append(GraphNode(
        id=query_id,
        type="query",
        label=query[:50],
        axis_hint=None,
        partition_group=None,
    ))

    for chunk in selected:
        memory_id = chunk.get("memory_id", "")
        axis = _get_axis_hint(chunk)

        # Chunk node
        nodes.append(GraphNode(
            id=memory_id,
            type="chunk",
            label=chunk.get("content", "")[:30],
            axis_hint=axis,
            partition_group=axis,
        ))

        # retrieved_in edge (query -> chunk)
        edges.append(GraphEdge(
            source_id=query_id,
            target_id=memory_id,
            type="retrieved_in",
            weight=chunk.get("hybrid_score", 0.0),
        ))

        # indexed_as edge (chunk -> source doc)
        source_ref = chunk.get("source_ref", "")
        if isinstance(source_ref, dict):
            doc_id = source_ref.get("doc_id", "")
        elif isinstance(source_ref, str):
            doc_id = source_ref
        else:
            doc_id = ""

        if doc_id:
            # Add doc node if not already present
            doc_node_id = f"doc:{doc_id}"
            if not any(n.id == doc_node_id for n in nodes):
                nodes.append(GraphNode(
                    id=doc_node_id,
                    type="doc",
                    label=str(doc_id)[:30],
                    axis_hint=None,
                    partition_group=None,
                ))
            edges.append(GraphEdge(
                source_id=memory_id,
                target_id=doc_node_id,
                type="indexed_as",
                weight=1.0,
            ))

    return GraphTelemetryEvent(
        timestamp=time.time(),
        query_id=query_id,
        nodes=nodes,
        edges=edges,
    )
