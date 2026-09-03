from __future__ import annotations

import json
import shutil
import sqlite3

import pytest

from gateway.evidence_gateway import EvidenceTomGateway
from gateway.permanent_library import longest_common_substring_chars
from gateway.runtime_archive import (
    digest_file, export_snapshot, import_snapshot, validate_snapshot,
)
from gateway.tom_gateway import TomGateway
from gateway.tests.test_evidence_loads import _Provider


def _commit_seed(runtime, text, key):
    preview = runtime.preview_rank(text, 10, 2000)
    arguments = {
        "activated_branch_ids": preview["activated_branch_ids"],
    }
    if preview.get("structural_analysis") is not None:
        arguments["structural_analysis"] = preview["structural_analysis"]
    return runtime.commit_turn("user", text, key, **arguments)


def _trace_for(preview, admitted):
    wanted = set(admitted)
    return [row for row in preview["candidate_trace"] if row["id"] in wanted]


def _table_bytes(runtime, table):
    rows = runtime.library.db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    return json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()


def _recover(target, archive, ledger, archive_digest):
    with sqlite3.connect(ledger) as database:
        database.execute(
            "CREATE TABLE recovery_imports("
            "id TEXT PRIMARY KEY,project_id TEXT,archive_digest TEXT)"
        )
    context = {
        "project_id": "archived", "ledger_path": str(ledger),
        "archive_digest": archive_digest, "state_digest": "sha256:state",
    }
    intent = import_snapshot(target, "stage", archive, context)
    import_snapshot(target, "publish", archive, intent)
    with sqlite3.connect(ledger) as database:
        database.execute(
            "INSERT INTO recovery_imports VALUES(?,?,?)",
            (intent["token"], "archived", archive_digest),
        )
    import_snapshot(target, "finalize", archive, intent)
    return target.project("archived")


def test_rows_match_packet_order_fusion_overlap_and_dismissal(tmp_path):
    runtime = TomGateway(tmp_path).project("outcomes")
    first = _commit_seed(runtime, "alpha beam connection", "seed-a")
    second = _commit_seed(runtime, "beta column restraint", "seed-b")
    preview = runtime.preview_rank("compare the two retained details", 10, 2000)
    admitted = [second["anchor_id"], first["anchor_id"]]
    trace = _trace_for(preview, admitted)
    response = "Use alpha beam connection as the governing detail."
    result = runtime.commit_turn(
        "user", "compare the two retained details", "observed",
        response_text=response,
        admitted_anchor_ids=admitted,
        activated_branch_ids=preview["activated_branch_ids"],
        retrieval_trace=trace,
        conflict_dismissed=True,
        packet_digest="packet-observed",
    )
    rows = runtime.library.retrieval_outcomes("observed")
    assert [row["record_id"] for row in rows] == admitted
    assert [row["rank"] for row in rows] == [1, 2]
    by_id = {row["id"]: row for row in trace}
    for row in rows:
        source = by_id[row["record_id"]]
        for field in (
            "rrf_score", "lexical_rank", "structural_rank", "matched_branch_id",
        ):
            assert row[field] == source[field]
        assert row["conflict_dismissed"] == 1
        assert row["tick"] == result["engine_tick_after"]
    assert next(row for row in rows if row["record_id"] == first["anchor_id"])[
        "verbatim_overlap_chars"
    ] == len("alpha beam connection")
    assert all(row["structural_similarity"] is None for row in rows)


def test_empty_packet_idempotency_and_exact_paraphrase_overlap(tmp_path):
    runtime = TomGateway(tmp_path).project("empty")
    seed = _commit_seed(runtime, "a copper brace resists drift", "seed")
    empty = runtime.commit_turn("user", "nothing admitted", "empty")
    assert runtime.library.retrieval_outcomes("empty") == []
    preview = runtime.preview_rank("discuss drift resistance", 10, 2000)
    trace = _trace_for(preview, [seed["anchor_id"]])
    runtime.commit_turn(
        "user", "discuss drift resistance", "paraphrase",
        response_text="The metal diagonal limits sway.",
        admitted_anchor_ids=[seed["anchor_id"]], retrieval_trace=trace,
    )
    before = _table_bytes(runtime, "retrieval_outcomes")
    replay = runtime.commit_turn(
        "user", "ignored on idempotent replay", "paraphrase",
        admitted_anchor_ids=[], retrieval_trace=[],
    )
    assert replay["idempotency_key"] == "paraphrase"
    assert _table_bytes(runtime, "retrieval_outcomes") == before
    committed = "USER\ndiscuss drift resistance\nASSISTANT\nThe metal diagonal limits sway."
    expected = longest_common_substring_chars("a copper brace resists drift", committed)
    assert runtime.library.retrieval_outcomes("paraphrase")[0][
        "verbatim_overlap_chars"
    ] == expected
    assert expected < len("a copper brace resists drift")


def test_outcome_write_rolls_back_when_later_commit_phase_fails(tmp_path, monkeypatch):
    runtime = TomGateway(tmp_path).project("atomic")
    seed = _commit_seed(runtime, "retained anchor", "seed")
    preview = runtime.preview_rank("use retained anchor", 10, 2000)
    before_tick = runtime.engine.state.tick
    monkeypatch.setattr(
        runtime.library, "set_head",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("forced after outcome")),
    )
    with pytest.raises(RuntimeError, match="forced after outcome"):
        runtime.commit_turn(
            "user", "use retained anchor", "failed",
            admitted_anchor_ids=[seed["anchor_id"]],
            retrieval_trace=_trace_for(preview, [seed["anchor_id"]]),
        )
    assert runtime.library.retrieval_outcomes("failed") == []
    assert runtime.engine.state.tick == before_tick


def test_structural_similarity_is_existing_score_and_missing_evidence_is_null(tmp_path):
    legacy = TomGateway(tmp_path / "mixed").project("mixed")
    old = _commit_seed(legacy, "legacy anchor", "legacy")
    legacy.library.db.close()
    runtime = EvidenceTomGateway(
        tmp_path / "mixed", structure_mode="shadow", structure_provider=_Provider(),
    ).project("mixed")
    first_preview = runtime.preview_rank("A causes B.", 10, 2000)
    structural = runtime.commit_turn(
        "user", "A causes B.", "structural",
        structural_analysis=first_preview["structural_analysis"],
    )
    preview = runtime.preview_rank("B causes A.", 10, 2000)
    admitted = [old["anchor_id"], structural["anchor_id"]]
    expected = {
        row["record_id"]: row["combined_score"]
        for row in preview["shadow_structural_retrieval"]
    }
    runtime.commit_turn(
        "user", "B causes A.", "comparison",
        admitted_anchor_ids=admitted,
        retrieval_trace=_trace_for(preview, admitted),
        structural_analysis=preview["structural_analysis"],
    )
    rows = {row["record_id"]: row for row in runtime.library.retrieval_outcomes("comparison")}
    assert rows[old["anchor_id"]]["structural_similarity"] is None
    assert rows[structural["anchor_id"]]["structural_similarity"] == expected[
        structural["anchor_id"]
    ]


def test_capture_does_not_change_packet_tree_rgm_checkpoint_or_existing_tables(tmp_path):
    source = tmp_path / "source"
    seeded = TomGateway(source).project("same-project")
    seed = _commit_seed(seeded, "same retained anchor", "seed")
    seeded.library.db.close()
    copied = tmp_path / "copied"
    shutil.copytree(source, copied)
    controls = []
    for root, include_trace in ((source, False), (copied, True)):
        runtime = TomGateway(root).project("same-project")
        runtime.engine.rng.seed(3800)
        preview = runtime.preview_rank("same next turn", 10, 2000)
        packet = json.dumps(preview, sort_keys=True, separators=(",", ":"))
        trace = _trace_for(preview, [seed["anchor_id"]]) if include_trace else []
        result = runtime.commit_turn(
            "user", "same next turn", "next",
            response_text="same response",
            admitted_anchor_ids=[seed["anchor_id"]],
            activated_branch_ids=preview["activated_branch_ids"],
            retrieval_trace=trace,
            packet_digest="same-packet",
        )
        controls.append({
            "packet": packet,
            "state": runtime.serialized_state_bytes(),
            "checkpoint": result["checkpoint_digest"],
            "library_records": _table_bytes(runtime, "library_records"),
            "demotions": _table_bytes(runtime, "demotions"),
            "structural_commits": _table_bytes(runtime, "structural_commits"),
            "result": result,
        })
    assert controls[0] == controls[1]


def test_archive_round_trip_preserves_rows_and_pre_wp38_archive_imports(tmp_path):
    gateway = TomGateway(tmp_path / "source")
    runtime = gateway.project("archived")
    seed = _commit_seed(runtime, "archived anchor", "seed")
    preview = runtime.preview_rank("quote archived anchor", 10, 2000)
    runtime.commit_turn(
        "user", "quote archived anchor", "outcome",
        response_text="archived anchor",
        admitted_anchor_ids=[seed["anchor_id"]],
        retrieval_trace=_trace_for(preview, [seed["anchor_id"]]),
    )
    archive = tmp_path / "archive"
    export_snapshot(gateway, "archived", archive)
    before = (archive / "library.sqlite3").read_bytes()
    validate_snapshot(gateway, archive)
    assert (archive / "library.sqlite3").read_bytes() == before
    with sqlite3.connect(archive / "library.sqlite3") as database:
        assert database.execute("SELECT COUNT(*) FROM retrieval_outcomes").fetchone() == (1,)
    recovered = _recover(
        TomGateway(tmp_path / "current-target"), archive,
        tmp_path / "current-recovery.sqlite3", "sha256:current",
    )
    assert _table_bytes(recovered, "retrieval_outcomes") == _table_bytes(
        runtime, "retrieval_outcomes"
    )

    old = tmp_path / "old-archive"
    export_snapshot(gateway, "archived", old)
    with sqlite3.connect(old / "library.sqlite3") as database:
        database.execute("DROP TABLE retrieval_outcomes")
    manifest = json.loads((old / "runtime-manifest.json").read_bytes())
    manifest["files"]["library.sqlite3"] = digest_file(old / "library.sqlite3")
    (old / "runtime-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    )
    validate_snapshot(gateway, old)
    recovered_old = _recover(
        TomGateway(tmp_path / "old-target"), old,
        tmp_path / "old-recovery.sqlite3", "sha256:old",
    )
    assert recovered_old.library.retrieval_outcomes() == []


def test_longest_common_substring_is_exact_unicode_not_fuzzy():
    assert longest_common_substring_chars("beam Δ resists", "quote beam Δ resists exactly") == 14
    assert longest_common_substring_chars("abcXYZdef", "123XYZ789") == 3
    assert longest_common_substring_chars("", "anything") == 0
