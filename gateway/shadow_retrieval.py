"""Pure WP-37 evidence-addressed retrieval comparison helpers.

Sparse evidence is an address on this path, never a force.  These helpers only
project frozen signatures, select cohorts, and rank immutable snapshots.  They
do not own a runtime and expose no write or step surface.
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence

from gateway.structural_preview import RRF_K, W_LEAF, select_cohort


COMPARISON_VERSION = "tom-assist-shadow-retrieval/1.0"


def evidence_address(load_signature: Mapping[str, Any]):
    """Project an evidenced 17D signature into the pinned read-only 8D address."""
    from agency.mechanics.sicd_msr_load import LoadSignature
    from agency.mechanics.sicd_msr_routing_basis import (
        project_load_signature_to_routing_basis,
    )

    signature = LoadSignature.from_mapping(dict(load_signature), strict=True)
    projection = project_load_signature_to_routing_basis(signature)
    return signature, tuple(float(value) for value in projection.vector_8d)


def ranked_hash_channel(lexical: Sequence[tuple[str, float]]) -> list[dict[str, Any]]:
    ordered = sorted(
        ((str(record_id), float(score)) for record_id, score in lexical),
        key=lambda row: (-row[1], row[0]),
    )
    return [
        {
            "id": record_id,
            "rank": rank,
            "score": score,
            "score_space": "hashed_bag_cosine",
        }
        for rank, (record_id, score) in enumerate(ordered, 1)
    ]


def dense_channel_with_unscored_tail(
    records: Mapping[str, Any],
    lexical: Sequence[tuple[str, float]],
    structural_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Form one rank without ever comparing dense and hash scalar values."""
    available = {str(record_id) for record_id in records}
    dense_seen: set[str] = set()
    dense_rows: list[dict[str, Any]] = []
    for row in sorted(
        structural_rows,
        key=lambda item: (-float(item["combined_score"]), str(item["record_id"])),
    ):
        record_id = str(row["record_id"])
        if record_id not in available or record_id in dense_seen:
            continue
        dense_seen.add(record_id)
        dense_rows.append({
            "id": record_id,
            "score": float(row["combined_score"]),
            "score_space": "dense_multivector_plus_directed_graph",
            "dense_semantic_score": float(row["dense_semantic_score"]),
            "directed_graph_score": float(row["directed_graph_score"]),
        })

    tail_rows = [
        {
            "id": row["id"],
            "score": row["score"],
            "score_space": "hashed_bag_unscored_tail",
        }
        for row in ranked_hash_channel(lexical)
        if row["id"] in available and row["id"] not in dense_seen
    ]
    ranking = []
    for rank, row in enumerate([*dense_rows, *tail_rows], 1):
        ranking.append({**row, "rank": rank})
    return {
        "ranking": ranking,
        "dense_scored": dense_rows,
        "unscored_tail": tail_rows,
        "dense_scored_count": len(dense_rows),
        "unscored_tail_count": len(tail_rows),
    }


def evidence_addressed_anchor_snapshot(
    records: Mapping[str, Any], history: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Return ephemeral resonance records; never alter the retained anchors."""
    newest: dict[str, Mapping[str, Any]] = {}
    for item in sorted(
        history,
        key=lambda row: (int(row.get("tick", 0)), str(row.get("commit_key", ""))),
    ):
        newest[str(item["record_id"])] = item

    snapshot: dict[str, dict[str, Any]] = {}
    evidence_sources: list[dict[str, Any]] = []
    fallback_ids: list[str] = []
    fallback_unrankable_ids: list[str] = []
    for record_id, record in sorted(
        ((str(record_id), record) for record_id, record in records.items())
    ):
        retained = newest.get(record_id)
        if retained is not None:
            _, vector = evidence_address(retained["load_signature"])
            snapshot[record_id] = {"leaf_vec": list(vector)}
            evidence_sources.append({
                "record_id": record_id,
                "commit_key": str(retained["commit_key"]),
                "tick": int(retained["tick"]),
                "analysis_digest": str(retained["analysis_digest"]),
            })
            continue
        stored = (
            record.get("leaf_vec")
            if isinstance(record, Mapping)
            else getattr(record, "leaf_vec", None)
        )
        # Preserve absence as absence.  This is deliberately not a projection
        # from text and not a zero-vector substitute.
        snapshot[record_id] = {"leaf_vec": None if stored is None else list(stored)}
        fallback_ids.append(record_id)
        if stored is None or len(stored) != 8:
            fallback_unrankable_ids.append(record_id)
    evidence_ids = [row["record_id"] for row in evidence_sources]
    return snapshot, {
        "with_retained_evidence_count": len(evidence_ids),
        "without_retained_evidence_count": len(fallback_ids),
        "with_retained_evidence_ids": evidence_ids,
        "without_retained_evidence_ids": fallback_ids,
        "fallback_unrankable_ids": fallback_unrankable_ids,
        "evidence_sources": evidence_sources,
    }


def structural_channel(
    records: Mapping[str, Any], cohort: Sequence[tuple[str, Sequence[float], float]],
) -> list[dict[str, Any]]:
    from agency.mechanics.preview_readout import rank_by_branch_resonance

    _, details = rank_by_branch_resonance(dict(sorted(records.items())), list(cohort))
    ordered = sorted(
        ((str(record_id), str(branch_id), float(score))
         for record_id, branch_id, score in details),
        key=lambda row: (-row[2], row[0]),
    )
    return [
        {
            "id": record_id,
            "rank": rank,
            "score": score,
            "matched_branch_id": branch_id,
        }
        for rank, (record_id, branch_id, score) in enumerate(ordered, 1)
    ]


def fuse_ranked_channels(
    semantic: Sequence[Mapping[str, Any]],
    structural: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Apply the unchanged reciprocal-rank fusion to already-ranked channels."""
    semantic_map = {str(row["id"]): row for row in semantic}
    structural_map = {str(row["id"]): row for row in structural}
    fused = []
    for record_id in sorted(semantic_map.keys() | structural_map.keys()):
        semantic_row = semantic_map.get(record_id)
        structural_row = structural_map.get(record_id)
        semantic_rank = int(semantic_row["rank"]) if semantic_row else None
        structural_rank = int(structural_row["rank"]) if structural_row else None
        rrf = (
            (1.0 - W_LEAF) / (RRF_K + semantic_rank)
            if semantic_rank else 0.0
        ) + (
            W_LEAF / (RRF_K + structural_rank)
            if structural_rank else 0.0
        )
        fused.append({
            "id": record_id,
            "semantic_score": float(semantic_row["score"]) if semantic_row else 0.0,
            "semantic_score_space": (
                str(semantic_row["score_space"]) if semantic_row else None
            ),
            "structural_resonance": (
                float(structural_row["score"]) if structural_row else 0.0
            ),
            "lexical_rank": semantic_rank,
            "structural_rank": structural_rank,
            "rrf_score": rrf,
            "matched_branch_id": (
                str(structural_row["matched_branch_id"])
                if structural_row else None
            ),
        })
    return sorted(fused, key=lambda row: (-row["rrf_score"], row["id"]))


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0, "minimum": None, "median": None,
            "p90_nearest_rank": None, "maximum": None, "mean": None,
        }
    ordered = sorted(float(value) for value in values)
    p90_index = max(0, math.ceil(0.9 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "median": float(statistics.median(ordered)),
        "p90_nearest_rank": ordered[p90_index],
        "maximum": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def rank_divergence(
    current: Sequence[Mapping[str, Any]], proposed: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    current_rank = {str(row["id"]): rank for rank, row in enumerate(current, 1)}
    proposed_rank = {str(row["id"]): rank for rank, row in enumerate(proposed, 1)}
    ids = sorted(current_rank.keys() | proposed_rank.keys())
    missing_rank = len(ids) + 1
    rows = []
    for record_id in ids:
        left = current_rank.get(record_id, missing_rank)
        right = proposed_rank.get(record_id, missing_rank)
        rows.append({
            "id": record_id,
            "current_rank": left,
            "proposed_rank": right,
            "absolute_delta": abs(left - right),
            "missing_from_current": record_id not in current_rank,
            "missing_from_proposed": record_id not in proposed_rank,
        })
    return {
        "per_anchor": rows,
        "absolute_delta_distribution": _distribution(
            [row["absolute_delta"] for row in rows]
        ),
    }


def _current_structural_channel(
    current_fused: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = [row for row in current_fused if row.get("structural_rank") is not None]
    return [
        {
            "id": str(row["id"]),
            "rank": int(row["structural_rank"]),
            "score": float(row["structural_resonance"]),
            "matched_branch_id": row.get("matched_branch_id"),
        }
        for row in sorted(rows, key=lambda item: (item["structural_rank"], item["id"]))
    ]


def build_shadow_comparison(
    *,
    branches: Mapping[str, Any],
    records: Mapping[str, Any],
    lexical: Sequence[tuple[str, float]],
    current_cohort: Sequence[tuple[str, Sequence[float], float]],
    current_fused: Sequence[Mapping[str, Any]],
    evidence_load_signature: Mapping[str, Any],
    structural_history: Sequence[Mapping[str, Any]],
    structural_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    evidence_signature, address_8d = evidence_address(evidence_load_signature)
    proposed_cohort, proposed_branch_trace = select_cohort(branches, evidence_signature)
    anchor_snapshot, evidence_report = evidence_addressed_anchor_snapshot(
        records, structural_history
    )
    dense = dense_channel_with_unscored_tail(records, lexical, structural_rows)
    proposed_structural = structural_channel(anchor_snapshot, proposed_cohort)
    proposed_fused = fuse_ranked_channels(dense["ranking"], proposed_structural)
    current_semantic = ranked_hash_channel(lexical)
    current_ids = [str(row[0]) for row in current_cohort]
    proposed_ids = [str(row[0]) for row in proposed_cohort]
    overlap = len(set(current_ids) & set(proposed_ids))
    union = set(current_ids) | set(proposed_ids)
    return {
        "version": COMPARISON_VERSION,
        "serving_result_unchanged": True,
        "address_only_never_force": True,
        "query_evidence_load_signature": evidence_signature.as_dict(),
        "query_evidence_address_8d": list(address_8d),
        "current": {
            "cohort_branch_ids": current_ids,
            "semantic_channel": current_semantic,
            "structural_channel": _current_structural_channel(current_fused),
            "fused_ranking": [dict(row) for row in current_fused],
        },
        "proposed": {
            "cohort_branch_ids": proposed_ids,
            "branch_trace": proposed_branch_trace,
            "semantic_channel": dense["ranking"],
            "dense_scored": dense["dense_scored"],
            "unscored_tail": dense["unscored_tail"],
            "structural_channel": proposed_structural,
            "fused_ranking": proposed_fused,
        },
        "cohort_divergence": {
            "lists_differ": current_ids != proposed_ids,
            "overlap_count": overlap,
            "symmetric_difference_count": len(set(current_ids) ^ set(proposed_ids)),
            "jaccard_similarity": (overlap / len(union)) if union else 1.0,
        },
        "anchor_evidence": evidence_report,
        "rank_divergence": rank_divergence(current_fused, proposed_fused),
    }


def hash_profile_collision_report(
    vectors: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    groups: dict[tuple[float, ...], list[str]] = {}
    for record_id, vector in sorted(vectors.items()):
        groups.setdefault(tuple(float(value) for value in vector), []).append(str(record_id))
    collisions = [ids for ids in groups.values() if len(ids) > 1]
    participants = sum(len(ids) for ids in collisions)
    return {
        "anchor_count": len(vectors),
        "collision_group_count": len(collisions),
        "collision_participant_count": participants,
        "collision_rate": participants / len(vectors) if vectors else 0.0,
        "collision_groups": sorted(collisions),
    }


def rank_position_correlation(
    dense_channel: Sequence[Mapping[str, Any]],
    hash_channel: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    dense_ranks = {str(row["id"]): int(row["rank"]) for row in dense_channel}
    hash_ranks = {str(row["id"]): int(row["rank"]) for row in hash_channel}
    ids = sorted(dense_ranks.keys() & hash_ranks.keys())
    left = [float(dense_ranks[record_id]) for record_id in ids]
    right = [float(hash_ranks[record_id]) for record_id in ids]
    correlation = None
    if len(ids) >= 2:
        left_mean = sum(left) / len(left)
        right_mean = sum(right) / len(right)
        numerator = sum(
            (lvalue - left_mean) * (rvalue - right_mean)
            for lvalue, rvalue in zip(left, right)
        )
        left_norm = math.sqrt(sum((value - left_mean) ** 2 for value in left))
        right_norm = math.sqrt(sum((value - right_mean) ** 2 for value in right))
        if left_norm > 0.0 and right_norm > 0.0:
            correlation = numerator / (left_norm * right_norm)
    return {
        "common_record_count": len(ids),
        "common_record_ids": ids,
        "pearson_correlation_of_deterministic_rank_positions": correlation,
    }


def distribution(values: Sequence[float]) -> dict[str, Any]:
    """Public frozen summary helper for the label-free calibration runner."""
    return _distribution(values)
