"""
Helpers for semantic-vs-structural metrics in the mechanics layer.

This module intentionally remains dependency-light so it can be used from
simulation harnesses without pulling in large optional stacks.
"""
from __future__ import annotations

import math
import re
from typing import Any, Iterable, List, Optional, Sequence, Tuple

import os

from gateway.vendor.rgm17d.state.state_types import BranchState

EPS = 1e-8


def _env_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


_STIFFNESS_KAPPA_FLOOR = _env_float("TOM_STIFFNESS_KAPPA_FLOOR", 0.0)

AXIS_LABELS = ("L", "S", "T")


def _get_axes() -> Tuple[List[str], int]:
    """Return (AXES, N_AXES) if defined; otherwise default to L/S/T."""
    try:
        from tom_core.geometry.axes import AXES as _AXES, N_AXES as _N_AXES
        axes_list = list(_AXES)
        n_axes = int(_N_AXES)
        if axes_list and n_axes == len(axes_list):
            return axes_list, n_axes
    except Exception:
        pass
    return list(AXIS_LABELS), 3


_AXIS_KEYWORDS = {
    "L": {
        "logic", "logical", "reason", "reasoning", "abstract", "abstraction",
        "math", "mathematical", "proof", "deduce", "deduction", "infer",
        "inference", "causality", "causal", "cause", "effect", "code",
        "algorithm", "formal", "analyze", "analysis", "analytical",
        "syllogism", "premise", "conclusion", "theorem", "axiom",
        "hypothesis", "derive", "derivation", "conditional", "implication",
    },
    "S": {
        "structure", "structural", "spatial", "pattern", "patterns",
        "architecture", "architectural", "design", "organization", "organize",
        "layout", "topology", "graph", "tree", "hierarchy", "hierarchical",
        "network", "relationship", "relationships", "connection", "map",
        "mapping", "diagram", "schema", "framework", "model", "component",
        "module", "composition", "decompose", "arrangement", "geometry",
    },
    "T": {
        "temporal", "time", "timing", "sequence", "sequential", "order",
        "ordering", "schedule", "scheduling", "plan", "planning", "phase",
        "step", "steps", "stage", "pipeline", "workflow", "process",
        "execution", "execute", "flow", "timeline", "duration", "deadline",
        "before", "after", "next", "then", "priority", "prioritize",
        "iteration", "cycle", "cadence", "milestone", "progress",
    },
}


def _normalize_axis_w(axis_w: Iterable[float], n_axes: int) -> Tuple[List[float], bool]:
    """
    Return (normalised axis list, used_fallback).

    used_fallback is True if input was invalid/missing and we returned uniform default.
    """
    vals = list(axis_w)[:n_axes]
    if len(vals) < n_axes:
        vals.extend([0.0] * (n_axes - len(vals)))

    total = sum(vals)
    if total <= 0.0 or not math.isfinite(total):
        return [1.0 / n_axes] * n_axes, True

    return [v / total for v in vals], False


def _safe_axis_values(values: Sequence[Any]) -> Tuple[Tuple[float, float, float], bool]:
    cleaned: list[float] = []
    invalid = False
    for idx in range(3):
        try:
            val = float(values[idx]) if idx < len(values) else 0.0
        except (TypeError, ValueError):
            val = 0.0
            invalid = True
        if not math.isfinite(val) or val < 0.0:
            val = 0.0
            invalid = True
        cleaned.append(val)
    return (cleaned[0], cleaned[1], cleaned[2]), invalid


def _normalize_semantic_vector(
    values: Optional[Sequence[Any]],
) -> Optional[Tuple[float, float, float]]:
    if values is None:
        return None
    (L_raw, S_raw, T_raw), invalid = _safe_axis_values(values)
    total = L_raw + S_raw + T_raw
    if invalid or total <= 0.0 or not math.isfinite(total):
        return None
    return (L_raw / total, S_raw / total, T_raw / total)


def resolve_semantic_axis(
    raw_axis: Optional[Sequence[Any]],
    fallback: Optional[Sequence[Any]] = None,
) -> Tuple[float, float, float]:
    """Resolve semantic axis weights with fallback to the configured prior."""
    resolved = _normalize_semantic_vector(raw_axis)
    if resolved is not None:
        return resolved
    fallback_resolved = _normalize_semantic_vector(fallback)
    if fallback_resolved is not None:
        return fallback_resolved
    # Degenerate fallback: semantic signal and priors are missing/invalid.
    return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)


def _tokenize(text: str) -> list[str]:
    return [tok for tok in re.split(r"[^a-z0-9]+", text.lower()) if tok]


def _axis_from_focus_text(text: str) -> Optional[Tuple[float, float, float]]:
    tokens = _tokenize(text)
    if not tokens:
        return None
    scores = {axis: 0.0 for axis in AXIS_LABELS}
    for token in tokens:
        for axis, keywords in _AXIS_KEYWORDS.items():
            if token in keywords:
                scores[axis] += 1.0
    if all(val <= 0.0 for val in scores.values()):
        return None
    return (scores["L"], scores["S"], scores["T"])


def _axis_from_structural_adjustments(adjustments: Any) -> Optional[Tuple[float, float, float]]:
    if not isinstance(adjustments, list):
        return None
    scores = {axis: 0.0 for axis in AXIS_LABELS}
    for entry in adjustments:
        if not isinstance(entry, dict):
            continue
        target = str(entry.get("target", "")).lower()
        if not target:
            continue
        tokens = set(_tokenize(target))
        if "axis" not in tokens and "semantic" not in tokens:
            continue
        magnitude = entry.get("magnitude", 1.0)
        try:
            magnitude_val = float(magnitude)
        except (TypeError, ValueError):
            magnitude_val = 1.0
        if "l" in tokens:
            scores["L"] += max(0.0, magnitude_val)
        if "s" in tokens:
            scores["S"] += max(0.0, magnitude_val)
        if "t" in tokens:
            scores["T"] += max(0.0, magnitude_val)
    if all(val <= 0.0 for val in scores.values()):
        return None
    return (scores["L"], scores["S"], scores["T"])


def semantic_axis_from_state(state: Any) -> Optional[Tuple[float, float, float]]:
    """Derive a raw semantic vector from controller/LLM state if available."""
    llm_json = getattr(state, "last_llm_json", None)
    if isinstance(llm_json, dict):
        direct = llm_json.get("semantic_axis") or llm_json.get("semantic_axes")
        if isinstance(direct, (list, tuple)):
            resolved = _normalize_semantic_vector(direct)
            if resolved is not None:
                return resolved

        semantic_block = llm_json.get("semantic") if isinstance(llm_json.get("semantic"), dict) else {}
        if semantic_block:
            axis_values = [
                semantic_block.get("axis_L_sem"),
                semantic_block.get("axis_S_sem"),
                semantic_block.get("axis_T_sem"),
            ]
            resolved = _normalize_semantic_vector(axis_values)
            if resolved is not None:
                return resolved

        adjustments = llm_json.get("structural_adjustments")
        axis_from_structural = _axis_from_structural_adjustments(adjustments)
        if axis_from_structural is not None:
            return axis_from_structural

        plan = llm_json.get("plan") if isinstance(llm_json.get("plan"), dict) else {}
        focus_text = plan.get("focus") or plan.get("summary")
        if isinstance(focus_text, str) and focus_text.strip():
            axis_from_focus = _axis_from_focus_text(focus_text)
            if axis_from_focus is not None:
                return axis_from_focus

        prediction = llm_json.get("prediction") if isinstance(llm_json.get("prediction"), dict) else {}
        risk_text = prediction.get("risk")
        if isinstance(risk_text, str) and risk_text.strip():
            axis_from_focus = _axis_from_focus_text(risk_text)
            if axis_from_focus is not None:
                return axis_from_focus

    return None


def semantic_axis_from_candidate(candidate: dict) -> Optional[Tuple[float, float, float]]:
    """Extract implied (L, S, T) axis from a candidate LLM JSON dict.

    Mirrors the exact extraction cascade of semantic_axis_from_state()
    but reads from candidate dict instead of state.last_llm_json.
    Returns None when no axis data can be extracted (caller assigns penalty).
    """
    if not isinstance(candidate, dict):
        return None

    direct = candidate.get("semantic_axis") or candidate.get("semantic_axes")
    if isinstance(direct, (list, tuple)):
        resolved = _normalize_semantic_vector(direct)
        if resolved is not None:
            return resolved

    semantic_block = candidate.get("semantic") if isinstance(candidate.get("semantic"), dict) else {}
    if semantic_block:
        axis_values = [
            semantic_block.get("axis_L_sem"),
            semantic_block.get("axis_S_sem"),
            semantic_block.get("axis_T_sem"),
        ]
        resolved = _normalize_semantic_vector(axis_values)
        if resolved is not None:
            return resolved

    adjustments = candidate.get("structural_adjustments")
    axis_from_structural = _axis_from_structural_adjustments(adjustments)
    if axis_from_structural is not None:
        return axis_from_structural

    plan = candidate.get("plan") if isinstance(candidate.get("plan"), dict) else {}
    focus_text = plan.get("focus") or plan.get("summary")
    if isinstance(focus_text, str) and focus_text.strip():
        axis_from_focus = _axis_from_focus_text(focus_text)
        if axis_from_focus is not None:
            return axis_from_focus

    prediction = candidate.get("prediction") if isinstance(candidate.get("prediction"), dict) else {}
    risk_text = prediction.get("risk")
    if isinstance(risk_text, str) and risk_text.strip():
        axis_from_risk = _axis_from_focus_text(risk_text)
        if axis_from_risk is not None:
            return axis_from_risk

    return None


def axis_w_for_branch(
    branch: BranchState,
    semantic_axis: Sequence[Any],
) -> Tuple[float, float, float]:
    """Blend a semantic axis prior with branch-specific topology for axis_w."""
    base = resolve_semantic_axis(semantic_axis)
    depth = int(getattr(branch, "depth", 0) or 0)
    theta = float(getattr(branch, "theta", 0.0) or 0.0)

    depth_bias = [0.0, 0.0, 0.0]
    depth_idx = depth % 3
    depth_bias[depth_idx] = 0.06 + 0.01 * min(depth, 6)

    angle_bias = [
        0.04 * (1.0 + math.cos(theta)),
        0.04 * (1.0 + math.sin(theta)),
        0.04 * (1.0 + math.cos(theta + math.pi / 2.0)),
    ]

    raw = [
        max(0.0, base[0] + depth_bias[0] + angle_bias[0]),
        max(0.0, base[1] + depth_bias[1] + angle_bias[1]),
        max(0.0, base[2] + depth_bias[2] + angle_bias[2]),
    ]
    normalized = resolve_semantic_axis(raw)
    return normalized


def stiffness_proxy(b: BranchState) -> float:
    """Compute stiffness proxy K_b := r^4 * kappa / ell (EI/L analogy).

    Kappa acts as structural health: branches with low kappa (plastically
    deformed under sustained load) contribute less to aggregate shares.
    Optional floor (TOM_STIFFNESS_KAPPA_FLOOR) ensures deformed branches
    still contribute to structural shares.
    """
    r = float(getattr(b, "r", 0.0) or 0.0)
    ell = float(getattr(b, "ell", 0.0) or 0.0)
    kappa = float(getattr(b, "kappa", 1.0))
    if kappa < 0.0:
        kappa = 1.0
    if _STIFFNESS_KAPPA_FLOOR > 0.0 and kappa < _STIFFNESS_KAPPA_FLOOR:
        kappa = _STIFFNESS_KAPPA_FLOOR
    return max(EPS, (r ** 4) * kappa / max(EPS, ell))


def structural_shares(state) -> List[float]:
    """Compute stiffness-weighted structural shares across axes."""
    axes_list, n_axes = _get_axes()
    branches = getattr(state, "branches", {}) or {}

    total_k = 0.0
    accum = [0.0] * n_axes

    for b in branches.values():
        k_b = stiffness_proxy(b)
        axis_w_raw = getattr(b, "axis_w", None)
        if axis_w_raw is None or not isinstance(axis_w_raw, (list, tuple)):
            axis_w = [1.0 / n_axes] * n_axes
        else:
            axis_w, _ = _normalize_axis_w(axis_w_raw, n_axes)

        total_k += k_b
        for a in range(n_axes):
            accum[a] += k_b * axis_w[a]

    if total_k <= 0.0:
        return [1.0 / n_axes] * n_axes

    return [accum[a] / total_k for a in range(n_axes)]


def structural_shares_from_arrays(arrays) -> List[float]:
    """Compute stiffness-weighted structural shares from packed branch arrays."""
    import numpy as _np

    n_axes = 3
    if getattr(arrays, "n", 0) <= 0:
        return [1.0 / n_axes] * n_axes

    r = _np.asarray(arrays.r, dtype=_np.float64)
    ell = _np.asarray(arrays.ell, dtype=_np.float64)
    kappa = _np.asarray(arrays.kappa, dtype=_np.float64)
    axis_w = _np.asarray(arrays.axis_w, dtype=_np.float64)

    if _STIFFNESS_KAPPA_FLOOR > 0.0:
        kappa = _np.maximum(kappa, _STIFFNESS_KAPPA_FLOOR)
    kappa = _np.where(kappa < 0.0, 1.0, kappa)

    stiffness = _np.maximum(EPS, (r ** 4) * kappa / _np.maximum(EPS, ell))
    total_k = float(stiffness.sum())
    if total_k <= 0.0:
        return [1.0 / n_axes] * n_axes

    accum = stiffness @ axis_w
    return [float(accum[a] / total_k) for a in range(n_axes)]


def leaf_shares(state) -> List[float]:
    """
    Compute reservoir-leaf shares across axes.

    IMPORTANT SEMANTICS:
    - In this codebase, BranchState.leaves is already an axis-resolved reservoir
      vector (per-axis leaf canopy) that contributes directly to κ_local.
    - Therefore, canonical leaf shares are computed by summing leaves per-axis
      across branches, NOT by summing and redistributing via axis_w.
    - Only if leaves are missing/invalid do we fall back to equal shares.
    """
    axes_list, n_axes = _get_axes()
    branches = getattr(state, "branches", {}) or {}

    accum = [0.0] * n_axes
    for b in branches.values():
        leaves = getattr(b, "leaves", None)
        if not isinstance(leaves, (list, tuple)):
            continue

        try:
            for a in range(min(n_axes, len(leaves))):
                val = float(leaves[a])
                if math.isfinite(val):
                    accum[a] += val
        except (TypeError, ValueError):
            # Ignore invalid leaf vectors rather than poisoning totals.
            continue

    total_leaf = sum(accum)
    if total_leaf <= 0.0 or not math.isfinite(total_leaf):
        return [1.0 / n_axes] * n_axes

    return [accum[a] / total_leaf for a in range(n_axes)]


def compute_lst_balance(
    shares: Tuple[float, float, float],
    targets: Tuple[float, float, float],
) -> float:
    """Compute raw L1 distance between structural shares and semantic targets."""
    return abs(shares[0] - targets[0]) + abs(shares[1] - targets[1]) + abs(shares[2] - targets[2])


def lst_balance(
    shares: Tuple[float, float, float],
    targets: Tuple[float, float, float],
) -> float:
    """Scalar mismatch metric between structural shares and semantic targets (raw L1)."""
    return abs(shares[0] - targets[0]) + abs(shares[1] - targets[1]) + abs(shares[2] - targets[2])


def canopy_env_bias_semantic_target(
    base_target: Tuple[float, float, float],
    struct_shares: Tuple[float, float, float],
    leaf_shares: Tuple[float, float, float],
    *,
    imbalance: float,
    max_gain: float = 0.35,
) -> Tuple[Tuple[float, float, float], dict]:
    gain = max(0.0, min(float(max_gain), 1.4 * float(imbalance)))

    def _norm3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        x0, x1, x2 = (float(v[0]), float(v[1]), float(v[2]))
        x0 = x0 if math.isfinite(x0) and x0 > 0.0 else 0.0
        x1 = x1 if math.isfinite(x1) and x1 > 0.0 else 0.0
        x2 = x2 if math.isfinite(x2) and x2 > 0.0 else 0.0
        s = x0 + x1 + x2
        if s <= EPS:
            return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
        return (x0 / s, x1 / s, x2 / s)

    base = _norm3(base_target)
    dL = float(struct_shares[0]) - float(leaf_shares[0])
    dS = float(struct_shares[1]) - float(leaf_shares[1])
    dT = float(struct_shares[2]) - float(leaf_shares[2])

    biased = _norm3(
        (
            max(0.0, base[0] + gain * dL),
            max(0.0, base[1] + gain * dS),
            max(0.0, base[2] + gain * dT),
        )
    )

    info = {
        "gain": float(gain),
        "struct_share": [float(struct_shares[0]), float(struct_shares[1]), float(struct_shares[2])],
        "leaf_share": [float(leaf_shares[0]), float(leaf_shares[1]), float(leaf_shares[2])],
        "delta": [float(dL), float(dS), float(dT)],
        "semantic_target_base": [float(base[0]), float(base[1]), float(base[2])],
        "semantic_target_biased": [float(biased[0]), float(biased[1]), float(biased[2])],
    }
    return biased, info


# ============================================================================
# Leaf / Structure Aggregation Metrics (leaf_branch.md v1)
# ============================================================================


def leaf_struct_metrics(state) -> dict:
    """
    Compute canonical leaf/struct aggregation metrics per leaf_branch.md §4.

    Returns dict with:
        - Leaf_share: List[float] - normalized leaf shares per axis
        - Struct_share: List[float] - normalized structure shares per axis
        - LeafStruct_ratio_axis: List[float] - leaf/structure ratios per axis
        - imbalance_max: float - max |Leaf_share[a] - Struct_share[a]|
        - defaulted_any: bool - True if any defaults were used
        - defaulted_signals: List[str] - reasons for defaults
        - axis_w_defaulted_count: int - count of branches with invalid/missing axis_w
        - leaves_defaulted_count: int - count of branches with invalid/missing leaves
        - affected_branch_ids: List[str] - sample of branch IDs that used defaults (capped at 10)
        - Leaf_total: float - total leaf magnitude across all branches
        - Struct_total: float - total structural weight across all branches

    N-axis compatible: uses _get_axes() to support arbitrary number of axes.
    Uses leaves vector directly (already axis-resolved), NOT sum then redistribute.
    Uses stiffness_proxy (r^4*kappa/ell) for structural weight.
    """
    axes_list, n_axes = _get_axes()
    branches = getattr(state, "branches", {}) or {}

    # Anomaly tracking
    defaulted_signals = []
    axis_w_defaulted_count = 0
    leaves_defaulted_count = 0
    affected_branch_ids = []

    if not branches:
        # Empty tree fallback
        uniform = [1.0 / n_axes] * n_axes
        defaulted_signals.append("empty_tree")
        result = {
            "Leaf_share": uniform.copy(),
            "Struct_share": uniform.copy(),
            "LeafStruct_ratio_axis": [1.0] * n_axes,
            "imbalance_max": 0.0,
            "defaulted_any": True,
            "defaulted_signals": defaulted_signals,
            "axis_w_defaulted_count": 0,
            "leaves_defaulted_count": 0,
            "affected_branch_ids": [],
            "Leaf_total": 0.0,
            "Struct_total": 0.0,
        }
        # Add flattened keys for backward compatibility
        for a, axis_label in enumerate(axes_list):
            result[f"Leaf_share_{axis_label}"] = uniform[a]
            result[f"Struct_share_{axis_label}"] = uniform[a]
            result[f"LeafStruct_ratio_{axis_label}"] = 1.0
        return result

    # Per-axis accumulators
    Leaf = [0.0] * n_axes
    Struct = [0.0] * n_axes

    for b in branches.values():
        branch_id = getattr(b, "id", None)

        # Leaf: use leaves vector directly (already axis-resolved)
        leaves_vec = getattr(b, "leaves", None)
        leaves_valid = False
        if isinstance(leaves_vec, (list, tuple)) and len(leaves_vec) > 0:
            for a in range(min(n_axes, len(leaves_vec))):
                try:
                    val = float(leaves_vec[a])
                    if math.isfinite(val) and val > 0.0:
                        Leaf[a] += val
                        leaves_valid = True
                except (TypeError, ValueError):
                    pass

        if not leaves_valid:
            leaves_defaulted_count += 1
            if branch_id and len(affected_branch_ids) < 10 and branch_id not in affected_branch_ids:
                affected_branch_ids.append(str(branch_id))

        # Structure: use stiffness_proxy (r^4*kappa/ell) weighted by axis_w
        k_b = stiffness_proxy(b)
        axis_w_raw = getattr(b, "axis_w", None)
        used_fallback = False
        if axis_w_raw is None or not isinstance(axis_w_raw, (list, tuple)):
            axis_w = [1.0 / n_axes] * n_axes
            used_fallback = True
        else:
            axis_w, used_fallback = _normalize_axis_w(axis_w_raw, n_axes)

        if used_fallback:
            axis_w_defaulted_count += 1
            if branch_id and len(affected_branch_ids) < 10 and branch_id not in affected_branch_ids:
                affected_branch_ids.append(str(branch_id))

        for a in range(n_axes):
            Struct[a] += k_b * axis_w[a]

    # Totals
    Leaf_total = sum(Leaf)
    Struct_total = sum(Struct)

    # Shares (normalized)
    if Leaf_total > EPS:
        Leaf_share = [Leaf[a] / Leaf_total for a in range(n_axes)]
    else:
        Leaf_share = [1.0 / n_axes] * n_axes
        defaulted_signals.append("leaf_total_zero")

    if Struct_total > EPS:
        Struct_share = [Struct[a] / Struct_total for a in range(n_axes)]
    else:
        Struct_share = [1.0 / n_axes] * n_axes
        defaulted_signals.append("struct_total_zero")

    # Leaf/Struct ratios
    LeafStruct_ratio = []
    for a in range(n_axes):
        if Struct[a] > EPS:
            LeafStruct_ratio.append(Leaf[a] / Struct[a])
        else:
            LeafStruct_ratio.append(0.0)

    # Imbalance: max |Leaf_share[a] - Struct_share[a]|
    imbalance_vals = [abs(Leaf_share[a] - Struct_share[a]) for a in range(n_axes)]
    imbalance_max = max(imbalance_vals) if imbalance_vals else 0.0

    # Add signals for per-branch defaulting
    if axis_w_defaulted_count > 0:
        defaulted_signals.append("axis_w_invalid")
    if leaves_defaulted_count > 0:
        defaulted_signals.append("leaves_missing")

    defaulted_any = len(defaulted_signals) > 0

    # Return dict with vector keys + flattened backward-compatible keys
    result = {
        "Leaf_share": Leaf_share,
        "Struct_share": Struct_share,
        "LeafStruct_ratio_axis": LeafStruct_ratio,
        "imbalance_max": imbalance_max,
        "defaulted_any": defaulted_any,
        "defaulted_signals": defaulted_signals,
        "axis_w_defaulted_count": axis_w_defaulted_count,
        "leaves_defaulted_count": leaves_defaulted_count,
        "affected_branch_ids": affected_branch_ids[:10],  # Cap at 10
        "Leaf_total": Leaf_total,
        "Struct_total": Struct_total,
    }

    # Add flattened keys for backward compatibility
    for a, axis_label in enumerate(axes_list):
        result[f"Leaf_share_{axis_label}"] = Leaf_share[a]
        result[f"Struct_share_{axis_label}"] = Struct_share[a]
        result[f"LeafStruct_ratio_{axis_label}"] = LeafStruct_ratio[a]

    return result
