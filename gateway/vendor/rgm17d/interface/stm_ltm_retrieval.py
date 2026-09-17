"""
Milestone 3B: STM-triggered LTM Retrieval

Lightweight wrapper around existing _retrieve_relevant_memories() that adds:
- State-based trigger computation (NO text heuristics)
- Deterministic bounds (max 10 items, 2000 chars)
- Session constraint capping (max 3, reserve 5 slots for others)

Design Principles:
1. Reuse existing retrieval logic - NO fork
2. Apply bounds after retrieval
3. NO time-window filtering (avoids tick/epoch confusion)
4. Deterministic constraint capping
"""

import os
import time as _time
from collections import OrderedDict
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Continuity VectorStore LRU cache
# ---------------------------------------------------------------------------
_continuity_vs_cache: OrderedDict = OrderedDict()  # tenant -> (VectorStore, build_time, last_record_id, candidate_count)
_CACHE_TTL_S = 300
_CACHE_MAX_TENANTS = 16


@dataclass
class RetrievalTrigger:
    """
    Structured retrieval trigger computed from STM state.
    NO text heuristics - all fields derived from state structure.
    """
    trigger_type: str  # "pending_context" | "conversation_continuity" | "intent_context"
    intent: Optional[str] = None
    query_keys: List[str] = field(default_factory=list)
    trigger_reason: str = ""


def compute_retrieval_triggers(
    conversation_history: List[Dict[str, Any]],
    pending_interaction: Optional[Any],
    resolved_pending: Optional[Dict[str, Any]],
) -> List[RetrievalTrigger]:
    """
    Compute retrieval triggers from STM STATE (not text).

    NO text scanning. Triggers based on:
    1. Resolved pending intent (indicates specific context need)
    2. Conversation history length (indicates ongoing discussion)
    3. Active pending intent (indicates continuity need)

    Args:
        conversation_history: Recent conversation turns
        pending_interaction: Active pending (if any)
        resolved_pending: Resolved pending payload (if continuity)

    Returns:
        List of retrieval triggers
    """
    triggers = []

    # Trigger 1: Resolved pending with intent
    # When user responds to pending, retrieve context for that intent
    if resolved_pending and resolved_pending.get("intent"):
        triggers.append(RetrievalTrigger(
            trigger_type="pending_context",
            intent=resolved_pending["intent"],
            query_keys=[resolved_pending.get("choice_value", "")],
            trigger_reason=f"Resolved pending: {resolved_pending['intent']}",
        ))

    # Trigger 2: Ongoing conversation (>= 3 turns)
    # Retrieve context from recent conversation
    if conversation_history and len(conversation_history) >= 3:
        triggers.append(RetrievalTrigger(
            trigger_type="conversation_continuity",
            query_keys=[],
            trigger_reason=f"Ongoing conversation ({len(conversation_history)} turns)",
        ))

    # Trigger 3: Active pending with intent
    # Retrieve context to inform choice presentation
    if pending_interaction and hasattr(pending_interaction, 'intent'):
        intent = pending_interaction.intent
        if intent:
            triggers.append(RetrievalTrigger(
                trigger_type="intent_context",
                intent=intent,
                query_keys=[intent],
                trigger_reason=f"Active pending: {intent}",
            ))

    return triggers


def retrieve_ltm_with_stm_triggers(
    controller: Any,
    triggers: List[RetrievalTrigger],
    max_items: int = 10,
    max_chars: int = 2000,
    *,
    user_text: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Retrieve LTM memories using STM triggers, applying RRF fusion and Milestone 3 bounds.

    Uses two-stage candidate generation:
    1. Vector-scored candidates from _retrieve_relevant_memories() (over state.memory.anchors)
    2. RGM vector candidates from rgm.read_memory() (if available + metrics present)

    Fuses using Reciprocal Rank Fusion (RRF) with priors.

    Args:
        controller: ToMController with state.memory.anchors
        triggers: List of RetrievalTrigger from compute_retrieval_triggers()
        max_items: Max items to return (default 10)
        max_chars: Max total chars (default 2000)
        user_text: Optional user query text for fallback retrieval when no triggers

    Returns:
        (memories list, telemetry dict)
    """
    from gateway.vendor.rgm17d.interface.chat_adapter import _retrieve_relevant_memories

    if controller is None:
        return [], {"triggers_count": 0, "items_retrieved": 0}

    # Build query text from triggers
    query_parts = []
    for trigger in (triggers or [])[:2]:  # Max 2 triggers
        if trigger.intent:
            query_parts.append(trigger.intent)
        elif trigger.query_keys:
            query_parts.extend(trigger.query_keys[:2])

    # Fallback: use user_text if no trigger-based query
    if query_parts:
        query_text = " ".join(query_parts)
    elif user_text:
        query_text = user_text
    else:
        # No triggers and no user_text - skip retrieval
        return [], {"triggers_count": 0, "items_retrieved": 0}

    # =========================================================================
    # STAGE 1: Candidate Generation (High Recall)
    # =========================================================================

    Kb = 30  # Primary candidate count (vector-scored)
    Kv = 30  # RGM vector candidate count

    # 1a. Vector-scored candidates (retrieval over state.memory.anchors)
    scored_items, scoring_telemetry = _retrieve_relevant_memories(
        controller,
        user_text=query_text,
        max_memories=Kb,
        min_relevance=0.1,  # Lower threshold to get more candidates
    )

    # Build rank and score maps (1-indexed rank)
    score_rank = {}  # mem_id -> rank (1..Kb)
    relevance_score = {}  # mem_id -> score
    scored_items_by_id = {}  # mem_id -> item dict
    for rank, item in enumerate(scored_items, start=1):
        mem_id = item.get("id")
        if mem_id:
            score_rank[mem_id] = rank
            relevance_score[mem_id] = item.get("relevance_score", 0.0)
            scored_items_by_id[mem_id] = item

    # 1b. RGM vector candidates (if available + metrics present)
    cos_rank = {}  # mem_id -> rank (1..Kv)
    cos_score = {}  # mem_id -> similarity score
    cos_records_by_id = {}  # mem_id -> MemoryRecord (for branch-resonance in Stage 1g)

    state = getattr(controller, "state", None)
    metrics = getattr(state, "metrics", None) if state else None
    rgm = getattr(controller, "rgm", None)
    if rgm is None:
        sicd = getattr(controller, "sicd", None)
        rgm = getattr(sicd, "memory", None) if sicd else None

    rgm_error = None
    if rgm and metrics and hasattr(rgm, "read_memory"):
        try:
            rgm_results = rgm.read_memory(
                query_text,
                context_metrics=metrics,
                k=Kv,
            )
            # DEF-01 fix: read_memory() returns List[MemoryRecord], not tuples.
            # Use rank position for RRF (ranks already encode similarity ordering).
            for rank, record in enumerate(rgm_results, start=1):
                rec_id = getattr(record, "id", None)
                if rec_id:
                    cos_rank[rec_id] = rank
                    cos_score[rec_id] = 1.0 / rank  # Normalized rank-based score
                    cos_records_by_id[rec_id] = record
        except Exception as e:
            rgm_error = str(e)

    # 1c. Continuity candidates (cross-session recall from persistent store)
    Kp = 30
    persist_rank = {}  # mem_id -> rank (1..Kp)
    persist_score = {}  # mem_id -> similarity score
    persist_records_by_id = {}  # mem_id -> MemoryRecord
    continuity_id = getattr(controller, 'continuity_id', None)
    continuity_store_size = 0
    continuity_error = None

    if continuity_id:
        try:
            from gateway.vendor.rgm17d.memory.persistent_store import get_memory_store
            from gateway.vendor.rgm17d.memory.rgm import VectorStore as _VectorStore

            cont_tenant = f"continuity_{continuity_id}"
            cont_store = get_memory_store(cont_tenant)
            all_continuity = cont_store.get_by_type("continuity")
            continuity_store_size = len(all_continuity)

            # Retrieval-side TTL: 90 days
            now = _time.time()
            max_age_s = 90 * 86400
            recent = [r for r in all_continuity if now - r.created_at < max_age_s]
            candidates = recent[-500:]  # Scan cap: most recent 500

            if candidates:
                # LRU-cached VectorStore per tenant
                last_id = candidates[-1].memory_id
                n_cand = len(candidates)
                cached = _continuity_vs_cache.get(cont_tenant)
                if cached and (now - cached[1] < _CACHE_TTL_S) and cached[2] == last_id and cached[3] == n_cand:
                    vs = cached[0]
                    _continuity_vs_cache.move_to_end(cont_tenant)
                else:
                    vs = _VectorStore()
                    for r in candidates:
                        vs.add(r.memory_id, r.content)
                    _continuity_vs_cache[cont_tenant] = (vs, now, last_id, n_cand)
                    while len(_continuity_vs_cache) > _CACHE_MAX_TENANTS:
                        _continuity_vs_cache.popitem(last=False)

                ranked_pairs = vs.query(query_text, k=Kp)
                persist_records_by_id = {r.memory_id: r for r in candidates}
                for rank, (rec_id, sim) in enumerate(ranked_pairs, start=1):
                    persist_rank[rec_id] = rank
                    persist_score[rec_id] = sim
        except Exception as e:
            continuity_error = str(e)

    # =========================================================================
    # STAGE 1d: Action outcome candidates (agent learning from persistent store)
    # =========================================================================

    Ka = 20
    action_rank = {}
    action_score_map = {}
    action_records_by_id = {}
    action_store_size = 0
    action_error = None
    action_learning_enabled = False
    action_cap_applied = False

    try:
        from gateway.vendor.rgm17d.config.compat import get_action_learning_enabled
        action_learning_enabled = get_action_learning_enabled(default=False)
    except ImportError:
        pass

    if action_learning_enabled and continuity_id:
        try:
            from gateway.vendor.rgm17d.memory.persistent_store import get_memory_store
            from gateway.vendor.rgm17d.memory.rgm import VectorStore as _VectorStore

            action_tenant = f"actions_{continuity_id}"
            action_store = get_memory_store(action_tenant)
            all_actions = action_store.get_by_type("action_outcome")
            action_store_size = len(all_actions)

            try:
                from gateway.vendor.rgm17d.config.compat import get_action_learning_ttl_days
                ttl_days = get_action_learning_ttl_days(default=90)
            except ImportError:
                ttl_days = 90
            max_age_s_action = ttl_days * 86400
            now_action = _time.time()
            recent_actions = [r for r in all_actions if now_action - r.created_at < max_age_s_action]
            action_candidates = recent_actions[-200:]  # Scan cap

            if action_candidates:
                a_last_id = action_candidates[-1].memory_id
                a_n_cand = len(action_candidates)
                a_cache_key = f"action_{action_tenant}"
                a_cached = _continuity_vs_cache.get(a_cache_key)
                if a_cached and (now_action - a_cached[1] < _CACHE_TTL_S) and a_cached[2] == a_last_id and a_cached[3] == a_n_cand:
                    a_vs = a_cached[0]
                    _continuity_vs_cache.move_to_end(a_cache_key)
                else:
                    a_vs = _VectorStore()
                    for r in action_candidates:
                        a_vs.add(r.memory_id, r.content)
                    _continuity_vs_cache[a_cache_key] = (a_vs, now_action, a_last_id, a_n_cand)
                    while len(_continuity_vs_cache) > _CACHE_MAX_TENANTS:
                        _continuity_vs_cache.popitem(last=False)

                a_ranked_pairs = a_vs.query(query_text, k=Ka)
                action_records_by_id = {r.memory_id: r for r in action_candidates}
                for rank, (rec_id, sim) in enumerate(a_ranked_pairs, start=1):
                    action_rank[rec_id] = rank
                    action_score_map[rec_id] = sim
        except Exception as e:
            action_error = str(e)

    # =========================================================================
    # STAGE 1f: Agent observation candidates (cross-reference for chatbot)
    # (moved before leaf-rank so agent_obs_records_by_id is populated)
    # =========================================================================

    Kag = 15
    agent_obs_rank = {}
    agent_obs_score_map = {}
    agent_obs_records_by_id = {}
    agent_obs_store_size = 0
    agent_obs_error = None
    agent_obs_cap_applied = False
    _agent_memory_enabled = False

    try:
        from gateway.vendor.rgm17d.config.compat import get_agent_memory_enabled
        _agent_memory_enabled = get_agent_memory_enabled(default=True)
    except ImportError:
        pass

    if _agent_memory_enabled and continuity_id:
        try:
            from gateway.vendor.rgm17d.memory.persistent_store import get_memory_store as _get_mem_store
            from gateway.vendor.rgm17d.memory.rgm import VectorStore as _AgVectorStore

            ag_tenant = f"agent_{continuity_id}"
            ag_store = _get_mem_store(ag_tenant)
            all_ag_obs = ag_store.get_by_type("agent_observation")
            agent_obs_store_size = len(all_ag_obs)

            try:
                from gateway.vendor.rgm17d.config.compat import get_agent_memory_ttl_days
                ag_ttl_days = get_agent_memory_ttl_days(default=90)
            except ImportError:
                ag_ttl_days = 90
            ag_max_age_s = ag_ttl_days * 86400
            now_ag = _time.time()
            recent_ag = [r for r in all_ag_obs if now_ag - r.created_at < ag_max_age_s]
            ag_candidates = recent_ag[-200:]  # Scan cap

            if ag_candidates:
                ag_last_id = ag_candidates[-1].memory_id
                ag_n_cand = len(ag_candidates)
                ag_cache_key = f"agent_{ag_tenant}"
                ag_cached = _continuity_vs_cache.get(ag_cache_key)
                if ag_cached and (now_ag - ag_cached[1] < _CACHE_TTL_S) and ag_cached[2] == ag_last_id and ag_cached[3] == ag_n_cand:
                    ag_vs = ag_cached[0]
                    _continuity_vs_cache.move_to_end(ag_cache_key)
                else:
                    ag_vs = _AgVectorStore()
                    for r in ag_candidates:
                        ag_vs.add(r.memory_id, r.content)
                    _continuity_vs_cache[ag_cache_key] = (ag_vs, now_ag, ag_last_id, ag_n_cand)
                    while len(_continuity_vs_cache) > _CACHE_MAX_TENANTS:
                        _continuity_vs_cache.popitem(last=False)

                ag_ranked_pairs = ag_vs.query(query_text, k=Kag)
                agent_obs_records_by_id = {r.memory_id: r for r in ag_candidates}
                for rank, (rec_id, sim) in enumerate(ag_ranked_pairs, start=1):
                    if sim < 0.05:  # Similarity floor
                        continue
                    agent_obs_rank[rec_id] = rank
                    agent_obs_score_map[rec_id] = sim
        except Exception as e:
            agent_obs_error = str(e)

    # =========================================================================
    # STAGE 1g: Branch-resonance rank (structural prior from SICD tree)
    # (after 1f so all record pools are available)
    # =========================================================================
    leaf_rank = {}  # mem_id -> rank (1..N)
    _leaf_rank_branch_ids: list = []
    _leaf_rank_scores: list = []
    _leaf_rank_k = 16
    _sem_axis: list = [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]
    _resonance_match_details: list = []  # Gate 1: raw (mem_id, branch_id, cosine)
    try:
        from gateway.vendor.rgm17d.agency.mechanics.leaf_vectors import (
            select_activated_branches, rank_by_branch_resonance,
            accumulate_resonance,
        )
        _ctrl_state = getattr(controller, "state", None)
        _branches = getattr(_ctrl_state, "branches", None) if _ctrl_state else None

        # Get current semantic axis for branch activation (fallback chain)
        _sem_axis = None
        if _ctrl_state is not None:
            _last_axis = getattr(_ctrl_state, "last_axis_load", None)
            if _last_axis is not None and len(_last_axis) >= 3:
                _sem_axis = list(_last_axis[:3])
            if _sem_axis is None:
                _sem_targets = getattr(_ctrl_state, "semantic_targets", None)
                if _sem_targets is not None and len(_sem_targets) >= 3:
                    _sem_axis = list(_sem_targets[:3])
            if _sem_axis is None:
                _sem_axis = [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0]  # uniform fallback

        if _branches is not None and len(_branches) > 0:
            try:
                _leaf_rank_k = int(os.getenv("TOM_LEAF_VEC_TOP_K", "16"))
            except (ValueError, TypeError):
                _leaf_rank_k = 16
            _top_k = select_activated_branches(_branches, _sem_axis, k=_leaf_rank_k)

            # Coverage telemetry
            _leaf_rank_branch_ids = [bid for bid, _, _ in _top_k]
            _leaf_rank_scores = [sc for _, _, sc in _top_k]

            if _top_k:
                # Collect ALL pools for branch-resonance ranking.
                _all_records = {}
                _all_records.update(persist_records_by_id)
                _all_records.update(action_records_by_id)
                _all_records.update(agent_obs_records_by_id)
                _all_records.update(cos_records_by_id)

                # score_rank items are dicts without leaf_vec — look up
                # the original anchor objects from state.memory.anchors.
                _anchors = getattr(getattr(_ctrl_state, "memory", None), "anchors", None)
                if _anchors and isinstance(_anchors, dict):
                    for mid in scored_items_by_id:
                        if mid not in _all_records and mid in _anchors:
                            _all_records[mid] = _anchors[mid]

                leaf_rank, _resonance_match_details = rank_by_branch_resonance(
                    _all_records, _top_k,
                )

                # Gate 1: accumulate resonance observation on branch state.
                # NO control authority — pure telemetry accumulation.
                _tick = getattr(_ctrl_state, "tick", 0)
                accumulate_resonance(
                    _branches, _leaf_rank_branch_ids,
                    _resonance_match_details, _tick,
                )
    except Exception:
        pass

    # =========================================================================
    # STAGE 2: RRF Fusion
    # =========================================================================

    # Union of all candidate IDs (including continuity + action + agent obs + leaf-vector)
    all_ids = set(score_rank.keys()) | set(cos_rank.keys()) | set(persist_rank.keys()) | set(action_rank.keys()) | set(agent_obs_rank.keys()) | set(leaf_rank.keys())
    k_rrf = 60  # RRF constant
    w_p = 0.5  # Half-weight for continuity source

    # Action outcome weight
    try:
        from gateway.vendor.rgm17d.config.compat import get_action_learning_retrieval_weight
        w_a = get_action_learning_retrieval_weight(default=0.3)
    except ImportError:
        w_a = 0.3

    # Leaf-vector weight
    try:
        from gateway.vendor.rgm17d.config.compat import get_leaf_vec_retrieval_weight
        w_l = get_leaf_vec_retrieval_weight(default=0.6)
    except ImportError:
        w_l = 0.6

    # C2: per-memory resonance_ema bonus from best-matching branch.
    # w_l_effective = w_l * (1 + resonance_ema_of_best_branch).
    # Validated: 2× independent batches, all 5 gates PASS (spec §9.4).
    _mem_ema_bonus: dict = {}
    if _resonance_match_details and _branches:
        for _mid, _bid, _raw_cos in _resonance_match_details:
            _br = _branches.get(_bid) if hasattr(_branches, "get") else None
            if _br is not None:
                _ema = getattr(_br, "resonance_ema", 0.0)
                if _mid not in _mem_ema_bonus or _ema > _mem_ema_bonus[_mid]:
                    _mem_ema_bonus[_mid] = _ema

    # Agent observation weight
    try:
        from gateway.vendor.rgm17d.config.compat import get_agent_memory_retrieval_weight
        w_ag = get_agent_memory_retrieval_weight(default=0.2)
    except ImportError:
        w_ag = 0.2

    # Compute RRF base score
    rrf_scores = {}
    for mem_id in all_ids:
        r_b = score_rank.get(mem_id)
        r_c = cos_rank.get(mem_id)
        r_p = persist_rank.get(mem_id)
        r_a = action_rank.get(mem_id)
        r_ag = agent_obs_rank.get(mem_id)
        r_l = leaf_rank.get(mem_id)
        rrf = 0.0
        if r_b:
            rrf += 1.0 / (k_rrf + r_b)
        if r_c:
            rrf += 1.0 / (k_rrf + r_c)
        if r_p:
            rrf += w_p / (k_rrf + r_p)
        if r_a:
            rrf += w_a / (k_rrf + r_a)
        if r_ag:
            rrf += w_ag / (k_rrf + r_ag)
        if r_l:
            _w_l_eff = w_l * (1.0 + _mem_ema_bonus.get(mem_id, 0.0))
            rrf += _w_l_eff / (k_rrf + r_l)
        rrf_scores[mem_id] = rrf

    # =========================================================================
    # STAGE 3: Apply Priors
    # =========================================================================

    lambda_strength = 0.3
    mu_recency = 0.15

    final_scores = {}
    for mem_id, rrf in rrf_scores.items():
        # Get anchor_strength and recency from scored item (if available)
        item = scored_items_by_id.get(mem_id, {})
        anchor_strength = item.get("anchor_strength") or 0.5
        recency = item.get("recency") or 0.5

        # Apply priors
        score = rrf * (1 + lambda_strength * anchor_strength) * (1 + mu_recency * recency)
        final_scores[mem_id] = score

    # =========================================================================
    # STAGE 4: Rank with Deterministic Tie-breaks
    # =========================================================================

    def sort_key(mem_id):
        """Tie-break: anchor_strength > cosine > relevance > recency > mem_id"""
        item = scored_items_by_id.get(mem_id, {})
        return (
            -final_scores[mem_id],  # Primary: final score (descending)
            -(item.get("anchor_strength") or 0),  # Tie-break 1
            -cos_score.get(mem_id, 0),  # Tie-break 2
            -relevance_score.get(mem_id, 0),  # Tie-break 3
            -(item.get("recency") or 0),  # Tie-break 4
            mem_id,  # Tie-break 5: stable sort by ID
        )

    ranked_ids = sorted(all_ids, key=sort_key)

    # Build fused memories list
    # DEF-07 fix: include vector-only candidates (not just BM25 items).
    # Look up anchor data from state.memory.anchors for vector-only items.
    state_anchors = {}
    if state and hasattr(state, "memory"):
        mem_obj = getattr(state.memory, "anchors", None)
        if isinstance(mem_obj, dict):
            state_anchors = mem_obj

    fused_memories = []
    for mem_id in ranked_ids:
        item = scored_items_by_id.get(mem_id)
        if item:
            # Use scored item as base, update relevance_score with fused score
            fused_item = dict(item)
            fused_item["relevance_score"] = final_scores[mem_id]
            fused_memories.append(fused_item)
        elif mem_id in cos_rank:
            # DEF-07 fix: Vector-only candidate — construct dict from state anchors
            anchor = state_anchors.get(mem_id)
            if anchor and isinstance(anchor, dict):
                fused_item = {
                    "id": mem_id,
                    "content": anchor.get("content", ""),
                    "relevance_score": final_scores[mem_id],
                    "anchor_type": anchor.get("anchor_type"),
                    "semantic_tags": anchor.get("semantic_tags", []),
                    "anchor_strength": anchor.get("anchor_strength", 0.5),
                    "recency": anchor.get("recency", 0.5),
                    "source": "vector_only",
                }
                fused_memories.append(fused_item)
        elif mem_id in persist_rank:
            # Continuity-only candidate — construct dict from persistent MemoryRecord
            record = persist_records_by_id.get(mem_id)
            if record:
                age_days = (_time.time() - record.created_at) / 86400
                fused_memories.append({
                    "id": mem_id,
                    "content": record.content,
                    "relevance_score": final_scores[mem_id],
                    "anchor_type": "continuity",
                    "semantic_tags": record.semantic_tags,
                    "anchor_strength": record.strength,
                    "recency": max(0.1, 1.0 - age_days / 365.0),
                    "source": "continuity",
                })
        elif mem_id in action_rank:
            # Action outcome candidate — from agent learning store
            record = action_records_by_id.get(mem_id)
            if record:
                age_days = (_time.time() - record.created_at) / 86400
                fused_memories.append({
                    "id": mem_id,
                    "content": record.content,
                    "relevance_score": final_scores[mem_id],
                    "anchor_type": "action_outcome",
                    "semantic_tags": record.semantic_tags,
                    "anchor_strength": record.strength,
                    "recency": max(0.1, 1.0 - age_days / 365.0),
                    "source": "action_outcome",
                })
        elif mem_id in agent_obs_rank:
            # Agent observation candidate — cross-reference from agent store
            record = agent_obs_records_by_id.get(mem_id)
            if record:
                age_days = (_time.time() - record.created_at) / 86400
                fused_memories.append({
                    "id": mem_id,
                    "content": record.content,
                    "relevance_score": final_scores[mem_id],
                    "anchor_type": "agent_observation",
                    "semantic_tags": record.semantic_tags,
                    "anchor_strength": record.strength,
                    "recency": max(0.1, 1.0 - age_days / 365.0),
                    "source": "agent_observation",
                })

    # =========================================================================
    # STAGE 4b: Cap continuity items (max 5 in final result)
    # =========================================================================

    cont_n = 0
    capped_memories = []
    for mem in fused_memories:
        if mem.get("anchor_type") == "continuity":
            cont_n += 1
            if cont_n > 5:
                continue
        capped_memories.append(mem)
    fused_memories = capped_memories
    continuity_cap_applied = cont_n > 5

    # Cap action outcome items
    try:
        from gateway.vendor.rgm17d.config.compat import get_action_learning_retrieval_max
        action_max = get_action_learning_retrieval_max(default=3)
    except ImportError:
        action_max = 3
    action_n = 0
    capped2 = []
    for mem in fused_memories:
        if mem.get("anchor_type") == "action_outcome":
            action_n += 1
            if action_n > action_max:
                continue
        capped2.append(mem)
    fused_memories = capped2
    action_cap_applied = action_n > action_max

    # Cap agent observation items
    try:
        from gateway.vendor.rgm17d.config.compat import get_agent_memory_retrieval_max
        agent_obs_max = get_agent_memory_retrieval_max(default=2)
    except ImportError:
        agent_obs_max = 2
    agent_obs_n = 0
    capped3 = []
    for mem in fused_memories:
        if mem.get("anchor_type") == "agent_observation":
            agent_obs_n += 1
            if agent_obs_n > agent_obs_max:
                continue
        capped3.append(mem)
    fused_memories = capped3
    agent_obs_cap_applied = agent_obs_n > agent_obs_max

    # =========================================================================
    # STAGE 5: Apply Milestone 3 Bounds
    # =========================================================================

    bounded_memories = _apply_milestone3_bounds(
        fused_memories,
        max_items=max_items,
        max_chars=max_chars,
    )

    # =========================================================================
    # Build Telemetry
    # =========================================================================

    overlap_count = len(set(score_rank.keys()) & set(cos_rank.keys()))

    telemetry = {
        **scoring_telemetry,
        "strategy": "vector_rrf_fusion",
        "triggers_count": len(triggers) if triggers else 0,
        "trigger_types": [t.trigger_type for t in triggers] if triggers else [],
        "items_retrieved": len(bounded_memories),
        "truncated": len(fused_memories) > len(bounded_memories),
        "bounded_by": "milestone3",
        "fallback_query": not bool(query_parts),
        # RRF-specific telemetry
        "kb": Kb,
        "kv": Kv,
        "score_candidates": len(score_rank),
        "rgm_candidates": len(cos_rank),
        "candidate_union_size": len(all_ids),
        "overlap_count": overlap_count,
        "score_top_ids": list(score_rank.keys())[:10],
        "cos_top_ids": list(cos_rank.keys())[:10],
        "rrf_topk_ids": ranked_ids[:10],
        "rrf_topk_scores": [round(final_scores[id], 6) for id in ranked_ids[:10]],
    }
    if rgm_error:
        telemetry["rgm_error"] = rgm_error
    # Continuity telemetry
    telemetry["continuity_id"] = continuity_id
    telemetry["continuity_candidates"] = len(persist_rank)
    telemetry["continuity_top_ids"] = list(persist_rank.keys())[:10]
    telemetry["continuity_cap_applied"] = continuity_cap_applied
    telemetry["continuity_store_size"] = continuity_store_size
    if continuity_error:
        telemetry["continuity_error"] = continuity_error
    # Action learning telemetry
    telemetry["action_learning_enabled"] = action_learning_enabled
    telemetry["action_candidates"] = len(action_rank)
    telemetry["action_top_ids"] = list(action_rank.keys())[:10]
    telemetry["action_cap_applied"] = action_cap_applied
    telemetry["action_store_size"] = action_store_size
    if action_error:
        telemetry["action_error"] = action_error
    # Agent observation telemetry
    telemetry["agent_obs_enabled"] = _agent_memory_enabled
    telemetry["agent_obs_candidates"] = len(agent_obs_rank)
    telemetry["agent_obs_top_ids"] = list(agent_obs_rank.keys())[:10]
    telemetry["agent_obs_cap_applied"] = agent_obs_cap_applied
    telemetry["agent_obs_store_size"] = agent_obs_store_size
    if agent_obs_error:
        telemetry["agent_obs_error"] = agent_obs_error
    # Branch-resonance coverage telemetry
    telemetry["leaf_rank_branch_ids"] = _leaf_rank_branch_ids
    telemetry["leaf_rank_scores"] = _leaf_rank_scores
    telemetry["leaf_rank_k"] = _leaf_rank_k
    telemetry["leaf_rank_axis"] = _sem_axis

    # =========================================================================
    # Gate 1: Per-turn resonance trace (observation only, NO control authority)
    # =========================================================================
    _prompt_mem_ids = {m.get("id") for m in bounded_memories if m.get("id")}
    _resonance_trace = []
    for _mid, _bid, _cos in _resonance_match_details:
        _resonance_trace.append({
            "memory_id": _mid,
            "branch_id": _bid,
            "raw_cosine": round(_cos, 6),
            "selected_in_prompt": _mid in _prompt_mem_ids,
        })
    telemetry["resonance_trace"] = _resonance_trace
    telemetry["resonance_matches"] = len(_resonance_match_details)
    telemetry["resonance_turns_with_matches"] = 1 if _resonance_match_details else 0

    # Per-branch resonance EMA snapshot (top-10 by EMA for diagnostics)
    _branch_emas = []
    try:
        _ctrl_st = getattr(controller, "state", None)
        _br = getattr(_ctrl_st, "branches", None) if _ctrl_st else None
        if _br:
            _items = _br.values() if hasattr(_br, "values") else _br
            for _b in _items:
                _rema = getattr(_b, "resonance_ema", 0.0)
                if _rema > 0.0:
                    _branch_emas.append({
                        "branch_id": getattr(_b, "id", ""),
                        "resonance_ema": round(_rema, 6),
                        "resonance_count": getattr(_b, "resonance_count", 0),
                        "last_match_tick": getattr(_b, "last_match_tick", 0),
                    })
            _branch_emas.sort(key=lambda x: -x["resonance_ema"])
    except Exception:
        pass
    telemetry["resonance_branch_top10"] = _branch_emas[:10]

    return bounded_memories, telemetry


def _apply_milestone3_bounds(
    memories: List[Dict[str, Any]],
    max_items: int = 10,
    max_chars: int = 2000,
) -> List[Dict[str, Any]]:
    """
    Apply Milestone 3 deterministic bounds:
    1. Cap session constraints to max 3
    2. Reserve at least 5 slots for non-constraints
    3. Limit total items to max_items
    4. Limit total chars to max_chars

    Args:
        memories: List of memories from _retrieve_relevant_memories
        max_items: Max items (default 10)
        max_chars: Max total chars (default 2000)

    Returns:
        Bounded memories list
    """
    # Separate session constraints from other memories
    constraints = []
    others = []

    for mem in memories:
        # Use anchor_type field (added in PR1) for type detection
        # Fallback to text heuristics for backward compatibility
        anchor_type = mem.get("anchor_type")

        is_constraint = anchor_type == "session_constraint"

        # Fallback heuristics if anchor_type not present
        if anchor_type is None:
            mem_id = mem.get("id", "")
            # M3/DEF-06: Use resolve_content for bounds checking
            from gateway.vendor.rgm17d.memory.content_resolver import resolve_content as _rc
            mem_content = _rc(mem, "prompt") or "" if isinstance(mem, dict) else mem.get("content", "")
            is_constraint = (
                "constraint" in mem_id.lower() or
                mem_content.startswith("Session constraint:")
            )

        if is_constraint:
            constraints.append(mem)
        else:
            others.append(mem)

    # Cap constraints to max 3
    constraints = constraints[:3]

    # Reserve at least 5 slots for non-constraints (if available)
    min_non_constraint_slots = min(5, len(others))
    max_constraint_slots = max_items - min_non_constraint_slots

    # Take up to max_constraint_slots constraints
    bounded_constraints = constraints[:max_constraint_slots]

    # Take remaining slots from others
    remaining_slots = max_items - len(bounded_constraints)
    bounded_others = others[:remaining_slots]

    # Combine: constraints first (high priority), then others
    result = bounded_constraints + bounded_others

    # Apply char limit
    # M3/DEF-06: Use resolve_content for char counting
    from gateway.vendor.rgm17d.memory.content_resolver import resolve_content as _rc
    total_chars = 0
    final_result = []

    for mem in result:
        content = _rc(mem, "prompt") or "" if isinstance(mem, dict) else mem.get("content", "")
        if total_chars + len(content) > max_chars:
            break  # Hit char limit
        final_result.append(mem)
        total_chars += len(content)

    return final_result


def format_ltm_context_for_prompt(memories: List[Dict[str, Any]]) -> str:
    """
    Format retrieved memories for prompt injection.

    Args:
        memories: List of memory dicts from retrieve_ltm_with_stm_triggers

    Returns:
        Formatted string for prompt
    """
    if not memories:
        return ""

    # M3/DEF-06: Use resolve_content for prompt formatting
    from gateway.vendor.rgm17d.memory.content_resolver import resolve_content as _rc
    lines = ["## Retrieved Context (LTM):"]
    for mem in memories:
        content = (_rc(mem, "prompt") or "")[:200] if isinstance(mem, dict) else mem.get("content", "")[:200]
        lines.append(f"- {content}")

    return "\n".join(lines)
