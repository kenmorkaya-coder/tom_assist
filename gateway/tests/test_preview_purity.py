from __future__ import annotations

import inspect
from pathlib import Path

from gateway.tom_gateway import PINNED_SHA, SEED_BRANCH_COUNT, SEED_TICK, ProjectRuntime, TomGateway

TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")


def seeded_gateway(tmp_path: Path) -> tuple[TomGateway, ProjectRuntime]:
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    assert gateway.runtime_sha.startswith(PINNED_SHA)
    runtime = gateway.project("purity-project")
    assert runtime.engine.state.tick == SEED_TICK
    assert len(runtime.engine.state.branches) == SEED_BRANCH_COUNT
    turns = [
        "Keep all project processing local and deterministic.",
        "Use explicit state authority and preserve prior decisions.",
        "Preview ranking must never mutate the committed substrate.",
    ]
    for index, text in enumerate(turns):
        result = runtime.commit_turn("user", text, f"seed-{index}")
        assert result["engine_tick_after"] == SEED_TICK + index + 1
        assert result["anchor_id"] != "deferred"
    return gateway, runtime


def test_preview_path_has_no_forbidden_calls() -> None:
    source = inspect.getsource(ProjectRuntime.preview_rank)
    assert ".read_memory(" not in source
    assert ".process(" not in source
    assert ".step(" not in source


def test_one_hundred_mixed_previews_are_byte_pure(tmp_path: Path, monkeypatch) -> None:
    _gateway, runtime = seeded_gateway(tmp_path)
    before_tree, before_rgm = runtime.serialized_state_bytes()
    before_tick = runtime.rgm.state.current_tick
    before_engine_tick = runtime.engine.state.tick
    before_library = list(runtime.library.db.iterdump())

    def forbidden(*_args, **_kwargs):
        raise AssertionError("a forbidden mutating surface was reached by preview")

    runtime.rgm.read_memory = forbidden
    runtime.engine.step = forbidden
    runtime.engine.apply_leaf_vec_update = forbidden
    import agency.mechanics.leaf_vectors as leaf_vectors
    monkeypatch.setattr(leaf_vectors, "select_activated_branches", forbidden)
    drafts = ["connected beam column load path", "rule contradiction equations", "first then after stage sequence"]
    for index in range(100):
        result = runtime.preview_rank(
            f"{drafts[index % 3]} draft {index % 13}",
            1 + (index % 10),
            80 + (index % 17) * 37,
        )
        assert result["activation_id"].startswith("sha256:")
        assert len(result["activated_branch_ids"]) == 16
        assert any(row["structural_rank"] is not None for row in result["candidate_trace"])
        assert result["policy_version"] == "context-policy/1.3"

    after_tree, after_rgm = runtime.serialized_state_bytes()
    assert after_tree == before_tree
    assert after_rgm == before_rgm
    assert runtime.rgm.state.current_tick == before_tick
    assert runtime.engine.state.tick == before_engine_tick
    assert list(runtime.library.db.iterdump()) == before_library


def test_identical_preview_is_deterministic_across_runtime_restart(tmp_path: Path) -> None:
    gateway, runtime = seeded_gateway(tmp_path)
    expected = runtime.preview_rank("Which local-only constraint applies?", 10, 2000)
    del runtime
    del gateway

    restarted = TomGateway(tmp_path / "data", TOM_MASTER)
    actual = restarted.project("purity-project").preview_rank(
        "Which local-only constraint applies?", 10, 2000
    )
    assert actual == expected
