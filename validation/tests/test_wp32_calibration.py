from __future__ import annotations

import inspect

import pytest

from validation.calibration.wp31_cases import expanded_cases as wp31_expanded_cases
from validation.calibration.wp32_cases import expanded_cases
from validation.calibration.wp32_runner import (
    READINESS_THRESHOLDS,
    _history_checks,
    _validated_telemetry,
    check,
    validate_case_contract,
)


def test_wp32_contract_retains_all_wp31_cases_and_freezes_80_cases():
    cases = expanded_cases()
    validate_case_contract(cases)
    assert len(cases) == 80
    for retained, original in zip(cases[:52], wp31_expanded_cases()):
        assert retained["case_id"] == original["case_id"]
        assert retained["text"] == original["text"]
        assert retained["expected_relations"] == original["expected_relations"]
        assert retained["expected_signals"] == original["expected_signals"]
        assert retained["min_chunks"] == original["min_chunks"]
    assert sum(case["family"] == "history" for case in cases) == 8
    assert check()["cases"] == 80


def test_wp32_readiness_thresholds_are_fixed_before_run():
    assert READINESS_THRESHOLDS == {
        "strict_observation_rate": 0.90,
        "minimum_family_observation_rate": 0.75,
        "end_to_end_relation_recall": 0.90,
        "maximum_reversed_relations": 0,
        "maximum_unexpected_relation_rate": 0.05,
        "end_to_end_signal_recall": 0.80,
        "multi_relation_exact_rate": 0.80,
        "history_case_rate": 0.875,
        "load_shape_rate": 1.0,
    }


def test_wp32_worker_telemetry_is_exact_and_fail_closed():
    telemetry = {
        "planned_chunks": 3,
        "attempted_chunks": 2,
        "successful_chunks": 1,
        "failed_chunk_index": 1,
        "chunks": [{
            "chunk_index": 0,
            "tool_parse_mode": "native",
            "schema_projection_applied": False,
        }],
    }
    assert _validated_telemetry(telemetry) == telemetry
    malformed = dict(telemetry, attempted_chunks=0)
    with pytest.raises(ValueError, match="inconsistent"):
        _validated_telemetry(malformed)
    with pytest.raises(ValueError, match="missing or malformed"):
        _validated_telemetry(None)


def test_wp32_history_bounds_are_deterministic():
    checks = _history_checks(
        [
            {"channel": "recurrence", "minimum": 0.7},
            {"channel": "decay", "minimum": 0.1, "maximum": 0.2},
        ],
        {"recurrence": 0.8, "decay": 1 / 6},
    )
    assert all(row["met"] for row in checks)
    assert not _history_checks(
        [{"channel": "recurrence", "maximum": 0.5}],
        {"recurrence": 0.8},
    )[0]["met"]


def test_wp32_runner_has_no_provider_or_preview_mutation_surface():
    source = inspect.getsource(__import__(
        "validation.calibration.wp32_runner", fromlist=["dummy"]
    ))
    for forbidden in (
        "rgm.read_memory", "ToMClient.process", "engine.step",
        "OPENAI_API_KEY", "openai_client", "auth_profiles", "feeling_wheel",
    ):
        assert forbidden not in source
    assert '"provider_calls": 0' in source
