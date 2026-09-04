#!/usr/bin/env python3
"""Run the frozen WP-37 label-free retrieval diagnostic."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

import gateway.tom_gateway as legacy_gateway
from gateway.evidence_gateway import EvidenceTomGateway
from gateway.shadow_retrieval import (
    distribution,
    hash_profile_collision_report,
    rank_position_correlation,
)
from gateway.structural_analysis import (
    CANDIDATE_VERSION,
    PARSER_VERSION,
    SIGNAL_NAMES,
    text_digest,
)
from validation.calibration.wp36b_runner import Encoder, MODEL_PATH


ROOT = Path(__file__).resolve().parents[2]
PREREG_PATH = ROOT / "validation" / "calibration" / "WP37_PREREGISTRATION.md"
CORPUS_PATH = ROOT / "validation" / "calibration" / "wp37_shadow_corpus.json"
DEFAULT_OUTPUT = ROOT / "validation" / "runs" / "wp37-shadow-dense-retrieval-v1"
FREEZE_COMMIT = "0449bcd9c1b3607542fbf3de49439d8904011959"
PREREG_SHA256 = "47a62888d31fc2b854c89d0bffdc798333a311c59bafe37982f0a0283987cea1"
CORPUS_SHA256 = "9b4e4c8e263a19d7ea5da1976ca6d81968fffe9192cfcb359ccefd302a9f10c9"
SERVING_FIELDS = (
    "triggers",
    "ranked_anchors",
    "activated_branch_ids",
    "candidate_trace",
    "branch_trace",
    "load_signature",
    "policy_version",
    "checkpoint_digest",
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _candidate(text: str, structure: Mapping[str, Any]) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    orientations: list[dict[str, Any]] = []
    causal_relations: list[dict[str, Any]] = []
    causal = structure.get("causal")
    orientation = structure.get("orientation")
    if causal is not None:
        cause = str(causal["cause"])
        effect = str(causal["effect"])
        entities = [
            {
                "id": "source", "label": cause, "kind": "event",
                "evidence": _span(text, cause), "confidence": 1.0,
            },
            {
                "id": "target", "label": effect, "kind": "outcome",
                "evidence": _span(text, effect), "confidence": 1.0,
            },
        ]
        causal_relations = [{
            "id": "relation", "cause_entity_id": "source",
            "effect_entity_id": "target", "kind": str(causal["kind"]),
            "modality": str(causal.get("modality", "asserted")),
            "negated": bool(causal.get("negated", False)),
            "evidence": _span(text, text), "confidence": 1.0,
        }]
    elif orientation is not None:
        source = str(orientation["source"])
        target = str(orientation["target"])
        entities = [
            {
                "id": "source", "label": source, "kind": "event",
                "evidence": _span(text, source), "confidence": 1.0,
            },
            {
                "id": "target", "label": target, "kind": "outcome",
                "evidence": _span(text, target), "confidence": 1.0,
            },
        ]
        orientations = [{
            "id": "orientation", "source_entity_id": "source",
            "target_entity_id": "target", "kind": str(orientation["kind"]),
            "polarity": str(orientation.get("polarity", "positive")),
            "modality": str(orientation.get("modality", "asserted")),
            "negated": bool(orientation.get("negated", False)),
            "evidence": _span(text, text), "confidence": 1.0,
        }]

    signals = {name: [] for name in SIGNAL_NAMES}
    for name, quotes in structure.get("signals", {}).items():
        if name not in signals:
            raise ValueError(f"unsupported frozen fixture signal: {name}")
        signals[name] = [
            {"evidence": _span(text, str(quote)), "confidence": 1.0}
            for quote in quotes
        ]
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": entities,
        "orientations": orientations,
        "causal_relations": causal_relations,
        "signals": signals,
        "unknown_fields": [],
        "confidence": 1.0,
    }


class FrozenFixtureProvider:
    """Fixture candidate provider with real cached local MiniLM profiles."""

    def __init__(self, corpus: Mapping[str, Any], encoder: Encoder) -> None:
        self.encoder = encoder
        self.entries = {
            str(row["text"]): row
            for group in ("evidence_commits", "queries")
            for row in corpus[group]
        }
        self.cache: dict[str, dict[str, Any]] = {}
        self.profile_build_count = 0

    def analyze(self, text: str) -> dict[str, Any]:
        cached = self.cache.get(text)
        if cached is not None:
            return copy.deepcopy(cached)
        row = self.entries.get(text)
        if row is None:
            raise ValueError(f"text absent from frozen WP-37 corpus: {text}")
        profile = self.encoder.profile(text)
        self.profile_build_count += 1
        result = {
            "chunk_candidates": [{
                "chunk_index": 0,
                "candidate": _candidate(text, row.get("structure", {})),
            }],
            "semantic_profile": profile,
            "parser_model": {
                "version": PARSER_VERSION,
                "model": "fixture/wp37-evidence-candidate",
                "revision": "frozen-corpus-v1",
            },
        }
        self.cache[text] = result
        return copy.deepcopy(result)


def _close_runtime(runtime: Any) -> None:
    runtime.library.db.close()


def _leaf_snapshot(runtime: Any) -> bytes:
    return _canonical_json({
        str(record_id): getattr(record, "leaf_vec", None)
        for record_id, record in sorted(runtime.rgm.state.anchors.items())
    })


def _schema_snapshot(runtime: Any) -> bytes:
    rows = runtime.library.db.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    return _canonical_json(rows)


def _commit_corpus(
    data_dir: Path, corpus: Mapping[str, Any], provider: FrozenFixtureProvider,
) -> tuple[Any, dict[str, Any]]:
    legacy = legacy_gateway.TomGateway(data_dir)
    legacy_runtime = legacy.project("wp37-shadow-corpus")
    legacy_results = []
    for row in corpus["legacy_commits"]:
        preview = legacy_runtime.preview_rank(row["text"], 20, 20_000)
        legacy_results.append(legacy_runtime.commit_turn(
            "user", row["text"], f"wp37-{row['id']}",
            activated_branch_ids=preview["activated_branch_ids"],
        ))
    _close_runtime(legacy_runtime)

    shadow = EvidenceTomGateway(
        data_dir, structure_mode="shadow", structure_provider=provider
    )
    runtime = shadow.project("wp37-shadow-corpus")
    evidence_results = []
    for row in corpus["evidence_commits"]:
        preview = runtime.preview_rank(row["text"], 20, 20_000)
        evidence_results.append(runtime.commit_turn(
            "user", row["text"], f"wp37-{row['id']}",
            activated_branch_ids=preview["activated_branch_ids"],
            structural_analysis=preview["structural_analysis"],
        ))
    return runtime, {
        "legacy_commit_count": len(legacy_results),
        "evidence_commit_count": len(evidence_results),
        "anchor_ids": [
            row["anchor_id"] for row in [*legacy_results, *evidence_results]
        ],
    }


def _serving_control(runtime: Any, text: str, observed: Mapping[str, Any]) -> bool:
    control = legacy_gateway.ProjectRuntime.preview_rank(runtime, text, 20, 20_000)
    return all(observed[field] == control[field] for field in SERVING_FIELDS)


def _query_observation(runtime: Any, row: Mapping[str, Any]) -> dict[str, Any]:
    first = runtime.preview_rank(row["text"], 20, 20_000)
    second = runtime.preview_rank(row["text"], 20, 20_000)
    comparison = first["shadow_retrieval_comparison"]
    if _canonical_json(comparison) != _canonical_json(
        second["shadow_retrieval_comparison"]
    ):
        raise RuntimeError(f"same-process comparison mismatch: {row['id']}")
    if not _serving_control(runtime, row["text"], first):
        raise RuntimeError(f"serving path diverged from control: {row['id']}")
    dense = [
        item for item in comparison["proposed"]["semantic_channel"]
        if item["score_space"] == "dense_multivector_plus_directed_graph"
    ]
    correlation = rank_position_correlation(
        dense, comparison["current"]["semantic_channel"]
    )
    current_fused = comparison["current"]["fused_ranking"]
    proposed_fused = comparison["proposed"]["fused_ranking"]
    return {
        "query_id": row["id"],
        "source_text_sha256": text_digest(row["text"]),
        "comparison": comparison,
        "top_anchor": {
            "current": current_fused[0]["id"] if current_fused else None,
            "proposed": proposed_fused[0]["id"] if proposed_fused else None,
            "changed": (
                (current_fused[0]["id"] if current_fused else None)
                != (proposed_fused[0]["id"] if proposed_fused else None)
            ),
        },
        "dense_vs_hash_rank_correlation": correlation,
        "same_process_repeat_exact": True,
        "serving_control_exact": True,
    }


def _purity_proof(runtime: Any, query: Mapping[str, Any]) -> dict[str, Any]:
    tree_before, rgm_before = runtime.serialized_state_bytes()
    tick_before = int(runtime.engine.state.tick)
    commit_count_before = len(runtime._active_structural_history())
    leaf_before = _leaf_snapshot(runtime)
    schema_before = _schema_snapshot(runtime)
    expected = None
    for _ in range(100):
        preview = runtime.preview_rank(query["text"], 20, 20_000)
        encoded = _canonical_json(preview["shadow_retrieval_comparison"])
        if expected is None:
            expected = encoded
        elif encoded != expected:
            raise RuntimeError("100-repeat comparison is not deterministic")
    tree_after, rgm_after = runtime.serialized_state_bytes()
    result = {
        "repeat_count": 100,
        "comparison_exact": True,
        "engine_bytes_exact": tree_before == tree_after,
        "rgm_bytes_exact": rgm_before == rgm_after,
        "tick_before": tick_before,
        "tick_after": int(runtime.engine.state.tick),
        "structural_commit_count_before": commit_count_before,
        "structural_commit_count_after": len(runtime._active_structural_history()),
        "stored_leaf_vec_bytes_exact": leaf_before == _leaf_snapshot(runtime),
        "library_schema_bytes_exact": schema_before == _schema_snapshot(runtime),
    }
    if not all(value is True for key, value in result.items() if key.endswith("exact")):
        raise RuntimeError("WP-37 purity byte proof failed")
    if result["tick_before"] != result["tick_after"]:
        raise RuntimeError("WP-37 purity tick proof failed")
    if result["structural_commit_count_before"] != result["structural_commit_count_after"]:
        raise RuntimeError("WP-37 purity structural-commit proof failed")
    return result


def _summary(
    observations: list[Mapping[str, Any]], collision: Mapping[str, Any],
) -> dict[str, Any]:
    cohort_deltas = [
        row["comparison"]["cohort_divergence"]["symmetric_difference_count"]
        for row in observations
    ]
    rank_deltas = [
        anchor["absolute_delta"]
        for row in observations
        for anchor in row["comparison"]["rank_divergence"]["per_anchor"]
    ]
    correlations = [
        row["dense_vs_hash_rank_correlation"]
        ["pearson_correlation_of_deterministic_rank_positions"]
        for row in observations
    ]
    nonnull_correlations = [value for value in correlations if value is not None]
    return {
        "interpretation": "LABEL-FREE OBSERVATIONS ONLY; NEITHER RANKING IS CALLED BETTER",
        "query_count": len(observations),
        "cohort_lists_differ_count": sum(
            bool(row["comparison"]["cohort_divergence"]["lists_differ"])
            for row in observations
        ),
        "cohort_symmetric_difference_distribution": distribution(cohort_deltas),
        "top_anchor_changed_count": sum(
            bool(row["top_anchor"]["changed"]) for row in observations
        ),
        "fused_absolute_rank_delta_distribution": distribution(rank_deltas),
        "anchors_with_retained_evidence_distribution": distribution([
            row["comparison"]["anchor_evidence"]["with_retained_evidence_count"]
            for row in observations
        ]),
        "anchors_without_retained_evidence_distribution": distribution([
            row["comparison"]["anchor_evidence"]["without_retained_evidence_count"]
            for row in observations
        ]),
        "hash_profile_collisions": collision,
        "dense_vs_hash_rank_correlations": correlations,
        "dense_vs_hash_rank_correlation_distribution": distribution(
            nonnull_correlations
        ),
        "relevance_labels_used": False,
        "relevance_scores_run": False,
        "g_gate_verdict": None,
    }


def run(output: Path, model: Path) -> dict[str, Any]:
    if _sha256(PREREG_PATH) != PREREG_SHA256:
        raise RuntimeError("WP-37 pre-registration differs from frozen bytes")
    if _sha256(CORPUS_PATH) != CORPUS_SHA256:
        raise RuntimeError("WP-37 corpus differs from frozen bytes")
    freeze_commit = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(PREREG_PATH)],
        cwd=ROOT, text=True,
    ).strip()
    if freeze_commit != FREEZE_COMMIT:
        raise RuntimeError("WP-37 freeze commit mismatch")
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    encoder = Encoder(model)
    provider = FrozenFixtureProvider(corpus, encoder)
    with tempfile.TemporaryDirectory(prefix="tom-assist-wp37-") as temporary:
        data_dir = Path(temporary) / "data"
        runtime, commits = _commit_corpus(data_dir, corpus, provider)
        observations = [
            _query_observation(runtime, row) for row in corpus["queries"]
        ]
        purity = _purity_proof(runtime, corpus["queries"][0])
        collision = hash_profile_collision_report(
            runtime.rgm.vector_store._vectors
        )
        _close_runtime(runtime)

        restarted_gateway = EvidenceTomGateway(
            data_dir, structure_mode="shadow", structure_provider=provider
        )
        restarted = restarted_gateway.project("wp37-shadow-corpus")
        for row, observation in zip(corpus["queries"], observations):
            preview = restarted.preview_rank(row["text"], 20, 20_000)
            if _canonical_json(preview["shadow_retrieval_comparison"]) != _canonical_json(
                observation["comparison"]
            ):
                raise RuntimeError(f"restart comparison mismatch: {row['id']}")
            observation["restart_exact"] = True
        checkpoint = restarted._current_checkpoint_digest()
        tick = int(restarted.engine.state.tick)
        branch_count = len(restarted.engine.state.branches)
        _close_runtime(restarted)

    summary = _summary(observations, collision)
    manifest = {
        "schema_version": "tom-assist-wp37-label-free-run/1.0",
        "status": "OBSERVATIONAL-NOT-A-GATE",
        "freeze_commit": FREEZE_COMMIT,
        "preregistration_sha256": PREREG_SHA256,
        "corpus_sha256": CORPUS_SHA256,
        "code_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "seed_profile": corpus["seed_profile"],
        "tree_tick": tick,
        "tree_branch_count": branch_count,
        "checkpoint_digest": checkpoint,
        "provider_generation_count": 0,
        "local_minilm_profile_build_count": provider.profile_build_count,
        "relevance_labels_used": False,
        "relevance_scores_run": False,
        "commit_inventory": commits,
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "manifest.json").write_bytes(_canonical_json(manifest) + b"\n")
    (output / "observations.json").write_bytes(
        _canonical_json(observations) + b"\n"
    )
    (output / "purity.json").write_bytes(_canonical_json(purity) + b"\n")
    (output / "summary.json").write_bytes(_canonical_json(summary) + b"\n")
    return {"manifest": manifest, "summary": summary, "purity": purity}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.model), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
