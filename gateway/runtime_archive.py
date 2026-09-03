"""WAL-aware runtime backups and recoverable, non-overwriting import intents.

The Rust archive coordinator holds the ledger writer lock while this module
snapshots the runtime or publishes an already-validated staging directory.
No upstream code/files are changed; no physics or plastic recall is called.
"""
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import uuid

FORMAT = "tom-assist-runtime-archive/1"


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_in(root):
    if root.is_symlink():
        raise ValueError("runtime archive root may not be a symlink")
    files = {}
    for path in root.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("runtime archive contains a symlink/special file")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path
    return files


def readonly_db(path):
    # Export backup files are closed/checkpointed single SQLite files. Immutable
    # read-only mode avoids generating WAL/SHM sidecars in an input archive.
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db.execute("PRAGMA trusted_schema=OFF")
    return db


def validate_snapshot(gateway, root):
    from gateway.tom_gateway import canonical_digest, DEFAULT_SETTINGS
    entries = files_in(root)
    manifest = json.loads((root / "runtime-manifest.json").read_bytes())
    if manifest["format"] != FORMAT or manifest["runtime_version"] != gateway.runtime_sha:
        raise ValueError("runtime archive format/pin mismatch")
    if manifest["seed_artifact_sha256"] != gateway.seed.artifact_sha256 or manifest["mechanics_profile_sha256"] != gateway.seed.mechanics_profile_sha256:
        raise ValueError("runtime archive seed/physics profile mismatch")
    from gateway.tom_gateway import _safe_project_id
    _safe_project_id(manifest["project_id"])
    expected = manifest["files"]
    if set(entries) != set(expected) | {"runtime-manifest.json"}:
        raise ValueError("runtime archive inventory mismatch")
    for name, digest in expected.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or name not in entries:
            raise ValueError("unsafe runtime archive path")
        if name not in ("library.sqlite3", "creation_metadata.json") and not re.fullmatch(r"checkpoints/[0-9a-f-]{36}/(tree_state|rgm_state|commit_state|metadata)\.json", name):
            raise ValueError("unexpected runtime archive file")
        if digest_file(entries[name]) != digest:
            raise ValueError(f"runtime archive checksum mismatch: {name}")
    if not {"library.sqlite3", "creation_metadata.json"} <= set(expected):
        raise ValueError("runtime archive is incomplete")
    metadata = json.loads((root / "creation_metadata.json").read_bytes())
    if metadata["project_id"] != manifest["project_id"]:
        raise ValueError("runtime archive project mismatch")
    db = readonly_db(root / "library.sqlite3")
    try:
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("library integrity check failed")
        objects = {(kind, name) for kind, name in db.execute("SELECT type,name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")}
        legacy_objects = {("table", "library_records"), ("table", "runtime_head"), ("table", "demotions"), ("index", "library_content_hash")}
        structural_objects = legacy_objects | {("table", "structural_commits")}
        outcome_objects = structural_objects | {("table", "retrieval_outcomes")}
        document_objects = {
            ("table", "documents"), ("table", "document_chunks"),
        }
        accepted_objects = {
            frozenset(legacy_objects),
            frozenset(structural_objects),
            frozenset(outcome_objects),
            frozenset(structural_objects | document_objects),
            frozenset(outcome_objects | document_objects),
        }
        if frozenset(objects) not in accepted_objects:
            raise ValueError("unrecognized library schema objects")
        originals = {}
        original_texts = {}
        for rid, digest, content, encoded in db.execute("SELECT record_id,content_hash,content,record_json FROM library_records"):
            row = json.loads(encoded)
            if hashlib.sha256(content.encode()).hexdigest() != digest or row["id"] != rid or row["content_hash"] != digest:
                raise ValueError("permanent library original/hash mismatch")
            originals[rid] = digest
            original_texts[rid] = content
        heads = db.execute("SELECT tree,rgm,idempotency,settings FROM runtime_head").fetchall()
        if len(heads) != 1:
            raise ValueError("runtime head missing/ambiguous")
        tree, rgm, keys, settings = map(json.loads, heads[0])
        if canonical_digest({"engine":tree,"rgm":rgm}) != manifest["checkpoint_digest"]:
            raise ValueError("runtime head digest mismatch")
        if not isinstance(keys, dict) or set(settings) != set(DEFAULT_SETTINGS) or type(settings["teach_on_conflict"]) is not bool or type(settings["front_row_capacity"]) is not int or not 1 <= settings["front_row_capacity"] <= 1_000_000:
            raise ValueError("runtime commit/settings snapshot invalid")
        def twins(anchors):
            for rid, record in anchors.items():
                if originals.get(rid) != record["content_hash"]:
                    raise ValueError("front-row/checkpoint anchor has no durable twin")
        twins(rgm["anchors"])
        for rid, digest, reason in db.execute("SELECT record_id,content_hash,reason FROM demotions"):
            if originals.get(rid) != digest or reason not in ("decayed", "capacity"):
                raise ValueError("invalid demotion provenance")
        if ("table", "structural_commits") in objects:
            from gateway.structural_analysis import (
                SUPPORTED_COMPILER_VERSIONS,
                digest as structural_digest,
            )
            for commit_key, rid, source_digest, compiler, analysis_digest, encoded, tick in db.execute(
                "SELECT commit_key,record_id,source_text_sha256,compiler_version,"
                "analysis_digest,analysis_json,tick FROM structural_commits"
            ):
                analysis = json.loads(encoded)
                unsigned = {key:value for key,value in analysis.items() if key != "analysis_digest"}
                if (
                    not commit_key or rid not in originals or type(tick) is not int
                    or compiler not in SUPPORTED_COMPILER_VERSIONS
                    or analysis.get("compiler_version") != compiler
                    or analysis.get("source_text_sha256") != source_digest
                    or analysis.get("candidate", {}).get("source_text_sha256") != source_digest
                    or analysis.get("analysis_digest") != analysis_digest
                    or structural_digest(unsigned) != analysis_digest
                    or structural_digest(analysis.get("candidate")) != analysis.get("candidate_digest")
                ):
                    raise ValueError("invalid structural-commit provenance")
        if ("table", "retrieval_outcomes") in objects:
            from gateway.permanent_library import longest_common_substring_chars
            outcome_rows = db.execute(
                "SELECT commit_key,record_id,rank,rrf_score,lexical_rank,"
                "structural_rank,matched_branch_id,verbatim_overlap_chars,"
                "structural_similarity,conflict_dismissed,tick "
                "FROM retrieval_outcomes ORDER BY commit_key,rank,record_id"
            ).fetchall()
            expected_rank = {}
            for (
                commit_key, rid, rank, rrf_score, lexical_rank, structural_rank,
                matched_branch_id, overlap, structural_similarity,
                conflict_dismissed, tick,
            ) in outcome_rows:
                receipt = keys.get(commit_key)
                committed_id = receipt.get("anchor_id") if isinstance(receipt, dict) else None
                expected_rank[commit_key] = expected_rank.get(commit_key, 0) + 1
                numeric = (rrf_score, structural_similarity)
                if (
                    rid not in originals or committed_id not in original_texts
                    or rank != expected_rank[commit_key]
                    or any(value is not None and not math.isfinite(value) for value in numeric)
                    or any(value is not None and (type(value) is not int or value <= 0)
                           for value in (lexical_rank, structural_rank))
                    or matched_branch_id is not None and not isinstance(matched_branch_id, str)
                    or overlap != longest_common_substring_chars(
                        original_texts[rid], original_texts[committed_id]
                    )
                    or conflict_dismissed not in (0, 1)
                    or type(tick) is not int
                    or tick != receipt.get("engine_tick_after")
                ):
                    raise ValueError("invalid retrieval-outcome provenance")
        if ("table", "documents") in objects:
            from gateway.document_ingestion import (
                ALLOWED_DOCUMENT_MEDIA_TYPES,
                DOCUMENT_CHUNKING_VERSION,
                DOCUMENT_EMBEDDING_VERSION,
                MAX_DOCUMENT_CHUNKS,
                MAX_DOCUMENT_SOURCE_CHARS,
                decode_vector_f32,
            )
            documents = {}
            for row in db.execute(
                "SELECT document_id,display_name,content_sha256,content,byte_length,"
                "media_type,chunking_version,embedding_version,ingested_tick,tombstoned_at "
                "FROM documents ORDER BY document_id"
            ):
                (
                    document_id, display_name, content_digest, content, byte_length,
                    media_type, chunking_version, embedding_version, ingested_tick,
                    tombstoned_at,
                ) = row
                if (
                    document_id != "document-" + content_digest[:32]
                    or hashlib.sha256(content.encode("utf-8")).hexdigest() != content_digest
                    or byte_length != len(content.encode("utf-8"))
                    or not display_name or len(content) > MAX_DOCUMENT_SOURCE_CHARS
                    or media_type not in ALLOWED_DOCUMENT_MEDIA_TYPES
                    or chunking_version != DOCUMENT_CHUNKING_VERSION
                    or embedding_version != DOCUMENT_EMBEDDING_VERSION
                    or type(ingested_tick) is not int
                    or tombstoned_at is not None and not isinstance(tombstoned_at, str)
                ):
                    raise ValueError("invalid document provenance")
                documents[document_id] = content
            grouped = {document_id: [] for document_id in documents}
            for row in db.execute(
                "SELECT document_id,chunk_index,start,end,text_sha256,passage_vector,"
                "analysis_digest,load_signature_json FROM document_chunks "
                "ORDER BY document_id,chunk_index"
            ):
                document_id, index, start, end, text_digest, vector, analysis, load = row
                content = documents.get(document_id)
                if (
                    content is None or index != len(grouped[document_id])
                    or not 0 <= start < end <= len(content)
                    or hashlib.sha256(content[start:end].encode("utf-8")).hexdigest() != text_digest
                    or analysis is not None or load is not None
                ):
                    raise ValueError("invalid document-chunk provenance")
                decode_vector_f32(vector)
                grouped[document_id].append((start, end))
            for document_id, spans in grouped.items():
                if (
                    not 1 <= len(spans) <= MAX_DOCUMENT_CHUNKS
                    or spans[0][0] != 0 or spans[-1][1] != len(documents[document_id])
                    or any(
                        start >= spans[index - 1][1] or end <= spans[index - 1][1]
                        for index, (start, end) in enumerate(spans[1:], 1)
                    )
                ):
                    raise ValueError("document chunks do not overlap and cover their source")
        for folder in (root / "checkpoints").glob("*"):
            expected_files = {"tree_state.json", "rgm_state.json", "commit_state.json", "metadata.json"}
            if {p.name for p in folder.iterdir()} != expected_files:
                raise ValueError("incomplete/legacy checkpoint in runtime archive")
            checkpoint = json.loads((folder / "metadata.json").read_bytes())
            checkpoint_rgm = json.loads((folder / "rgm_state.json").read_bytes())
            payload = {"engine":json.loads((folder / "tree_state.json").read_bytes()),"rgm":checkpoint_rgm}
            if canonical_digest(payload) != checkpoint["digest"] or canonical_digest(json.loads((folder / "commit_state.json").read_bytes())) != checkpoint["commit_state_digest"]:
                raise ValueError("archived checkpoint digest mismatch")
            twins(checkpoint_rgm["anchors"])
        return manifest
    finally:
        db.close()


def export_snapshot(gateway, project_id, destination):
    from gateway.tom_gateway import canonical_json, canonical_digest
    runtime = gateway.project(project_id)
    root = Path(destination)
    with runtime.lock:
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
        target = sqlite3.connect(root / "library.sqlite3")
        try:
            runtime.library.db.backup(target)
            target.execute("PRAGMA journal_mode=DELETE")
        finally:
            target.close()
        os.chmod(root / "library.sqlite3", 0o600)
        shutil.copy2(runtime._creation_metadata_path, root / "creation_metadata.json")
        checkpoints = runtime.state_dir / "checkpoints"
        if checkpoints.exists():
            files_in(checkpoints)  # Refuse links, do not follow them during copy.
            shutil.copytree(checkpoints, root / "checkpoints")
        db = readonly_db(root / "library.sqlite3")
        try:
            tree, rgm = db.execute("SELECT tree,rgm FROM runtime_head").fetchone()
        finally:
            db.close()
        manifest = {"format":FORMAT,"project_id":project_id,"runtime_version":gateway.runtime_sha,
                    "seed_artifact_sha256":gateway.seed.artifact_sha256,
                    "mechanics_profile_sha256":gateway.seed.mechanics_profile_sha256,
                    "checkpoint_digest":canonical_digest({"engine":json.loads(tree),"rgm":json.loads(rgm)}),
                    "files":{name:digest_file(path) for name,path in files_in(root).items()}}
        (root / "runtime-manifest.json").write_bytes(canonical_json(manifest))
        validate_snapshot(gateway, root)
        return manifest


def committed(intent):
    path = Path(intent["ledger_path"]).resolve()
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        return db.execute("SELECT 1 FROM recovery_imports WHERE id=? AND project_id=? AND archive_digest=?",
                          (intent["token"], intent["project_id"], intent["archive_digest"])).fetchone() is not None
    finally:
        db.close()


def finalize_pending(project_dir):
    from gateway.tom_gateway import _atomic_write, canonical_json
    marker = project_dir / "tom/recovery-intent.json"
    if not marker.exists():
        return
    intent = json.loads(marker.read_bytes())
    if not committed(intent):
        raise ValueError("incomplete project import; retry the same verified archive")
    _atomic_write(project_dir / "tom/recovery-receipt.json", canonical_json(intent))
    marker.unlink()


def import_snapshot(gateway, action, directory, context):
    from gateway.tom_gateway import ProjectRuntime, _safe_project_id, _atomic_write, canonical_json
    project_id = _safe_project_id(context["project_id"])
    final = gateway.data_dir / "projects" / project_id
    staging_root = gateway.data_dir / "recovery-staging"
    staging_root.mkdir(mode=0o700, exist_ok=True)
    if action == "stage":
        root = Path(directory)
        manifest = validate_snapshot(gateway, root)
        if manifest["project_id"] != project_id:
            raise ValueError("runtime and ledger project mismatch")
        if final.is_symlink():
            raise ValueError("runtime destination is a symlink; import never overwrites")
        if final.exists():
            marker = final / "tom/recovery-intent.json"
            if marker.exists():
                pending = json.loads(marker.read_bytes())
                if all(pending.get(key) == context.get(key) for key in ("project_id", "ledger_path", "archive_digest")) and not committed(pending):
                    return pending
            raise ValueError("runtime project already exists; import never overwrites")
        intent = {**context, "token":str(uuid.uuid4())}
        stage = staging_root / intent["token"]
        stage.mkdir(mode=0o700)
        shutil.copytree(root, stage / "tom")
        validate_snapshot(gateway, stage / "tom")  # Recheck the copied bytes.
        factory = getattr(gateway, "create_project_runtime", None)
        probe = (
            factory(project_id, stage / "tom")
            if callable(factory)
            else ProjectRuntime(project_id, stage / "tom", gateway.runtime_sha, gateway.seed)
        )
        try:
            expected = probe.library.head()
            if probe.serialized_state_bytes() != expected[:2]:
                raise ValueError("runtime restore is not byte-identical")
        finally:
            probe.library.db.close()
        _atomic_write(stage / "tom/recovery-intent.json", canonical_json(intent))
        return intent
    token = context.get("token", "")
    if not re.fullmatch(r"[0-9a-f-]{36}", token):
        raise ValueError("invalid import token")
    stage = staging_root / token
    location = stage if stage.exists() else final
    marker = location / "tom/recovery-intent.json"
    if action == "finalize" and not marker.exists() and (final / "tom/recovery-receipt.json").exists():
        return {"finalized":True}
    if not marker.exists() or json.loads(marker.read_bytes()) != context:
        raise ValueError("import intent mismatch")
    if action == "publish":
        if location == final:
            return context  # Recovery of a crash before the ledger COMMIT.
        if final.exists() or final.is_symlink():
            raise ValueError("runtime destination already exists")
        final.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for path in files_in(stage).values():
            with path.open("rb") as stream: os.fsync(stream.fileno())
        for folder in sorted((p for p in stage.rglob("*") if p.is_dir()), key=lambda p:len(p.parts), reverse=True) + [stage]:
            descriptor = os.open(folder, os.O_RDONLY)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        stage.rename(final)
        descriptor = os.open(final.parent, os.O_RDONLY)
        try: os.fsync(descriptor)
        finally: os.close(descriptor)
        return context
    if action == "finalize":
        finalize_pending(final)
        return {"finalized":True}
    if action == "abort":
        if committed(context):
            finalize_pending(final)
            return {"committed":True}
        # Keep failed-import evidence recoverable; never remove an existing project.
        quarantine = staging_root / (token + ".aborted")
        if quarantine.exists():
            raise ValueError("aborted import evidence already exists")
        location.rename(quarantine)
        return {"aborted":True}
    raise ValueError("unknown runtime archive action")
