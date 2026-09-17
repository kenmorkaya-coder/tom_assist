#!/usr/bin/env python3
"""Run the frozen SCAW automatic-parser to 32x32 matrix Tree diagnostic."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
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
from gateway.structural_analysis import merge_chunk_candidates  # noqa: E402
from gateway.structure_provider import (  # noqa: E402
    StructureProviderError,
    StructureWorkerClient,
)
from validation.calibration.matrix_tree_32sq_runner import (  # noqa: E402
    build_tree,
    canonical_json,
    cosine,
    event_matrix,
    search_tree,
    sha256_bytes,
    sha256_file,
)


FIXTURE_PATH = (
    ROOT / "validation" / "calibration" / "matrix_tree_scaw_parser_fixture.json"
)
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration"
    / "MATRIX_TREE_SCAW_PARSER_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "d1d8f35065379b18f7f6070cbb8cb3736b86f82c5db8cddb7a025e69769dad4f"
)
MINILM_MODEL = Path(
    "/Users/kenmorkaya/.cache/huggingface/hub/"
    "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
    "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
)
GEMMA_MODEL = Path(
    "/Users/kenmorkaya/.cache/huggingface/hub/"
    "models--mlx-community--gemma-4-26b-a4b-it-4bit/snapshots/"
    "0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
)
GEMMA_PYTHON = Path(
    "/Users/kenmorkaya/PycharmProjects/tom_sicd_gemma/.venv/bin/python"
)


def structure_worker() -> StructureWorkerClient:
    script = ROOT / "gateway" / "structure_worker.py"
    return StructureWorkerClient([
        sys.executable,
        str(script.resolve()),
        "--embedding-model",
        str(MINILM_MODEL.resolve()),
        "--gemma-python",
        str(GEMMA_PYTHON.resolve()),
        "--gemma-model",
        str(GEMMA_MODEL.resolve()),
    ], timeout_seconds=600.0)


def embedding_worker() -> DocumentEmbeddingWorkerClient:
    script = ROOT / "gateway" / "document_embedding_worker.py"
    return DocumentEmbeddingWorkerClient([
        sys.executable, str(script.resolve()), "--model", str(MINILM_MODEL.resolve()),
    ])


def candidate_events(candidate: Mapping[str, Any]) -> list[dict[str, str]]:
    """Project only validated directed parser records; invent no relation."""
    entities = {str(row["id"]): str(row["label"]) for row in candidate["entities"]}
    events = []
    for row in candidate["causal_relations"]:
        events.append({
            "source": entities[str(row["cause_entity_id"])],
            "target": entities[str(row["effect_entity_id"])],
            "relation": " ".join((
                str(row["kind"]), str(row["modality"]),
                "negated" if row["negated"] else "affirmed",
            )),
            "context": str(row["evidence"]["quote"]),
        })
    for row in candidate["orientations"]:
        events.append({
            "source": entities[str(row["source_entity_id"])],
            "target": entities[str(row["target_entity_id"])],
            "relation": " ".join((
                str(row["kind"]), str(row["polarity"]), str(row["modality"]),
                "negated" if row["negated"] else "affirmed",
            )),
            "context": str(row["evidence"]["quote"]),
        })
    unique = {
        tuple(event[field] for field in ("source", "target", "relation", "context")): event
        for event in events
    }
    return [unique[key] for key in sorted(unique)]


def parse_one(
    provider: StructureWorkerClient, source_id: str, text: str,
) -> dict[str, Any]:
    try:
        result = provider.analyze(text)
        _, candidate = merge_chunk_candidates(
            text, result["semantic_profile"], result["chunk_candidates"],
        )
        telemetry = result["worker_telemetry"]
        return {
            "source_id": source_id,
            "status": "parsed",
            "source_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "attempted_chunks": int(telemetry["attempted_chunks"]),
            "failed_chunks": 0,
            "parser_model": result["parser_model"],
            "candidate": candidate,
            "events": candidate_events(candidate),
            "failures": [],
        }
    except StructureProviderError as error:
        telemetry = error.telemetry or {}
        failures = list(telemetry.get("failures", []))
        if not failures and error.failure is not None:
            failures = [error.failure]
        return {
            "source_id": source_id,
            "status": "failed_closed",
            "source_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "attempted_chunks": int(telemetry.get("attempted_chunks", 0)),
            "failed_chunks": len(failures),
            "parser_model": None,
            "candidate": None,
            "events": [],
            "failures": failures,
        }


def embed_event_fields(
    parsed: Sequence[Mapping[str, Any]],
) -> dict[str, list[float]]:
    texts = sorted({
        value
        for source in parsed
        for event in source["events"]
        for value in event.values()
    })
    provider = embedding_worker()
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


def matrix_sets(
    parsed: Sequence[Mapping[str, Any]],
    semantic_vectors: Mapping[str, Sequence[float]],
    matrix_config: Mapping[str, Any],
) -> dict[str, list[list[float]]]:
    return {
        str(source["source_id"]): [
            event_matrix(event, semantic_vectors, matrix_config)
            for event in source["events"]
        ]
        for source in parsed
        if source["events"]
    }


def normalized_sum(matrices: Sequence[Sequence[float]]) -> list[float]:
    total = [sum(matrix[index] for matrix in matrices) for index in range(32 * 32)]
    norm = sum(value * value for value in total) ** 0.5
    if norm < 1e-12:
        raise ValueError("parsed event matrices cancel to zero")
    return [value / norm for value in total]


def record_score(
    query_matrices: Sequence[Sequence[float]],
    passage_matrices: Sequence[Sequence[float]],
) -> float:
    return max(
        cosine(query, passage)
        for query in query_matrices
        for passage in passage_matrices
    )


def rank_records(
    query_matrices: Sequence[Sequence[float]],
    passage_matrices: Mapping[str, Sequence[Sequence[float]]],
    candidates: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    ids = sorted(candidates if candidates is not None else passage_matrices)
    scored = sorted(
        ((source_id, record_score(query_matrices, passage_matrices[source_id])) for source_id in ids),
        key=lambda row: (-row[1], row[0]),
    )
    return [
        {"passage_id": source_id, "rank": rank, "score": score}
        for rank, (source_id, score) in enumerate(scored, 1)
    ]


def relevant_rank(ranked: Sequence[Mapping[str, Any]], passage_id: str) -> int | None:
    return next(
        (int(row["rank"]) for row in ranked if row["passage_id"] == passage_id),
        None,
    )


def recall(ranked: Sequence[Mapping[str, Any]], relevant: Sequence[str], k: int) -> float:
    top = {row["passage_id"] for row in ranked if int(row["rank"]) <= k}
    return sum(source_id in top for source_id in relevant) / len(relevant)


def safe_parse_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Keep raw source-derived labels outside the compact outcome."""
    candidate = row["candidate"]
    return {
        "source_id": row["source_id"],
        "status": row["status"],
        "source_sha256": row["source_sha256"],
        "attempted_chunks": row["attempted_chunks"],
        "failed_chunks": row["failed_chunks"],
        "event_count": len(row["events"]),
        "entity_count": len(candidate["entities"]) if candidate else 0,
        "orientation_count": len(candidate["orientations"]) if candidate else 0,
        "causal_relation_count": len(candidate["causal_relations"]) if candidate else 0,
        "failure_codes": [failure["code"] for failure in row["failures"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output exists; frozen diagnostic runs are append-forbidden")
    output.mkdir(parents=True)
    if sha256_file(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("frozen SCAW parser fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if (
        "FROZEN — OWNER AUTHORISED LOCAL GEMMA GENERATION" not in preregistration
        or EXPECTED_FIXTURE_SHA256 not in preregistration
    ):
        raise SystemExit("SCAW parser pre-registration is not frozen")
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    corpus_path = Path(fixture["external_corpus"]["path"])
    if sha256_file(corpus_path) != fixture["external_corpus"]["sha256"]:
        raise SystemExit("external SCAW corpus digest mismatch")
    for path in (MINILM_MODEL, GEMMA_MODEL):
        if not path.is_dir():
            raise SystemExit(f"cached local model missing: {path.name}")
    if not GEMMA_PYTHON.is_file():
        raise SystemExit("local Gemma Python is missing")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    passages = corpus["passages"]
    if len(passages) != int(fixture["external_corpus"]["passage_count"]):
        raise SystemExit("external SCAW passage count mismatch")
    expected_hashes = {
        row["passage_id"]: row["text_sha256"] for row in passages
    }
    structure = structure_worker()
    parsed_passages: list[dict[str, Any]] = []
    parsed_queries: list[dict[str, Any]] = []
    try:
        for row in passages:
            observed = "sha256:" + hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
            if observed != expected_hashes[row["passage_id"]]:
                raise ValueError("external SCAW passage source hash mismatch")
            parsed_passages.append(parse_one(structure, row["passage_id"], row["text"]))
        for row in fixture["queries"]:
            parsed_queries.append(parse_one(structure, row["id"], row["text"]))
    finally:
        structure.close()

    attempts = sum(
        row["attempted_chunks"] for row in [*parsed_passages, *parsed_queries]
    )
    if attempts > int(fixture["generation_limit"]):
        raise ValueError("local Gemma generation limit exceeded")
    fields = embed_event_fields([*parsed_passages, *parsed_queries])
    passage_matrices = matrix_sets(parsed_passages, fields, fixture["matrix"])
    query_matrices = matrix_sets(parsed_queries, fields, fixture["matrix"])
    if len(passage_matrices) < 2:
        raise ValueError("automatic parser produced too few matrix-bearing passages")
    passage_prototypes = {
        source_id: normalized_sum(matrices)
        for source_id, matrices in passage_matrices.items()
    }
    tree = build_tree(
        list(passage_prototypes), passage_prototypes,
        int(fixture["tree"]["leaf_capacity"]),
    )
    index_payload = {
        "version": "tom-assist-scaw-parser-matrix-tree/0.1-shadow",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "passage_matrices": passage_matrices,
        "passage_prototypes": passage_prototypes,
        "tree": tree,
        "tree_config": fixture["tree"],
        "matrix_config": fixture["matrix"],
    }
    index_bytes = canonical_json(index_payload) + b"\n"
    index_path = output / "matrix_tree.json"
    index_path.write_bytes(index_bytes)
    reloaded = json.loads(index_path.read_text(encoding="utf-8"))
    reload_exact = canonical_json(reloaded) + b"\n" == index_bytes

    observations = []
    for query in fixture["queries"]:
        query_id = query["id"]
        relevant = list(query["relevant_passage_ids"])
        matrices = query_matrices.get(query_id)
        if not matrices:
            observations.append({
                "query_id": query_id,
                "family": query["family"],
                "status": "query_has_no_automatic_matrix",
                "relevant_passage_ids": relevant,
                "direct_matrix": None,
                "matrix_tree": None,
            })
            continue
        query_prototype = normalized_sum(matrices)
        direct = rank_records(matrices, passage_matrices)
        selected = search_tree(
            reloaded["tree"], query_prototype, reloaded["passage_prototypes"],
            int(fixture["tree"]["beam_width"]),
        )
        selective = rank_records(
            matrices, reloaded["passage_matrices"], selected["candidate_ids"],
        )
        observations.append({
            "query_id": query_id,
            "family": query["family"],
            "status": "ranked",
            "relevant_passage_ids": relevant,
            "query_event_count": len(matrices),
            "direct_matrix": {
                "relevant_ranks": {
                    source_id: relevant_rank(direct, source_id) for source_id in relevant
                },
                "recall_at_k": {
                    str(k): recall(direct, relevant, k) for k in fixture["fixed_k"]
                },
                "top_five": direct[:5],
            },
            "matrix_tree": {
                "relevant_ranks": {
                    source_id: relevant_rank(selective, source_id) for source_id in relevant
                },
                "recall_at_k": {
                    str(k): recall(selective, relevant, k) for k in fixture["fixed_k"]
                },
                "top_five": selective[:5],
                "candidate_ids": selected["candidate_ids"],
                "candidate_count": selected["candidate_count"],
                "visited_node_count": selected["visited_node_count"],
            },
        })

    ranked = [row for row in observations if row["status"] == "ranked"]
    def mean_recall(channel: str, k: int) -> float:
        return (
            sum(row[channel]["recall_at_k"][str(k)] for row in ranked)
            / len(observations)
        )

    all_failures = [
        failure
        for row in [*parsed_passages, *parsed_queries]
        for failure in row["failures"]
    ]
    failure_codes = Counter(failure["code"] for failure in all_failures)
    unclassified = int(failure_codes.get("unclassified", 0))
    corpus_size = len(passages)
    checks = {
        "all_parser_chunks_attempted_within_limit": attempts == int(
            fixture["generation_limit"]
        ),
        "unclassified_failures_zero": unclassified == 0,
        "tree_examines_fewer_than_all_passages": all(
            row["matrix_tree"]["candidate_count"] < corpus_size for row in ranked
        ),
        "restart_byte_exact": reload_exact,
    }
    raw_parse_path = output / "raw_parser_records.json"
    raw_parse_path.write_bytes(canonical_json({
        "passages": parsed_passages,
        "queries": parsed_queries,
    }) + b"\n")
    report = {
        "version": "tom-assist-scaw-automatic-parser-matrix-tree-diagnostic/1.0",
        "status": "completed_local_shadow_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "external_corpus_sha256": fixture["external_corpus"]["sha256"],
        "source_pdf_sha256": fixture["external_corpus"]["source_pdf_sha256"],
        "local_gemma_chunk_generations": attempts,
        "generation_limit": fixture["generation_limit"],
        "oauth_calls": 0,
        "cloud_calls": 0,
        "network_calls": 0,
        "product_changed": False,
        "uses_17d_or_8d_document_route": False,
        "parser": {
            "passage_sources": len(parsed_passages),
            "passage_sources_failed_closed": sum(
                row["status"] != "parsed" for row in parsed_passages
            ),
            "passage_sources_with_directed_events": len(passage_matrices),
            "passage_sources_without_directed_events": sum(
                not row["events"] for row in parsed_passages
            ),
            "query_sources_failed_closed": sum(
                row["status"] != "parsed" for row in parsed_queries
            ),
            "query_sources_without_directed_events": sum(
                not row["events"] for row in parsed_queries
            ),
            "failure_codes": dict(sorted(failure_codes.items())),
            "unclassified_failure_count": unclassified,
            "compact_records": [
                safe_parse_record(row) for row in [*parsed_passages, *parsed_queries]
            ],
            "raw_sensitive_records_path": str(raw_parse_path),
            "raw_sensitive_records_sha256": sha256_bytes(raw_parse_path.read_bytes()),
        },
        "index": {
            "path": str(index_path),
            "sha256": sha256_bytes(index_bytes),
            "byte_length": len(index_bytes),
            "matrix_shape": [32, 32],
            "matrix_bearing_passage_count": len(passage_matrices),
            "reload_byte_exact": reload_exact,
        },
        "aggregate": {
            "observation_count": len(observations),
            "ranked_observation_count": len(ranked),
            "direct_matrix_mean_recall_at_k": {
                str(k): mean_recall("direct_matrix", k) for k in fixture["fixed_k"]
            },
            "matrix_tree_mean_recall_at_k": {
                str(k): mean_recall("matrix_tree", k) for k in fixture["fixed_k"]
            },
            "mean_tree_candidate_count": (
                sum(row["matrix_tree"]["candidate_count"] for row in ranked) / len(ranked)
                if ranked else None
            ),
            "max_tree_candidate_count": max(
                (row["matrix_tree"]["candidate_count"] for row in ranked),
                default=None,
            ),
            "external_corpus_passage_count": corpus_size,
        },
        "diagnostic_checks": checks,
        "observations": observations,
        "scope_boundary": {
            "automatic_parser_tested": True,
            "contract_text_committed": False,
            "full_corpus_fallback_used": False,
            "production_replacement_authorised_by_this_result": False,
            "matrix_native_growth_law_exists": False,
            "g_gate_verdict": None,
        },
    }
    report_path = output / "report.json"
    report_path.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(report_path),
        "local_gemma_chunk_generations": attempts,
        "parser": {
            key: report["parser"][key] for key in (
                "passage_sources_failed_closed",
                "passage_sources_with_directed_events",
                "passage_sources_without_directed_events",
                "query_sources_failed_closed",
                "query_sources_without_directed_events",
                "failure_codes",
            )
        },
        "aggregate": report["aggregate"],
        "checks": checks,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
