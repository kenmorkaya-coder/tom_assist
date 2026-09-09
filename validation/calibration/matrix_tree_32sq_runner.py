#!/usr/bin/env python3
"""Run the frozen local shadow diagnostic for a directly matrix-driven Tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gateway.document_ingestion import (  # noqa: E402
    DocumentEmbeddingWorkerClient,
    build_document_query_profile,
)


FIXTURE_PATH = ROOT / "validation" / "calibration" / "matrix_tree_32sq_fixture.json"
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration" / "MATRIX_TREE_32SQ_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "8ad95a36318e6e4e0e29fc43b950e097da70857ff6e1230dfe370a24b00d3a4f"
)
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_PATH = Path(
    "/Users/kenmorkaya/.cache/huggingface/hub/"
    "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
    + MODEL_REVISION
)
MASK64 = (1 << 64) - 1


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) ** 2 for value in values))
    if norm < 1e-12:
        raise ValueError("matrix diagnostic vector collapsed to zero")
    return [float(value) / norm for value in values]


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("matrix diagnostic vector dimensions differ")
    left_n = normalize(left)
    right_n = normalize(right)
    return sum(a * b for a, b in zip(left_n, right_n))


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def project_384_to_32(values: Sequence[float], seed: int) -> list[float]:
    """Fixed JL projection of semantic values; labels are never hashed."""
    if len(values) != 384:
        raise ValueError("MiniLM vector must contain 384 values")
    scale = 1.0 / math.sqrt(32.0)
    projected = []
    for output_index in range(32):
        total = 0.0
        for input_index, value in enumerate(values):
            key = (
                int(seed)
                ^ ((output_index + 1) * 0xD6E8FEB86659FD93)
                ^ ((input_index + 1) * 0xA5A35625AA5A3563)
            ) & MASK64
            sign = 1.0 if splitmix64(key) & 1 else -1.0
            total += sign * float(value)
        projected.append(total * scale)
    return normalize(projected)


def outer(left: Sequence[float], right: Sequence[float]) -> list[float]:
    return [float(a) * float(b) for a in left for b in right]


def event_matrix(
    event: Mapping[str, str],
    semantic_vectors: Mapping[str, Sequence[float]],
    matrix_config: Mapping[str, Any],
) -> list[float]:
    if set(event) != {"source", "target", "relation", "context"}:
        raise ValueError("teacher event must have source/target/relation/context")
    seed = int(matrix_config["projection_seed"])
    vectors = {
        field: project_384_to_32(semantic_vectors[text], seed)
        for field, text in event.items()
    }
    source_target = outer(vectors["source"], vectors["target"])
    relation = outer(vectors["relation"], vectors["relation"])
    context = outer(vectors["context"], vectors["context"])
    raw = [
        float(matrix_config["source_target_weight"]) * source_target[index]
        + float(matrix_config["relation_weight"]) * relation[index]
        + float(matrix_config["context_weight"]) * context[index]
        for index in range(32 * 32)
    ]
    return normalize(raw)


def transpose(matrix: Sequence[float]) -> list[float]:
    if len(matrix) != 32 * 32:
        raise ValueError("matrix must be 32 by 32")
    return [matrix[column * 32 + row] for row in range(32) for column in range(32)]


def prototype(member_ids: Sequence[str], matrices: Mapping[str, Sequence[float]]) -> list[float]:
    return normalize([
        sum(float(matrices[member_id][index]) for member_id in member_ids)
        for index in range(32 * 32)
    ])


def farthest_pair(member_ids: Sequence[str], matrices: Mapping[str, Sequence[float]]) -> tuple[str, str]:
    pairs = [
        (cosine(matrices[left], matrices[right]), left, right)
        for left_index, left in enumerate(member_ids)
        for right in member_ids[left_index + 1:]
    ]
    if not pairs:
        raise ValueError("an internal matrix Tree node needs two members")
    _, left, right = min(pairs, key=lambda row: (row[0], row[1], row[2]))
    return left, right


def build_tree(
    member_ids: Sequence[str],
    matrices: Mapping[str, Sequence[float]],
    leaf_capacity: int,
    node_id: str = "root",
) -> dict[str, Any]:
    members = sorted(member_ids)
    node = {
        "node_id": node_id,
        "prototype": prototype(members, matrices),
        "member_count": len(members),
    }
    if len(members) <= leaf_capacity:
        return {**node, "kind": "leaf", "members": members}
    pivot_left, pivot_right = farthest_pair(members, matrices)
    left, right = [pivot_left], [pivot_right]
    for member_id in members:
        if member_id in {pivot_left, pivot_right}:
            continue
        left_score = cosine(matrices[member_id], matrices[pivot_left])
        right_score = cosine(matrices[member_id], matrices[pivot_right])
        if left_score > right_score or (
            left_score == right_score and member_id < pivot_right
        ):
            left.append(member_id)
        else:
            right.append(member_id)
    return {
        **node,
        "kind": "branch",
        "pivots": [pivot_left, pivot_right],
        "children": [
            build_tree(left, matrices, leaf_capacity, node_id + "/0"),
            build_tree(right, matrices, leaf_capacity, node_id + "/1"),
        ],
    }


def search_tree(
    tree: Mapping[str, Any],
    query: Sequence[float],
    matrices: Mapping[str, Sequence[float]],
    beam_width: int,
) -> dict[str, Any]:
    frontier = [dict(tree)]
    visited = []
    while any(node["kind"] == "branch" for node in frontier):
        expanded = []
        for node in frontier:
            visited.append({
                "node_id": node["node_id"],
                "kind": node["kind"],
                "member_count": node["member_count"],
                "prototype_score": cosine(query, node["prototype"]),
            })
            expanded.extend(node["children"] if node["kind"] == "branch" else [node])
        frontier = sorted(
            expanded,
            key=lambda node: (-cosine(query, node["prototype"]), node["node_id"]),
        )[:beam_width]
    for node in frontier:
        visited.append({
            "node_id": node["node_id"],
            "kind": node["kind"],
            "member_count": node["member_count"],
            "prototype_score": cosine(query, node["prototype"]),
        })
    candidates = sorted({
        member_id for node in frontier for member_id in node["members"]
    })
    ranked = sorted(
        ((member_id, cosine(query, matrices[member_id])) for member_id in candidates),
        key=lambda row: (-row[1], row[0]),
    )
    return {
        "ranked": [
            {"passage_id": member_id, "rank": rank, "score": score}
            for rank, (member_id, score) in enumerate(ranked, 1)
        ],
        "candidate_ids": candidates,
        "candidate_count": len(candidates),
        "visited_nodes": visited,
        "visited_node_count": len(visited),
    }


def full_rank(query: Sequence[float], matrices: Mapping[str, Sequence[float]]) -> list[dict[str, Any]]:
    return [
        {"passage_id": member_id, "rank": rank, "score": score}
        for rank, (member_id, score) in enumerate(sorted(
            ((member_id, cosine(query, matrix)) for member_id, matrix in matrices.items()),
            key=lambda row: (-row[1], row[0]),
        ), 1)
    ]


def recall_at_k(ranked: Sequence[Mapping[str, Any]], relevant: Sequence[str], k: int) -> float:
    admitted = {row["passage_id"] for row in ranked if int(row["rank"]) <= k}
    return sum(member_id in admitted for member_id in relevant) / len(relevant)


def rank_of(ranked: Sequence[Mapping[str, Any]], passage_id: str) -> int | None:
    return next(
        (int(row["rank"]) for row in ranked if row["passage_id"] == passage_id),
        None,
    )


def worker() -> DocumentEmbeddingWorkerClient:
    script = ROOT / "gateway" / "document_embedding_worker.py"
    return DocumentEmbeddingWorkerClient([
        sys.executable, str(script.resolve()), "--model", str(MODEL_PATH.resolve()),
    ])


def embed_fields(payload: Mapping[str, Any]) -> dict[str, list[float]]:
    texts = sorted({
        text
        for group in (payload["passages"], payload["queries"])
        for row in group
        for text in row["event"].values()
    } | set(payload["orientation_control"]["forward"].values())
      | set(payload["orientation_control"]["reversed"].values()))
    provider = worker()
    try:
        return {
            text: [
                float(value)
                for value in build_document_query_profile(text, provider)["passage_vector"]
            ]
            for text in texts
        }
    finally:
        provider.close()


def validate_fixture(payload: Any) -> dict[str, Any]:
    required = {
        "version", "purpose", "fixed_k", "tree", "matrix", "passages",
        "queries", "orientation_control", "diagnostic_expectations",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("matrix Tree fixture shape mismatch")
    if payload["fixed_k"] != [1, 3, 5]:
        raise ValueError("matrix Tree fixed-k depths changed")
    if payload["tree"] != {"leaf_capacity": 2, "beam_width": 2}:
        raise ValueError("matrix Tree search mechanics changed")
    passage_ids = [row["id"] for row in payload["passages"]]
    if len(passage_ids) != 16 or len(set(passage_ids)) != 16:
        raise ValueError("matrix Tree passage inventory changed")
    if len(payload["queries"]) != 10:
        raise ValueError("matrix Tree observation count changed")
    for row in [*payload["passages"], *payload["queries"]]:
        if set(row["event"]) != {"source", "target", "relation", "context"}:
            raise ValueError("matrix Tree event shape mismatch")
    for row in payload["queries"]:
        if not row["relevant_passage_ids"] or not set(
            row["relevant_passage_ids"]
        ) <= set(passage_ids):
            raise ValueError("matrix Tree relevance declaration is invalid")
    return dict(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output path exists; frozen diagnostic runs are append-forbidden")
    output.mkdir(parents=True)
    if sha256_file(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("frozen matrix Tree fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if (
        "FROZEN FOR LOCAL SHADOW DIAGNOSTIC" not in preregistration
        or EXPECTED_FIXTURE_SHA256 not in preregistration
    ):
        raise SystemExit("matrix Tree pre-registration is not frozen")
    if not MODEL_PATH.is_dir():
        raise SystemExit("cached local MiniLM revision is unavailable")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    semantic_vectors = embed_fields(fixture)
    matrices = {
        row["id"]: event_matrix(row["event"], semantic_vectors, fixture["matrix"])
        for row in fixture["passages"]
    }
    tree = build_tree(
        list(matrices), matrices, int(fixture["tree"]["leaf_capacity"]),
    )
    index_payload = {
        "version": "tom-assist-direct-matrix-tree-index/0.1-shadow",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "matrix_config": fixture["matrix"],
        "tree_config": fixture["tree"],
        "matrices": matrices,
        "tree": tree,
    }
    index_bytes = canonical_json(index_payload) + b"\n"
    index_path = output / "matrix_tree.json"
    index_path.write_bytes(index_bytes)
    reloaded_payload = json.loads(index_path.read_text(encoding="utf-8"))
    reloaded_bytes = canonical_json(reloaded_payload) + b"\n"
    reload_byte_exact = reloaded_bytes == index_bytes

    observations = []
    for row in fixture["queries"]:
        query_matrix = event_matrix(row["event"], semantic_vectors, fixture["matrix"])
        direct = full_rank(query_matrix, matrices)
        selective = search_tree(
            reloaded_payload["tree"], query_matrix,
            reloaded_payload["matrices"], int(fixture["tree"]["beam_width"]),
        )
        relevant = list(row["relevant_passage_ids"])
        observations.append({
            "query_id": row["id"],
            "family": row["family"],
            "relevant_passage_ids": relevant,
            "query_matrix_sha256": sha256_bytes(canonical_json(query_matrix)),
            "direct_matrix": {
                "relevant_ranks": {
                    member_id: rank_of(direct, member_id) for member_id in relevant
                },
                "recall_at_k": {
                    str(k): recall_at_k(direct, relevant, k)
                    for k in fixture["fixed_k"]
                },
                "top_five": direct[:5],
                "score_spread": direct[0]["score"] - direct[-1]["score"],
            },
            "matrix_tree": {
                "relevant_ranks": {
                    member_id: rank_of(selective["ranked"], member_id)
                    for member_id in relevant
                },
                "recall_at_k": {
                    str(k): recall_at_k(selective["ranked"], relevant, k)
                    for k in fixture["fixed_k"]
                },
                **selective,
            },
        })

    forward = event_matrix(
        fixture["orientation_control"]["forward"], semantic_vectors,
        fixture["matrix"],
    )
    reversed_matrix = event_matrix(
        fixture["orientation_control"]["reversed"], semantic_vectors,
        fixture["matrix"],
    )
    transpose_error = max(
        abs(left - right) for left, right in zip(transpose(forward), reversed_matrix)
    )
    fixed_k = fixture["fixed_k"]
    direct_mean = {
        str(k): sum(row["direct_matrix"]["recall_at_k"][str(k)] for row in observations)
        / len(observations)
        for k in fixed_k
    }
    tree_mean = {
        str(k): sum(row["matrix_tree"]["recall_at_k"][str(k)] for row in observations)
        / len(observations)
        for k in fixed_k
    }
    expectations = fixture["diagnostic_expectations"]
    checks = {
        "direct_matrix_recall_at_1": direct_mean["1"] >= float(
            expectations["direct_matrix_mean_recall_at_1_min"]
        ),
        "selective_tree_recall_at_3": tree_mean["3"] >= float(
            expectations["tree_mean_recall_at_3_min"]
        ),
        "selective_tree_never_scans_all_passages": all(
            row["matrix_tree"]["candidate_count"] < len(matrices)
            for row in observations
        ),
        "orientation_transpose": transpose_error <= float(
            expectations["orientation_transpose_max_absolute_error"]
        ),
        "restart_byte_exact": reload_byte_exact,
    }
    report = {
        "version": "tom-assist-direct-matrix-tree-diagnostic/1.0",
        "status": "completed_local_shadow_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "preregistration_sha256": sha256_file(PREREGISTRATION_PATH),
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "model_revision": MODEL_REVISION,
        "provider_generations": 0,
        "gemma_generations": 0,
        "network_calls": 0,
        "product_changed": False,
        "uses_17d_or_8d_document_route": False,
        "index": {
            "path": str(index_path),
            "sha256": sha256_bytes(index_bytes),
            "byte_length": len(index_bytes),
            "passage_count": len(matrices),
            "matrix_shape": [32, 32],
            "reload_byte_exact": reload_byte_exact,
        },
        "aggregate": {
            "direct_matrix_mean_recall_at_k": direct_mean,
            "matrix_tree_mean_recall_at_k": tree_mean,
            "mean_tree_candidate_count": sum(
                row["matrix_tree"]["candidate_count"] for row in observations
            ) / len(observations),
            "max_tree_candidate_count": max(
                row["matrix_tree"]["candidate_count"] for row in observations
            ),
            "corpus_size": len(matrices),
        },
        "orientation": {
            "reversal_is_matrix_transpose": transpose_error <= float(
                expectations["orientation_transpose_max_absolute_error"]
            ),
            "max_absolute_error": transpose_error,
            "forward_reverse_cosine": cosine(forward, reversed_matrix),
        },
        "diagnostic_expectation_checks": checks,
        "all_diagnostic_expectations_met": all(checks.values()),
        "observations": observations,
        "scope_boundary": {
            "teacher_events_are_predeclared": True,
            "natural_language_parser_tested": False,
            "full_corpus_fallback_used": False,
            "production_ready_claimed": False,
            "g_gate_verdict": None,
        },
    }
    report_path = output / "report.json"
    report_path.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(report_path),
        "aggregate": report["aggregate"],
        "orientation": report["orientation"],
        "checks": checks,
        "all_diagnostic_expectations_met": report["all_diagnostic_expectations_met"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
