from __future__ import annotations

from copy import deepcopy
import hashlib
import json

import pytest

from gateway.dense_load17 import (
    ANCHOR_BANK_PATH,
    HISTORY_EVIDENCE_CHANNELS,
    compile_dense_shadow_load,
    derive_driver_evidence,
    load_anchor_bank,
    validate_dense_shadow_load,
)
import gateway.dense_load17 as dense_module
from gateway.semantic_chunks import build_semantic_profile
from gateway.structural_analysis import CANDIDATE_VERSION, CHANNELS, SIGNAL_NAMES, text_digest


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


def test_anchor_cosine_precomputation_is_exactly_equivalent_to_original_formula():
    text, profile, _ = _fixture()
    bank = load_anchor_bank()

    def original(family):
        names = dense_module.CHANNELS if family == "channels" else dense_module.DRIVERS
        chunks = profile["chunks"]
        beta = bank["formula"]["absolute_beta"]
        temperature = bank["formula"]["contrast_temperature"]
        measurements = {}
        for name in names:
            candidates = []
            for chunk in chunks:
                vector = chunk["values"]
                positives = [
                    (dense_module._cosine(vector, anchor["vector"]), anchor)
                    for anchor in bank[family][name]
                ]
                positive_cosine, positive_anchor = max(
                    positives, key=lambda item: (item[0], item[1]["anchor_id"])
                )
                contrasts = [
                    (dense_module._cosine(vector, anchor["vector"]), anchor)
                    for other in names if other != name
                    for anchor in bank[family][other]
                ]
                contrast_cosine, contrast_anchor = max(
                    contrasts, key=lambda item: (item[0], item[1]["anchor_id"])
                )
                absolute = dense_module.math.exp(-beta * (1.0 - positive_cosine))
                specificity = dense_module._sigmoid(
                    (positive_cosine - contrast_cosine) / temperature
                )
                candidates.append({
                    "value": absolute * specificity,
                    "absolute_resonance": absolute,
                    "contrast_specificity": specificity,
                    "positive_cosine": positive_cosine,
                    "contrast_cosine": contrast_cosine,
                    "positive_anchor_id": positive_anchor["anchor_id"],
                    "positive_anchor_sha256": positive_anchor["text_sha256"],
                    "contrast_anchor_id": contrast_anchor["anchor_id"],
                    "contrast_anchor_sha256": contrast_anchor["text_sha256"],
                    "chunk_index": int(chunk["index"]),
                    "start": int(chunk["start"]),
                    "end": int(chunk["end"]),
                    "chunk_text_sha256": chunk["text_sha256"],
                })
            measurements[name] = max(
                candidates, key=lambda item: (item["value"], -item["chunk_index"])
            )
        return measurements

    for family in ("channels", "drivers"):
        assert dense_module._semantic_measurements(
            text, profile, bank, family,
        ) == original(family)


def test_missing_history_never_falls_through_to_legacy_dynamic_defaults():
    text, profile, analysis = _fixture()
    analysis["load_signature"]["novelty"] = 1.0
    analysis["load_signature"]["decay"] = 1.0
    result = compile_dense_shadow_load(text, profile, analysis)
    records = {row["channel"]: row for row in result["channel_records"]}

    for channel in HISTORY_EVIDENCE_CHANNELS:
        assert records[channel]["combined_evidence"] is None
        assert records[channel]["value"] == records[channel]["semantic"]["value"]
        assert records[channel]["value"] < 1.0


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


def test_driver_evidence_is_compiled_from_exact_candidate_quotes_and_cannot_be_overridden():
    text, profile, analysis = _fixture()
    text = "The report rejects the unsafe path and records that the repair is complete."

    def span(quote):
        start = text.index(quote)
        return {"start": start, "end": start + len(quote), "quote": quote}

    signals = {name: [] for name in SIGNAL_NAMES}
    signals["rejections"] = [{
        "evidence": span("rejects the unsafe path"), "confidence": 0.91,
    }]
    signals["completions"] = [{
        "evidence": span("repair is complete"), "confidence": 0.86,
    }]
    candidate = {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [],
        "orientations": [],
        "causal_relations": [],
        "signals": signals,
        "unknown_fields": [],
        "confidence": 1.0,
    }
    direct = derive_driver_evidence(text, candidate)
    assert direct["threat_load"]["value"] == 0.91
    assert direct["sustenance_potential"]["value"] == 0.86
    assert direct["procreation_potential"] == {"value": 0.0, "support": []}
    assert direct["threat_load"]["support"][0]["quote"] == "rejects the unsafe path"

    analysis["candidate"] = candidate
    analysis["load_signature"] = {name: 0.0 for name in CHANNELS}
    bank = load_anchor_bank()
    vector = list(bank["drivers"]["threat_load"][0]["vector"])
    profile = build_semantic_profile(
        text,
        [{"start": 0, "end": len(text), "values": vector}],
        model=bank["embedding_model"], revision=bank["embedding_revision"],
    )
    result = compile_dense_shadow_load(text, profile, analysis)
    records = {row["driver"]: row for row in result["driver_records"]}
    assert records["threat_load"]["direct_evidence"] == 0.91
    assert len(records["threat_load"]["direct_support"]) == 1

    analysis["driver_evidence"] = {"threat_load": 1.0}
    with pytest.raises(ValueError, match="numeric driver_evidence overrides are not accepted"):
        compile_dense_shadow_load(text, profile, analysis)


def test_contradiction_and_inference_corroboration_requires_exact_structural_span():
    text, profile, analysis = _fixture()
    quote = "deterministic semantic fixture"
    start = text.index(quote)
    analysis["load_signature"]["L_inference"] = 0.7
    analysis["channel_records"] = [{
        "channel": "L_inference",
        "support": [{
            "kind": "span", "path": "signals.inferences[0].evidence",
            "start": start, "end": start + len(quote), "quote": quote,
            "confidence": 0.9,
        }],
    }]
    result = compile_dense_shadow_load(text, profile, analysis)
    assert result["structural_corroboration"]["L_inference"]["present"] is True
    assert result["structural_corroboration"]["L_contradiction"]["present"] is False

    analysis["channel_records"][0]["support"][0]["quote"] = "wrong"
    with pytest.raises(ValueError, match="is not exact"):
        compile_dense_shadow_load(text, profile, analysis)


def test_module_is_not_a_preview_or_runtime_mutation_path():
    source = ANCHOR_BANK_PATH.parents[1].joinpath("dense_load17.py").read_text(encoding="utf-8")
    for forbidden in ("engine.step(", "ToMClient.process(", "rgm.read_memory("):
        assert forbidden not in source
