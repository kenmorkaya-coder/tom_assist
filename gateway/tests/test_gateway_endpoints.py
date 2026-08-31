from __future__ import annotations

import json
from pathlib import Path

from gateway.tom_gateway import (
    KAPPA_DECAY_SOURCE,
    PINNED_SHA,
    SEED_ARTIFACT_SHA256,
    SEED_PROFILE,
    SEED_TICK,
    TomGateway,
    canonical_digest,
    canonical_json,
)

TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")


def test_capabilities_and_verifiers_are_honest_and_deterministic(tmp_path: Path) -> None:
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    health_status, health = gateway.handle("GET", "/health")
    assert health_status == 200
    assert health["pinned_sha_match"] is True
    assert health["runtime_version"].startswith(PINNED_SHA)

    status, capabilities = gateway.handle("GET", "/capabilities")
    assert status == 200
    assert capabilities["supports_readonly_ranking"] is True
    assert capabilities["supports_checkpoint_restore"] is True
    assert capabilities["supports_nonmutating_load_preview"] is False
    assert capabilities["seed_profile"] == SEED_PROFILE
    assert capabilities["seed_artifact_sha256"] == SEED_ARTIFACT_SHA256
    assert capabilities["seed_tick"] == SEED_TICK
    assert capabilities["seed_branch_count"] == 10_000
    assert capabilities["mechanics_parameters"]["TOM_TAU1"] == "4.0"
    assert capabilities["mechanics_parameters"]["TOM_KAPPA_DECAY"] == "0.03"
    assert capabilities["kappa_decay_source"] == KAPPA_DECAY_SOURCE

    status, drift = gateway.handle(
        "POST",
        "/verify/drift",
        {
            "answer_text": "Upload all state to a public service.",
            "invariants": [
                {
                    "id": "constraint-local",
                    "description": "State stays local",
                    "contradict_patterns": ["upload all state"],
                }
            ],
        },
    )
    assert status == 200
    assert drift["decision"] == "block"
    assert drift["residual_components"]["R_contradiction"] == 1.0

    status, claims = gateway.handle(
        "POST",
        "/verify/claims",
        {
            "claims": ["SQLite uses write ahead logging"],
            "corpus_chunks": [
                {"id": "chunk-1", "source": "spec", "text": "SQLite uses write ahead logging for the local event store."}
            ],
        },
    )
    assert status == 200
    assert claims["supported_count"] == 1

    status, structure = gateway.handle(
        "POST",
        "/adjudicate/structure",
        {
            "proposal": {"selected_operator": "implement", "constraints_checked": ["local-only"]},
            "expected": {"expected_operator": "implement", "required_constraints": ["local-only"]},
        },
    )
    assert status == 200
    assert structure["accepted"] is True


def test_commit_idempotency_checkpoint_and_restore(tmp_path: Path) -> None:
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    runtime = gateway.project("checkpoint-project")
    initial_digest = runtime._current_checkpoint_digest()
    assert runtime.engine.state.tick == SEED_TICK
    first = runtime.commit_turn("user", "First committed turn", "turn-1")
    duplicate = runtime.commit_turn("user", "ignored duplicate text", "turn-1")
    assert duplicate == first
    assert first["engine_tick_before"] == SEED_TICK
    assert first["engine_tick_after"] == SEED_TICK + 1
    assert first["prior_checkpoint_digest"] == initial_digest
    assert first["seed_checkpoint_digest"] == initial_digest
    assert first["checkpoint_digest"] != initial_digest
    assert runtime.engine.state.tick == SEED_TICK + 1

    checkpoint = runtime.save_checkpoint()
    runtime.commit_turn("assistant", "Second committed turn", "turn-2")
    assert runtime.engine.state.tick == SEED_TICK + 2
    restored = runtime.restore_checkpoint(checkpoint["checkpoint_id"])
    assert restored["digest"] == checkpoint["digest"]
    assert runtime.engine.state.tick == SEED_TICK + 1
    assert runtime._current_checkpoint_digest() == checkpoint["digest"]


def test_python_canonical_digest_matches_shared_fixture() -> None:
    fixture_path = Path(__file__).parents[2] / "tests" / "fixtures" / "protocol" / "canonical_digest.json"
    fixture = json.loads(fixture_path.read_text())
    assert canonical_json(fixture["value"]).decode() == fixture["canonical_json"]
    assert canonical_digest(fixture["value"]) == fixture["digest"]
