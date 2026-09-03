from __future__ import annotations

from gateway.structure_failures import (
    FAILURE_DEFINITIONS,
    MAX_FAILURE_DETAIL_CHARACTERS,
    ClassifiedStructureError,
    classify_failure,
    record_for_code,
    taxonomy_summary,
    validate_worker_telemetry,
)
from gateway.structure_worker import attempt_all_chunks
from gateway.structural_analysis import CANDIDATE_VERSION, SIGNAL_NAMES, text_digest


def _empty_candidate(text: str) -> dict:
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [],
        "orientations": [],
        "causal_relations": [],
        "signals": {name: [] for name in SIGNAL_NAMES},
        "unknown_fields": [],
        "confidence": 1.0,
    }


def test_every_enumerated_raise_family_triggers_its_unique_category():
    assert len({item.code for item in FAILURE_DEFINITIONS}) == len(FAILURE_DEFINITIONS)
    records = []
    for definition in FAILURE_DEFINITIONS:
        record = classify_failure(
            ValueError(definition.example), stage=definition.stage,
        )
        assert record["category"] == definition.code, definition
        assert definition.source
        records.append(record)
    summary = taxonomy_summary(records)
    assert summary["unclassified_count"] == 0
    assert summary["taxonomy_complete"] is True


def test_all_chunks_are_attempted_and_one_failure_fails_the_passage():
    class FixtureGemma:
        def __init__(self):
            self.calls = []

        def analyze(self, request_id, source_text, glossary):
            self.calls.append((request_id, source_text, glossary))
            if request_id.endswith(":1"):
                raise ClassifiedStructureError(record_for_code(
                    "tool.name", "Gemma called the wrong structure tool",
                ))
            return {
                "candidate": _empty_candidate(source_text),
                "boundary_telemetry": {"tool_parse_mode": "fixture"},
            }

    gemma = FixtureGemma()
    result = attempt_all_chunks(gemma, "request", ["one", "two", "three"])
    candidates = result.pop("chunk_candidates")
    telemetry = validate_worker_telemetry({"planned_chunks": 3, **result})
    assert len(gemma.calls) == 3
    assert [row["attempt_ordinal"] for row in telemetry["attempts"]] == [1, 2, 3]
    assert [row["outcome"] for row in telemetry["attempts"]] == [
        "succeeded", "failed", "succeeded",
    ]
    assert telemetry["attempted_chunks"] == 3
    assert telemetry["successful_chunks"] == 2
    assert telemetry["passage_failed"] is True
    assert telemetry["failed_chunk_index"] == 1
    assert telemetry["failures"][0]["chunk_index"] == 1
    assert telemetry["failures"][0]["attempt_ordinal"] == 2
    assert telemetry["taxonomy"]["unclassified_count"] == 0
    assert [row["chunk_index"] for row in candidates] == [0, 2]


def test_failure_detail_is_bounded_without_losing_its_ends():
    detail = "CAUSE-FIRST " + "x" * 1000 + " CAUSE-LAST"
    record = record_for_code("model.invoke", detail, chunk_index=4, attempt_ordinal=5)
    assert len(record["detail"]) == MAX_FAILURE_DETAIL_CHARACTERS
    assert record["detail"].startswith("CAUSE-FIRST")
    assert record["detail"].endswith("CAUSE-LAST")
    assert record["chunk_index"] == 4
    assert record["attempt_ordinal"] == 5


def test_unclassified_is_never_absorbed_and_is_reported_loudly():
    record = classify_failure(
        RuntimeError("entirely new failure"), stage="candidate_validation",
    )
    summary = taxonomy_summary([record])
    assert record["category"] == "unclassified"
    assert summary["unclassified_count"] == 1
    assert summary["taxonomy_complete"] is False
