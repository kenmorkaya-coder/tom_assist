#!/usr/bin/env python3
"""Run the frozen, local-only native document Tree selective diagnostic."""
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
    decode_vector_f32,
)
from gateway.structural_analysis import CHANNELS  # noqa: E402
from gateway.tom_gateway import TomGateway  # noqa: E402


FIXTURE_PATH = (
    ROOT / "validation" / "calibration"
    / "document_tree_native_selective_fixture.json"
)
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration"
    / "NATIVE_DOCUMENT_TREE_SELECTIVE_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "0d42b6bc7b32710db90e1b2c9724557fa815b6477fc67c0c57666f54659226fd"
)
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_PATH = Path(
    "/Users/kenmorkaya/.cache/huggingface/hub/"
    "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
    + MODEL_REVISION
)
PROJECT_ID = "native-selective-diagnostic"


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("diagnostic cosine dimensions differ")
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm < 1e-12 or right_norm < 1e-12:
        raise ValueError("diagnostic cosine received a zero vector")
    return numerator / (left_norm * right_norm)


def validate_fixture(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {
        "version", "purpose", "fixed_k", "passages", "queries",
    }:
        raise ValueError("frozen fixture shape mismatch")
    fixed_k = payload["fixed_k"]
    if fixed_k != [1, 3, 5]:
        raise ValueError("frozen fixed-k depths changed")
    passages = payload["passages"]
    queries = payload["queries"]
    if not isinstance(passages, list) or len(passages) < 10:
        raise ValueError("frozen fixture needs relevant passages and distractors")
    if not isinstance(queries, list) or len(queries) < 6:
        raise ValueError("frozen fixture needs several direct/paraphrase observations")
    passage_ids = []
    for row in passages:
        if not isinstance(row, Mapping) or set(row) != {"id", "text"}:
            raise ValueError("frozen passage shape mismatch")
        if not isinstance(row["id"], str) or not row["id"]:
            raise ValueError("frozen passage ID is missing")
        if not isinstance(row["text"], str) or not row["text"].strip():
            raise ValueError("frozen passage text is missing")
        passage_ids.append(row["id"])
    if len(set(passage_ids)) != len(passage_ids):
        raise ValueError("frozen passage IDs are not unique")
    query_ids = []
    families: dict[str, int] = {}
    for row in queries:
        if not isinstance(row, Mapping) or set(row) != {
            "id", "family", "text", "relevant_passage_ids",
        }:
            raise ValueError("frozen query shape mismatch")
        relevant = row["relevant_passage_ids"]
        if not isinstance(relevant, list) or not relevant:
            raise ValueError("frozen query has no predeclared relevant passage")
        if any(item not in passage_ids for item in relevant):
            raise ValueError("frozen query names an absent passage")
        query_ids.append(row["id"])
        families[row["family"]] = families.get(row["family"], 0) + 1
    if len(set(query_ids)) != len(query_ids):
        raise ValueError("frozen query IDs are not unique")
    if set(families.values()) != {2}:
        raise ValueError("each frozen family must have one direct query and one paraphrase")
    return dict(payload)


def worker() -> DocumentEmbeddingWorkerClient:
    script = ROOT / "gateway" / "document_embedding_worker.py"
    return DocumentEmbeddingWorkerClient([
        sys.executable, str(script.resolve()), "--model", str(MODEL_PATH.resolve()),
    ])


def close_runtime(runtime: Any, provider: DocumentEmbeddingWorkerClient) -> None:
    provider.close()
    runtime.library.db.close()
    runtime.document_index.db.close()


def ordered_rows(scores: Mapping[str, float]) -> list[dict[str, Any]]:
    return [
        {"passage_id": passage_id, "rank": rank, "score": score}
        for rank, (passage_id, score) in enumerate(
            sorted(scores.items(), key=lambda item: (-item[1], item[0])), 1,
        )
    ]


def stage_result(
    scores: Mapping[str, float], relevant: Sequence[str], fixed_k: Sequence[int],
) -> dict[str, Any]:
    ordered = ordered_rows(scores)
    ranks = {row["passage_id"]: row["rank"] for row in ordered}
    values = [row["score"] for row in ordered]
    return {
        "relevant_ranks": {passage_id: ranks[passage_id] for passage_id in relevant},
        "recall_at_k": {
            str(k): sum(ranks[passage_id] <= k for passage_id in relevant) / len(relevant)
            for k in fixed_k
        },
        "score_min": min(values),
        "score_max": max(values),
        "score_spread": max(values) - min(values),
        "top_five": ordered[:5],
    }


def load_rows(runtime: Any) -> tuple[list[dict[str, Any]], dict[str, str]]:
    metadata = runtime.document_index.project_chunk_metadata(PROJECT_ID)
    rows = []
    passage_to_row_id = {}
    for row in runtime.library.document_chunks(active_only=True):
        key = (str(row["document_id"]), int(row["chunk_index"]))
        merged = {**row, **metadata[key]}
        row_id = f"{row['document_id']}:chunk:{int(row['chunk_index'])}"
        merged["row_id"] = row_id
        rows.append(merged)
        passage_to_row_id[str(row["display_name"])] = row_id
    return rows, passage_to_row_id


def observe_queries(
    runtime: Any,
    provider: DocumentEmbeddingWorkerClient,
    fixture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows, passage_to_row_id = load_rows(runtime)
    if len(rows) != len(fixture["passages"]):
        raise ValueError("diagnostic ingestion did not retain exactly one chunk per passage")
    row_id_to_passage = {row_id: passage for passage, row_id in passage_to_row_id.items()}
    chunk_vectors = {
        row_id_to_passage[row["row_id"]]: decode_vector_f32(row["passage_vector"])
        for row in rows
    }
    chunk_loads = {
        row_id_to_passage[row["row_id"]]: [
            float(json.loads(row["load_signature_json"])[name]) for name in CHANNELS
        ]
        for row in rows
    }
    chunk_routes = {
        row_id_to_passage[row["row_id"]]: [
            float(value) for value in row["routing_basis_8d"]["vector_8d"]
        ]
        for row in rows
    }
    observations = []
    for query in fixture["queries"]:
        profile = build_document_query_profile(query["text"], provider)
        analysis, cohort, branch_trace = runtime.document_index.query_address(
            query["text"], profile,
        )
        native, telemetry = runtime.document_index.structural_scores(
            PROJECT_ID, rows, cohort,
        )
        query_embedding = [float(value) for value in profile["passage_vector"]]
        query_load = [float(analysis["load_signature"][name]) for name in CHANNELS]
        query_route = [
            float(value) for value in analysis["routing_basis_8d"]["vector_8d"]
        ]
        stage_scores = {
            "embedding_384d": {
                passage_id: cosine(query_embedding, vector)
                for passage_id, vector in chunk_vectors.items()
            },
            "compiled_load_17d": {
                passage_id: cosine(query_load, vector)
                for passage_id, vector in chunk_loads.items()
            },
            "routing_basis_8d": {
                passage_id: cosine(query_route, vector)
                for passage_id, vector in chunk_routes.items()
            },
            "native_tree_reader": {
                row_id_to_passage[row_id]: float(value["score"])
                for row_id, value in native.items()
            },
        }
        relevant = list(query["relevant_passage_ids"])
        observations.append({
            "query_id": query["id"],
            "family": query["family"],
            "query_text": query["text"],
            "relevant_passage_ids": relevant,
            "query_analysis_digest": analysis["analysis_digest"],
            "query_embedding_sha256": sha256_bytes(canonical_json(query_embedding)),
            "query_load_17d": {
                name: analysis["load_signature"][name] for name in CHANNELS
            },
            "query_routing_basis_8d": analysis["routing_basis_8d"],
            "selected_branches": branch_trace,
            "query_region_identity": telemetry["query_region_identity"],
            "numeric_spread_is_not_relevance_proof": True,
            "stages": {
                name: stage_result(scores, relevant, fixture["fixed_k"])
                for name, scores in stage_scores.items()
            },
        })
    return observations


def region_comparison(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    branch_sets = {
        row["query_id"]: {item["branch_id"] for item in row["selected_branches"]}
        for row in observations
    }
    pairs = []
    for left_index, left in enumerate(observations):
        for right in observations[left_index + 1:]:
            left_set = branch_sets[left["query_id"]]
            right_set = branch_sets[right["query_id"]]
            union = left_set | right_set
            pairs.append({
                "left": left["query_id"],
                "right": right["query_id"],
                "same_family": left["family"] == right["family"],
                "identical_region": left_set == right_set,
                "branch_jaccard": len(left_set & right_set) / len(union) if union else 1.0,
            })
    values = [row["branch_jaccard"] for row in pairs]
    return {
        "unique_query_region_identities": len({
            row["query_region_identity"] for row in observations
        }),
        "observation_count": len(observations),
        "identical_region_pair_count": sum(row["identical_region"] for row in pairs),
        "jaccard_min": min(values),
        "jaccard_max": max(values),
        "pairs": pairs,
    }


def aggregate(observations: Sequence[Mapping[str, Any]], fixed_k: Sequence[int]) -> dict[str, Any]:
    stages = tuple(observations[0]["stages"])
    return {
        stage: {
            "mean_recall_at_k": {
                str(k): sum(
                    row["stages"][stage]["recall_at_k"][str(k)]
                    for row in observations
                ) / len(observations)
                for k in fixed_k
            },
            "median_relevant_rank": sorted(
                next(iter(row["stages"][stage]["relevant_ranks"].values()))
                for row in observations
            )[len(observations) // 2],
            "top_one_hits": sum(
                next(iter(row["stages"][stage]["relevant_ranks"].values())) == 1
                for row in observations
            ),
        }
        for stage in stages
    }


def source_fidelity(runtime: Any, fixture: Mapping[str, Any]) -> dict[str, Any]:
    expected = {row["id"]: row["text"].encode("utf-8") for row in fixture["passages"]}
    observed = {}
    for row in runtime.list_documents():
        document = runtime.get_document(row["document_id"])
        observed[document["display_name"]] = document["content"].encode("utf-8")
    return {
        "all_exact": set(expected) == set(observed) and all(
            observed.get(name) == content for name, content in expected.items()
        ),
        "passages": {
            name: {
                "source_sha256": sha256_bytes(content),
                "reloaded_sha256": sha256_bytes(observed[name]),
                "byte_length": len(content),
                "exact": observed[name] == content,
            }
            for name, content in expected.items()
        },
    }


def stable_projection(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "query_id": row["query_id"],
        "query_analysis_digest": row["query_analysis_digest"],
        "query_embedding_sha256": row["query_embedding_sha256"],
        "query_region_identity": row["query_region_identity"],
        "selected_branches": row["selected_branches"],
        "stages": row["stages"],
    } for row in observations]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output path already exists; diagnostic runs are append-forbidden")
    output.mkdir(parents=True)
    if sha256_file(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("frozen diagnostic fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if "FROZEN FOR LOCAL DIAGNOSTIC" not in preregistration:
        raise SystemExit("diagnostic pre-registration is not frozen")
    if EXPECTED_FIXTURE_SHA256 not in preregistration:
        raise SystemExit("diagnostic pre-registration lacks the fixture digest")
    if not MODEL_PATH.is_dir():
        raise SystemExit("cached local MiniLM revision is unavailable")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    data_dir = output / "state"
    provider = worker()
    gateway = TomGateway(data_dir, document_embedding_provider=provider)
    runtime = gateway.project(PROJECT_ID)
    seed_bytes_before = gateway.seed.artifact_path.read_bytes()
    empty_tree_bytes = runtime.document_index.durable_tree_bytes()
    seeded_copy_exact = empty_tree_bytes == seed_bytes_before
    ingestion = []
    for passage in fixture["passages"]:
        retained = runtime.ingest_document(
            passage["id"], passage["text"], "text/plain",
        )
        if retained["chunk_count"] != 1:
            raise ValueError("each frozen diagnostic passage must remain one product chunk")
        ingestion.append({
            "passage_id": passage["id"],
            "document_id": retained["document_id"],
            "content_sha256": retained["content_sha256"],
            "chunk_count": retained["chunk_count"],
        })
    document_tree_after_ingestion = runtime.document_index.durable_tree_bytes()
    first = observe_queries(runtime, provider, fixture)
    first_fidelity = source_fidelity(runtime, fixture)
    first_head = runtime.document_index.head_metadata()
    owner_seed_after_first = gateway.seed.artifact_path.read_bytes()
    close_runtime(runtime, provider)

    restarted_provider = worker()
    restarted_gateway = TomGateway(
        data_dir, document_embedding_provider=restarted_provider,
    )
    restarted = restarted_gateway.project(PROJECT_ID)
    second = observe_queries(restarted, restarted_provider, fixture)
    second_fidelity = source_fidelity(restarted, fixture)
    second_head = restarted.document_index.head_metadata()
    reloaded_tree_bytes = restarted.document_index.durable_tree_bytes()
    owner_seed_after_restart = restarted_gateway.seed.artifact_path.read_bytes()
    close_runtime(restarted, restarted_provider)

    first_stable = stable_projection(first)
    second_stable = stable_projection(second)
    report = {
        "version": "tom-assist-document-tree-native-selective-diagnostic/1.0",
        "status": "completed_local_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "preregistration_sha256": sha256_file(PREREGISTRATION_PATH),
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "model_revision": MODEL_REVISION,
        "provider_generations": 0,
        "gemma_generations": 0,
        "network_calls": 0,
        "project": {
            "project_id": PROJECT_ID,
            "data_dir": str(data_dir),
            "document_tree_path": str(
                data_dir / "projects" / PROJECT_ID / "tom" / "document-index"
                / "tree_state.json"
            ),
            "dedicated_copy_of_python_10k_seed_exact_before_ingestion": seeded_copy_exact,
            "seed_sha256": sha256_bytes(seed_bytes_before),
            "empty_project_tree_sha256": sha256_bytes(empty_tree_bytes),
            "tree_after_ingestion_sha256": sha256_bytes(document_tree_after_ingestion),
            "tree_changed_by_document_ingestion": (
                empty_tree_bytes != document_tree_after_ingestion
            ),
            "owner_seed_unchanged": (
                seed_bytes_before == owner_seed_after_first == owner_seed_after_restart
            ),
            "head_before_restart": first_head,
            "head_after_restart": second_head,
        },
        "ingestion": ingestion,
        "observations": first,
        "aggregate": aggregate(first, fixture["fixed_k"]),
        "query_region_comparison": region_comparison(first),
        "restart": {
            "stable_projection_exact": first_stable == second_stable,
            "first_projection_sha256": sha256_bytes(canonical_json(first_stable)),
            "second_projection_sha256": sha256_bytes(canonical_json(second_stable)),
            "tree_bytes_exact": reloaded_tree_bytes == document_tree_after_ingestion,
            "tree_sha256_before": sha256_bytes(document_tree_after_ingestion),
            "tree_sha256_after": sha256_bytes(reloaded_tree_bytes),
            "source_fidelity_before": first_fidelity,
            "source_fidelity_after": second_fidelity,
        },
        "interpretation_boundary": {
            "full_corpus_traversal_counted_as_success": False,
            "clause_expansion_counted_as_success": False,
            "lexical_or_hybrid_rank_counted_as_success": False,
            "twenty_five_item_inclusion_counted_as_success": False,
            "numeric_spread_counted_as_relevance": False,
            "native_success_measure": "predeclared passage recall at fixed k only",
        },
    }
    if not seeded_copy_exact or not report["project"]["owner_seed_unchanged"]:
        raise ValueError("dedicated document Tree seed-copy protection failed")
    if not first_fidelity["all_exact"] or not second_fidelity["all_exact"]:
        raise ValueError("source-byte fidelity failed")
    (output / "report.json").write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(output / "report.json"),
        "aggregate": report["aggregate"],
        "unique_query_regions": report["query_region_comparison"][
            "unique_query_region_identities"
        ],
        "restart_exact": report["restart"]["stable_projection_exact"],
        "source_fidelity": first_fidelity["all_exact"] and second_fidelity["all_exact"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
