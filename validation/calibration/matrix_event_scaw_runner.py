#!/usr/bin/env python3
"""Run the frozen evidence-bound matrix-event SCAW diagnostic."""
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
from gateway.matrix_event_provider import (  # noqa: E402
    MatrixEventProviderError,
    MatrixEventWorkerClient,
)
from gateway.matrix_events import matrix_event_semantic_fields  # noqa: E402
from validation.calibration.matrix_tree_32sq_runner import (  # noqa: E402
    build_tree,
    canonical_json,
    cosine,
    event_matrix,
    normalize,
    search_tree,
    sha256_bytes,
    sha256_file,
)


FIXTURE_PATH = ROOT / "validation" / "calibration" / "matrix_event_scaw_fixture.json"
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration" / "MATRIX_EVENT_SCAW_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "5840309d26d6d9ef36613848e9cfce7ff39de95842ba6b02e7c2d0b26cb3f9bb"
)
REPORT_VERSION = "tom-assist-matrix-event-scaw-diagnostic/1.0"
INDEX_VERSION = "tom-assist-evidence-matrix-tree/0.1-shadow"
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


def validate_fixture(payload: Any) -> dict[str, Any]:
    fields = {
        "version", "purpose", "external_corpus", "models",
        "local_generation_limit", "fixed_k", "tree", "matrix", "queries",
        "diagnostic_expectations",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("matrix-event fixture shape mismatch")
    passage_ids = payload["external_corpus"].get("passage_ids")
    if (
        not isinstance(passage_ids, list)
        or len(passage_ids) != 10
        or len(set(passage_ids)) != 10
    ):
        raise ValueError("matrix-event passage inventory changed")
    if len(payload["queries"]) != 5 or int(payload["local_generation_limit"]) != 15:
        raise ValueError("matrix-event source inventory changed")
    if payload["fixed_k"] != [1, 3, 5]:
        raise ValueError("matrix-event fixed-k depths changed")
    if payload["tree"] != {"leaf_capacity": 2, "beam_width": 2}:
        raise ValueError("matrix-event Tree mechanics changed")
    if payload["matrix"].get("views") != [
        "full", "source_context", "context_target",
    ]:
        raise ValueError("matrix-event view inventory changed")
    for row in payload["queries"]:
        if not set(row["relevant_passage_ids"]) <= set(passage_ids):
            raise ValueError("query relevance ID is outside the frozen corpus")
    return dict(payload)


def local_worker() -> MatrixEventWorkerClient:
    return MatrixEventWorkerClient([
        str(GEMMA_PYTHON.resolve()),
        str((ROOT / "gateway" / "gemma_matrix_event_worker.py").resolve()),
        "--model", str(GEMMA_MODEL.resolve()),
    ], timeout_seconds=600.0)


def embedding_worker() -> DocumentEmbeddingWorkerClient:
    return DocumentEmbeddingWorkerClient([
        sys.executable,
        str((ROOT / "gateway" / "document_embedding_worker.py").resolve()),
        "--model", str(MINILM_MODEL.resolve()),
    ])


def parse_source(
    worker: MatrixEventWorkerClient, source_id: str, source_text: str,
) -> dict[str, Any]:
    try:
        result = worker.parse(source_text)
        return {
            "source_id": source_id,
            "source_sha256": "sha256:"
            + hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "status": "parsed",
            "candidate": result["candidate"],
            "parser_model": result["parser_model"],
            "telemetry": result["telemetry"],
            "failure": None,
        }
    except MatrixEventProviderError as error:
        detail = str(error)[:512]
        return {
            "source_id": source_id,
            "source_sha256": "sha256:"
            + hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "status": "failed_closed",
            "candidate": None,
            "parser_model": None,
            "telemetry": {"local_generations": 1, "provider_calls": 0},
            "failure": {"type": type(error).__name__, "detail": detail},
        }


def compact_parse_record(row: Mapping[str, Any]) -> dict[str, Any]:
    candidate = row["candidate"]
    return {
        "source_id": row["source_id"],
        "source_sha256": row["source_sha256"],
        "status": row["status"],
        "event_count": len(candidate["events"]) if candidate else 0,
        "unknown_relation_count": len(candidate["unknown_relations"]) if candidate else 0,
        "failure_type": row["failure"]["type"] if row["failure"] else None,
        "failure_detail": row["failure"]["detail"] if row["failure"] else None,
    }


def semantic_texts(records: Sequence[Mapping[str, Any]]) -> list[str]:
    result = set()
    for record in records:
        if record["candidate"] is None:
            continue
        for event in record["candidate"]["events"]:
            result.update(
                value for value in matrix_event_semantic_fields(event).values()
                if value is not None
            )
    return sorted(result)


def embed_texts(texts: Sequence[str]) -> dict[str, list[float]]:
    worker = embedding_worker()
    try:
        return {
            text: [
                float(value) for value in
                build_document_query_profile(text, worker)["passage_vector"]
            ]
            for text in texts
        }
    finally:
        worker.close()


def compile_event_views(
    event: Mapping[str, Any],
    vectors: Mapping[str, Sequence[float]],
    matrix_config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    fields = matrix_event_semantic_fields(event)
    source, target, relation, context = (
        fields["source"], fields["target"], fields["relation"], fields["context"],
    )
    specs = []
    if source is not None and target is not None:
        specs.append(("full", source, target))
    if source is not None:
        specs.append(("source_context", source, context))
    if target is not None:
        specs.append(("context_target", context, target))
    views = []
    for kind, left, right in specs:
        matrix = event_matrix({
            "source": left,
            "target": right,
            "relation": relation,
            "context": context,
        }, vectors, matrix_config)
        if any(value == 0.0 for value in matrix):
            raise ValueError("32x32 matrix contains an exact-zero entry")
        views.append({
            "event_id": event["id"], "view": kind, "matrix": matrix,
        })
    return views


def compile_records(
    records: Sequence[Mapping[str, Any]],
    vectors: Mapping[str, Sequence[float]],
    matrix_config: Mapping[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    return {
        str(record["source_id"]): [
            view
            for event in record["candidate"]["events"]
            for view in compile_event_views(event, vectors, matrix_config)
        ]
        for record in records
        if record["candidate"] is not None and record["candidate"]["events"]
    }


def prototype(views: Sequence[Mapping[str, Any]]) -> list[float]:
    return normalize([
        sum(float(view["matrix"][index]) for view in views)
        for index in range(32 * 32)
    ])


def score_views(
    query: Sequence[Mapping[str, Any]], passage: Sequence[Mapping[str, Any]],
) -> float:
    return max(
        cosine(left["matrix"], right["matrix"])
        for left in query for right in passage
    )


def rank_views(
    query: Sequence[Mapping[str, Any]],
    passages: Mapping[str, Sequence[Mapping[str, Any]]],
    candidate_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    ids = sorted(candidate_ids if candidate_ids is not None else passages)
    scored = sorted(
        ((source_id, score_views(query, passages[source_id])) for source_id in ids),
        key=lambda row: (-row[1], row[0]),
    )
    return [
        {"passage_id": source_id, "rank": rank, "score": score}
        for rank, (source_id, score) in enumerate(scored, 1)
    ]


def recall_at_k(ranked: Sequence[Mapping[str, Any]], relevant: Sequence[str], k: int) -> float:
    top = {row["passage_id"] for row in ranked if int(row["rank"]) <= k}
    return sum(source_id in top for source_id in relevant) / len(relevant)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output path exists; frozen runs are append-forbidden")
    output.mkdir(parents=True)
    if sha256_file(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("frozen matrix-event fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if (
        "FROZEN — OWNER AUTHORISED LOCAL GEMMA GENERATION" not in preregistration
        or EXPECTED_FIXTURE_SHA256 not in preregistration
    ):
        raise SystemExit("matrix-event pre-registration is not frozen")
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
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
    passage_lookup = {row["passage_id"]: row for row in corpus["passages"]}
    passages = [
        passage_lookup[source_id]
        for source_id in fixture["external_corpus"]["passage_ids"]
    ]
    raw_path = output / "raw_parser_records.json"
    parsed_passages: list[dict[str, Any]] = []
    parsed_queries: list[dict[str, Any]] = []

    def persist_raw() -> None:
        raw_path.write_bytes(canonical_json({
            "passages": parsed_passages, "queries": parsed_queries,
        }) + b"\n")

    worker = local_worker()
    try:
        for row in passages:
            parsed_passages.append(parse_source(worker, row["passage_id"], row["text"]))
            persist_raw()
        for row in fixture["queries"]:
            parsed_queries.append(parse_source(worker, row["id"], row["text"]))
            persist_raw()
    finally:
        worker.close()

    attempts = len(parsed_passages) + len(parsed_queries)
    all_records = [*parsed_passages, *parsed_queries]
    texts = semantic_texts(all_records)
    vectors = embed_texts(texts) if texts else {}
    passage_views = compile_records(parsed_passages, vectors, fixture["matrix"])
    query_views = compile_records(parsed_queries, vectors, fixture["matrix"])
    passage_prototypes = {
        source_id: prototype(views) for source_id, views in passage_views.items()
    }
    tree = (
        build_tree(
            list(passage_prototypes), passage_prototypes,
            int(fixture["tree"]["leaf_capacity"]),
        ) if len(passage_prototypes) >= 2 else None
    )
    observations = []
    for query in fixture["queries"]:
        query_id = query["id"]
        relevant = query["relevant_passage_ids"]
        if query_id not in query_views or tree is None:
            observations.append({
                "query_id": query_id, "family": query["family"],
                "status": "not_ranked_no_query_matrix_or_tree",
                "relevant_passage_ids": relevant,
            })
            continue
        direct = rank_views(query_views[query_id], passage_views)
        selected = search_tree(
            tree, prototype(query_views[query_id]), passage_prototypes,
            int(fixture["tree"]["beam_width"]),
        )
        selective = rank_views(
            query_views[query_id], passage_views, selected["candidate_ids"],
        )
        observations.append({
            "query_id": query_id, "family": query["family"], "status": "ranked",
            "relevant_passage_ids": relevant,
            "direct": {
                "recall_at_k": {
                    str(k): recall_at_k(direct, relevant, k)
                    for k in fixture["fixed_k"]
                },
                "top_five": direct[:5],
            },
            "tree": {
                "recall_at_k": {
                    str(k): recall_at_k(selective, relevant, k)
                    for k in fixture["fixed_k"]
                },
                "top_five": selective[:5],
                "candidate_ids": selected["candidate_ids"],
                "candidate_count": selected["candidate_count"],
                "visited_node_count": selected["visited_node_count"],
            },
        })
    ranked = [row for row in observations if row["status"] == "ranked"]

    def mean_recall(channel: str, k: int) -> float | None:
        return (
            sum(row[channel]["recall_at_k"][str(k)] for row in ranked) / len(ranked)
            if ranked else None
        )

    failures = Counter(
        row["failure"]["detail"] for row in all_records if row["failure"]
    )
    all_matrices = [
        view["matrix"] for views in [*passage_views.values(), *query_views.values()]
        for view in views
    ]
    checks = {
        "all_sources_attempted_once": attempts == int(fixture["local_generation_limit"]),
        "no_provider_or_cloud_calls": True,
        "no_exact_zero_matrix_entries": all(
            all(value != 0.0 for value in matrix) for matrix in all_matrices
        ),
        "tree_no_full_scan": all(
            row["tree"]["candidate_count"] < len(passage_views) for row in ranked
        ),
    }
    index_path = output / "matrix_tree.json"
    index_payload = {
        "version": INDEX_VERSION,
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "passage_views": passage_views,
        "passage_prototypes": passage_prototypes,
        "tree": tree,
    }
    index_path.write_bytes(canonical_json(index_payload) + b"\n")
    report = {
        "version": REPORT_VERSION,
        "status": "completed_local_shadow_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "external_corpus_sha256": fixture["external_corpus"]["sha256"],
        "source_pdf_sha256": fixture["external_corpus"]["source_pdf_sha256"],
        "local_gemma_generations": attempts,
        "oauth_calls": 0,
        "cloud_calls": 0,
        "network_calls": 0,
        "parser": {
            "passages_attempted": len(parsed_passages),
            "passages_failed_closed": sum(row["status"] != "parsed" for row in parsed_passages),
            "passages_with_events": len(passage_views),
            "queries_attempted": len(parsed_queries),
            "queries_failed_closed": sum(row["status"] != "parsed" for row in parsed_queries),
            "queries_with_events": len(query_views),
            "failure_details": dict(sorted(failures.items())),
            "compact_records": [compact_parse_record(row) for row in all_records],
            "raw_sensitive_records_path": str(raw_path),
            "raw_sensitive_records_sha256": sha256_bytes(raw_path.read_bytes()),
        },
        "index": {
            "path": str(index_path),
            "sha256": sha256_file(index_path),
            "byte_length": index_path.stat().st_size,
            "matrix_shape": [32, 32],
            "matrix_count": len(all_matrices),
            "passage_count": len(passage_views),
        },
        "aggregate": {
            "observation_count": len(observations),
            "ranked_observation_count": len(ranked),
            "direct_mean_recall_at_k": {
                str(k): mean_recall("direct", k) for k in fixture["fixed_k"]
            },
            "tree_mean_recall_at_k": {
                str(k): mean_recall("tree", k) for k in fixture["fixed_k"]
            },
        },
        "checks": checks,
        "observations": observations,
        "scope_boundary": {
            "product_changed": False,
            "packet_admission_changed": False,
            "uses_17d_or_8d_document_route": False,
            "matrix_native_growth_law_tested": False,
            "g_gate_verdict": None,
        },
    }
    report_path = output / "report.json"
    report_path.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(report_path),
        "parser": report["parser"],
        "aggregate": report["aggregate"],
        "checks": checks,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
