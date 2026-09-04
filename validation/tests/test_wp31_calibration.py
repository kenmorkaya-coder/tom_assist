from __future__ import annotations

from copy import deepcopy

from gateway.structural_analysis import CANDIDATE_VERSION, text_digest
from validation.calibration.wp31_cases import expanded_cases
from validation.calibration.wp31_runner import (
    _error_code,
    cases_digest,
    score_candidate,
    validate_case_contract,
)


def _candidate(text: str):
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [
            {
                "id": "alpha", "label": "Alpha", "kind": "event",
                "evidence": {"start": 0, "end": 5, "quote": "Alpha"},
                "confidence": 1.0,
            },
            {
                "id": "beta", "label": "Beta", "kind": "outcome",
                "evidence": {"start": 13, "end": 17, "quote": "Beta"},
                "confidence": 1.0,
            },
        ],
        "orientations": [],
        "causal_relations": [{
            "id": "relation", "cause_entity_id": "alpha", "effect_entity_id": "beta",
            "kind": "causes", "modality": "asserted", "negated": False,
            "evidence": {"start": 0, "end": 18, "quote": text}, "confidence": 1.0,
        }],
        "signals": {name: [] for name in (
            "rules", "contradictions", "inferences", "sequences",
            "memory_references", "future_references", "completions", "rejections",
        )},
        "unknown_fields": [],
        "confidence": 1.0,
    }


def test_wp31_case_contract_is_exact_and_compact():
    cases = expanded_cases()
    validate_case_contract(cases)
    assert len(cases) == 52
    assert len(cases_digest(cases)) == 71
    assert sum("pair_id" in case for case in cases) == 10
    assert all(len(case["text"]) < 5_000 for case in cases)


def test_wp31_long_cases_are_expanded_but_source_definition_stays_small():
    long_cases = [case for case in expanded_cases() if case["family"] == "long_position"]
    assert len(long_cases) == 6
    assert all(case["min_chunks"] == 2 for case in long_cases)
    assert all(len(case["text"]) > 1_000 for case in long_cases)


def test_wp31_scoring_preserves_causal_direction():
    case = expanded_cases()[0]
    candidate = _candidate(case["text"])
    score = score_candidate(case, candidate)
    assert score["matched_relation_count"] == 1
    assert score["reversed_relations"] == []

    reversed_candidate = deepcopy(candidate)
    reversed_candidate["causal_relations"][0]["cause_entity_id"] = "beta"
    reversed_candidate["causal_relations"][0]["effect_entity_id"] = "alpha"
    reversed_score = score_candidate(case, reversed_candidate)
    assert reversed_score["matched_relation_count"] == 0
    assert len(reversed_score["reversed_relations"]) == 1


def test_wp31_runner_has_no_provider_or_preview_mutation_surface():
    import inspect
    from validation.calibration import wp31_runner

    source = inspect.getsource(wp31_runner)
    for forbidden in (
        "oauth_provider", "TOM_ASSIST_LIVE_OAUTH", "rgm.read_memory",
        "ToMClient.process", "engine.step", "feeling_wheel_mapper",
    ):
        assert forbidden not in source
    assert '"provider_calls": 0' in source


def test_wp31_error_taxonomy_unwraps_worker_failures():
    assert _error_code("StructureProviderError: RuntimeError: JSONDecodeError: bad") == (
        "invalid_tool_json"
    )
    assert _error_code("ValueError: entities[0] has no exact evidence quote") == (
        "missing_evidence_quote"
    )
    assert _error_code("ValueError: evidence quote is missing or ambiguous") == (
        "ambiguous_evidence_quote"
    )
    assert _error_code("ValueError: No function provided.") == "missing_tool_call"
    assert _error_code("ValueError: fields mismatch: extra=['label']") == (
        "extra_schema_field"
    )
