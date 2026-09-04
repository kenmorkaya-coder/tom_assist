from __future__ import annotations

import math
import shutil
import time
from pathlib import Path

import pytest

from gateway.tom_gateway import (
    EFFECTIVE_KAPPA_DECAY,
    KAPPA_DECAY_SOURCE,
    SEED_ARTIFACT_RELATIVE,
    SEED_ARTIFACT_SHA256,
    SEED_BRANCH_COUNT,
    SEED_PROFILE,
    SEED_TICK,
    TomGateway,
)

TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")


def test_two_fresh_projects_have_identical_seed_artifacts_and_checkpoint_lineage(
    tmp_path: Path,
) -> None:
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    left = gateway.project("seed-left")
    right = gateway.project("seed-right")

    assert left._tree_path.read_bytes() == right._tree_path.read_bytes()
    assert left._rgm_path.read_bytes() == right._rgm_path.read_bytes()
    assert left._current_checkpoint_digest() == right._current_checkpoint_digest()
    assert left.engine.state.tick == right.engine.state.tick == SEED_TICK
    assert len(left.engine.state.branches) == len(right.engine.state.branches) == SEED_BRANCH_COUNT
    assert not left.rgm.state.anchors
    assert not right.rgm.state.anchors

    parameters = gateway.seed.mechanics_parameters
    assert parameters["TOM_KAPPA_DECAY"] == "0.03"
    for runtime in (left, right):
        assert runtime.engine.cfg.tau1 == float(parameters["TOM_TAU1"])
        assert runtime.engine.cfg.kappa_update.heal_rate == float(parameters["TOM_HEAL_RATE"])
        assert runtime.engine.cfg.kappa_update.damage_rate == float(parameters["TOM_DAMAGE_RATE"])
        assert runtime.engine.cfg.kappa_update.kappa_decay == EFFECTIVE_KAPPA_DECAY == 0.03
        assert runtime.engine.cfg.kappa_update.kappa_decay == float(
            parameters["TOM_KAPPA_DECAY"]
        )
        assert runtime.engine.cfg.kappa_update.kappa_delta_cap == float(
            parameters["TOM_KAPPA_DELTA_CAP"]
        )
        assert runtime.engine.cfg.kappa_update.kappa_nourish_recovery == float(
            parameters["TOM_KAPPA_NOURISH_RECOVERY"]
        )

    for runtime in (left, right):
        metadata = runtime.creation_metadata
        assert metadata["seed_profile"] == SEED_PROFILE
        assert metadata["seed_artifact_sha256"] == SEED_ARTIFACT_SHA256
        assert metadata["seed_tick"] == SEED_TICK
        assert metadata["seed_branch_count"] == SEED_BRANCH_COUNT
        assert metadata["kappa_decay_source"] == KAPPA_DECAY_SOURCE
        assert metadata["initial_checkpoint_digest"] == runtime._current_checkpoint_digest()
        assert runtime._creation_metadata_path.is_file()


def test_corrupted_seed_copy_fails_project_creation_closed(tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted-seed.json"
    shutil.copyfile(TOM_MASTER / SEED_ARTIFACT_RELATIVE, corrupted)
    with corrupted.open("r+b") as handle:
        handle.seek(-1, 2)
        final = handle.read(1)
        handle.seek(-1, 2)
        handle.write(b"0" if final != b"0" else b"1")

    with pytest.raises(ValueError, match="document Tree seed digest mismatch"):
        TomGateway(tmp_path / "data", TOM_MASTER, seed_artifact=corrupted)
    assert not (tmp_path / "data" / "projects" / "must-fail-closed" / "tom" / "tree_state.json").exists()


@pytest.mark.parametrize("unreviewed_decay", ["0.053193359375", "nan", "inf"])
def test_kappa_profile_divergence_refuses_project_creation(tmp_path, unreviewed_decay):
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    gateway.seed.mechanics_parameters["TOM_KAPPA_DECAY"] = unreviewed_decay
    with pytest.raises(ValueError, match="kappa_decay differs from audited effective physics"):
        gateway.project("unreviewed-physics")
    assert not (tmp_path / "data/projects/unreviewed-physics/tom/tree_state.json").exists()


def test_seeded_preview_latency_guard(tmp_path: Path) -> None:
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    runtime = gateway.project("latency-project")
    runtime.preview_rank("warm the deterministic query path", 10, 2000)

    durations_ms = []
    for index in range(20):
        started = time.perf_counter()
        runtime.preview_rank(f"latency draft {index}", 10, 2000)
        durations_ms.append((time.perf_counter() - started) * 1000.0)
    ordered = sorted(durations_ms)
    p95_ms = ordered[math.ceil(0.95 * len(ordered)) - 1]
    print(
        f"seeded_preview_latency_ms p50={ordered[len(ordered) // 2]:.3f} "
        f"p95={p95_ms:.3f} max={max(ordered):.3f}"
    )
    assert p95_ms < 500.0
