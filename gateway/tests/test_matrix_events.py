import copy
import json

import pytest

from gateway.matrix_events import (
    MATRIX_EVENT_SCHEMA_VERSION,
    build_matrix_event_prompt,
    matrix_event_response_format,
    matrix_event_semantic_fields,
    project_matrix_event_fields,
    validate_matrix_event_candidate,
)


def candidate():
    return {
        "events": [
            {
                "source_evidence": {"quote": "the Contractor"},
                "target_evidence": {"quote": "pay the levy"},
                "relation_kind": "obligation",
                "relation_evidence": {
                    "quote": "the Contractor must pay the levy"
                },
                "context_evidence": {"quote": "Before construction starts"},
                "modality": "asserted",
                "negated": False,
                "confidence": 1.0,
            }
        ],
        "unknown_relations": [],
    }


def test_candidate_is_exactly_bound_and_semantic_fields_use_evidence():
    source = "Before construction starts, the Contractor must pay the levy."
    result = validate_matrix_event_candidate(candidate(), source)
    assert result["schema_version"] == MATRIX_EVENT_SCHEMA_VERSION
    event = result["events"][0]
    assert event["source_evidence"] == {
        "start": 28, "end": 42, "quote": "the Contractor",
    }
    assert event["target_evidence"]["quote"] == "pay the levy"
    assert matrix_event_semantic_fields(event) == {
        "source": "the Contractor",
        "target": "pay the levy",
        "relation": "obligation asserted affirmed",
        "context": "Before construction starts",
    }


def test_question_keeps_unknown_answer_endpoint_null():
    source = "What must the Contractor do before construction starts?"
    payload = candidate()
    payload["events"][0].update({
        "source_evidence": {"quote": "the Contractor"},
        "target_evidence": None,
        "relation_evidence": {"quote": "must the Contractor do"},
        "context_evidence": {"quote": "before construction starts"},
        "modality": "questioned",
    })
    result = validate_matrix_event_candidate(payload, source)
    fields = matrix_event_semantic_fields(result["events"][0])
    assert fields["target"] is None
    assert fields["source"] == "the Contractor"


def test_assertion_with_unknown_endpoint_fails_closed():
    source = "The Contractor must pay the levy."
    payload = candidate()
    payload["events"][0].update({
        "source_evidence": {"quote": "The Contractor"},
        "target_evidence": None,
        "relation_evidence": {"quote": "The Contractor must pay the levy"},
        "context_evidence": None,
    })
    with pytest.raises(ValueError, match="only when modality is questioned"):
        validate_matrix_event_candidate(payload, source)


def test_ambiguous_or_invented_quote_fails_closed():
    source = "The Contractor pays. The Contractor reports."
    payload = candidate()
    payload["events"][0].update({
        "source_evidence": {"quote": "The Contractor"},
        "target_evidence": {"quote": "reports"},
        "relation_evidence": {"quote": source},
        "context_evidence": None,
    })
    with pytest.raises(ValueError, match="occur exactly once"):
        validate_matrix_event_candidate(payload, source)


def test_repeated_endpoint_is_disambiguated_only_by_relation_span():
    source = "The Contractor pays. The Contractor reports."
    payload = candidate()
    payload["events"][0].update({
        "source_evidence": {"quote": "The Contractor"},
        "target_evidence": {"quote": "reports"},
        "relation_evidence": {"quote": "The Contractor reports"},
        "context_evidence": None,
    })
    result = validate_matrix_event_candidate(payload, source)
    assert result["events"][0]["source_evidence"] == {
        "start": 21, "end": 35, "quote": "The Contractor",
    }
    payload["events"][0]["source_evidence"] = {"quote": "the Superintendent"}
    with pytest.raises(ValueError, match="occur exactly once"):
        validate_matrix_event_candidate(payload, source)


def test_repeated_context_is_disambiguated_only_by_relation_span():
    source = "Before work, A must pay. Before work, A must report."
    payload = candidate()
    payload["events"][0].update({
        "source_evidence": {"quote": "A"},
        "target_evidence": {"quote": "report"},
        "relation_evidence": {"quote": "Before work, A must report"},
        "context_evidence": {"quote": "Before work"},
    })
    result = validate_matrix_event_candidate(payload, source)
    assert result["events"][0]["context_evidence"] == {
        "start": 25, "end": 36, "quote": "Before work",
    }


def test_presentation_fields_are_removed_but_missing_facts_are_not_repaired():
    payload = candidate()
    payload["explanation"] = "ignore"
    payload["events"][0]["matrix"] = [1.0]
    payload["events"][0]["source_evidence"]["start"] = 999
    projected = project_matrix_event_fields(payload)
    assert set(projected) == {"events", "unknown_relations"}
    assert "matrix" not in projected["events"][0]
    assert projected["events"][0]["source_evidence"] == {
        "quote": "the Contractor"
    }
    broken = copy.deepcopy(payload)
    del broken["events"][0]["target_evidence"]
    with pytest.raises(ValueError, match="fields mismatch"):
        validate_matrix_event_candidate(project_matrix_event_fields(broken), "x")


def test_schema_and_prompt_exclude_values_and_define_direction():
    response_format = matrix_event_response_format()
    serialized = json.dumps(response_format)
    assert '"matrix"' not in serialized
    assert '"vector"' not in serialized
    assert '"start"' not in serialized
    assert '"end"' not in serialized
    prompt = build_matrix_event_prompt("A must do B before C.")
    assert "actor -> action" in prompt
    assert "prerequisite -> gated/dependent action" in prompt
    assert "An unanswered endpoint must be null" in prompt
    assert "Never invent the answer" in prompt
