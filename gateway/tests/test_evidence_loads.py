from __future__ import annotations

from copy import deepcopy
import json
import sqlite3

import pytest

from gateway.structural_analysis import (
    CANDIDATE_VERSION,
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
    PARSER_VERSION,
    build_analysis,
    directed_graph_fingerprint,
    directed_graph_similarity,
    text_digest,
    validate_candidate,
    validate_frozen_analysis,
)
from gateway.evidence_gateway import EvidenceProjectRuntime, EvidenceTomGateway as TomGateway
from gateway.runtime_archive import export_snapshot, validate_snapshot
from gateway.structure_provider import isolated_worker_environment


def _span(text: str, quote: str, occurrence: int = 0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _fact(text: str, quote: str, confidence=1.0):
    return {"evidence": _span(text, quote), "confidence": confidence}


def _candidate(
    text: str,
    *,
    cause="A",
    effect="B",
    kind="causes",
    negated=False,
    memory=False,
    contradiction=False,
):
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [
            {"id": "entity_a", "label": "A", "kind": "event", "evidence": _span(text, "A"), "confidence": 1.0},
            {"id": "entity_b", "label": "B", "kind": "outcome", "evidence": _span(text, "B"), "confidence": 1.0},
        ],
        "orientations": [],
        "causal_relations": [{
            "id": "cause_1",
            "cause_entity_id": "entity_a" if cause == "A" else "entity_b",
            "effect_entity_id": "entity_b" if effect == "B" else "entity_a",
            "kind": kind,
            "modality": "asserted",
            "negated": negated,
            "evidence": _span(text, text),
            "confidence": 1.0,
        }],
        "signals": {
            "rules": [],
            "contradictions": [_fact(text, text)] if contradiction else [],
            "inferences": [],
            "sequences": [_fact(text, text)],
            "memory_references": [_fact(text, text)] if memory else [],
            "future_references": [],
            "completions": [],
            "rejections": [],
        },
        "unknown_fields": [],
        "confidence": 1.0,
    }


def _vector(axis=0):
    values = [0.0] * EMBEDDING_DIMENSION
    values[axis] = 1.0
    return {
        "version": EMBEDDING_VERSION,
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "revision": "fixture",
        "dimension": EMBEDDING_DIMENSION,
        "values": values,
    }


def _parser():
    return {
        "version": PARSER_VERSION,
        "model": "local/gemma-fixture",
        "revision": "fixture-revision",
    }


class _Provider:
    def __init__(self):
        self.calls = []

    def analyze(self, text):
        self.calls.append(text)
        if text == "A causes B.":
            return {
                "candidate": _candidate(text), "semantic_vector": _vector(0),
                "parser_model": _parser(),
            }
        if text == "B causes A.":
            return {
                "candidate": _candidate(text, cause="B", effect="A"),
                "semantic_vector": _vector(1),
                "parser_model": _parser(),
            }
        if text == "A prevents B.":
            return {
                "candidate": _candidate(text, kind="prevents", contradiction=True),
                "semantic_vector": _vector(2),
                "parser_model": _parser(),
            }
        raise AssertionError(f"unexpected fixture text: {text}")


def test_causal_direction_is_preserved_not_collapsed_into_magnitude():
    forward_text, reverse_text = "A causes B.", "B causes A."
    forward = validate_candidate(_candidate(forward_text), forward_text)
    reverse = validate_candidate(
        _candidate(reverse_text, cause="B", effect="A"), reverse_text
    )
    assert directed_graph_fingerprint(forward) != directed_graph_fingerprint(reverse)
    assert directed_graph_similarity(forward, reverse) == 0.0
    assert directed_graph_fingerprint(forward)[0][2:4] == ["a", "b"]
    assert directed_graph_fingerprint(reverse)[0][2:4] == ["b", "a"]


def test_orientation_direction_is_preserved_separately_from_load_magnitude():
    text = "A supports B."
    forward = _candidate(text)
    forward["causal_relations"] = []
    forward["orientations"] = [{
        "id": "orientation_1",
        "source_entity_id": "entity_a",
        "target_entity_id": "entity_b",
        "kind": "supports",
        "polarity": "positive",
        "modality": "asserted",
        "negated": False,
        "evidence": _span(text, text),
        "confidence": 1.0,
    }]
    reverse = deepcopy(forward)
    reverse["orientations"][0]["source_entity_id"] = "entity_b"
    reverse["orientations"][0]["target_entity_id"] = "entity_a"
    validated_forward = validate_candidate(forward, text)
    validated_reverse = validate_candidate(reverse, text)
    assert directed_graph_fingerprint(validated_forward)[0][2:4] == ["a", "b"]
    assert directed_graph_fingerprint(validated_reverse)[0][2:4] == ["b", "a"]
    assert directed_graph_similarity(validated_forward, validated_reverse) == 0.0


def test_exact_evidence_binding_and_endpoint_validation_fail_closed():
    text = "A causes B."
    bad_quote = _candidate(text)
    bad_quote["causal_relations"][0]["evidence"]["quote"] = "B causes A."
    with pytest.raises(ValueError, match="quote does not exactly match"):
        validate_candidate(bad_quote, text)
    bad_endpoint = _candidate(text)
    bad_endpoint["causal_relations"][0]["effect_entity_id"] = "missing"
    with pytest.raises(ValueError, match="invalid cause-to-effect endpoints"):
        validate_candidate(bad_endpoint, text)
    extra_load = _candidate(text)
    extra_load["load_signature"] = {"S_entity": 1.0}
    with pytest.raises(ValueError, match="extra=.*load_signature"):
        validate_candidate(extra_load, text)


def test_history_dynamics_are_distinct_and_replay_exactly():
    text = "A causes B."
    first = build_analysis(
        text, _candidate(text), _vector(0), _parser(), [], "checkpoint-0"
    )
    assert first["load_signature"]["novelty"] == 1.0
    assert first["load_signature"]["decay"] == 1.0
    assert first["load_signature"]["frequency"] == 0.0
    assert first["load_signature"]["recurrence"] == 0.0
    history = [{
        "record_id": "turn-1",
        "candidate": first["candidate"],
        "semantic_vector": first["semantic_vector"],
        "static_load": first["static_load"],
    }]
    repeated = build_analysis(
        text, _candidate(text, memory=True), _vector(0), _parser(), history, "checkpoint-1"
    )
    load = repeated["load_signature"]
    assert load["recurrence"] == 1.0
    assert load["frequency"] == 1.0
    assert load["persistence"] == 1.0
    assert load["novelty"] == 0.0
    assert load["decay"] == 0.0
    assert load["T_memory"] > first["load_signature"]["T_memory"]
    assert validate_frozen_analysis(repeated, text, history, "checkpoint-1") == repeated
    tampered = deepcopy(repeated)
    tampered["load_signature"]["frequency"] = 0.25
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_frozen_analysis(tampered, text, history, "checkpoint-1")

    mixed_history = [
        history[0],
        {
            "record_id": "turn-2",
            "candidate": first["candidate"],
            "semantic_vector": _vector(1),
            "static_load": first["static_load"],
        },
    ]
    mixed = build_analysis(
        text, _candidate(text), _vector(0), _parser(), mixed_history, "checkpoint-2"
    )
    assert mixed["load_signature"]["recurrence"] == 1.0
    assert mixed["load_signature"]["frequency"] == 0.5
    assert mixed["load_signature"]["frequency"] != mixed["load_signature"]["recurrence"]
    assert mixed["load_signature"]["persistence"] == 0.0
    assert mixed["load_signature"]["decay"] > 0.0


def test_structural_evidence_activates_dimensions_without_keyword_wheel():
    text = "A prevents B."
    analysis = build_analysis(
        text, _candidate(text, kind="prevents", contradiction=True), _vector(0),
        _parser(), [], "checkpoint"
    )
    load = analysis["load_signature"]
    for channel in (
        "S_entity", "S_dependency", "S_topology", "L_contradiction",
        "L_inference", "T_sequence", "threat_amplitude", "novelty", "decay",
    ):
        assert load[channel] > 0.0, channel
    assert load["frequency"] != load["recurrence"] or load["frequency"] == 0.0


def test_authoritative_gateway_binds_preview_to_commit_and_restart(tmp_path):
    provider = _Provider()
    gateway = TomGateway(
        tmp_path, structure_mode="authoritative", structure_provider=provider
    )
    runtime = gateway.project("evidence-load")
    before = runtime.serialized_state_bytes()
    before_library = runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0]
    previews = [runtime.preview_rank("A causes B.", 10, 2000) for _ in range(100)]
    preview = previews[0]
    assert all(item == preview for item in previews)
    assert runtime.serialized_state_bytes() == before
    assert runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0] == before_library
    assert preview["structural_load_mode"] == "authoritative"
    assert preview["structural_analysis"]["load_signature"] == preview["load_signature"]
    assert preview["structural_analysis"]["parser_model"] == _parser()
    result = runtime.commit_turn(
        "user", "A causes B.", "turn-1",
        activated_branch_ids=preview["activated_branch_ids"],
        structural_analysis=preview["structural_analysis"],
    )
    assert result["structural_load"]["mode"] == "authoritative"
    assert result["structural_load"]["causal_relation_count"] == 1
    assert result["commit_drive"]["plan"]["load_signature_17"] == preview["load_signature"]
    assert len(result["commit_drive"]["plan"]["driver_vec"]) == 3
    assert any(value > 0.0 for value in result["commit_drive"]["plan"]["driver_vec"])
    assert len(result["commit_drive"]["plan"]["routing_basis_8d"]) == 8
    assert runtime.library.structural_analysis("turn-1") == preview["structural_analysis"]

    archive = tmp_path / "runtime-archive"
    export_snapshot(gateway, "evidence-load", archive)
    validate_snapshot(gateway, archive)
    with sqlite3.connect(archive / "library.sqlite3") as database:
        archived = json.loads(database.execute(
            "SELECT analysis_json FROM structural_commits WHERE commit_key='turn-1'"
        ).fetchone()[0])
    assert archived == preview["structural_analysis"]

    restarted = TomGateway(
        tmp_path, structure_mode="authoritative", structure_provider=provider
    ).project("evidence-load")
    second = restarted.preview_rank("A causes B.", 10, 2000)
    assert second["structural_analysis"]["history_metrics"]["history_count"] == 1
    assert second["structural_analysis"]["load_signature"]["recurrence"] == 1.0
    assert second["shadow_structural_retrieval"][0]["record_id"] == result["anchor_id"]

    stale = second["structural_analysis"]
    reverse = restarted.preview_rank("B causes A.", 10, 2000)
    restarted.commit_turn(
        "user", "B causes A.", "turn-2",
        activated_branch_ids=reverse["activated_branch_ids"],
        structural_analysis=reverse["structural_analysis"],
    )
    with pytest.raises(ValueError, match="stale; prepare again"):
        restarted.commit_turn("user", "A causes B.", "turn-stale", structural_analysis=stale)


def test_canonical_commit_reports_17d_tsp_and_routing_values(tmp_path):
    provider = _Provider()
    runtime = TomGateway(
        tmp_path, structure_mode="authoritative", structure_provider=provider
    ).project("telemetry")
    assert __import__("os").environ["TOM_FEELING_WHEEL_ENABLED"] == "0"
    preview = runtime.preview_rank("A prevents B.", 10, 2000)
    result = runtime.commit_turn(
        "user", "A prevents B.", "turn-1",
        activated_branch_ids=preview["activated_branch_ids"],
        structural_analysis=preview["structural_analysis"],
    )
    plan = result["commit_drive"]["plan"]
    assert len(plan["load_signature_17"]) == 17
    assert all(value > 0.0 for value in plan["driver_vec"]), "T/S/P must all be evidenced"
    assert len(plan["semantic_target"]) == 3
    assert len(plan["routing_basis_8d"]) == 8
    assert plan["routing_basis_confidence"] > 0.0
    assert plan["wind_magnitude"] > 0.0


def test_structure_path_contains_no_emotion_lexicon_import():
    root = __import__("pathlib").Path(__file__).parents[1]
    for name in (
        "structural_analysis.py", "structure_provider.py", "structure_worker.py",
        "gemma_structure_worker.py",
    ):
        source = (root / name).read_text(encoding="utf-8").casefold()
        assert "agency.excitation.feeling_wheel" not in source
        assert "feeling_wheel_mapper" not in source
        assert "emotion_wheel" not in source


def test_local_model_environment_is_offline_and_credential_free(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross")
    monkeypatch.setenv("HF_TOKEN", "must-not-cross")
    monkeypatch.setenv("TOM_ASSIST_OAUTH_BROKER_SOCKET", "/must/not/cross")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-cross")
    environment = isolated_worker_environment()
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TOM_FEELING_WHEEL_ENABLED"] == "0"
    assert not any("must-not-cross" in value for value in environment.values())


def test_evidence_preview_contains_no_forbidden_runtime_mutation_calls():
    import inspect

    source = inspect.getsource(EvidenceProjectRuntime.preview_rank)
    for forbidden in ("rgm.read_memory", "ToMClient.process", "engine.step"):
        assert forbidden not in source
