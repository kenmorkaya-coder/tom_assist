"""Unchanged upstream document retrieval function; chat orchestration excluded."""
from __future__ import annotations
import hashlib
import os
import sys
import time
from typing import Any, Dict, List, Tuple

def _retrieve_relevant_memories(
    controller: Any,
    user_text: str,
    *,
    max_memories: int = 5,
    min_relevance: float = 0.3,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve relevant memories from controller's memory store for prompt injection.

    This is the first part of the "brilliance" hook - warm sessions have
    accumulated memories that can inform responses.

    TELEMETRY CHOKE POINT 1: Memory Retrieval
    Emits: mem_count, topK IDs, similarity scores, tokens, payload hash, retrieval latency

    Args:
        controller: ToMController instance
        user_text: Current user input to match against
        max_memories: Maximum memories to retrieve
        min_relevance: Minimum relevance score threshold

    Returns:
        Tuple of (memories list, retrieval telemetry dict)
    """
    retrieval_start = time.time()

    telemetry = {
        "choke_point": 1,
        "choke_name": "memory_retrieval",
        "mem_store_type": None,
        "mem_store_size": 0,
        "candidates_scanned": 0,
        "candidates_above_threshold": 0,
        "mem_count": 0,
        "topk_ids": [],
        "topk_scores": [],
        "topk_tokens": [],
        "payload_hash": None,
        "retrieval_latency_ms": 0,
    }

    if controller is None:
        telemetry["retrieval_latency_ms"] = round((time.time() - retrieval_start) * 1000, 2)
        return [], telemetry

    memories = []
    all_candidates = []  # Track all scanned candidates for telemetry

    try:
        state = getattr(controller, "state", None)
        if state is None:
            telemetry["retrieval_latency_ms"] = round((time.time() - retrieval_start) * 1000, 2)
            return [], telemetry

        # Vector scoring over state.memory.anchors
        # Priority: state.memory.anchors (brilliance hook) > memory_store > memories
        memory_store = None

        # First, check state.memory.anchors (where brilliance hook writes)
        memory_obj = getattr(state, "memory", None)
        if memory_obj is not None:
            anchors = getattr(memory_obj, "anchors", None)
            if anchors and len(anchors) > 0:
                memory_store = anchors
                telemetry["mem_store_type"] = "memory.anchors"

        # Fallback to other memory stores
        if memory_store is None:
            memory_store = getattr(state, "memory_store", None) or getattr(state, "memories", None)

        if memory_store is None:
            # Try sicd memory if available
            sicd = getattr(controller, "sicd", None)
            if sicd:
                memory_store = getattr(sicd, "memory_store", None)

        if memory_store is None:
            telemetry["retrieval_latency_ms"] = round((time.time() - retrieval_start) * 1000, 2)
            return [], telemetry

        # =================================================================
        # VECTOR SCORING: Build similarity map from RGM vector store
        # =================================================================
        _vector_scores: Dict[str, float] = {}
        _vector_search_used = False
        try:
            _rgm = getattr(controller, "rgm", None)
            if _rgm is None:
                _sicd = getattr(controller, "sicd", None)
                _rgm = getattr(_sicd, "memory", None) if _sicd else None
            if _rgm and hasattr(_rgm, "vector_store") and _rgm.vector_store is not None:
                _vs_candidates = _rgm.vector_store.query(user_text, k=max_memories * 3)
                for _rid, _sim in _vs_candidates:
                    _vector_scores[str(_rid)] = float(_sim)
                _vector_search_used = True
                telemetry["scoring_method"] = "vector"
        except Exception:
            pass  # Fall through — vector unavailable
        if not _vector_search_used:
            telemetry["scoring_method"] = "vector_unavailable"

        # Determine memory store type and size
        if isinstance(memory_store, dict):
            telemetry["mem_store_type"] = "dict"
            telemetry["mem_store_size"] = len(memory_store)
        elif isinstance(memory_store, list):
            telemetry["mem_store_type"] = "list"
            telemetry["mem_store_size"] = len(memory_store)
        else:
            telemetry["mem_store_type"] = type(memory_store).__name__
            telemetry["mem_store_size"] = len(memory_store) if hasattr(memory_store, "__len__") else 0

        # =====================================================================
        # DETERMINISTIC DOC SCOPING: Use active_doc_ids from state (NOT keyword detection)
        # If docs are active for this session, prioritize reference_doc anchors
        # =====================================================================
        active_doc_ids = []
        memory_obj = getattr(state, "memory", None)
        if memory_obj is not None:
            active_doc_ids = getattr(memory_obj, "active_doc_ids", [])

        # Build required DOC: tag prefixes from active docs
        required_doc_tags = [f"DOC:{doc_id}" for doc_id in active_doc_ids]
        telemetry["active_doc_ids"] = active_doc_ids
        telemetry["doc_scope_active"] = len(active_doc_ids) > 0

        # Handle different memory store formats
        if isinstance(memory_store, dict):
            # Dict-based memory store
            for key, mem in memory_store.items():
                mem_content = ""
                mem_id = str(key)
                anchor_type = None
                if isinstance(mem, dict):
                    # M3/DEF-06: Use resolve_content for BM25 scoring
                    from gateway.vendor.rgm17d.memory.content_resolver import resolve_content as _rc
                    mem_content = _rc(mem, "bm25") if os.environ.get("TOM_USE_RESOLVE_CONTENT", "1") != "0" else str(mem.get("content", mem.get("text", "")))
                    if mem_content is None:
                        continue  # Unresolvable — skip this anchor for BM25
                    mem_id = str(mem.get("id", key))
                    anchor_type = mem.get("anchor_type")
                elif isinstance(mem, str):
                    mem_content = mem
                elif hasattr(mem, "content"):
                    mem_content = str(getattr(mem, "content", ""))
                    mem_id = str(getattr(mem, "id", key))
                    anchor_type = getattr(mem, "anchor_type", None)

                if not mem_content:
                    continue

                # Get semantic tags for tag-based filtering
                mem_tags = []
                if isinstance(mem, dict):
                    mem_tags = mem.get("semantic_tags", [])
                elif hasattr(mem, "semantic_tags"):
                    mem_tags = getattr(mem, "semantic_tags", [])

                # Deterministic doc scoping: if docs are active, prioritize matching anchors
                is_session_constraint = anchor_type == "session_constraint"
                is_reference_doc = anchor_type == "reference_doc"

                # When docs are active, include reference_doc anchors with matching DOC: tags
                # or non-doc anchors (session constraints, etc.)
                if required_doc_tags and not is_session_constraint:
                    if is_reference_doc:
                        # Must have matching DOC: tag
                        has_matching_tag = any(
                            str(t) in required_doc_tags for t in mem_tags
                        )
                        if not has_matching_tag:
                            continue  # Skip reference_doc without matching tag
                    # Non-doc anchors pass through for now

                telemetry["candidates_scanned"] += 1

                # Score via vector similarity (primary) or 0.0 if vector unavailable
                if _vector_search_used:
                    relevance = _vector_scores.get(mem_id, 0.0)
                else:
                    relevance = 0.0
                all_candidates.append({"id": mem_id, "score": relevance, "tokens": len(mem_content.split())})

                # Session constraint memories ALWAYS pass (they define how to respond)
                # For doc-scoped retrieval, use lower threshold since tag filtering already narrowed scope
                effective_min_relevance = min_relevance * 0.3 if required_doc_tags else min_relevance
                if not is_session_constraint and relevance < effective_min_relevance:
                    continue

                telemetry["candidates_above_threshold"] += 1

                # Extract axis hint if available (convert string "L"|"S"|"T" to dict format)
                axis_hint = {}
                if isinstance(mem, dict):
                    raw_hint = mem.get("axis_hint", {})
                elif hasattr(mem, "axis_hint"):
                    raw_hint = getattr(mem, "axis_hint", {})
                else:
                    raw_hint = {}

                # Normalize axis_hint: convert string format to dict format
                if isinstance(raw_hint, str) and raw_hint in ("L", "S", "T"):
                    # String hint maps to primary axis with 0.7, others get 0.15
                    axis_hint = {"L": 0.15, "S": 0.15, "T": 0.15}
                    axis_hint[raw_hint] = 0.7
                elif isinstance(raw_hint, dict):
                    axis_hint = raw_hint
                else:
                    axis_hint = {}

                # Extract source_refs for doc chunk provenance (guards non-dict metadata)
                source_refs = None
                if isinstance(mem, dict):
                    source_refs = mem.get("source_refs") or mem.get("source_ref")
                    if source_refs is None:
                        meta = mem.get("metadata")
                        if isinstance(meta, dict):
                            source_refs = meta.get("source_refs") or meta.get("source_ref")
                elif hasattr(mem, "source_refs"):
                    source_refs = getattr(mem, "source_refs", None)
                elif hasattr(mem, "metadata"):
                    meta = getattr(mem, "metadata", None)
                    if isinstance(meta, dict):
                        source_refs = meta.get("source_ref")
                # Normalize to list
                if source_refs and not isinstance(source_refs, list):
                    source_refs = [source_refs]

                # Extract anchor_strength for RRF priors
                anchor_strength = None
                if isinstance(mem, dict):
                    anchor_strength = mem.get("anchor_strength", mem.get("strength"))
                elif hasattr(mem, "anchor_strength"):
                    anchor_strength = getattr(mem, "anchor_strength", None)

                memories.append({
                    "id": mem_id,
                    "content": mem_content[:500],  # Truncate
                    "relevance_score": relevance,
                    "recency": 0.5,  # Default recency
                    "axis_hint": axis_hint,
                    "tokens": len(mem_content.split()),
                    "anchor_type": anchor_type,
                    "semantic_tags": mem_tags,
                    "source_refs": source_refs,
                    "anchor_strength": anchor_strength,
                })

        elif isinstance(memory_store, list):
            # List-based memory store
            for i, mem in enumerate(memory_store):
                mem_content = ""
                mem_id = str(i)
                anchor_type = None
                if isinstance(mem, dict):
                    mem_content = str(mem.get("content", mem.get("text", "")))
                    mem_id = str(mem.get("id", i))
                    anchor_type = mem.get("anchor_type")
                elif isinstance(mem, str):
                    mem_content = mem
                elif hasattr(mem, "content"):
                    mem_content = str(getattr(mem, "content", ""))
                    mem_id = str(getattr(mem, "id", i))
                    anchor_type = getattr(mem, "anchor_type", None)

                if not mem_content:
                    continue

                # Get semantic tags for tag-based filtering
                mem_tags = []
                if isinstance(mem, dict):
                    mem_tags = mem.get("semantic_tags", [])
                elif hasattr(mem, "semantic_tags"):
                    mem_tags = getattr(mem, "semantic_tags", [])

                # Deterministic doc scoping: if docs are active, prioritize matching anchors
                is_session_constraint = anchor_type == "session_constraint"
                is_reference_doc = anchor_type == "reference_doc"

                # When docs are active, include reference_doc anchors with matching DOC: tags
                if required_doc_tags and not is_session_constraint:
                    if is_reference_doc:
                        has_matching_tag = any(
                            str(t) in required_doc_tags for t in mem_tags
                        )
                        if not has_matching_tag:
                            continue

                telemetry["candidates_scanned"] += 1

                # Score via vector similarity (primary) or 0.0 if vector unavailable
                if _vector_search_used:
                    relevance = _vector_scores.get(mem_id, 0.0)
                else:
                    relevance = 0.0
                all_candidates.append({"id": mem_id, "score": relevance, "tokens": len(mem_content.split())})

                # For doc-scoped retrieval, use lower threshold
                effective_min_relevance = min_relevance * 0.3 if required_doc_tags else min_relevance
                if not is_session_constraint and relevance < effective_min_relevance:
                    continue

                telemetry["candidates_above_threshold"] += 1

                # Compute recency based on position (later = more recent)
                recency = (i + 1) / len(memory_store) if memory_store else 0.5

                # Extract and normalize axis hint (convert string "L"|"S"|"T" to dict format)
                raw_hint = {}
                if isinstance(mem, dict):
                    raw_hint = mem.get("axis_hint", {})
                elif hasattr(mem, "axis_hint"):
                    raw_hint = getattr(mem, "axis_hint", {})

                # Normalize axis_hint: convert string format to dict format
                if isinstance(raw_hint, str) and raw_hint in ("L", "S", "T"):
                    axis_hint = {"L": 0.15, "S": 0.15, "T": 0.15}
                    axis_hint[raw_hint] = 0.7
                elif isinstance(raw_hint, dict):
                    axis_hint = raw_hint
                else:
                    axis_hint = {}

                # Extract source_refs for doc chunk provenance (guards non-dict metadata)
                source_refs = None
                if isinstance(mem, dict):
                    source_refs = mem.get("source_refs") or mem.get("source_ref")
                    if source_refs is None:
                        meta = mem.get("metadata")
                        if isinstance(meta, dict):
                            source_refs = meta.get("source_refs") or meta.get("source_ref")
                elif hasattr(mem, "source_refs"):
                    source_refs = getattr(mem, "source_refs", None)
                elif hasattr(mem, "metadata"):
                    meta = getattr(mem, "metadata", None)
                    if isinstance(meta, dict):
                        source_refs = meta.get("source_ref")
                # Normalize to list
                if source_refs and not isinstance(source_refs, list):
                    source_refs = [source_refs]

                # Extract anchor_strength for RRF priors
                anchor_strength = None
                if isinstance(mem, dict):
                    anchor_strength = mem.get("anchor_strength", mem.get("strength"))
                elif hasattr(mem, "anchor_strength"):
                    anchor_strength = getattr(mem, "anchor_strength", None)

                memories.append({
                    "id": mem_id,
                    "content": mem_content[:500],
                    "relevance_score": relevance,
                    "recency": recency,
                    "axis_hint": axis_hint,
                    "tokens": len(mem_content.split()),
                    "anchor_type": anchor_type,
                    "semantic_tags": mem_tags,
                    "source_refs": source_refs,
                    "anchor_strength": anchor_strength,
                })

        # =====================================================================
        # FGR POST-SELECTION: Use covering-design selection when enabled
        # Falls back to simple score-based ranking when disabled or on failure
        # =====================================================================
        fgr_used = False
        try:
            from gateway.vendor.rgm17d.config.compat import get_bool, get_config_value
            fgr_enabled = get_bool("fgr.enabled", "TOM_FGR_ENABLED", default=True)
        except Exception:
            fgr_enabled = True

        # Compute effective K: adaptive scaling or fixed max_memories
        effective_k = max_memories
        try:
            from gateway.vendor.rgm17d.config.compat import get_bool as _gb, get_config_value as _gcv
            adaptive_k_enabled = _gb("fgr.adaptive_k", "TOM_FGR_ADAPTIVE_K", default=True)
            if adaptive_k_enabled and fgr_enabled:
                from gateway.vendor.rgm17d.memory.finite_geometry_retrieval import compute_adaptive_k
                k_base = int(_gcv("fgr.k_base", "TOM_FGR_K_BASE", default=5))
                k_max = int(_gcv("fgr.k_max", "TOM_FGR_K_MAX", default=12))
                k_threshold = int(_gcv("fgr.k_scale_threshold", "TOM_FGR_K_SCALE_THRESHOLD", default=50))
                dataset_size = telemetry.get("mem_store_size", 0)
                effective_k = compute_adaptive_k(
                    dataset_size,
                    k_base=k_base,
                    k_max=k_max,
                    k_scale_threshold=k_threshold,
                )
                telemetry["adaptive_k"] = {
                    "enabled": True,
                    "dataset_size": dataset_size,
                    "k_base": k_base,
                    "k_max": k_max,
                    "k_scale_threshold": k_threshold,
                    "effective_k": effective_k,
                }
        except Exception:
            pass  # Fall back to fixed max_memories

        if fgr_enabled and len(memories) > effective_k:
            try:
                from gateway.vendor.rgm17d.memory.finite_geometry_retrieval import finite_geometry_select
                from dataclasses import asdict as _fgr_asdict

                fgr_selected, fgr_telemetry = finite_geometry_select(
                    candidates=memories,
                    query=user_text,
                    K=effective_k,
                )
                fgr_data = _fgr_asdict(fgr_telemetry)
                # Attach adaptive K info inside fgr telemetry for frontend display
                if "adaptive_k" in telemetry:
                    fgr_data["adaptive_k"] = telemetry["adaptive_k"]
                telemetry["fgr"] = fgr_data

                if not fgr_telemetry.fallback_used:
                    memories = fgr_selected
                    fgr_used = True
                else:
                    # Fallback: use score-only ranking
                    memories.sort(key=lambda m: m["relevance_score"], reverse=True)
                    memories = memories[:effective_k]
                    fgr_used = False
            except Exception as fgr_err:
                print(f"[chat_adapter] FGR selection failed, falling back to score-only: {fgr_err}", file=sys.stderr)
                telemetry["fgr_error"] = str(fgr_err)
                memories.sort(key=lambda m: m["relevance_score"], reverse=True)
                memories = memories[:effective_k]
        else:
            # FGR disabled or not enough candidates - use simple top-K
            memories.sort(key=lambda m: m["relevance_score"], reverse=True)
            memories = memories[:effective_k]

        telemetry["fgr_used"] = fgr_used

        # Populate telemetry with topK results
        telemetry["mem_count"] = len(memories)
        telemetry["topk_ids"] = [m["id"] for m in memories]
        telemetry["topk_scores"] = [round(m["relevance_score"], 4) for m in memories]
        telemetry["topk_tokens"] = [m["tokens"] for m in memories]

        # Compute payload hash for deduplication/debugging
        if memories:
            payload_str = "|".join(m["content"][:100] for m in memories)
            telemetry["payload_hash"] = hashlib.md5(payload_str.encode()).hexdigest()[:12]

        # Graph telemetry emission (for future GraphRAG 3D visualization)
        if fgr_used and memories:
            try:
                from gateway.vendor.rgm17d.memory.finite_geometry_retrieval import build_graph_telemetry
                from dataclasses import asdict as _gt_asdict
                graph_event = build_graph_telemetry(
                    query=user_text,
                    query_id=telemetry.get("payload_hash", "unknown"),
                    selected=memories,
                )
                telemetry["graph"] = _gt_asdict(graph_event)
            except Exception:
                pass  # Graph telemetry is optional, never break retrieval

    except Exception as e:
        telemetry["error"] = str(e)
        print(f"[chat_adapter] Memory retrieval failed: {e}", file=sys.stderr)

    telemetry["retrieval_latency_ms"] = round((time.time() - retrieval_start) * 1000, 2)
    return memories, telemetry
