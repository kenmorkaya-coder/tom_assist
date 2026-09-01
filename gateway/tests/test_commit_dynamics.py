from copy import deepcopy

import pytest

from gateway.tom_gateway import TomGateway, COMMIT_DYNAMICS
from gateway.permanent_library import content_hash


def test_exchange_teaches_rotates_reseats_exactly_once_and_survives_restart(tmp_path):
    gateway = TomGateway(tmp_path)
    runtime = gateway.project("experience")
    used = runtime.commit_turn("user", "A local beam connects two columns", "seed-used")["anchor_id"]
    unused = runtime.commit_turn("user", "A rule requires explicit approval", "seed-unused")["anchor_id"]
    runtime.rgm.state.anchors[used].anchor_strength = 0.5
    runtime.rgm.state.anchors[unused].anchor_strength = 0.5
    runtime.save_checkpoint()
    preview = runtime.preview_rank("connected beam column load path", 10, 2000)
    serving = preview["activated_branch_ids"]
    usage = {bid: b.usage_count for bid, b in runtime.engine.state.branches.items()}
    vectors = {bid: deepcopy(b.sem_vec) for bid, b in runtime.engine.state.branches.items()}
    result = runtime.commit_turn("user", "Inspect this beam", "exchange", response_text="The connected beam transfers force to each column.",
                                 activated_branch_ids=serving, admitted_anchor_ids=[used], packet_digest="sent-packet")
    assert result["commit_dynamics"] == COMMIT_DYNAMICS
    assert result["taught"] and result["teach_reason"] == "committed_response"
    assert runtime.engine.state.last_leaf_vec_update_tick == result["engine_tick_after"]
    assert any(b.sem_vec != vectors[bid] for bid, b in runtime.engine.state.branches.items() if bid in vectors)
    for bid, branch in runtime.engine.state.branches.items():
        assert branch.usage_count == usage.get(bid, 0) + int(bid in serving)
    assert runtime.rgm.state.anchors[used].anchor_strength == 0.5 + 0.05 - 0.002
    assert runtime.rgm.state.anchors[used].access_count == 1
    assert runtime.rgm.state.anchors[unused].anchor_strength < 0.5
    assert runtime.rgm.state.anchors[unused].access_count == 0
    state = runtime.serialized_state_bytes()
    assert runtime.commit_turn("user", "ignored replay", "exchange") == result
    assert runtime.serialized_state_bytes() == state
    restarted = TomGateway(tmp_path).project("experience")
    assert restarted.commit_turn("user", "ignored restart replay", "exchange") == result
    assert restarted.serialized_state_bytes() == state


def test_commit_drive_is_the_pinned_17_channel_routing_application(tmp_path):
    runtime = TomGateway(tmp_path).project("canonical-drive")
    text = "First inspect the beam dependency, then preserve the rejected cloud path."
    from agency.mechanics.sicd_msr_load_application import project_msr_load_to_sicd_step
    from gateway.structural_preview import project_text

    signature = project_text(text)[0]
    expected = project_msr_load_to_sicd_step(signature).as_dict()
    result = runtime.commit_turn("user", text, "canonical-17d")

    assert result["commit_drive"]["source"] == "tom_assist_committed_exchange"
    assert result["commit_drive"]["applied"] is True
    assert result["commit_drive"]["plan"] == expected
    assert tuple(runtime.engine.state.last_semantic_routing_basis_8d) == tuple(expected["routing_basis_8d"])
    assert result["engine_tick_after"] == result["engine_tick_before"] + 1


def test_conflict_dismissal_skips_teaching_only_when_configured(tmp_path, monkeypatch):
    runtime = TomGateway(tmp_path).project("conflict")
    runtime.update_settings({"teach_on_conflict": False})
    from agency.mechanics.sicd_engine import TreeGrowthEngine
    original = TreeGrowthEngine.apply_leaf_vec_update
    calls = []

    def teach(engine, payload):
        calls.append(payload)
        return original(engine, payload)

    monkeypatch.setattr(TreeGrowthEngine, "apply_leaf_vec_update", teach)
    result = runtime.commit_turn("user", "beam", "dismissed", response_text="beam column connection", conflict_dismissed=True)
    assert not calls and not result["taught"]
    assert result["teach_reason"] == "conflict_dismissed_policy"
    runtime.update_settings({"teach_on_conflict": True})
    runtime.commit_turn("user", "beam", "allowed", response_text="beam column connection", conflict_dismissed=True)
    assert len(calls) == 1
    assert set(calls[0]) == {"semantic_axis", "loads", "confidence"}
    assert set(calls[0]["loads"]) == {"delta_x", "delta_F", "phi", "intensity"}


@pytest.mark.parametrize("phase", ["step", "write", "teach", "rotate", "reseat", "journal"])
def test_phase_failure_rolls_back_the_whole_quintuple(tmp_path, monkeypatch, phase):
    runtime = TomGateway(tmp_path).project("rollback")
    before = runtime.serialized_state_bytes()
    prior_head = runtime.library.head()
    from gateway.front_row import FrontRowMemory
    from agency.mechanics.sicd_engine import TreeGrowthEngine
    branch_id = next(iter(runtime.engine.state.branches))
    original_step = TreeGrowthEngine.step

    def remove_serving_branch(engine, *args, **kwargs):
        metrics = original_step(engine, *args, **kwargs)
        del engine.state.branches[branch_id]
        return metrics

    def fail(*args, **kwargs):
        raise RuntimeError("injected phase failure")

    with monkeypatch.context() as patch:
        if phase == "step": patch.setattr(TreeGrowthEngine, "step", fail)
        if phase == "write": patch.setattr(FrontRowMemory, "write_memory", fail)
        if phase == "teach": patch.setattr(TreeGrowthEngine, "apply_leaf_vec_update", fail)
        if phase == "reseat": patch.setattr(FrontRowMemory, "reseat", fail)
        if phase == "journal": patch.setattr(runtime.library, "set_head", fail)
        if phase == "rotate": patch.setattr(TreeGrowthEngine, "step", remove_serving_branch)
        with pytest.raises((RuntimeError, ValueError), match="injected|physics removed"):
            runtime.commit_turn("user", "beam", "retryable", response_text="beam column connection", activated_branch_ids=[branch_id])
    assert runtime.serialized_state_bytes() == before
    assert runtime.library.head() == prior_head
    assert not runtime._idempotency
    assert not runtime.library.events()
    assert runtime.commit_turn("user", "beam", "retryable", response_text="beam column connection")["taught"]


def test_library_first_and_4096_capacity_demotion_readmission(tmp_path):
    runtime = TomGateway(tmp_path).project("capacity")
    from memory.rgm import MemoryRecord, PolicyOutcome
    assert runtime.rgm.capacity == 4096
    for index in range(4096):
        text = f"Permanent original content {index}"
        record = MemoryRecord(id=f"record-{index:04d}", content=text, content_hash=content_hash(text),
                              anchor_strength=0.001 if index == 0 else 0.7, S=1, C=1, H=0,
                              novelty_score=1, policy_outcome=PolicyOutcome.PERMIT, created_tick=runtime.engine.state.tick)
        if index == 0:
            with pytest.raises(ValueError, match="library-first"):
                runtime.rgm.write(record)
        runtime.library.retain(record, runtime.rgm._record_to_dict(record))
        assert runtime.rgm.write(record) == record.id
    runtime.save_checkpoint()
    runtime.commit_turn("user", "new committed turn", "overflow")
    assert len(runtime.rgm.state.anchors) == 4096
    assert "record-0000" not in runtime.rgm.state.anchors
    event = runtime.library.events()[0]
    assert event["record_id"] == "record-0000" and event["reason"] == "capacity"
    assert content_hash(runtime.library.get(event["record_id"])["content"]) == event["content_hash"]
    result = runtime.commit_turn("user", "use the old record", "readmit", admitted_anchor_ids=["record-0000"])
    assert result["readmitted_anchor_ids"] == ["record-0000"]
    assert "record-0000" in runtime.rgm.state.anchors
    assert len(runtime.rgm.state.anchors) == 4096
    assert runtime.memory_diagnostics()["library_count"] == 4098
    victim = next(record for rid, record in runtime.rgm.state.anchors.items() if rid.startswith("record-") and rid != "record-0000")
    victim.anchor_strength, victim.decay_rate = 0.0001, 0.002
    runtime.commit_turn("user", "let unused weak anchors fade", "decay")
    assert any(row["record_id"] == victim.id and row["reason"] == "decayed" for row in runtime.library.events())
    assert runtime.library.get(victim.id) is not None


def test_checkpoint_restores_bytes_idempotency_and_settings_but_keeps_library(tmp_path):
    runtime = TomGateway(tmp_path).project("battery")
    runtime.commit_turn("user", "seed", "before", response_text="beam column connection")
    checkpoint = runtime.save_checkpoint()
    before = runtime.serialized_state_bytes()
    before_keys = dict(runtime._idempotency)
    runtime.update_settings({"front_row_capacity": 1, "teach_on_conflict": False})
    runtime.commit_turn("user", "experience", "after", response_text="beam column connection")
    library_count = runtime.memory_diagnostics()["library_count"]
    events = runtime.library.events()
    runtime.restore_checkpoint(checkpoint["checkpoint_id"])
    assert runtime.serialized_state_bytes() == before
    assert runtime._idempotency == before_keys
    assert runtime.settings == {"front_row_capacity": 4096, "teach_on_conflict": True}
    assert runtime.memory_diagnostics()["library_count"] == library_count
    assert runtime.library.events() == events
    assert TomGateway(tmp_path).project("battery").serialized_state_bytes() == before
    assert runtime.commit_turn("user", "experience", "after", response_text="beam column connection")["taught"]


def test_lost_json_projection_recovers_from_durable_sqlite_head(tmp_path, monkeypatch):
    runtime = TomGateway(tmp_path).project("recover")
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "_write_head_artifacts", lambda head: (_ for _ in ()).throw(OSError("disk projection failure")))
        committed = runtime.commit_turn("user", "beam", "once", response_text="beam column connection")
    state = runtime.serialized_state_bytes()
    recovered = TomGateway(tmp_path).project("recover")
    assert recovered.serialized_state_bytes() == state
    assert recovered.commit_turn("user", "beam", "once") == committed


def test_order_and_exact_pinned_ema(tmp_path, monkeypatch):
    runtime = TomGateway(tmp_path).project("ordered")
    from agency.mechanics.sicd_engine import TreeGrowthEngine, _normalize3
    from agency.mechanics.leaf_vectors import compose_leaf_vec, ema_update_vec
    from gateway.front_row import FrontRowMemory
    phases = []
    serving = runtime.preview_rank("connected beam", 10, 2000)["activated_branch_ids"]
    usage = {bid: b.usage_count for bid, b in runtime.engine.state.branches.items()}
    step, write, teach, reseat = TreeGrowthEngine.step, FrontRowMemory.write_memory, TreeGrowthEngine.apply_leaf_vec_update, FrontRowMemory.reseat

    def counted_step(engine, *args, **kwargs):
        phases.append("step")
        return step(engine, *args, **kwargs)

    def counted_write(rgm, record):
        assert phases == ["step"]
        rgm.library.assert_twin(record)
        phases.append("rgm_write")
        return write(rgm, record)

    def checked_teach(engine, payload):
        assert phases == ["step", "rgm_write"]
        branch = engine.state.branches[serving[0]]
        incoming, confidence = compose_leaf_vec(payload["semantic_axis"], payload["loads"], payload["confidence"])
        axis = _normalize3(tuple(payload["semantic_axis"]))
        aw = _normalize3(tuple(branch.axis_w))
        gate = max(0.0, sum(aw[i] * axis[i] for i in range(3)) - 1 / 3) / (1 - 1 / 3)
        alpha = engine.cfg.kappa_update.leaf_vec_ema_alpha * min(1.0, max(0.0, confidence)) * (0.1 + 0.9 * gate)
        expected = ema_update_vec(branch.sem_vec, incoming, alpha)
        teach(engine, payload)
        assert branch.sem_vec == expected  # Exact canonical arithmetic, not a tolerance.
        assert all(b.usage_count == usage.get(bid, 0) for bid, b in engine.state.branches.items())
        phases.append("leaf_vec_teach")

    def checked_reseat(rgm, ids, key):
        assert phases == ["step", "rgm_write", "leaf_vec_teach"]
        assert all(b.usage_count == usage.get(bid, 0) + int(bid in serving) for bid, b in runtime.engine.state.branches.items())
        phases.extend(["usage_rotation", "front_row_reseat"])
        return reseat(rgm, ids, key)

    monkeypatch.setattr(TreeGrowthEngine, "step", counted_step)
    monkeypatch.setattr(FrontRowMemory, "write_memory", counted_write)
    monkeypatch.setattr(TreeGrowthEngine, "apply_leaf_vec_update", checked_teach)
    monkeypatch.setattr(FrontRowMemory, "reseat", checked_reseat)
    runtime.commit_turn("user", "beam", "ordered", response_text="beam column connection", activated_branch_ids=serving)
    assert phases == COMMIT_DYNAMICS


def test_missing_demotion_twin_fails_loudly_without_partial_commit(tmp_path):
    runtime = TomGateway(tmp_path).project("missing-twin")
    victim = runtime.commit_turn("user", "weak old anchor", "old")["anchor_id"]
    runtime.rgm.state.anchors[victim].anchor_strength = 0.1
    runtime.save_checkpoint()
    runtime.update_settings({"front_row_capacity": 1})
    before, head = runtime.serialized_state_bytes(), runtime.library.head()
    # Corrupt only this test's disposable database to exercise the hard assertion.
    runtime.library.db.execute("DELETE FROM library_records WHERE record_id=?", (victim,))
    with pytest.raises(ValueError, match="library-first invariant"):
        runtime.commit_turn("user", "new anchor", "new", response_text="beam column connection")
    assert runtime.serialized_state_bytes() == before
    assert runtime.library.head() == head
    assert not runtime.library.events()
    assert "new" not in runtime._idempotency


def test_settings_are_validated_project_local_and_restart_durable(tmp_path):
    gateway = TomGateway(tmp_path)
    a, b = gateway.project("settings-a"), gateway.project("settings-b")
    before = a.serialized_state_bytes()
    a.update_settings({"front_row_capacity": 8192, "teach_on_conflict": False})
    assert a.serialized_state_bytes() == before
    assert b.settings == {"front_row_capacity": 4096, "teach_on_conflict": True}
    for invalid in ({"front_row_capacity": True}, {"front_row_capacity": 0}, {"teach_on_conflict": "false"}, {"unknown": 1}):
        with pytest.raises(ValueError): a.update_settings(invalid)
    restored = TomGateway(tmp_path).project("settings-a")
    assert restored.settings == a.settings
    assert restored.rgm.capacity == 8192


def test_permanent_library_keeps_full_original_after_zero_copy_and_demotion(tmp_path):
    runtime = TomGateway(tmp_path).project("full-original")
    original = "Full Unicode original Δ beam column connection. " * 30
    rid = runtime.commit_turn("user", original, "original")["anchor_id"]
    front_row = runtime.rgm.state.anchors[rid]
    assert front_row.content == ""
    assert len(front_row.content_summary) <= 256
    assert runtime.library.get(rid)["content"] == original
    front_row.anchor_strength = 0.1
    runtime.save_checkpoint()
    runtime.update_settings({"front_row_capacity": 1})
    runtime.commit_turn("user", "another anchor", "demote")
    assert rid not in runtime.rgm.state.anchors
    assert runtime.library.events()[0]["content_hash"] == content_hash(original)
    restarted = TomGateway(tmp_path).project("full-original")
    assert restarted.library.get(rid)["content"] == original
    restarted.commit_turn("user", "committed use of original", "readmit-original", admitted_anchor_ids=[rid])
    assert rid in restarted.rgm.state.anchors
    assert restarted.library.get(rid)["content"] == original
