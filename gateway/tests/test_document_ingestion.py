from __future__ import annotations

import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import types

import pytest

from gateway.document_ingestion import (
    DOCUMENT_CHUNKING_VERSION,
    DOCUMENT_EMBEDDING_VERSION,
    MAX_DOCUMENT_CHUNKS,
    MAX_DOCUMENT_SOURCE_CHARS,
    decode_vector_f32,
)
from gateway.evidence_gateway import EvidenceTomGateway
from gateway.runtime_archive import digest_file, export_snapshot, import_snapshot, validate_snapshot
from gateway.semantic_chunks import EMBEDDING_DIMENSION, build_token_chunks
from gateway.structural_analysis import build_analysis, compile_load
from gateway.tests.test_evidence_loads import (
    _Provider as StructureProvider,
    _candidate,
    _empty_candidate,
)
from gateway.tom_gateway import TomGateway


ROOT = Path(__file__).parents[2]


class FixtureEmbeddingProvider:
    def __init__(self, axis=0):
        self.axis = axis
        self.calls = []

    def embed_document(self, text):
        self.calls.append(text)
        offsets = [(index, index + 1) for index in range(len(text))]
        plan = build_token_chunks(
            text,
            offsets,
            max_source_chars=MAX_DOCUMENT_SOURCE_CHARS,
            max_chunks=MAX_DOCUMENT_CHUNKS,
        )
        chunks = []
        for row in plan:
            vector = [0.0] * EMBEDDING_DIMENSION
            vector[self.axis] = 1.0
            chunks.append({
                "index": row["index"], "start": row["start"], "end": row["end"],
                "values": vector,
            })
        return {"model": "fixture/minilm", "revision": "fixture-v1", "chunks": chunks}


def _state(runtime):
    return {
        "bytes": runtime.serialized_state_bytes(),
        "tick": runtime.engine.state.tick,
        "checkpoint": runtime._current_checkpoint_digest(),
        "structural": runtime.library.db.execute(
            "SELECT COUNT(*) FROM structural_commits"
        ).fetchone()[0],
        "anchors": len(runtime.rgm.state.anchors),
    }


def _recover(target, archive, ledger, digest):
    with sqlite3.connect(ledger) as database:
        database.execute(
            "CREATE TABLE recovery_imports("
            "id TEXT PRIMARY KEY,project_id TEXT,archive_digest TEXT)"
        )
    context = {
        "project_id": "documents", "ledger_path": str(ledger),
        "archive_digest": digest, "state_digest": "sha256:state",
    }
    intent = import_snapshot(target, "stage", archive, context)
    import_snapshot(target, "publish", archive, intent)
    with sqlite3.connect(ledger) as database:
        database.execute(
            "INSERT INTO recovery_imports VALUES(?,?,?)",
            (intent["token"], "documents", digest),
        )
    import_snapshot(target, "finalize", archive, intent)
    return target.project("documents")


def test_large_document_ingestion_is_inert_exact_complete_and_float32(tmp_path):
    provider = FixtureEmbeddingProvider()
    runtime = TomGateway(
        tmp_path, document_embedding_provider=provider,
    ).project("documents")
    content = "A" * 60_000
    before = _state(runtime)
    result = runtime.ingest_document("large.txt", content, "text/plain")
    assert _state(runtime) == before
    assert len(content) > 48_000
    assert result["chunk_count"] > 128
    assert result["chunking_version"] == DOCUMENT_CHUNKING_VERSION
    assert result["embedding_version"] == DOCUMENT_EMBEDDING_VERSION
    chunks = runtime.library.document_chunks(document_id=result["document_id"])
    assert chunks[0]["start"] == 0
    assert chunks[-1]["end"] == len(content)
    assert all(
        chunks[index]["start"] < chunks[index - 1]["end"] < chunks[index]["end"]
        for index in range(1, len(chunks))
    )
    for row in chunks:
        assert row["text"] == content[row["start"]:row["end"]]
        assert len(decode_vector_f32(row["passage_vector"])) == 384
        assert len(row["passage_vector"].encode("ascii")) == 2_048
        assert row["analysis_digest"] is None
        assert row["load_signature_json"] is None


def test_originals_are_immutable_content_idempotent_and_names_do_not_alias(tmp_path):
    provider = FixtureEmbeddingProvider()
    runtime = TomGateway(
        tmp_path, document_embedding_provider=provider,
    ).project("documents")
    first = runtime.ingest_document("notes.md", "alpha specification", "text/markdown")
    duplicate = runtime.ingest_document(
        "renamed.md", "alpha specification", "text/markdown"
    )
    second = runtime.ingest_document("notes.md", "beta specification", "text/markdown")
    assert duplicate["duplicate"] is True
    assert duplicate["document_id"] == first["document_id"]
    assert duplicate["display_name"] == "notes.md"
    assert second["document_id"] != first["document_id"]
    assert provider.calls == ["alpha specification", "beta specification"]
    assert runtime.get_document(first["document_id"])["content"] == "alpha specification"


def test_document_code_has_no_load_or_tree_application_path():
    for name in ("document_ingestion.py", "document_embedding_worker.py"):
        source = (ROOT / "gateway" / name).read_text(encoding="utf-8")
        for forbidden in (
            "compile_load", "LoadSignature", "engine.step", "rgm.write",
            "apply_msr_load_to_sicd_engine",
        ):
            assert forbidden not in source


def test_turn_load_matches_wp38_exactly_except_saturation_observation():
    text = "A causes B."
    proposed = StructureProvider().analyze(text)
    current = build_analysis(
        text, proposed["chunk_candidates"], proposed["semantic_profile"],
        proposed["parser_model"], [], "checkpoint",
    )
    source = subprocess.check_output(
        ["git", "show", "ef567486d963a424588901d3aa58477b340039b4:gateway/structural_analysis.py"],
        cwd=ROOT,
        text=True,
    )
    parent = types.ModuleType("wp38_structural_analysis")
    exec(compile(source, "wp38_structural_analysis.py", "exec"), parent.__dict__)
    prior = parent.build_analysis(
        text, proposed["chunk_candidates"], proposed["semantic_profile"],
        proposed["parser_model"], [], "checkpoint",
    )
    left = {key: value for key, value in current.items() if key not in {
        "analysis_version", "analysis_digest",
    }}
    right = {key: value for key, value in prior.items() if key not in {
        "analysis_version", "analysis_digest",
    }}
    left["channel_evidence"] = dict(left["channel_evidence"])
    left["channel_evidence"].pop("saturation_epsilon")
    left["channel_evidence"].pop("saturation_observations")
    assert left == right


def test_saturation_telemetry_distinguishes_ties_from_one_dominant_chunk():
    text = "A causes B."
    rich = _candidate(text)
    empty = _empty_candidate(text)
    tied = compile_load(
        rich, {"chunks": [{"values": [1.0]}]},
        [{"chunk_index": 0, "candidate": rich}, {"chunk_index": 1, "candidate": rich}],
        [],
    )["channel_evidence"]["saturation_observations"]
    dominant = compile_load(
        rich, {"chunks": [{"values": [1.0]}]},
        [{"chunk_index": 0, "candidate": rich}, {"chunk_index": 1, "candidate": empty}],
        [],
    )["channel_evidence"]["saturation_observations"]
    assert tied["S_dependency"] == {
        "within_epsilon_of_max": 2, "max_minus_median": 0.0, "chunk_count": 2,
    }
    assert dominant["S_dependency"]["within_epsilon_of_max"] == 1
    assert dominant["S_dependency"]["max_minus_median"] > 0.0
    assert set(tied) == {
        "S_entity", "S_dependency", "S_topology", "L_rule", "L_contradiction",
        "L_inference", "T_sequence", "T_memory", "T_future", "threat_amplitude",
    }


def test_shadow_reports_document_dense_rank_but_never_serves_it_and_withdraws(tmp_path):
    embeddings = FixtureEmbeddingProvider(axis=0)
    structure = StructureProvider()
    gateway = EvidenceTomGateway(
        tmp_path,
        structure_mode="shadow",
        structure_provider=structure,
        document_embedding_provider=embeddings,
    )
    runtime = gateway.project("documents")
    document = runtime.ingest_document("evidence.txt", "document evidence", "text/plain")
    seed_preview = runtime.preview_rank("B causes A.", 10, 2000)
    runtime.commit_turn(
        "user", "B causes A.", "seed",
        structural_analysis=seed_preview["structural_analysis"],
    )
    preview = runtime.preview_rank("A causes B.", 10, 2000)
    report = preview["shadow_retrieval_comparison"]["document_chunk_dense_channel"]
    assert report["document_chunk_count"] == 1
    assert report["chunks_that_would_displace_an_anchor"] == 1
    assert report["ranking"][0]["document_id"] == document["document_id"]
    assert report["ranking"][0]["packet_eligible"] is False
    assert report["ranking"][0]["structural_signature"] is None
    assert all(
        not row["id"].startswith("document-") for row in preview["ranked_anchors"]
    )
    assert all(not branch.startswith("document-") for branch in preview["activated_branch_ids"])
    retained = runtime.withdraw_document(document["document_id"], "2026-09-03T00:00:00Z")
    assert retained["tombstoned_at"] == "2026-09-03T00:00:00Z"
    assert runtime.list_documents() == []
    assert runtime.list_documents(include_withdrawn=True)[0]["document_id"] == document["document_id"]
    after = runtime.preview_rank("A causes B.", 10, 2000)
    assert after["shadow_retrieval_comparison"]["document_chunk_dense_channel"][
        "document_chunk_count"
    ] == 0


def test_binary_non_utf8_and_implicit_mutations_are_refused_without_storage(tmp_path):
    provider = FixtureEmbeddingProvider()
    gateway = TomGateway(tmp_path, document_embedding_provider=provider)
    runtime = gateway.project("documents")
    for content, media_type, message in (
        (b"binary", "text/plain", "UTF-8"),
        ("%PDF binary", "application/pdf", "binary formats"),
    ):
        with pytest.raises(ValueError, match=message):
            runtime.ingest_document("bad", content, media_type)
    status, result = gateway.handle("POST", "/document/ingest", {
        "project_id": "documents", "display_name": "implicit.txt",
        "content": "not explicit", "media_type": "text/plain",
    })
    assert status == 400
    assert "explicit user action" in result["message"]
    assert runtime.library.documents(include_withdrawn=True) == []
    assert provider.calls == []


def test_document_protocol_routes_require_explicit_mutation_and_round_trip(tmp_path):
    gateway = TomGateway(
        tmp_path, document_embedding_provider=FixtureEmbeddingProvider(),
    )
    ingest = {
        "project_id": "documents", "display_name": "protocol.md",
        "content": "Protocol document inventory.", "media_type": "text/markdown",
        "explicit_user_action": True,
    }
    status, created = gateway.handle("POST", "/document/ingest", ingest)
    assert status == 200
    status, listed = gateway.handle("POST", "/document/list", {
        "project_id": "documents", "include_withdrawn": False,
    })
    assert status == 200
    assert [row["document_id"] for row in listed["documents"]] == [
        created["document_id"]
    ]
    status, fetched = gateway.handle("POST", "/document/get", {
        "project_id": "documents", "document_id": created["document_id"],
    })
    assert status == 200
    assert fetched == {key: value for key, value in created.items() if key != "duplicate"}
    status, refused = gateway.handle("POST", "/document/withdraw", {
        "project_id": "documents", "document_id": created["document_id"],
        "tombstoned_at": "2026-09-03T00:00:00Z",
    })
    assert status == 400
    assert "explicit user action" in refused["message"]
    status, withdrawn = gateway.handle("POST", "/document/withdraw", {
        "project_id": "documents", "document_id": created["document_id"],
        "tombstoned_at": "2026-09-03T00:00:00Z", "explicit_user_action": True,
    })
    assert status == 200
    assert withdrawn["tombstoned_at"] == "2026-09-03T00:00:00Z"


def test_archive_preserves_documents_and_pre_wp39_archive_imports_empty(tmp_path):
    provider = FixtureEmbeddingProvider()
    gateway = TomGateway(tmp_path / "source", document_embedding_provider=provider)
    runtime = gateway.project("documents")
    document = runtime.ingest_document("archive.md", "archived document", "text/markdown")
    archive = tmp_path / "archive"
    export_snapshot(gateway, "documents", archive)
    validate_snapshot(gateway, archive)
    recovered = _recover(
        TomGateway(tmp_path / "target"), archive,
        tmp_path / "recovery.sqlite3", "sha256:current",
    )
    assert recovered.get_document(document["document_id"]) == runtime.get_document(
        document["document_id"]
    )

    old = tmp_path / "old"
    shutil.copytree(archive, old)
    with sqlite3.connect(old / "library.sqlite3") as database:
        database.execute("DROP TABLE document_declared_structures")
        database.execute("DROP TABLE document_chunks")
        database.execute("DROP TABLE documents")
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
    assert recovered_old.list_documents(include_withdrawn=True) == []
