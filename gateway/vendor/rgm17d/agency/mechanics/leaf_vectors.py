"""Per-leaf semantic vectors for SICD branches.

Pure functions — no SICD imports. Each branch carries an 8-dim semantic
signature composed from LLM response signals:

    [L, S, T, delta_x, delta_F, phi, intensity, confidence]

The vector is L2-normalized for cosine-similarity operations.  Raw
confidence is returned separately from compose_leaf_vec() because
L2-normalization distorts element magnitudes.
"""
from __future__ import annotations

import math
import os
from typing import Any, List, Optional, Tuple

LEAF_VEC_DIM = 8


def _env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


_KAPPA_FLOOR = _env_float("TOM_LEAF_VEC_KAPPA_FLOOR", 0.0)


def _l2_normalize(vec: List[float]) -> List[float]:
    """L2-normalize *vec*.  Zero-norm -> uniform [1/sqrt(dim)]*dim."""
    dim = len(vec)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm < 1e-12:
        u = 1.0 / math.sqrt(dim)
        return [u] * dim
    return [v / norm for v in vec]


def compose_leaf_vec(
    semantic_axis,
    loads,
    confidence: float,
) -> Tuple[List[float], float]:
    """Compose 8-dim vector + return raw confidence separately.

    Returns
    -------
    (L2-normalized 8-dim vector, raw_confidence)

    The raw confidence is returned as-is — callers must NOT extract it
    from the normalized vector (index 7 is distorted by normalization).
    """
    # Semantic axis: [L, S, T]
    if isinstance(semantic_axis, (list, tuple)) and len(semantic_axis) >= 3:
        L, S, T = float(semantic_axis[0]), float(semantic_axis[1]), float(semantic_axis[2])
    else:
        L = S = T = 1.0 / 3.0

    # Loads: delta_x, delta_F, phi, intensity
    if isinstance(loads, dict):
        delta_x = float(loads.get("delta_x", 0.0) or 0.0)
        delta_F = float(loads.get("delta_F", 0.0) or 0.0)
        phi = float(loads.get("phi", 0.0) or 0.0)
        intensity = float(loads.get("intensity", 0.0) or 0.0)
    else:
        delta_x = delta_F = phi = intensity = 0.0

    conf = float(confidence) if confidence is not None else 0.0

    raw = [L, S, T, delta_x, delta_F, phi, intensity, conf]
    return _l2_normalize(raw), conf


def ema_update_vec(
    current: Optional[List[float]],
    incoming: List[float],
    alpha: float,
) -> List[float]:
    """(1-alpha)*current + alpha*incoming -> re-normalize.

    If *current* is None, returns *incoming* directly (first update).
    """
    if current is None or len(current) != LEAF_VEC_DIM:
        return list(incoming)
    blended = [
        (1.0 - alpha) * c + alpha * i
        for c, i in zip(current, incoming)
    ]
    return _l2_normalize(blended)


def decay_vec(
    vec: List[float],
    age: int,
    half_life: int,
) -> Optional[List[float]]:
    """Exponential decay toward neutral [1/sqrt(8)]*8.

    Returns None when the remaining scale drops below 0.01 (fully expired).
    """
    if vec is None or len(vec) != LEAF_VEC_DIM:
        return None
    if half_life <= 0:
        return None

    scale = 0.5 ** (age / half_life)
    if scale < 0.01:
        return None

    dim = LEAF_VEC_DIM
    neutral_val = 1.0 / math.sqrt(dim)
    decayed = [
        neutral_val + scale * (v - neutral_val)
        for v in vec
    ]
    return _l2_normalize(decayed)


def cosine_similarity(a, b) -> float:
    """Standard cosine similarity.  Returns 0.0 on invalid input."""
    try:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a < 1e-12 or norm_b < 1e-12:
            return 0.0
        return dot / (norm_a * norm_b)
    except (TypeError, ValueError):
        return 0.0


def compute_tree_query_vec(branches) -> Optional[List[float]]:
    """Kappa-weighted average of all branch sem_vecs.

    Returns None if no branch has a populated sem_vec.
    Mirrors the weighting approach in semantic_metrics.structural_shares().
    """
    weighted_sum = [0.0] * LEAF_VEC_DIM
    total_weight = 0.0

    if not branches:
        return None

    items = branches.values() if hasattr(branches, "values") else branches

    for b in items:
        sv = getattr(b, "sem_vec", None)
        if sv is None or len(sv) != LEAF_VEC_DIM:
            continue
        kappa = getattr(b, "kappa", 1.0)
        if _KAPPA_FLOOR > 0.0:
            w = max(_KAPPA_FLOOR, float(kappa))
        else:
            w = max(0.0, float(kappa))
        for i in range(LEAF_VEC_DIM):
            weighted_sum[i] += w * sv[i]
        total_weight += w

    if total_weight < 1e-12:
        return None

    avg = [s / total_weight for s in weighted_sum]
    return _l2_normalize(avg)


def select_activated_branches(
    branches: Any,
    semantic_axis: List[float],
    k: int = 16,
) -> List[Tuple[str, List[float], float]]:
    """Select top-K activated branches for retrieval.

    Selection uses a composite score that genuinely rotates participation::

        score = align_gate * stiffness_proxy / (1 + usage_count)

    * align_gate: axis alignment with current semantic_axis (same gate as
      apply_leaf_vec_update).
    * stiffness_proxy: r^4 * kappa / ell — structural dominance (EI/L
      beam analogy).
    * usage_count: how many times this branch has been selected — penalises
      overuse, forcing new branches into the active set over time.

    Selected branches get ``usage_count += 1`` (mutates branch in-place).

    Returns ``(branch_id, sem_vec, composite_score)`` sorted descending.
    """
    from gateway.vendor.rgm17d.agency.mechanics.semantic_metrics import stiffness_proxy as _stiff

    _N_AXES = 3
    _ALIGN_THRESHOLD = 1.0 / _N_AXES

    # Normalize semantic axis
    _s = sum(float(x) for x in semantic_axis[:_N_AXES])
    if _s < 1e-12:
        sem_n = [1.0 / _N_AXES] * _N_AXES
    else:
        sem_n = [float(x) / _s for x in semantic_axis[:_N_AXES]]

    # Detect near-uniform axis: all components within ~1.7% of 1/N
    _uniform_eps = 0.05 / _N_AXES
    _axis_is_uniform = all(
        abs(sem_n[i] - 1.0 / _N_AXES) < _uniform_eps for i in range(_N_AXES)
    )

    items = branches.values() if hasattr(branches, "values") else branches
    scored: list = []

    for b in items:
        sv = getattr(b, "sem_vec", None)
        if sv is None or len(sv) != LEAF_VEC_DIM:
            continue

        if _axis_is_uniform:
            # Uniform axis = "no particular topic" -> bypass alignment gate.
            # Score by structural dominance and rotation only.
            align_gate = 1.0
        else:
            # Axis alignment gate (same formula as apply_leaf_vec_update)
            _aw_raw = getattr(b, "axis_w", None)
            if _aw_raw is not None and len(_aw_raw) >= _N_AXES:
                _s2 = sum(float(x) for x in _aw_raw[:_N_AXES])
                if _s2 > 1e-12:
                    _aw_n = [float(x) / _s2 for x in _aw_raw[:_N_AXES]]
                else:
                    _aw_n = [1.0 / _N_AXES] * _N_AXES
            else:
                _aw_n = [1.0 / _N_AXES] * _N_AXES

            alignment = sum(_aw_n[i] * sem_n[i] for i in range(_N_AXES))
            align_gate = max(0.0, alignment - _ALIGN_THRESHOLD) / max(1e-9, 1.0 - _ALIGN_THRESHOLD)

            if align_gate < 1e-6:
                continue  # Skip non-aligned branches entirely

        # Structural dominance via stiffness proxy (r^4 * kappa / ell)
        sp = _stiff(b)

        # Rotation via usage_count — branches used more often score lower
        uc = int(getattr(b, "usage_count", 0))
        score = align_gate * sp / (1.0 + uc)

        scored.append((getattr(b, "id", ""), sv, score, b))

    scored.sort(key=lambda x: -x[2])
    top_k = scored[:k]

    # Increment usage_count on selected branches (mutation for rotation)
    for _, _, _, b_ref in top_k:
        b_ref.usage_count = int(getattr(b_ref, "usage_count", 0)) + 1

    return [(bid, sv, sc) for bid, sv, sc, _ in top_k]


def rank_by_branch_resonance(
    records: dict,
    activated_branches: List[Tuple[str, List[float], float]],
) -> Tuple[dict, list]:
    """Rank memory records by max cosine similarity to activated branches.

    ``records`` maps ``mem_id`` to any object whose ``leaf_vec`` attribute
    (8-dim list) will be matched.  Objects without a valid ``leaf_vec`` are
    silently skipped.

    ``activated_branches`` is the output of :func:`select_activated_branches`
    — a list of ``(branch_id, sem_vec, score)`` tuples.

    Returns ``(ranks, match_details)`` where:
    - ``ranks``: ``{mem_id: rank}`` (1-indexed, lower is better)
    - ``match_details``: list of ``(mem_id, best_branch_id, raw_cosine)``
      for every record that had a valid leaf_vec match.
    """
    if not activated_branches:
        return {}, []

    sims: list = []
    match_details: list = []
    for mid, rec in records.items():
        rec_lv = getattr(rec, "leaf_vec", None)
        # Also handle plain dicts that carry leaf_vec
        if rec_lv is None and isinstance(rec, dict):
            rec_lv = rec.get("leaf_vec")
        if rec_lv is None or len(rec_lv) != LEAF_VEC_DIM:
            continue
        best_sim = -1.0
        best_bid = ""
        for bid, branch_sv, _ in activated_branches:
            sim = cosine_similarity(branch_sv, rec_lv)
            if sim > best_sim:
                best_sim = sim
                best_bid = bid
        sims.append((mid, best_sim))
        match_details.append((mid, best_bid, best_sim))

    sims.sort(key=lambda x: -x[1])
    ranks = {mid: rank for rank, (mid, _) in enumerate(sims, start=1)}
    return ranks, match_details


# Default EMA alpha for resonance accumulation (configurable via env)
_RESONANCE_ALPHA = _env_float("TOM_RESONANCE_EMA_ALPHA", 0.1)
_RESONANCE_DECAY = _env_float("TOM_RESONANCE_DECAY", 0.02)


def accumulate_resonance(
    branches: Any,
    activated_branch_ids: List[str],
    match_details: list,
    tick: int,
    alpha: Optional[float] = None,
    decay: Optional[float] = None,
) -> None:
    """Gate 1 observation: accumulate retrieval resonance on branch state.

    Updates ``resonance_ema``, ``resonance_count``, and ``last_match_tick``
    on branches that were activated and matched retrieved memories.
    Non-activated branches receive slow decay only.

    **NO CONTROL AUTHORITY.** This function is strictly observational.
    Promotion to spawn/routing requires ablation proof of decision-point gain.

    Args:
        branches: dict of branch_id → BranchState (mutated in place).
        activated_branch_ids: branch IDs selected by select_activated_branches().
        match_details: from rank_by_branch_resonance() — list of
            (mem_id, best_branch_id, raw_cosine).
        tick: current engine tick.
        alpha: EMA blend factor (default from TOM_RESONANCE_EMA_ALPHA, 0.1).
        decay: per-turn decay for non-activated branches (default 0.02).
    """
    if alpha is None:
        alpha = _RESONANCE_ALPHA
    if decay is None:
        decay = _RESONANCE_DECAY

    # Build per-branch max cosine from match details
    branch_max_cos: dict = {}
    for _mid, best_bid, raw_cos in match_details:
        if best_bid in branch_max_cos:
            branch_max_cos[best_bid] = max(branch_max_cos[best_bid], raw_cos)
        else:
            branch_max_cos[best_bid] = raw_cos

    activated_set = set(activated_branch_ids)
    items = branches.values() if hasattr(branches, "values") else branches

    for b in items:
        bid = getattr(b, "id", "")
        if bid in activated_set:
            max_cos = branch_max_cos.get(bid, 0.0)
            old_ema = getattr(b, "resonance_ema", 0.0)
            b.resonance_ema = alpha * max_cos + (1.0 - alpha) * old_ema
            if max_cos > 0.0:
                b.resonance_count = getattr(b, "resonance_count", 0) + 1
                b.last_match_tick = tick
        else:
            # Slow decay for non-activated branches
            old_ema = getattr(b, "resonance_ema", 0.0)
            if old_ema > 0.0:
                b.resonance_ema = old_ema * (1.0 - decay)
