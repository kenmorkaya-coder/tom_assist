"""Product fusion/trace adapter; e9fdef81c upstream arithmetic is canonical."""
from __future__ import annotations

POLICY_VERSION = "context-policy/1.3"
W_LEAF = 0.6  # Review 4 calibration prior, not a product efficacy claim.
RRF_K = 60


def project_text(text: str):
    # Mirror only the existing pure preparation chain, never the runtime bridge:
    # integration/tomowner_msr_runtime_bridge.py:85-103; projection.py:15-181;
    # integration/msr_field_packet.py:158-226; sicd_msr_load.py:65-124.
    # No new prose-to-shape rules. WP-22 also reuses this teaching projection.
    from integration.msr_prompt_text_projection import project_prompt_text_to_neutral_packet
    from integration.msr_field_packet import adapt_to_msr_field_packet
    from agency.mechanics.preview_readout import (
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


def select_cohort(branches, signature, k: int = 16):
    """Rank branches in the same canonical 8D basis used by commit drive."""
    from agency.mechanics.leaf_vectors import LEAF_VEC_DIM, cosine_similarity
    from agency.mechanics.semantic_metrics import stiffness_proxy
    from agency.mechanics.sicd_msr_routing_basis import (
        project_load_signature_to_routing_basis,
    )
    rows = dict(sorted((str(bid), branch) for bid, branch in branches.items()))
    query = project_load_signature_to_routing_basis(signature).vector_8d
    scored = []
    for bid, branch in rows.items():
        sem_vec = getattr(branch, "sem_vec", None)
        if sem_vec is None or len(sem_vec) != LEAF_VEC_DIM:
            continue
        scored.append((bid, sem_vec, cosine_similarity(query, sem_vec)))
    # IDs were sorted above, so Python's stable sort gives a deterministic ID
    # tie-break without changing the pinned cosine arithmetic.
    cohort = sorted(scored, key=lambda row: -row[2])[:k]
    trace = []
    for bid, _, score in cohort:
        branch = rows[bid]
        stiffness = stiffness_proxy(branch)
        usage = int(getattr(branch, "usage_count", 0))
        trace.append({"branch_id": bid,
                      "routing_basis_cosine": score,
                      "stiffness": stiffness, "usage_count": usage,
                      "selection_score": score})
    return cohort, trace


def fuse_anchors(records, lexical, cohort):
    from agency.mechanics.preview_readout import rank_by_branch_resonance
    _, details = rank_by_branch_resonance(dict(sorted(records.items())), cohort)
    structural = sorted(((rid, score, bid) for rid, bid, score in details),
                        key=lambda row: (-row[1], row[0]))
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
