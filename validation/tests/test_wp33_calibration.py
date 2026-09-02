from __future__ import annotations

import inspect

from validation.calibration.wp32_cases import expanded_cases as wp32_expanded_cases
from validation.calibration.wp33_cases import expanded_cases
from validation.calibration.wp33_runner import (
    READINESS_THRESHOLDS,
    check,
    validate_case_contract,
)


def test_wp33_contract_retains_wp32_with_only_declared_hd05_bound_change():
    cases = expanded_cases()
    prior = wp32_expanded_cases()
    validate_case_contract(cases)
    assert len(cases) == 94
    for current, original in zip(cases[:80], prior):
        assert current["case_id"] == original["case_id"]
        assert current["text"] == original["text"]
        assert current["expected_relations"] == original["expected_relations"]
        assert current["expected_signals"] == original["expected_signals"]
        if current["case_id"] == "HD-05":
            persistence = next(
                row for row in current["history_expectations"]
                if row["channel"] == "persistence"
            )
            assert persistence == {
                "channel": "persistence", "minimum": 2 / 3, "maximum": 2 / 3
            }
        else:
            assert current["history_expectations"] == original["history_expectations"]
    assert check()["cases"] == 94


def test_wp33_additions_are_fixed_and_direction_sensitive():
    added = expanded_cases()[80:]
    assert len(added) == 14
    assert {row["origin"] for row in added} == {"wp33_added"}
    assert sum(row["family"] == "multi_relation" for row in added) == 6
    assert sum(row["family"] == "long_position" for row in added) == 4
    assert sum(row["family"] == "parser_boundary" for row in added) == 4
    assert all(row["expected_relations"] for row in added)
    assert all(row["min_chunks"] >= 2 for row in added if row["family"] == "long_position")


def test_wp33_thresholds_and_safety_boundary_remain_fixed():
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
    source = inspect.getsource(__import__(
        "validation.calibration.wp33_runner", fromlist=["unused"]
    ))
    for forbidden in (
        "rgm.read_memory", "ToMClient.process", "engine.step",
        "OPENAI_API_KEY", "openai_client", "auth_profiles", "feeling_wheel",
    ):
        assert forbidden not in source
    assert '"provider_calls": 0' in source
