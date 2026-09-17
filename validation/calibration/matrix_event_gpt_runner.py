#!/usr/bin/env python3
"""Run the frozen four-call GPT matrix-event comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gateway.gpt_matrix_event_parser import (  # noqa: E402
    GPTMatrixEventParser,
    GPTMatrixEventParserError,
)
from gateway.oauth_provider import OAuthProvider  # noqa: E402
from validation.calibration.matrix_event_scaw_runner import (  # noqa: E402
    MINILM_MODEL,
    compact_parse_record,
    compile_records,
    embed_texts,
    prototype,
    rank_views,
    recall_at_k,
    semantic_texts,
)
from validation.calibration.matrix_tree_32sq_runner import (  # noqa: E402
    build_tree,
    canonical_json,
    search_tree,
    sha256_bytes,
    sha256_file,
)


FIXTURE_PATH = ROOT / "validation" / "calibration" / "matrix_event_gpt_fixture.json"
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration" / "MATRIX_EVENT_GPT_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "144dc638f69404f82619c33ba25539902162e1aef5cb766c6045b5076633546e"
)


def validate_fixture(payload: Any) -> dict[str, Any]:
    fields = {
        "version", "purpose", "external_corpus", "minilm_revision",
        "provider_call_limit", "tree", "matrix", "queries",
        "diagnostic_expectations",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("GPT matrix-event fixture shape mismatch")
    if payload["external_corpus"].get("passage_ids") != ["SCAW-013", "SCAW-019"]:
        raise ValueError("GPT passage inventory changed")
    if len(payload["queries"]) != 2 or int(payload["provider_call_limit"]) != 4:
        raise ValueError("GPT call inventory changed")
    if payload["tree"] != {"leaf_capacity": 1, "beam_width": 1}:
        raise ValueError("GPT matrix Tree mechanics changed")
    return dict(payload)


def parse_source(
    parser: GPTMatrixEventParser,
    source_id: str,
    source_text: str,
) -> dict[str, Any]:
    try:
        result = parser.parse(source_text, explicit_send=True)
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
    except GPTMatrixEventParserError as error:
        return {
            "source_id": source_id,
            "source_sha256": "sha256:"
            + hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "status": "failed_closed",
            "candidate": None,
            "parser_model": None,
            "telemetry": {"provider_calls": 1, "retry_count": 0},
            "failure": {
                "type": type(error).__name__,
                "detail": str(error)[:512],
                "provider_failure": error.provider_failure,
            },
        }


def main() -> int:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--output", required=True, type=Path)
    argument_parser.add_argument("--socket", required=True, type=Path)
    args = argument_parser.parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit("output path exists; frozen runs are append-forbidden")
    output.mkdir(parents=True)
    if sha256_file(FIXTURE_PATH) != EXPECTED_FIXTURE_SHA256:
        raise SystemExit("frozen GPT matrix-event fixture digest mismatch")
    preregistration = PREREGISTRATION_PATH.read_text(encoding="utf-8")
    if (
        "FROZEN — OWNER AUTHORISED FOUR EXPLICIT GPT CALLS" not in preregistration
        or EXPECTED_FIXTURE_SHA256 not in preregistration
    ):
        raise SystemExit("GPT matrix-event pre-registration is not frozen")
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    corpus_path = Path(fixture["external_corpus"]["path"])
    if sha256_file(corpus_path) != fixture["external_corpus"]["sha256"]:
        raise SystemExit("external SCAW corpus digest mismatch")
    if not MINILM_MODEL.is_dir():
        raise SystemExit("cached MiniLM model missing")
    provider = OAuthProvider(str(args.socket.resolve()))
    status = provider.status()
    if not status["connected"]:
        report = {
            "version": "tom-assist-matrix-event-gpt-diagnostic/1.0",
            "status": "skipped_oauth_not_connected",
            "fixture_sha256": EXPECTED_FIXTURE_SHA256,
            "oauth_status": status,
            "provider_calls": 0,
            "retry_count": 0,
            "g_gate_verdict": None,
        }
        report_path = output / "report.json"
        report_path.write_bytes(canonical_json(report) + b"\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    lookup = {row["passage_id"]: row for row in corpus["passages"]}
    passages = [lookup[source_id] for source_id in fixture["external_corpus"]["passage_ids"]]
    parser = GPTMatrixEventParser(provider)
    parsed_passages = []
    parsed_queries = []
    raw_path = output / "raw_parser_records.json"

    def persist_raw() -> None:
        raw_path.write_bytes(canonical_json({
            "passages": parsed_passages, "queries": parsed_queries,
        }) + b"\n")

    for row in passages:
        parsed_passages.append(parse_source(parser, row["passage_id"], row["text"]))
        persist_raw()
    for row in fixture["queries"]:
        parsed_queries.append(parse_source(parser, row["id"], row["text"]))
        persist_raw()
    attempts = len(parsed_passages) + len(parsed_queries)
    if attempts != int(fixture["provider_call_limit"]):
        raise ValueError("GPT provider call inventory changed")
    records = [*parsed_passages, *parsed_queries]
    texts = semantic_texts(records)
    vectors = embed_texts(texts) if texts else {}
    passage_views = compile_records(parsed_passages, vectors, fixture["matrix"])
    query_views = compile_records(parsed_queries, vectors, fixture["matrix"])
    prototypes = {
        source_id: prototype(views) for source_id, views in passage_views.items()
    }
    tree = (
        build_tree(
            list(prototypes), prototypes, int(fixture["tree"]["leaf_capacity"]),
        ) if len(prototypes) >= 2 else None
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
            tree, prototype(query_views[query_id]), prototypes,
            int(fixture["tree"]["beam_width"]),
        )
        selective = rank_views(
            query_views[query_id], passage_views, selected["candidate_ids"],
        )
        observations.append({
            "query_id": query_id, "family": query["family"], "status": "ranked",
            "relevant_passage_ids": relevant,
            "direct": {
                "recall_at_1": recall_at_k(direct, relevant, 1),
                "ranking": direct,
            },
            "tree": {
                "recall_at_1": recall_at_k(selective, relevant, 1),
                "ranking": selective,
                "candidate_ids": selected["candidate_ids"],
            },
        })
    all_matrices = [
        view["matrix"] for views in [*passage_views.values(), *query_views.values()]
        for view in views
    ]
    report = {
        "version": "tom-assist-matrix-event-gpt-diagnostic/1.0",
        "status": "completed_explicit_gpt_shadow_diagnostic_not_a_gate",
        "fixture_sha256": EXPECTED_FIXTURE_SHA256,
        "external_corpus_sha256": fixture["external_corpus"]["sha256"],
        "oauth_status": {
            "connected": status["connected"], "model": status["model"],
            "provider_surface": status["capabilities"]["provider_surface"],
        },
        "provider_calls": attempts,
        "retry_count": 0,
        "parser": {
            "passages_attempted": len(parsed_passages),
            "passages_failed_closed": sum(row["status"] != "parsed" for row in parsed_passages),
            "passages_with_events": len(passage_views),
            "queries_attempted": len(parsed_queries),
            "queries_failed_closed": sum(row["status"] != "parsed" for row in parsed_queries),
            "queries_with_events": len(query_views),
            "compact_records": [compact_parse_record(row) for row in records],
            "raw_sensitive_records_path": str(raw_path),
            "raw_sensitive_records_sha256": sha256_bytes(raw_path.read_bytes()),
        },
        "matrix": {
            "shape": [32, 32],
            "count": len(all_matrices),
            "no_exact_zero_entries": all(
                all(value != 0.0 for value in matrix) for matrix in all_matrices
            ),
        },
        "observations": observations,
        "scope_boundary": {
            "product_changed": False,
            "packet_admission_changed": False,
            "growth_or_learning_law_tested": False,
            "g_gate_verdict": None,
        },
    }
    report_path = output / "report.json"
    report_path.write_bytes(canonical_json(report) + b"\n")
    print(json.dumps({
        "report": str(report_path),
        "provider_calls": attempts,
        "parser": report["parser"],
        "matrix": report["matrix"],
        "observations": observations,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
