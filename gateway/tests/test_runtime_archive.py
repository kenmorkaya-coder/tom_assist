import json
from pathlib import Path
import sqlite3

import pytest

from gateway.tom_gateway import TomGateway
from gateway.runtime_archive import digest_file, export_snapshot, import_snapshot, validate_snapshot


def prepared(tmp_path):
    gateway = TomGateway(tmp_path / "source")
    runtime = gateway.project("recoverable")
    original = "Full original beam-column connection Δ. " * 40
    record = runtime.commit_turn("user", original, "first", response_text="The beam connects both columns.")
    runtime.save_checkpoint()
    runtime.update_settings({"front_row_capacity": 1, "teach_on_conflict": False})
    runtime.commit_turn("user", "another exchange", "second", response_text="Check the load path.")
    archive = tmp_path / "runtime-archive"
    before = runtime.serialized_state_bytes(), list(runtime.library.db.iterdump())
    export_snapshot(gateway, "recoverable", archive)
    assert (runtime.serialized_state_bytes(), list(runtime.library.db.iterdump())) == before
    ledger = tmp_path / "target.sqlite3"
    db = sqlite3.connect(ledger)
    db.execute("CREATE TABLE recovery_imports(id TEXT PRIMARY KEY,project_id TEXT,archive_digest TEXT)")
    db.commit()
    db.close()
    context = {"project_id":"recoverable", "ledger_path":str(ledger), "archive_digest":"sha256:fixture", "state_digest":"sha256:state"}
    return gateway, runtime, archive, context, record, original


def receipt(context):
    db = sqlite3.connect(context["ledger_path"])
    db.execute("INSERT INTO recovery_imports VALUES(?,?,?)", (context["token"], context["project_id"], context["archive_digest"]))
    db.commit()
    db.close()


def test_archive_recovers_full_library_settings_keys_checkpoints_and_bytes(tmp_path):
    source, runtime, archive, context, record, original = prepared(tmp_path)
    expected = runtime.serialized_state_bytes()
    before_verify = {str(p):digest_file(p) for p in archive.rglob("*") if p.is_file()}
    assert source.handle("POST", "/archive/runtime/verify", {"directory":str(archive)})[0] == 200
    assert {str(p):digest_file(p) for p in archive.rglob("*") if p.is_file()} == before_verify
    assert runtime.serialized_state_bytes() == expected
    target = TomGateway(tmp_path / "target")
    token = import_snapshot(target, "stage", archive, context)
    assert not (target.data_dir / "projects/recoverable").exists()
    import_snapshot(target, "publish", archive, token)
    receipt(token)
    import_snapshot(target, "finalize", archive, token)
    recovered = target.project("recoverable")
    assert recovered.serialized_state_bytes() == expected
    assert recovered.settings == runtime.settings
    assert recovered.library.events() == runtime.library.events()
    assert recovered.library.get(record["anchor_id"])["content"] == "USER\n" + original + "\nASSISTANT\nThe beam connects both columns."
    assert recovered.commit_turn("user", "ignored replay", "first") == record
    assert sorted(p.name for p in (recovered.state_dir / "checkpoints").iterdir()) == sorted(p.name for p in (runtime.state_dir / "checkpoints").iterdir())
    assert TomGateway(target.data_dir).project("recoverable").serialized_state_bytes() == expected


@pytest.mark.parametrize("damage", ["original", "twin", "settings"])
def test_rehashed_but_semantically_invalid_library_is_rejected(tmp_path, damage):
    _, _, archive, context, _, _ = prepared(tmp_path)
    with sqlite3.connect(archive / "library.sqlite3") as db:
        if damage == "original": db.execute("UPDATE library_records SET content='truncated'")
        elif damage == "twin": db.execute("DELETE FROM library_records")
        else: db.execute("UPDATE runtime_head SET settings='{}'")
    manifest = json.loads((archive / "runtime-manifest.json").read_bytes())
    manifest["files"]["library.sqlite3"] = digest_file(archive / "library.sqlite3")
    (archive / "runtime-manifest.json").write_text(json.dumps(manifest))
    target = TomGateway(tmp_path / "target")
    with pytest.raises(ValueError): import_snapshot(target, "stage", archive, context)
    assert not (target.data_dir / "projects/recoverable").exists()


def test_crash_before_ledger_commit_refuses_preview_then_same_archive_can_retry(tmp_path):
    _, runtime, archive, context, _, _ = prepared(tmp_path)
    target = TomGateway(tmp_path / "target")
    token = import_snapshot(target, "stage", archive, context)
    import_snapshot(target, "publish", archive, token)
    restarted = TomGateway(target.data_dir)
    with pytest.raises(ValueError, match="incomplete project import"):
        restarted.project("recoverable")
    assert import_snapshot(restarted, "stage", archive, context) == token
    receipt(token)
    # Crash after the ledger commit but before finalization is recovered lazily.
    assert restarted.project("recoverable").serialized_state_bytes() == runtime.serialized_state_bytes()


def test_abort_quarantines_only_new_import_and_existing_runtime_is_not_overwritten(tmp_path):
    _, _, archive, context, _, _ = prepared(tmp_path)
    target = TomGateway(tmp_path / "target")
    token = import_snapshot(target, "stage", archive, context)
    import_snapshot(target, "publish", archive, token)
    import_snapshot(target, "abort", archive, token)
    assert not (target.data_dir / "projects/recoverable").exists()
    assert (target.data_dir / "recovery-staging" / (token["token"] + ".aborted")).exists()
    existing = target.project("recoverable")
    before = existing.serialized_state_bytes()
    with pytest.raises(ValueError, match="already exists"):
        import_snapshot(target, "stage", archive, context)
    assert existing.serialized_state_bytes() == before
    linked = TomGateway(tmp_path / "linked-target")
    destination = linked.data_dir / "projects/recoverable"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(tmp_path / "absent-project", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        import_snapshot(linked, "stage", archive, context)
    assert destination.is_symlink()


@pytest.mark.parametrize("damage", ["missing", "changed", "pin", "symlink", "path"])
def test_invalid_archives_are_rejected_before_runtime_publication(tmp_path, damage):
    _, _, archive, context, _, _ = prepared(tmp_path)
    if damage == "missing": (archive / "library.sqlite3").unlink()
    if damage == "changed": (archive / "creation_metadata.json").write_text("{}")
    if damage in ("pin", "path"):
        manifest = json.loads((archive / "runtime-manifest.json").read_bytes())
        if damage == "pin": manifest["runtime_version"] = "different-runtime"
        else: manifest["files"]["../escape"] = "bad"
        (archive / "runtime-manifest.json").write_text(json.dumps(manifest))
    if damage == "symlink": (archive / "bad-link").symlink_to(tmp_path)
    target = TomGateway(tmp_path / "target")
    with pytest.raises(ValueError): import_snapshot(target, "stage", archive, context)
    assert not (target.data_dir / "projects/recoverable").exists()
