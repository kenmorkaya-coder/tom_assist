from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from gateway.dense_load17 import (
    ANCHOR_BANK_PATH,
    compile_dense_shadow_load,
    load_anchor_bank,
    validate_dense_shadow_load,
)
from gateway.semantic_chunks import build_semantic_profile
from gateway.structural_analysis import CHANNELS


def _canonical_json(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _fixture():
    bank = load_anchor_bank()
    text = "A deterministic semantic fixture."
    vector = list(bank["channels"]["L_rule"][0]["vector"])
    profile = build_semantic_profile(
        text,
        [{"start": 0, "end": len(text), "values": vector}],
        model=bank["embedding_model"],
        revision=bank["embedding_revision"],
    )
    analysis = {
        "load_signature": {name: 0.0 for name in CHANNELS},
        "history_metrics": {
            "combined_similarities": [],
            "static_distance_from_previous": 0.0,
            "change_evidence": 0.0,
        },
        "current_classification_confidence": None,
        "previous_classification_confidence": None,
        "driver_evidence": {},
        "directed_graph": [["approval", "requires", "release"]],
    }
    return text, profile, analysis


def test_anchor_bank_is_bound_to_frozen_source_and_compact():
    source_path = ANCHOR_BANK_PATH.parents[2] / "validation" / "calibration" / "wp36b_anchor_source.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    bank = load_anchor_bank()

    assert bank["source_sha256"] == "sha256:" + hashlib.sha256(_canonical_json(source)).hexdigest()
    assert tuple(bank["channels"]) == CHANNELS
    assert tuple(bank["drivers"]) == (
        "threat_load", "sustenance_potential", "procreation_potential",
    )
    assert ANCHOR_BANK_PATH.stat().st_size < 250_000


def test_dense_shadow_is_positive_provenanced_and_replays_exactly():
    text, profile, analysis = _fixture()
    result = compile_dense_shadow_load(text, profile, analysis)

    assert result["status"] == "shadow_only_not_authoritative"
    assert tuple(result["load_signature"]) == CHANNELS
    assert len(result["channel_records"]) == 17
    assert all(0.0 < value <= 1.0 for value in result["load_signature"].values())
    assert all(0.0 < value <= 1.0 for value in result["driver_loads"].values())
    assert all(record["semantic"]["positive_anchor_id"] for record in result["channel_records"])
    assert all(record["semantic"]["contrast_anchor_id"] for record in result["channel_records"])
    assert validate_dense_shadow_load(result, text, profile, analysis) == result


def test_dense_shadow_tamper_and_direction_change_fail_or_change_digest():
    text, profile, analysis = _fixture()
    result = compile_dense_shadow_load(text, profile, analysis)
    tampered = deepcopy(result)
    tampered["load_signature"]["L_rule"] *= 0.5
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_dense_shadow_load(tampered, text, profile, analysis)

    reversed_analysis = deepcopy(analysis)
    reversed_analysis["directed_graph"] = [["release", "requires", "approval"]]
    reversed_result = compile_dense_shadow_load(text, profile, reversed_analysis)
    assert reversed_result["load_signature"] == result["load_signature"]
    assert reversed_result["directed_graph_digest"] != result["directed_graph_digest"]
    assert reversed_result["analysis_digest"] != result["analysis_digest"]


def test_history_features_are_continuous_and_declining_burst_is_not_clamped():
    text, profile, analysis = _fixture()
    analysis["history_metrics"]["combined_similarities"] = [0.95, 0.92, 0.20, 0.18]
    analysis["history_metrics"]["static_distance_from_previous"] = 0.6
    analysis["current_classification_confidence"] = 0.8
    analysis["previous_classification_confidence"] = 0.3
    result = compile_dense_shadow_load(text, profile, analysis)
    records = {row["channel"]: row for row in result["channel_records"]}

    assert records["frequency"]["history_feature"] == pytest.approx(0.5625)
    assert records["burstiness"]["history_feature"] == pytest.approx(0.745)
    assert records["volatility"]["history_feature"] == pytest.approx(0.82)
    assert records["decay"]["history_feature"] == pytest.approx(0.5)
    assert all(record["value"] > 0.0 for record in records.values())


def test_module_is_not_a_preview_or_runtime_mutation_path():
    source = ANCHOR_BANK_PATH.parents[1].joinpath("dense_load17.py").read_text(encoding="utf-8")
    for forbidden in ("engine.step(", "ToMClient.process(", "rgm.read_memory("):
        assert forbidden not in source
