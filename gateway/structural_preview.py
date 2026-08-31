"""Read-only geometry mirrors at tom_master 8799ccbdd; no load application."""
from __future__ import annotations

import numpy as np

POLICY_VERSION = "context-policy/1.1"
W_LEAF = 0.6  # Review 4 calibration prior, not a product efficacy claim.
RRF_K = 60


def project_text(text: str):
    # Mirror only the existing pure preparation chain, never the runtime bridge:
    # integration/tomowner_msr_runtime_bridge.py:85-103; projection.py:15-181;
    # integration/msr_field_packet.py:158-226; sicd_msr_load.py:65-124.
    # No new prose-to-shape rules: Box 2 remains held.
    from integration.msr_prompt_text_projection import project_prompt_text_to_neutral_packet
    from integration.msr_field_packet import adapt_to_msr_field_packet
    from agency.mechanics.msr_8d_loading_aware_readout import (
        project_load_signature_to_channel_separated_basis,
        load_signature_120_readout_angle,
    )
    packet = adapt_to_msr_field_packet(project_prompt_text_to_neutral_packet(text))
    if not packet.schema_valid:
        raise ValueError("pinned prompt projection failed")
    signature = packet.load_signature
    # Pure 17->8 computation: msr_8d_loading_aware_readout.py:49-124.
    projection = project_load_signature_to_channel_separated_basis(signature)
    return signature, projection, load_signature_120_readout_angle(signature)


def unit_rows(values):
    values = np.asarray(values, dtype=float)
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-12)


def select_cohort(branches, projection, angle, kappa_floor: float, k: int = 16):
    """Vectorized leaf_vectors.py:197-253; deliberately omit mutation :255-257."""
    rows = sorted(((str(bid), b) for bid, b in branches.items()
                   if getattr(b, "sem_vec", None) is not None and len(b.sem_vec) == 8))
    if not rows:
        return [], []
    ids, objects = zip(*rows)
    vectors = unit_rows([b.sem_vec for b in objects])
    axis = np.asarray(projection.raw_8d[:3], dtype=float)
    axis = axis / axis.sum() if axis.sum() > 1e-12 else np.full(3, 1 / 3)
    axes = np.asarray([getattr(b, "axis_w", None) or (1 / 3,) * 3 for b in objects])[:, :3]
    sums = axes.sum(axis=1, keepdims=True)
    axes = np.divide(axes, sums, out=np.full_like(axes, 1 / 3), where=sums > 1e-12)
    align = (np.ones(len(rows)) if np.all(np.abs(axis - 1 / 3) < 0.05 / 3)
             else np.maximum(0.0, (axes * axis).sum(axis=1) - 1 / 3) / (2 / 3))
    # semantic_metrics.py:303-318, including the pinned kappa floor and EPS.
    radii = np.asarray([float(b.r or 0) for b in objects])
    lengths = np.asarray([float(b.ell or 0) for b in objects])
    kappa = np.asarray([float(b.kappa) for b in objects])
    kappa = np.maximum(np.where(kappa < 0, 1.0, kappa), kappa_floor)
    stiffness = np.maximum(1e-8, radii ** 4 * kappa / np.maximum(1e-8, lengths))
    usage = np.asarray([int(getattr(b, "usage_count", 0)) for b in objects])
    score = align * stiffness / (1 + usage)
    # Loading-aware cosine + theta gate mirror, msr_8d_loading_aware_readout.py:187-230.
    theta = np.asarray([float(getattr(b, "theta", 0) or 0) for b in objects])
    loading = (vectors * np.asarray(projection.vector_8d)).sum(axis=1) * (
        0.75 + 0.25 * np.maximum(0, 0.5 + 0.5 * np.cos(theta - angle)) ** 2)
    eligible = np.flatnonzero(align >= 1e-6)
    selected = eligible[np.argsort(-score[eligible], kind="stable")[:k]]
    cohort = [(ids[i], objects[i].sem_vec, float(score[i])) for i in selected]
    trace = [{"branch_id": ids[i], "alignment_gate": float(align[i]),
              "stiffness": float(stiffness[i]), "usage_count": int(usage[i]),
              "selection_score": float(score[i]), "loading_aware_score": float(loading[i])}
             for i in selected]
    return cohort, trace


def fuse_anchors(records, lexical, cohort):
    # rank_by_branch_resonance mirror, leaf_vectors.py:262-304: max cosine,
    # invalid/missing leaf vectors omitted. Stable ID ties survive restart.
    structural = []
    valid = sorted((rid, rec.leaf_vec) for rid, rec in records.items()
                   if getattr(rec, "leaf_vec", None) is not None and len(rec.leaf_vec) == 8)
    if valid and cohort:
        scores = unit_rows([v for _, v in valid]) @ unit_rows([v for _, v, _ in cohort]).T
        best = scores.argmax(axis=1)
        structural = [(rid, float(scores[i, best[i]]), cohort[best[i]][0])
                      for i, (rid, _) in enumerate(valid)]
        structural.sort(key=lambda row: (-row[1], row[0]))
    lexical = sorted(lexical, key=lambda row: (-row[1], row[0]))
    lexical_map = {rid: (rank, score) for rank, (rid, score) in enumerate(lexical, 1)}
    structural_map = {rid: (rank, score, bid) for rank, (rid, score, bid) in enumerate(structural, 1)}
    fused = []
    for rid in sorted(lexical_map.keys() | structural_map.keys()):
        lr, ls = lexical_map.get(rid, (None, 0.0))
        sr, ss, bid = structural_map.get(rid, (None, 0.0, None))
        rrf = ((1 - W_LEAF) / (RRF_K + lr) if lr else 0) + (W_LEAF / (RRF_K + sr) if sr else 0)
        fused.append({"id": rid, "semantic_score": float(ls), "structural_resonance": ss,
                      "lexical_rank": lr, "structural_rank": sr, "rrf_score": rrf,
                      "matched_branch_id": bid})
    return sorted(fused, key=lambda row: (-row["rrf_score"], row["id"]))
