from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

import gateway.tom_gateway as legacy
from gateway.evidence_gateway import EvidenceProjectRuntime, EvidenceTomGateway
from gateway.shadow_retrieval import (
    dense_channel_with_unscored_tail,
    evidence_address,
    evidence_addressed_anchor_snapshot,
    fuse_ranked_channels,
)
from gateway.structural_analysis import (
    CANDIDATE_VERSION,
    PARSER_VERSION,
    SIGNAL_NAMES,
    build_analysis,
    text_digest,
)
from gateway.semantic_chunks import EMBEDDING_DIMENSION
from validation.calibration.wp37_eval_harness import evaluate_external_labels


ROOT = Path(__file__).parents[2]
TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")


def _profile(text: str, axis: int) -> dict:
    from gateway.semantic_chunks import build_semantic_profile

    values = [0.0] * EMBEDDING_DIMENSION
    values[axis] = 1.0
    return build_semantic_profile(
        text,
        [{"start": 0, "end": len(text), "values": values}],
        model="fixture/wp37",
        revision="fixture-v1",
    )


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


class _Provider:
    def __init__(self) -> None:
        self.axes = {
            "evidence anchor": 0,
            "query": 0,
            "zero bearing": 1,
        }

    def analyze(self, text: str) -> dict:
        return {
            "chunk_candidates": [{
                "chunk_index": 0,
                "candidate": _empty_candidate(text),
            }],
            "semantic_profile": _profile(text, self.axes.get(text, 2)),
            "parser_model": {
                "version": PARSER_VERSION,
                "model": "fixture/wp37",
                "revision": "fixture-v1",
            },
        }


def _close(runtime) -> None:
    runtime.library.db.close()


def _leaf_bytes(runtime) -> bytes:
    return json.dumps(
        {
            record_id: getattr(record, "leaf_vec", None)
            for record_id, record in sorted(runtime.rgm.state.anchors.items())
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def _schema_bytes(runtime) -> bytes:
    rows = runtime.library.db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    return json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()


def _mixed_runtime(tmp_path: Path):
    baseline = legacy.TomGateway(tmp_path / "data", TOM_MASTER)
    baseline_runtime = baseline.project("wp37")
    baseline_preview = baseline_runtime.preview_rank("legacy anchor", 10, 2000)
    legacy_commit = baseline_runtime.commit_turn(
        "user", "legacy anchor", "legacy-1",
        activated_branch_ids=baseline_preview["activated_branch_ids"],
    )
    _close(baseline_runtime)

    provider = _Provider()
    shadow = EvidenceTomGateway(
        tmp_path / "data", TOM_MASTER,
        structure_mode="shadow", structure_provider=provider,
    )
    runtime = shadow.project("wp37")
    evidence_preview = runtime.preview_rank("evidence anchor", 10, 2000)
    evidence_commit = runtime.commit_turn(
        "user", "evidence anchor", "evidence-1",
        activated_branch_ids=evidence_preview["activated_branch_ids"],
        structural_analysis=evidence_preview["structural_analysis"],
    )
    return provider, runtime, legacy_commit, evidence_commit


def test_shadow_comparison_is_pure_fallback_explicit_and_serving_exact(tmp_path):
    provider, runtime, legacy_commit, evidence_commit = _mixed_runtime(tmp_path)
    evidence_record = runtime.rgm.state.anchors[evidence_commit["anchor_id"]]
    # WP-37 does not change the WP-36c write path: shadow commit still stores
    # the legacy text projection and only substitutes coordinates in memory.
    assert evidence_record.leaf_vec == list(legacy.project_text("evidence anchor")[1].vector_8d)

    before_tree, before_rgm = runtime.serialized_state_bytes()
    before_tick = runtime.engine.state.tick
    before_commit_count = len(runtime._active_structural_history())
    before_leaves = _leaf_bytes(runtime)
    before_schema = _schema_bytes(runtime)
    expected = None
    for _ in range(100):
        preview = runtime.preview_rank("query", 10, 2000)
        comparison = preview["shadow_retrieval_comparison"]
        encoded = json.dumps(comparison, sort_keys=True, separators=(",", ":"))
        assert encoded == expected or expected is None
        expected = encoded
        assert comparison["address_only_never_force"] is True
        assert comparison["serving_result_unchanged"] is True
        control = legacy.ProjectRuntime.preview_rank(runtime, "query", 10, 2000)
        for field in (
            "triggers", "ranked_anchors", "activated_branch_ids",
            "candidate_trace", "branch_trace", "load_signature",
            "policy_version", "checkpoint_digest",
        ):
            assert preview[field] == control[field]

    after_tree, after_rgm = runtime.serialized_state_bytes()
    assert after_tree == before_tree
    assert after_rgm == before_rgm
    assert runtime.engine.state.tick == before_tick
    assert len(runtime._active_structural_history()) == before_commit_count
    assert _leaf_bytes(runtime) == before_leaves
    assert _schema_bytes(runtime) == before_schema
    evidence = preview["shadow_retrieval_comparison"]["anchor_evidence"]
    assert evidence["with_retained_evidence_ids"] == [evidence_commit["anchor_id"]]
    assert evidence["without_retained_evidence_ids"] == [legacy_commit["anchor_id"]]
    assert evidence["fallback_unrankable_ids"] == []
    assert any(
        value == 0.0
        for value in preview["structural_analysis"]["load_signature"].values()
    )

    _close(runtime)
    restarted = EvidenceTomGateway(
        tmp_path / "data", TOM_MASTER,
        structure_mode="shadow", structure_provider=provider,
    ).project("wp37")
    assert restarted.preview_rank("query", 10, 2000)[
        "shadow_retrieval_comparison"
    ] == preview["shadow_retrieval_comparison"]


def test_anchor_evidence_projection_is_ephemeral_and_never_invents_fallback(tmp_path):
    gateway = EvidenceTomGateway(
        tmp_path / "data", TOM_MASTER,
        structure_mode="shadow", structure_provider=_Provider(),
    )
    load = {
        name: (0.0 if index % 3 == 0 else (index + 1) / 20.0)
        for index, name in enumerate(legacy.project_text("seed")[0].as_dict())
    }
    _, expected = evidence_address(load)
    records = {
        "with": {"leaf_vec": [9.0] * 8},
        "fallback": {"leaf_vec": [0.25] * 8},
        "absent": {"leaf_vec": None},
    }
    original = copy.deepcopy(records)
    snapshot, report = evidence_addressed_anchor_snapshot(records, [{
        "record_id": "with", "commit_key": "commit-1", "tick": 1,
        "analysis_digest": "sha256:evidence", "load_signature": load,
    }])
    assert snapshot["with"]["leaf_vec"] == list(expected)
    assert snapshot["fallback"]["leaf_vec"] == [0.25] * 8
    assert snapshot["absent"]["leaf_vec"] is None
    assert report["fallback_unrankable_ids"] == ["absent"]
    assert records == original
    assert gateway.structure_mode == "shadow"


def test_dense_scored_records_precede_separate_hash_tail_without_scalar_mix():
    records = {record_id: object() for record_id in ("hash-high", "dense-low", "tail")}
    lexical = [("hash-high", 0.99), ("tail", 0.75), ("dense-low", 0.01)]
    structural = [{
        "record_id": "dense-low", "combined_score": 0.02,
        "dense_semantic_score": 0.025, "directed_graph_score": 0.0,
    }]
    result = dense_channel_with_unscored_tail(records, lexical, structural)
    assert [row["id"] for row in result["ranking"]] == [
        "dense-low", "hash-high", "tail",
    ]
    assert [row["id"] for row in result["dense_scored"]] == ["dense-low"]
    assert [row["id"] for row in result["unscored_tail"]] == [
        "hash-high", "tail",
    ]
    assert [row["score_space"] for row in result["ranking"]] == [
        "dense_multivector_plus_directed_graph",
        "hashed_bag_unscored_tail",
        "hashed_bag_unscored_tail",
    ]
    fused = fuse_ranked_channels(result["ranking"], [])
    assert [row["id"] for row in fused] == ["dense-low", "hash-high", "tail"]


def test_wp35_nonzero_guard_precedes_loadsignature_in_preview_and_direct_commit(
    tmp_path, monkeypatch,
):
    from agency.mechanics.sicd_msr_load import LoadSignature

    gateway = EvidenceTomGateway(
        tmp_path / "data", TOM_MASTER,
        structure_mode="authoritative", structure_provider=_Provider(),
    )
    runtime = gateway.project("nonzero")
    before = runtime.serialized_state_bytes()
    before_tick = runtime.engine.state.tick
    before_count = len(runtime._active_structural_history())

    def forbidden(*_args, **_kwargs):
        raise AssertionError("LoadSignature must not be reached")

    monkeypatch.setattr(LoadSignature, "from_mapping", forbidden)
    with pytest.raises(ValueError, match="no synthetic floor"):
        runtime.preview_rank("zero bearing", 10, 2000)
    proposed = _Provider().analyze("zero bearing")
    analysis = build_analysis(
        "zero bearing", proposed["chunk_candidates"],
        proposed["semantic_profile"], proposed["parser_model"], [],
        runtime._current_checkpoint_digest(),
    )
    with pytest.raises(ValueError, match="no synthetic floor"):
        runtime.commit_turn(
            "user", "zero bearing", "direct-zero",
            structural_analysis=analysis,
        )
    assert runtime.serialized_state_bytes() == before
    assert runtime.engine.state.tick == before_tick
    assert len(runtime._active_structural_history()) == before_count


def test_product_default_legacy_is_byte_identical(tmp_path, monkeypatch):
    monkeypatch.delenv("TOM_ASSIST_STRUCTURE_MODE", raising=False)
    gateway = EvidenceTomGateway(tmp_path / "data", TOM_MASTER)
    assert gateway.structure_mode == "legacy"
    runtime = gateway.project("legacy-default")
    expected = legacy.ProjectRuntime.preview_rank(runtime, "unchanged", 10, 2000)
    assert runtime.preview_rank("unchanged", 10, 2000) == expected
    assert "shadow_retrieval_comparison" not in expected


def test_all_shadow_preview_helpers_have_no_forbidden_mutating_calls():
    from gateway import shadow_retrieval

    source = inspect.getsource(EvidenceProjectRuntime.preview_rank) + inspect.getsource(
        shadow_retrieval
    )
    assert ".read_memory(" not in source
    assert ".process(" not in source
    assert ".step(" not in source


def test_external_label_harness_is_only_proved_by_marked_synthetic_fixture():
    fixture_dir = Path(__file__).parent / "fixtures"
    rankings = json.loads(
        (fixture_dir / "wp37_synthetic_rankings.json").read_text(encoding="utf-8")
    )
    labels = json.loads(
        (fixture_dir / "wp37_synthetic_labels.json").read_text(encoding="utf-8")
    )
    assert rankings["label"] == "PLUMBING-ONLY-SYNTHETIC-NOT-EVIDENCE"
    assert labels["label"] == "PLUMBING-ONLY-SYNTHETIC-NOT-EVIDENCE"
    result = evaluate_external_labels(rankings, labels, precision_at=(1, 3))
    assert result["aggregate"]["current"]["mean_reciprocal_rank"] == 0.75
    assert result["aggregate"]["proposed"]["mean_reciprocal_rank"] == pytest.approx(
        2.0 / 3.0
    )
    assert result["aggregate"]["delta_proposed_minus_current"][
        "mean_reciprocal_rank"
    ] == pytest.approx(-1.0 / 12.0)
