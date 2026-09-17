from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import types

import pytest

from gateway.document_ingestion import (
    build_rgm_document_corpus,
    retain_rgm_document_corpus,
    resolve_rgm_document_chunk,
    build_rgm_evidence_context,
    DOCUMENT_CHUNKING_VERSION,
    DOCUMENT_MAX_CHUNK_TOKENS,
    DOCUMENT_EMBEDDING_VERSION,
    MAX_DOCUMENT_CHUNKS,
    MAX_DOCUMENT_SOURCE_CHARS,
    build_document_query_profile,
    decode_vector_f32,
    encode_vector_f32,
    prestart_relation_details,
    prestart_requirement_query,
    rank_document_chunks_for_packet,
    scan_prestart_relations,
)
from gateway.evidence_gateway import EvidenceTomGateway
from gateway.document_research import evidence_unit_for_position, parse_research_intent
from gateway.permanent_library import PermanentLibrary
from gateway.runtime_archive import digest_file, export_snapshot, import_snapshot, validate_snapshot
from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    build_semantic_profile,
    build_token_chunks,
)
from gateway.structural_analysis import CHANNELS, build_analysis, compile_load
from gateway.tests.test_evidence_loads import (
    _Provider as StructureProvider,
    _candidate,
    _empty_candidate,
)
from gateway.tom_gateway import TomGateway
from gateway.tom_gateway import GemmaInspection


ROOT = Path(__file__).parents[2]


def test_rgm_corpus_retains_tail_sections_and_splits_without_loss():
    sections = [f"{i}. Section {i}\n" + ("é界\f" * 2500 if i == 55 else "Evidence.") + "\n"
                for i in range(60)]
    source = "Repeated header\n\n" + "Repeated header\n\n".join(sections)
    detected = "\n".join("## " + s.rstrip("\n") for s in sections)
    corpus = build_rgm_document_corpus(source, detected, {"source": "synthetic"})
    assert len(corpus["sections"]) == 61
    assert len(corpus["chunks"]) > 61
    assert "".join(source[c["start"]:c["end"]] for c in corpus["chunks"]) == source
    assert all(0 < c["end"] - c["start"] <= 4000 for c in corpus["chunks"])
    assert any(s["title"] == "59. Section 59" for s in corpus["sections"])
    for chunk in corpus["chunks"]:
        assert chunk["start_line"] == source[:chunk["start"]].count("\n") + 1
        assert chunk["end_line"] == source[:chunk["end"] - 1].count("\n") + 1
        assert chunk["end_line"] >= chunk["start_line"]
    with pytest.raises(ValueError, match="cannot be aligned"):
        build_rgm_document_corpus(source, detected + "\ninvented sentence", {"source": "synthetic"})


def test_rgm_corpus_reopens_exact_unicode_ranges_and_rejects_bad_references(tmp_path):
    source = "1. Evidence\nSM → TfNSW: €20.\n2. Evidence\nTfNSW → SM: €40.\n"
    detected = source.replace("1. Evidence", "## 1. Evidence").replace("2. Evidence", "## 2. Evidence")
    corpus = build_rgm_document_corpus(source, detected, {"source": "synthetic"}, max_chunk_chars=24)
    path = tmp_path / "library.sqlite3"
    library = PermanentLibrary(path)
    references = retain_rgm_document_corpus(library, source, corpus)
    assert retain_rgm_document_corpus(library, source, corpus) == references
    library.db.close()
    library = PermanentLibrary(path)
    try:
        assert "".join(resolve_rgm_document_chunk(library, r) for r in references) == source
        for changed in ({"start": 1}, {"end_line": 999}, {"text_sha256": "0" * 64}):
            with pytest.raises(ValueError, match="not bound"):
                resolve_rgm_document_chunk(library, {**references[0], **changed})
        with pytest.raises(ValueError, match="missing"):
            resolve_rgm_document_chunk(library, {**references[0], "corpus_id": "absent"})
        library.db.execute("UPDATE library_records SET content = content || 'altered'")
        with pytest.raises(ValueError, match="integrity"):
            resolve_rgm_document_chunk(library, references[0])
    finally:
        library.db.close()


@pytest.mark.parametrize("damage", ["gap", "overlap", "hash", "tail", "source"])
def test_rgm_corpus_refuses_damaged_import_before_persistence(tmp_path, damage):
    source = "1. Evidence\n" + "abcdef" * 30
    corpus = build_rgm_document_corpus(source, "## " + source, {"source": "synthetic"}, max_chunk_chars=30)
    if damage == "gap":
        corpus["chunks"][1]["start"] += 1
    elif damage == "overlap":
        corpus["chunks"][1]["start"] -= 1
    elif damage == "hash":
        corpus["chunks"][1]["text_sha256"] = "0" * 64
    elif damage == "tail":
        corpus["chunks"].pop()
    else:
        source += "changed"
    library = PermanentLibrary(tmp_path / "library.sqlite3")
    try:
        with pytest.raises(ValueError):
            retain_rgm_document_corpus(library, source, corpus)
        assert library.db.execute("SELECT count(*) FROM library_records").fetchone()[0] == 0
    finally:
        library.db.close()


def _rgm_context_fixture(tmp_path):
    source = "1. First\n" + "Background. " * 60 + "SM pays the first premium.\n"
    source += "2. Second\n" + "Background. " * 60 + "TfNSW pays the second premium.\n"
    headings = source.replace("1. First", "## 1. First").replace("2. Second", "## 2. Second")
    corpus = build_rgm_document_corpus(source, headings, {"source": "fixture"})
    path = tmp_path / "library.sqlite3"
    library = PermanentLibrary(path)
    refs = retain_rgm_document_corpus(library, source, corpus)
    library.db.close()
    registry = {("document", r["chunk_id"]): r for r in refs}
    memories = [dict(id=r["chunk_id"], content=source[r["start"]:r["end"]][:200], relevance_score=score,
        semantic_tags={"document", "source"},
        source_refs=[dict(doc_id="document", chunk_id=r["chunk_id"], start=r["start"], end=r["end"],
                          source_text_sha256=r["text_sha256"])]) for r,score in zip(reversed(refs),(.81,.73))]
    return PermanentLibrary(path), registry, memories, source


def test_rgm_context_recovers_selected_tails_in_rank_order_after_reopening(tmp_path):
    library, registry, memories, source = _rgm_context_fixture(tmp_path)
    original = copy.deepcopy(memories)
    try:
        packet = build_rgm_evidence_context(library, memories, registry)
        assert [m["id"] for m in packet["memories"]] == [m["id"] for m in memories]
        assert [m["relevance_score"] for m in packet["memories"]] == [.81,.73]
        assert packet["memories"][0]["semantic_tags"] == {"document", "source"}
        assert packet["memories"][0]["semantic_tags"] is not memories[0]["semantic_tags"]
        assert packet["source_count"] == 2
        assert packet["source_chars"] == len(source)
        for m in packet["memories"]:
            ref = m["evidence_reference"]
            assert m["content"] == source[ref["start"]:ref["end"]]
            assert m["content"] in packet["context"]
            assert ref["provenance"] == {"source": "fixture"}
        assert packet["context"].index("TfNSW pays") < packet["context"].index("SM pays")
        assert memories == original
        assert build_rgm_evidence_context(library, [], registry)["context"] == ""
        # A tight consumer budget must not silently lose a tail or a candidate.
        with pytest.raises(ValueError, match="complete source context requires"):
            build_rgm_evidence_context(library, memories, registry, max_context_chars=200)
        assert build_rgm_evidence_context(library, memories, registry,
            max_context_chars=packet["context_chars"])["context"] == packet["context"]
    finally:
        library.db.close()


@pytest.mark.parametrize("damage", ["missing", "wrong_document", "wrong_chunk", "swapped_reference", "hash", "corpus"])
def test_rgm_context_refuses_broken_provenance_without_excerpt_fallback(tmp_path, damage):
    library, registry, memories, _ = _rgm_context_fixture(tmp_path)
    try:
        source = memories[0]["source_refs"][0]
        key = ("document", memories[0]["id"])
        if damage == "missing":
            registry.pop(key)
        elif damage == "wrong_document":
            source["doc_id"] = "different-document"
        elif damage == "wrong_chunk":
            memories[0]["id"] = memories[1]["id"]
        elif damage == "swapped_reference":
            registry[key] = registry[("document", memories[1]["id"])]
        elif damage == "hash":
            source["source_text_sha256"] = "0" * 64
        else:
            library.db.execute("UPDATE library_records SET content = content || 'altered'")
        with pytest.raises(ValueError):
            build_rgm_evidence_context(library, memories, registry)
    finally:
        library.db.close()




def _rgm_vector_only_fixture(tmp_path):
    library, registry, memories, raw = _rgm_context_fixture(tmp_path)
    original = {}
    for memory in memories:
        ref = memory["source_refs"][0]
        memory.update(content=raw[ref["start"]:ref["end"]], anchor_type="reference_doc",
                      semantic_tags=["DOC:document"])
        original[("document", memory["id"])] = copy.deepcopy(memory)
        memory.pop("source_refs")
        memory["source"] = "vector_only"
    return library, registry, memories, original


def test_rgm_vector_only_recovers_only_authenticated_original_references(tmp_path):
    library, registry, memories, originals = _rgm_vector_only_fixture(tmp_path)
    before = copy.deepcopy((memories, originals))
    try:
        with pytest.raises(ValueError, match="one source reference"):
            build_rgm_evidence_context(library, memories, registry)
        packet = build_rgm_evidence_context(library, memories, registry,
            original_anchors_by_source=originals)
        assert [m["id"] for m in packet["memories"]] == [m["id"] for m in memories]
        for old, new in zip(memories, packet["memories"]):
            assert all(new[k] == v for k, v in old.items())
            assert new["source_refs"] == originals[("document", old["id"])]["source_refs"]
            assert new["source_reference_recovery"]["method"] == "original_document_anchor"
        assert (memories, originals) == before
    finally: library.db.close()


@pytest.mark.parametrize("damage", ["unknown_anchor", "wrong_document", "multiple_documents", "no_tags",
    "changed_candidate", "changed_both", "truncated", "wrong_anchor_reference", "present_empty_refs",
    "present_bad_refs", "not_vector", "not_document", "corrupt_corpus"])
def test_rgm_vector_only_reference_recovery_refuses_unverified_or_conflicting_data(tmp_path, damage):
    library, registry, memories, originals = _rgm_vector_only_fixture(tmp_path)
    memory = memories[0]; key = ("document", memory["id"])
    try:
        if damage == "unknown_anchor": originals.pop(key)
        elif damage == "wrong_document": memory["semantic_tags"] = ["DOC:other"]
        elif damage == "multiple_documents": memory["semantic_tags"].append("DOC:other")
        elif damage == "no_tags": memory.pop("semantic_tags")
        elif damage == "changed_candidate": memory["content"] += " altered"
        elif damage == "changed_both":
            memory["content"] += " altered"; originals[key]["content"] = memory["content"]
        elif damage == "truncated": memory["content"] = memory["content"][:50]
        elif damage == "wrong_anchor_reference": originals[key]["source_refs"][0]["doc_id"] = "other"
        elif damage == "present_empty_refs": memory["source_refs"] = []
        elif damage == "present_bad_refs": memory["source_refs"] = [dict(doc_id="other",chunk_id=memory["id"])]
        elif damage == "not_vector": memory["source"] = "other"
        elif damage == "not_document": memory["anchor_type"] = "identity"
        else: library.db.execute("UPDATE library_records SET content = content || 'altered'")
        with pytest.raises(ValueError):
            build_rgm_evidence_context(library, memories, registry, original_anchors_by_source=originals)
    finally: library.db.close()


def test_stream1_retrieval_route_uses_only_the_prepared_project_session():
    calls = []
    expected = {"status": "matched", "matches": [{"source_id": "10.3"}]}

    def retrieve(question):
        calls.append(question)
        return expected

    gateway = TomGateway.__new__(TomGateway)
    gateway.stream1_document_indexes = {"m12": types.SimpleNamespace(retrieve=retrieve)}
    gateway.project = lambda *_: pytest.fail("Stream 1 retrieval must not load the legacy Tree")
    assert gateway.handle("POST", "/document/stream1/retrieve", {
        "project_id": "m12", "question": "When must the report be issued?",
    }) == (200, expected)
    assert calls == ["When must the report be issued?"]
    status, result = gateway.handle("POST", "/document/stream1/retrieve", {
        "project_id": "another-project", "question": "When must the report be issued?",
    })
    assert status == 503 and "no prepared Stream 1" in result["error"]
    assert len(calls) == 1


@pytest.mark.parametrize("value", [[[1.0]], [[0.0] * 32] * 32, [[float("nan")] * 32] * 32])
def test_stream1_retrieval_rejects_invalid_matrix_inputs(value):
    from gateway.document_tree import Stream1DocumentIndex
    with pytest.raises(ValueError, match="32 by 32 matrix"):
        Stream1DocumentIndex._matrix(value)


def _inspection_payload(**changes):
    return {"project_id": "inspection-project", "project_state_version": 1,
            "opt_in": True, "explicit_inspect": True, "adapter_id": "v14-4380",
            "extraction_mode": "saved", "source": {"kind": "saved_example"},
            "query_stream1": False, **changes}


def test_gemma_inspection_releases_token_probability_arrays():
    import gc
    import weakref
    class ProbabilityArray:
        pass
    arrays = []
    def stream():
        for index, text in enumerate(("first", " second", "")):
            gc.collect()
            assert sum(reference() is not None for reference in arrays) <= 1
            probabilities = ProbabilityArray()
            arrays.append(weakref.ref(probabilities))
            yield types.SimpleNamespace(text=text, token=106 if index == 2 else 7,
                finish_reason="stop" if index == 2 else None, prompt_tokens=20,
                generation_tokens=index + 1, peak_memory=14.25, logprobs=probabilities)
    result = GemmaInspection.collect_extraction(stream(), {106})
    gc.collect()
    assert all(reference() is None for reference in arrays)
    assert result["raw"] == "first second" and result["tokens"] == 3
    assert result["engine_peak_bytes"] == 14_250_000_000


@pytest.mark.parametrize("ending", [None, "length", "wrong_stop_token"])
def test_gemma_inspection_requires_complete_generation(ending):
    chunks = [] if ending is None else [types.SimpleNamespace(text="{}", token=7,
        finish_reason="stop" if ending == "wrong_stop_token" else ending,
        prompt_tokens=20, generation_tokens=1, peak_memory=14.25)]
    with pytest.raises(ValueError, match="complete end-of-turn"):
        GemmaInspection.collect_extraction(iter(chunks), {106})


def test_gemma_inspection_is_opt_in_and_saved_wiring_queries_real_isolated_stream1(tmp_path):
    gateway = types.SimpleNamespace(data_dir=tmp_path, _projects={})
    retained = tmp_path / "projects/inspection-project/retained.txt"
    retained.parent.mkdir(parents=True)
    retained.write_text("Existing project document; never used for experience teaching.")
    with pytest.raises(ValueError, match="explicit experimental"):
        GemmaInspection.inspect(gateway, _inspection_payload(opt_in=False))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = GemmaInspection.inspect(gateway, _inspection_payload(query_stream1=True, checkpoint_id="paired16-initial"))
    if GemmaInspection.package_hash() != GemmaInspection.STREAM_SHA:
        stages = {row["stage"]: row for row in result["stages"]}
        assert all(stages[name]["status"] == "passed" for name in (
            "input", "extraction", "validation", "compilation",
        ))
        assert stages["runtime"]["status"] == "blocked"
        assert stages["runtime"]["reason"].endswith(
            "ValueError: Stream 1 source identity changed; "
            "contract review required\n"
        )
        assert result["purity"]["live_runtime"]["unchanged"]
        assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        return
    assert all(row["status"] == "passed" for row in result["stages"]), result["stages"]
    graph = result["graph"]
    assert [event["action"] for event in graph["events"]] == ["stop", "notify"]
    assert graph["events"][0]["condition"] == graph["events"][1]["condition"] == "p1"
    notify = graph["events"][1]
    assert notify["roles"]["recipient"] and notify["roles"]["authority"] is None
    assert result["compiled"]["event_order"] == ["e1", "e2"]
    assert [row["load_id"] for row in result["runtime"]["responses"]] == ["e1", "e2"]
    assert result["runtime"]["state_before"] == result["runtime"]["state_after"]
    assert result["runtime"]["checkpoint_sha256"] == GemmaInspection.CHECKPOINT_SHA
    assert "unavailable" in result["runtime"]["interpretation"]
    assert result["purity"]["live_runtime"]["unchanged"]
    assert result["extraction"]["local_generations"] == 0
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # Exact saved model output, not a freshly authored answer labelled as a replay.
    evidence = ROOT / ".tmp/event-graph-lora-v16-session-001/epoch-0/dev_predictions.jsonl"
    saved = next(json.loads(line) for line in evidence.read_text().splitlines() if json.loads(line)["id"] == "v8-dev-6-0")
    assert saved["raw"] == GemmaInspection.SAVED_RAW


@pytest.mark.parametrize("problem", ["invalid_span", "unresolved", "duplicate_field"])
def test_gemma_inspection_stops_invalid_or_unresolved_output_before_compilation(tmp_path, monkeypatch, problem):
    wire = json.loads(GemmaInspection.SAVED_RAW)
    if problem == "invalid_span":
        wire["events"][0]["evidence"][0] = {"token_start": 3, "token_end": 3}
    elif problem == "unresolved":
        wire["unresolved"] = [{"reason": "actor remains ambiguous", "evidence": [{"token_start": 3, "token_end": 7}]}]
    raw = json.dumps(wire)
    if problem == "duplicate_field":
        raw = raw.replace('"version":', '"version":"discarded-value","version":', 1)
    monkeypatch.setattr(GemmaInspection, "SAVED_RAW", raw)
    monkeypatch.setattr(GemmaInspection, "launch_worker", lambda *args: pytest.fail("downstream worker must not run"))
    result = GemmaInspection.inspect(types.SimpleNamespace(data_dir=tmp_path, _projects={}), _inspection_payload(query_stream1=True))
    assert next(s for s in result["stages"] if s["stage"] == "validation")["status"] == "blocked"
    assert "compiled" not in result and "runtime" not in result


def test_gemma_inspection_discloses_normalization_and_blocks_gpu_on_resource_conflict(tmp_path, monkeypatch):
    gateway = types.SimpleNamespace(data_dir=tmp_path, _projects={})
    wire = json.loads(GemmaInspection.SAVED_RAW)
    wire["predicates"][0]["negated"] = True
    monkeypatch.setattr(GemmaInspection, "SAVED_RAW", json.dumps(wire))
    result = GemmaInspection.inspect(gateway, _inspection_payload())
    assert result["normalization"]["changed"]
    assert result["original_bound_graph"]["predicates"][0]["negated"] is True
    assert result["graph"]["predicates"][0]["comparator"] == "LE"
    monkeypatch.setattr(GemmaInspection, "resources", lambda **kwargs: {"blockers": ["another job"]})
    monkeypatch.setattr(GemmaInspection, "launch_worker", lambda *args: pytest.fail("GPU must not load"))
    result = GemmaInspection.inspect(gateway, _inspection_payload(extraction_mode="gemma", source={"kind": "draft", "id": "draft", "text": "Stop excavation.", "start": 0, "end": 16}))
    assert next(s for s in result["stages"] if s["stage"] == "extraction")["status"] == "blocked"
    assert "compiled" not in result


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
            max_tokens=DOCUMENT_MAX_CHUNK_TOKENS,
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
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", row["analysis_digest"])
        load = json.loads(row["load_signature_json"])
        assert set(load) == set(CHANNELS)
        assert all(0.0 < value <= 1.0 for value in load.values())


def test_broad_research_cursor_is_bounded_restartable_and_snapshot_bound(tmp_path):
    provider = FixtureEmbeddingProvider()
    data_dir = tmp_path / "data"
    runtime = TomGateway(
        data_dir, document_embedding_provider=provider,
    ).project("documents")
    content = "private-prose-marker " * 1_100
    retained = runtime.ingest_document(
        "large.txt", content, "text/plain",
    )
    assert retained["chunk_count"] > 128
    protected = {
        path: path.read_bytes() for path in (
            runtime.document_index.path,
            runtime.document_index.db_path,
            runtime.state_dir / "library.sqlite3",
            runtime._tree_path,
            runtime._rgm_path,
        )
    }
    query = "What must the contractor do before it starts work under the deed?"
    first = runtime.preview_rank(query, 64, 32_000)
    first_coverage = first["document_research_trace"]["processing_coverage"]
    assert first_coverage["examined_count"] == 128
    assert first_coverage["unexamined_count"] == retained["chunk_count"] - 128
    assert first_coverage["cursor"]["complete"] is False
    assert first["document_research_trace"]["gateway_packet_selection"][
        "ready_to_send"
    ] is False
    cursor = first_coverage["cursor"]["continuation"]
    assert cursor is not None
    encoded_cursor, _ = cursor.split(".", 1)
    decoded_cursor = json.loads(base64.urlsafe_b64decode(encoded_cursor))
    assert len(decoded_cursor["candidates"]) == 128
    assert all("text" not in row for row in decoded_cursor["candidates"])
    assert "private-prose-marker" not in cursor
    assert all(path.read_bytes() == before for path, before in protected.items())

    tampered = json.loads(json.dumps(decoded_cursor))
    tampered["candidates"][0]["semantic_score"] = 1.0
    tampered_bytes = json.dumps(
        tampered, sort_keys=True, separators=(",", ":"),
    ).encode()
    # A client can recompute a public checksum, but cannot mint the local HMAC.
    tampered_cursor = (
        base64.urlsafe_b64encode(tampered_bytes).decode()
        + "." + hashlib.sha256(tampered_bytes).hexdigest()
    )
    with pytest.raises(ValueError, match="cursor authentication failed"):
        runtime.preview_rank(
            query, 64, 32_000, processing_cursor=tampered_cursor,
        )

    other = TomGateway(
        data_dir, document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("other-project")
    other.ingest_document("large.txt", content, "text/plain")
    with pytest.raises(ValueError, match="cursor authentication failed"):
        other.preview_rank(query, 64, 32_000, processing_cursor=cursor)

    # The continuation is stateless: a fresh gateway can resume the exact
    # frozen snapshot without a preview-side database or Tree write.
    restarted = TomGateway(
        data_dir, document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("documents")
    while cursor is not None:
        preview = restarted.preview_rank(
            query, 64, 32_000, processing_cursor=cursor,
        )
        coverage = preview["document_research_trace"]["processing_coverage"]
        cursor = coverage["cursor"]["continuation"]
    assert coverage["cursor"]["complete"] is True
    assert coverage["examined_count"] == retained["chunk_count"]
    assert coverage["unexamined_count"] == 0
    assert preview["document_research_trace"]["gateway_packet_selection"][
        "ready_to_send"
    ] is True
    assert all(path.read_bytes() == before for path, before in protected.items())

    partial = runtime.preview_rank(query, 64, 32_000)
    stale_cursor = partial["document_research_trace"]["processing_coverage"][
        "cursor"
    ]["continuation"]
    runtime.ingest_document(
        "changed.txt", "A later retained document changes the frozen snapshot.",
        "text/plain",
    )
    with pytest.raises(ValueError, match="cursor snapshot is stale"):
        runtime.preview_rank(
            query, 64, 32_000, processing_cursor=stale_cursor,
        )


def test_document_chunk_plan_reserves_retokenization_margin_and_is_linear_at_boundaries():
    text = ("A requirement ends here.     " * 400) + "Final requirement."
    offsets = [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]
    plan = build_token_chunks(
        text, offsets, max_tokens=DOCUMENT_MAX_CHUNK_TOKENS,
        max_source_chars=MAX_DOCUMENT_SOURCE_CHARS,
        max_chunks=MAX_DOCUMENT_CHUNKS,
    )
    assert max(row["token_end"] - row["token_start"] for row in plan) <= 188
    assert plan[0]["start"] == 0
    assert plan[-1]["end"] == len(text)


def test_prestart_relation_instrument_preserves_orientation_and_excludes_completion():
    query = "What must the contractor do before it starts construction work?"
    assert prestart_requirement_query(query) is True
    rows = prestart_relation_details(
        "Before commencing work, the contractor must lodge the plan. "
        "As a condition precedent to Substantial Completion, it must submit as-builts."
    )
    assert [row["relation"] for row in rows] == ["before_commencing"]
    assert rows[0]["actor_role"] == "contractor"
    principal = prestart_relation_details(
        "The Principal must, on or before the commencement deadline, effect insurance."
    )
    assert principal[0]["actor_role"] == "principal"


def test_prestart_relation_taxonomy_rejects_non_duty_temporal_phrases():
    cases = [
        (
            "The Contractor acknowledges that the files were provided on or before "
            "the date of this deed.\n\n(b) The Contractor must perform any nominated Work.",
            "EXCLUDED_RELATION_CROSSES_AUTHORED_BOUNDARY",
        ),
        (
            "The Contractor must rehabilitate the parcel to the state agreed with "
            "the owner prior to commencing the work.",
            "EXCLUDED_BASELINE_OR_REFERENCE_TIME",
        ),
        (
            "The Contractor must submit every draft. The review period will not "
            "commence until the Contractor formally submits the final report.",
            "EXCLUDED_NONCONSTRUCTION_TEMPORAL_TARGET",
        ),
    ]
    for text, reason in cases:
        rows = scan_prestart_relations(text)
        assert rows
        assert all(row["decision"] == "excluded" for row in rows)
        assert reason in {row["reason_code"] for row in rows}

    project_gate = scan_prestart_relations(
        "The rights and obligations of the parties will not commence unless and "
        "until all Conditions Precedent are satisfied or waived."
    )
    included = [row for row in project_gate if row["decision"] == "included"]
    assert [row["relation"] for row in included] == ["parties_commencement_condition"]
    assert included[0]["conditionality"] == "project_wide"
    assert any(
        row["reason_code"] == "EXCLUDED_WEAKER_RELATION_INSIDE_PROJECT_GATE"
        for row in project_gate
    )


def test_gateway_is_authoritative_for_targeted_and_broad_research_scope():
    assert parse_research_intent(
        "What must the contractor do before it starts construction work under the deed?"
    )["broad_document_research"] is True
    assert parse_research_intent(
        "List all prerequisites under the deed before commencement."
    )["broad_document_research"] is True
    assert parse_research_intent(
        "List all prerequisites under the deed."
    )["broad_document_research"] is True
    assert parse_research_intent(
        "What must the contractor do before bulk excavation?"
    )["broad_document_research"] is False


def test_authored_parent_context_is_complete_when_small_and_segmented_when_oversize():
    lead = (
        "15.4(a) If the Contractor believes the direction is a Change it must, "
        "if it wishes to claim:\n"
    )
    child = "(i) before commencing the directed work, give written notice.\n"
    trailing = "but no claim is available unless the notice is given.\n"
    small_text = lead + child + trailing
    small_entries = [
        {
            "entry_id": "parent", "identifier": "15.4(a)", "kind": "subclause",
            "status": "valid", "parent_entry_id": "root",
            "span": {"start": 0, "end": len(small_text)},
        },
        {
            "entry_id": "child", "identifier": "15.4(a)(i)", "kind": "subclause",
            "status": "valid", "parent_entry_id": "parent",
            "span": {"start": len(lead), "end": len(lead) + len(child)},
        },
    ]
    small = {
        "content": small_text,
        "declared_structure": {"clause_index": {"entries": small_entries}},
    }
    unit = evidence_unit_for_position(small, len(lead) + child.index("before"))
    assert unit["identifier"] == "15.4(a)"
    assert unit["source_segments"] == [{
        "start": 0,
        "end": len(small_text),
        "role": "governing_parent_unit",
        "entry_id": "parent",
        "identifier": "15.4(a)",
    }]
    assert small_text[unit["start"]:unit["end"]].endswith(trailing)

    filler = "(ii) unrelated sibling material. " * 100
    oversize_text = lead + child + filler
    oversize_entries = [
        {
            "entry_id": "parent", "identifier": "15.4(a)", "kind": "subclause",
            "status": "valid", "parent_entry_id": "root",
            "span": {"start": 0, "end": len(oversize_text)},
        },
        {
            "entry_id": "child", "identifier": "15.4(a)(i)", "kind": "subclause",
            "status": "valid", "parent_entry_id": "parent",
            "span": {"start": len(lead), "end": len(lead) + len(child)},
        },
        {
            "entry_id": "sibling", "identifier": "15.4(a)(ii)", "kind": "subclause",
            "status": "valid", "parent_entry_id": "parent",
            "span": {"start": len(lead) + len(child), "end": len(oversize_text)},
        },
    ]
    oversize = {
        "content": oversize_text,
        "declared_structure": {"clause_index": {"entries": oversize_entries}},
    }
    unit = evidence_unit_for_position(
        oversize, len(lead) + child.index("before"),
    )
    assert unit["identifier"] == "15.4(a)(i)"
    assert unit["oversize"] is False
    assert [row["role"] for row in unit["source_segments"]] == [
        "governing_parent_lead", "relation_unit",
    ]
    composite = "\n\n".join(
        oversize_text[row["start"]:row["end"]]
        for row in unit["source_segments"]
    )
    assert lead.strip() in composite
    assert child.strip() in composite
    assert "unrelated sibling material" not in composite

    condition = (
        "12.17(d) To the extent that affected soil cannot be reused on site without "
        "breaching the deed, clause 12.17(b) applies, however:\n"
    )
    shared = (
        "(i) the Principal and the Contractor will also be required to determine "
        "an agreed scope prior to performing offsite remediation; and\n"
    )
    later = "(ii) unrelated later cost allocation. " * 100
    conditional_text = condition + shared + later
    conditional = {
        "content": conditional_text,
        "declared_structure": {"clause_index": {"entries": [
            {
                "entry_id": "condition", "identifier": "12.17(d)",
                "kind": "subclause", "status": "valid", "parent_entry_id": "root",
                "span": {"start": 0, "end": len(conditional_text)},
            },
            {
                "entry_id": "shared", "identifier": "12.17(d)(i)",
                "kind": "subclause", "status": "valid", "parent_entry_id": "condition",
                "span": {"start": len(condition), "end": len(condition) + len(shared)},
            },
            {
                "entry_id": "later", "identifier": "12.17(d)(ii)",
                "kind": "subclause", "status": "valid", "parent_entry_id": "condition",
                "span": {"start": len(condition) + len(shared), "end": len(conditional_text)},
            },
        ]}},
    }
    unit = evidence_unit_for_position(
        conditional, len(condition) + shared.index("prior"),
    )
    composite = "\n\n".join(
        conditional_text[row["start"]:row["end"]]
        for row in unit["source_segments"]
    )
    assert condition.strip() in composite
    assert shared.strip() in composite
    assert "unrelated later cost allocation" not in composite
    assert parse_research_intent(
        "What warranty applies after final completion?"
    )["broad_document_research"] is False


def test_nearest_authored_subject_and_duty_frame_control_prestart_admission(tmp_path):
    text = (
        "1. Interface notice\n"
        "1.1 To the extent that interface work is construction work, the Principal:\n"
        "(a) must give the interface manager prior notice before such construction "
        "work commences.\n\n"
        "2. Contractor gate\n"
        "2.1 Before commencing construction work, the Contractor must lodge the "
        "approved work plan.\n\n"
        "3. Engagement duration\n"
        "3.1 The Contractor's engagement will end immediately before rectification "
        "work commences.\n\n"
        "4. Shared condition\n"
        "4.1 The Principal and the Contractor will also be required to determine an "
        "agreed scope prior to performance of remediation activities.\n"
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("contract")
    retained = runtime.ingest_document("instrument.txt", text, "text/plain")
    preview = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    identifiers = [
        row["matched_clause_identifier"]
        for row in preview["ranked_document_chunks"]
    ]
    assert identifiers == ["2.1", "4.1"]
    decisions = preview["document_research_trace"]["authored_unit_scan"]
    assert any(
        row["clause_identifier"] == "1.1"
        and row["decision"] == "EXCLUDED_DIRECT_AUTHORED_ACTOR_MISMATCH"
        and any(relation["actor_role"] == "principal" and relation["decision"] == "excluded" for relation in row["relations"])
        for row in decisions
    )
    assert any(
        row["clause_identifier"] == "3.1"
        and row["decision"] == "EXCLUDED_NO_EXPLICIT_CONTRACTOR_DUTY"
        for row in preview["document_research_trace"]["clause_expansion"]
    )


def test_pronoun_duty_resolves_grammatical_actor_not_possessive_reference(tmp_path):
    text = (
        "15.4 Contractor direction\n"
        "(a) If the Contractor believes any Direction of the Principal's Representative "
        "constitutes a Change it must, if it wishes to make a Claim:\n"
        "(i) before commencing work on the Direction, give notice to the Principal's "
        "Representative.\n\n"
        "15.5 Principal direction\n"
        "(a) If the Principal believes the Contractor's proposal requires review it must:\n"
        "(i) before construction work commences, give its reviewer notice.\n"
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("contract")
    runtime.ingest_document("directions.txt", text, "text/plain")
    preview = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    assert [
        row["matched_clause_identifier"]
        for row in preview["ranked_document_chunks"]
    ] == ["15.4(a)"]
    admitted = [
        row for row in preview["document_research_trace"]["clause_expansion"]
        if row["decision"].startswith("EXPANDED")
    ]
    assert admitted
    actor = admitted[0]["actor_support"]
    assert actor.get("role") == "contractor" or "contractor" in actor.get("roles", [])
    assert any(
        str(row["clause_identifier"]).startswith("15.5")
        and row["decision"] == "EXCLUDED_DIRECT_AUTHORED_ACTOR_MISMATCH"
        for row in preview["document_research_trace"]["authored_unit_scan"]
    )


def test_nearest_modal_subject_beats_conditional_actor_and_object(tmp_path):
    text = (
        "1.1 If requested by the Principal, the SCAW Contractor must produce "
        "the required safety evidence to the Principal before the SCAW Contractor "
        "or a Subcontractor commences such work.\n\n"
        "2.1 If requested by the Contractor, the Principal must give its notice "
        "to the Contractor before construction work commences.\n"
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("contract")
    runtime.ingest_document("directions.txt", text, "text/plain")
    preview = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    assert [
        row["matched_clause_identifier"]
        for row in preview["ranked_document_chunks"]
    ] == ["1.1"]
    admitted = next(
        row for row in preview["document_research_trace"]["clause_expansion"]
        if row.get("clause_identifier") == "1.1"
        and row.get("actor_support", {}).get("role") == "contractor"
    )
    assert admitted["actor_support"]["role"] == "contractor"
    assert admitted["actor_support"]["kind"] == (
        "same_relation_unit_nearest_modal_subject"
    )


def test_mixed_case_enumerator_fails_closed_before_spilling_unrelated_text(tmp_path):
    text = (
        "4. Remediation gate\n"
        "4.1 The Contractor may not commence remediation work unless and until:\n"
        "(i) the plan is approved; and\n"
        "(Hi) the estimate is submitted.\n\n"
        "(G) an unrelated change will be valued separately.\n\n"
        "5. Clean gate\n"
        "5.1 Before commencing construction work, the Contractor must lodge the plan.\n\n"
        "6. OCR-preserving gate\n"
        "6.1 The Contractor may not commence remediation work unless and until:\n"
        "(i) the plan is approved; and\n"
        "(Hi) the estimate is submitted.\n"
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("contract")
    runtime.ingest_document("instrument.txt", text, "text/plain")
    preview = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    rows = preview["ranked_document_chunks"]
    assert {
        row["matched_clause_identifier"]
        for row in rows
    } == {"5.1", "6.1"}
    assert "(Hi) the estimate is submitted" in next(
        row["text"] for row in rows if row["matched_clause_identifier"] == "6.1"
    )
    assert any(
        row["decision"] == "EXCLUDED_MALFORMED_AUTHORED_NUMBERING"
        and row["numbering_issue"]["reason_code"] == "MIXED_CASE_ENUMERATOR"
        for row in preview["document_research_trace"]["clause_expansion"]
    )


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


def test_legacy_preview_admits_bounded_document_evidence_without_state_mutation(tmp_path):
    embeddings = FixtureEmbeddingProvider(axis=0)
    runtime = TomGateway(
        tmp_path, document_embedding_provider=embeddings,
    ).project("documents")
    document = runtime.ingest_document(
        "contract.txt", "Before starting work, the Contractor must submit the plan.",
        "text/plain",
    )
    before = _state(runtime)
    preview = runtime.preview_rank(
        "What must the Contractor do before starting work?", 10, 2000,
    )
    assert _state(runtime) == before
    assert preview["ranked_anchors"] == []
    assert len(preview["ranked_document_chunks"]) == 1
    ranked = preview["ranked_document_chunks"][0]
    assert ranked["id"] == f'{document["document_id"]}:chunk:0'
    assert ranked["document_id"] == document["document_id"]
    assert ranked["display_name"] == "contract.txt"
    assert ranked["text"] == "Before starting work, the Contractor must submit the plan."
    assert ranked["packet_eligible"] is True
    assert ranked["structural_signature"]["document_tree_version"] == (
        "tom-assist-project-document-tree/2.0"
    )
    assert ranked["structural_signature"]["chunk_analysis_digest"]
    assert ranked["excerpt_start"] == ranked["start"] == 0
    assert ranked["excerpt_end"] == ranked["end"]
    assert ranked["excerpt_sha256"].startswith("sha256:")
    assert preview == runtime.preview_rank(
        "What must the Contractor do before starting work?", 10, 2000,
    )
    assert _state(runtime) == before


def test_document_hybrid_rank_promotes_exact_clause_and_stops_at_next_clause():
    query = "What must the contractor do before it starts construction work under the deed?"
    vector = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    profile = build_semantic_profile(
        query,
        [{"start": 0, "end": len(query), "values": vector}],
        model="fixture/minilm",
        revision="fixture-v1",
    )
    distractor = "The Contractor performed early work under the deed."
    relevant = (
        "7.9 Long service levy\n\nBefore commencing any construction work under "
        "this deed, the Contractor must pay the levy and produce evidence of "
        "payment.\n\n11.3 Review of Project Plans\n\nUnrelated next clause."
    )

    def chunk(document_id, text):
        return {
            "document_id": document_id,
            "chunk_index": 0,
            "start": 0,
            "end": len(text),
            "text": text,
            "text_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
            "passage_vector": encode_vector_f32(vector),
            "display_name": "deed.txt",
        }

    ranked = rank_document_chunks_for_packet(
        query,
        profile,
        [chunk("document-a", distractor), chunk("document-b", relevant)],
        k=10,
        max_chars=2000,
    )
    assert ranked[0]["id"] == "document-b:chunk:0"
    assert ranked[0]["dense_rank"] == 2
    assert ranked[0]["lexical_rank"] == 1
    assert ranked[0]["text"].startswith("7.9 Long service levy")
    assert "must pay the levy and produce evidence" in ranked[0]["text"]
    assert "11.3 Review" not in ranked[0]["text"]


def test_native_tree_rank_replaces_historical_branch_overlap_as_admission_gate():
    query = "What must the contractor do before it starts construction work under the deed?"
    vector = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    profile = build_semantic_profile(
        query, [{"start": 0, "end": len(query), "values": vector}],
        model="fixture/minilm", revision="fixture-v1",
    )
    texts = {
        "retrieved": "1.1 Before starting construction work, the Contractor must submit a plan.",
        "historic-miss": "2.1 Before starting construction work, the Contractor must obtain approval.",
    }
    chunks, sources = [], {}
    for document_id in ["retrieved", "historic-miss"]:
        text = texts[document_id]
        chunks.append({
            "document_id": document_id, "chunk_index": 0,
            "start": 0, "end": len(text), "text": text,
            "text_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
            "passage_vector": encode_vector_f32(vector),
            "display_name": "fixture.txt", "analysis_digest": "sha256:receipt",
            "address_branches": [{"branch_id": document_id, "rank": 1}],
        })
        sources[document_id] = {
            "document_id": document_id, "content": text,
            "declared_structure": {"clause_index": {"entries": [{
                "entry_id": f"clause-{document_id}",
                "identifier": "1.1" if document_id == "retrieved" else "2.1",
                "kind": "clause", "status": "valid",
                "span": {"start": 0, "end": len(text)},
            }]}},
        }
    scores = {
        "retrieved:chunk:0": {
            "score": 0.91, "matched_branch_id": "current-a", "native_rank": 1,
            "historical_branch_overlap_count": 1,
        },
        "historic-miss:chunk:0": {
            "score": 0.90, "matched_branch_id": "current-b", "native_rank": 2,
            "historical_branch_overlap_count": 0,
        },
    }
    rows, trace = rank_document_chunks_for_packet(
        query, profile, chunks, k=24, max_chars=12000,
        structural_scores=scores, structural_telemetry={"informative": True},
        document_sources=sources, return_trace=True,
    )
    assert {row["document_id"] for row in rows} == {"retrieved", "historic-miss"}
    assert all(
        row["decision"] == "EXAMINED_TREE_NATIVE_COMPREHENSIVE"
        for row in trace["tree_candidate_retrieval"]
    )
    historic = next(
        row for row in trace["tree_candidate_retrieval"]
        if row["document_id"] == "historic-miss"
    )
    assert historic["historical_branch_overlap_count"] == 0
    assert historic["native_rank"] == 2
    assert trace["processing_coverage"]["examined_count"] == 2
    assert trace["processing_coverage"]["unexamined_count"] == 0


def test_ordinary_question_follows_tree_rank_without_semantic_override_or_tail_scan():
    query = "When is the inspection report due?"
    match = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    other = [0.0, 1.0] + [0.0] * (EMBEDDING_DIMENSION - 2)
    profile = build_semantic_profile(
        query, [{"start": 0, "end": len(query), "values": match}],
        model="fixture/minilm", revision="fixture-v1",
    )

    class UnexaminedText:
        def __str__(self):
            raise AssertionError("text outside the bounded selection was read")

    chunks, scores = [], {}
    for index in range(70):
        text = "The inspection report is due on Monday." if index in (1, 69) else "Archive the drawing."
        chunks.append({
            "document_id": "project-document", "chunk_index": index,
            "display_name": "fixture.txt", "start": index * 100,
            "end": index * 100 + len(text),
            "text": UnexaminedText() if index >= 64 else text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "passage_vector": encode_vector_f32(match if index in (1, 69) else other),
            "analysis_digest": f"sha256:{index:064x}",
        })
        scores[f"project-document:chunk:{index}"] = {
            "native_rank": index + 1, "score": 0.99 - index * 0.00001,
            "matched_branch_id": "native-branch",
        }
    rows, trace = rank_document_chunks_for_packet(
        query, profile, chunks, k=1, max_chars=500,
        structural_scores=scores, structural_telemetry={"informative": True},
        return_trace=True,
    )
    assert rows[0]["chunk_index"] == 0
    assert rows[0]["structural_rank"] == 1
    assert rows[0]["text"] == "Archive the drawing."
    assert rows[0]["score_space"] == "native_document_tree_rank"
    assert rows[0]["semantic_score"] < 0.01
    assert trace["processing_coverage"]["metadata_scored_count"] == 0
    assert trace["processing_coverage"]["policy"] == "tree_native_bounded_page"
    assert trace["processing_coverage"]["examined_count"] == 64
    assert trace["processing_coverage"]["unexamined_count"] == 6
    assert trace["processing_coverage"]["cursor"]["next_native_rank"] is None
    expected = next(row for row in trace["tree_candidate_retrieval"] if row["chunk_index"] == 69)
    assert expected["native_rank"] == 70
    assert "selection_rank" not in expected
    assert expected["decision"] == "UNEXAMINED_TREE_NATIVE_PAGE_LIMIT"
    reversed_rows, reversed_trace = rank_document_chunks_for_packet(
        query, profile, list(reversed(chunks)), k=1, max_chars=500,
        structural_scores=scores, structural_telemetry={"informative": True},
        return_trace=True,
    )
    assert (reversed_rows, reversed_trace) == (rows, trace)
    flat_rows = rank_document_chunks_for_packet(
        query, profile, chunks, k=1, max_chars=500,
        structural_scores=scores, structural_telemetry={"informative": False},
    )
    assert flat_rows[0]["chunk_index"] == 0
    # Change only native ranking: the promoted record now supplies the result.
    # Materialise its text now that it is inside the Tree-selected page.
    chunks[69]["text"] = "The inspection report is due on Monday."
    scores["project-document:chunk:0"]["native_rank"] = 70
    scores["project-document:chunk:69"]["native_rank"] = 1
    promoted = rank_document_chunks_for_packet(
        query, profile, chunks, k=1, max_chars=500,
        structural_scores=scores, structural_telemetry={"informative": True},
    )
    assert promoted[0]["chunk_index"] == 69
    assert promoted[0]["structural_rank"] == 1
    scores["project-document:chunk:69"]["matched_branch_id"] = ""
    with pytest.raises(ValueError, match="valid native Tree result"):
        rank_document_chunks_for_packet(
            query, profile, chunks, k=1, max_chars=500, structural_scores=scores,
        )


def test_exact_reference_can_reach_beyond_bounded_tree_page_and_cycle_is_reported():
    from gateway.declared_structure import build_declared_structure

    query = "Before this work, what must the contractor do?"
    vector = [1.0] + [0.0] * (EMBEDDING_DIMENSION - 1)
    profile = build_semantic_profile(
        query, [{"start": 0, "end": len(query), "values": vector}],
        model="fixture/minilm", revision="fixture-v1",
    )
    clauses = [
        "1.1 Before this work starts, the Contractor must inspect clause 1.66."
    ] + [
        f"1.{index} After completion, archive record {index}."
        for index in range(2, 66)
    ] + [
        "1.66 Before this work starts, the Contractor must obtain approval under clause 1.1."
    ]
    text = "1. GENERAL\n\n" + "\n\n".join(clauses)
    structure = build_declared_structure(text)
    by_identifier = {
        row["identifier"]: row
        for row in structure["clause_index"]["entries"]
        if row["kind"] == "clause"
    }
    document_id = "document-reference-page"
    chunks = []
    structural_scores = {}
    for index in range(1, 67):
        identifier = f"1.{index}"
        entry = by_identifier[identifier]
        start, end = entry["span"]["start"], entry["span"]["end"]
        chunk_index = index - 1
        row_id = f"{document_id}:chunk:{chunk_index}"
        chunk_text = text[start:end]
        chunks.append({
            "document_id": document_id,
            "display_name": "reference.txt",
            "chunk_index": chunk_index,
            "start": start,
            "end": end,
            "text": chunk_text,
            "text_sha256": "sha256:" + hashlib.sha256(chunk_text.encode()).hexdigest(),
            "passage_vector": encode_vector_f32(vector),
            "analysis_digest": f"sha256:{chunk_index:064x}",
            "address_branches": [{"branch_id": f"branch-{index}", "rank": 1}],
            "clause_provenance": [entry],
        })
        structural_scores[row_id] = {
            "score": 1.0 - index / 1000.0,
            "matched_branch_id": f"branch-{index}",
            "native_rank": index,
            "historical_branch_overlap_count": 0,
        }
    source = {
        "document_id": document_id,
        "display_name": "reference.txt",
        "content": text,
        "content_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
        "byte_length": len(text.encode()),
        "chunk_count": len(chunks),
        "declared_structure": structure,
    }
    rows, trace = rank_document_chunks_for_packet(
        query, profile, chunks, k=24, max_chars=12_000,
        structural_scores=structural_scores,
        structural_telemetry={"informative": True, "tree_digest": "sha256:tree"},
        document_sources={document_id: source}, return_trace=True,
    )
    assert trace["intent"]["broad_document_research"] is False
    assert any(
        row["chunk_index"] == 65
        and row["decision"] == "UNEXAMINED_TREE_NATIVE_PAGE_LIMIT"
        for row in trace["tree_candidate_retrieval"]
    )
    assert {row["matched_clause_identifier"] for row in rows} == {"1.1", "1.66"}, (
        trace["cross_reference_traversal"]
    )
    assert any(
        row["target_identifier"] == "1.66"
        and row["decision"] == "ADMITTED_LINKED_TEMPORAL_DUTY"
        for row in trace["cross_reference_traversal"]
    )
    assert any(
        row["decision"] == "REFERENCE_CYCLE_DETECTED"
        for row in trace["cross_reference_traversal"]
    )


def test_shadow_reports_document_dense_rank_and_packet_eligibility_then_withdraws(tmp_path):
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
    assert report["ranking"][0]["packet_eligible"] is True
    assert report["packet_admission_enabled"] is True
    assert report["ranking"][0]["structural_signature"] is None
    assert preview["ranked_document_chunks"][0]["document_id"] == document["document_id"]
    assert all(not row["id"].startswith("document-") for row in preview["ranked_anchors"])
    assert all(not branch.startswith("document-") for branch in preview["activated_branch_ids"])
    retained = runtime.withdraw_document(document["document_id"], "2026-09-03T00:00:00Z")
    assert retained["tombstoned_at"] == "2026-09-03T00:00:00Z"
    assert runtime.list_documents() == []
    assert runtime.list_documents(include_withdrawn=True)[0]["document_id"] == document["document_id"]
    after = runtime.preview_rank("A causes B.", 10, 2000)
    assert after["shadow_retrieval_comparison"]["document_chunk_dense_channel"][
        "document_chunk_count"
    ] == 0
    assert after["ranked_document_chunks"] == []


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


def test_documents_and_diagnostics_are_strictly_project_local(tmp_path):
    gateway = TomGateway(
        tmp_path, document_embedding_provider=FixtureEmbeddingProvider(),
    )
    left = gateway.project("left-project")
    right = gateway.project("right-project")
    retained = left.ingest_document(
        "left-only.md", "Only the left project may retrieve this requirement.",
        "text/markdown",
    )

    assert [row["document_id"] for row in left.list_documents()] == [
        retained["document_id"]
    ]
    assert right.list_documents() == []
    assert left.state_dir != right.state_dir
    assert left.library.db.execute("PRAGMA database_list").fetchone()[2] != (
        right.library.db.execute("PRAGMA database_list").fetchone()[2]
    )
    assert left.memory_diagnostics()["document_count"] == 1
    assert left.memory_diagnostics()["document_chunk_count"] == 1
    assert right.memory_diagnostics()["document_count"] == 0
    assert right.preview_rank("left project requirement", 10, 2000)[
        "ranked_document_chunks"
    ] == []


def test_each_project_owns_a_seeded_document_tree_and_preview_is_byte_pure(tmp_path):
    provider = FixtureEmbeddingProvider(axis=0)
    data = tmp_path / "data"
    gateway = TomGateway(data, document_embedding_provider=provider)
    left = gateway.project("left-project")
    right = gateway.project("right-project")
    assert left.document_index is not right.document_index
    assert left.document_index.path == (
        data.resolve() / "projects/left-project/tom/document-index/tree_state.json"
    )
    assert right.document_index.path == (
        data.resolve() / "projects/right-project/tom/document-index/tree_state.json"
    )
    assert left.document_index.durable_tree_bytes() == gateway.seed.artifact_path.read_bytes()
    assert right.document_index.durable_tree_bytes() == gateway.seed.artifact_path.read_bytes()

    left_experience_before = left.serialized_state_bytes()
    right_experience_before = right.serialized_state_bytes()
    left_doc = left.ingest_document(
        "left.txt",
        "Before work starts, the left contractor must submit the approved safety plan.",
        "text/plain",
    )
    assert right.document_index.durable_tree_bytes() == gateway.seed.artifact_path.read_bytes()
    assert right.document_index.engine.state.tick == gateway.seed.tick
    right_doc = right.ingest_document(
        "right.txt",
        "The right project warranty expires after final completion.",
        "text/plain",
    )
    assert left.serialized_state_bytes() == left_experience_before
    assert right.serialized_state_bytes() == right_experience_before
    assert left.document_index.engine.state.tick == gateway.seed.tick + 1
    assert right.document_index.engine.state.tick == gateway.seed.tick + 1
    assert left.document_index.project_commit_count("left-project") == 1
    assert right.document_index.project_commit_count("right-project") == 1
    assert {
        row[0] for row in left.document_index.db.execute(
            "SELECT DISTINCT project_id FROM chunk_commits"
        )
    } == {"left-project"}
    assert {
        row[0] for row in right.document_index.db.execute(
            "SELECT DISTINCT project_id FROM chunk_commits"
        )
    } == {"right-project"}
    with pytest.raises(ValueError, match="foreign project"):
        left.document_index.project_commits("right-project")

    left_tree_before = left.document_index.durable_tree_bytes()
    right_tree_before = right.document_index.durable_tree_bytes()
    left_before = left.serialized_state_bytes()
    preview = left.preview_rank("What must happen before work starts?", 10, 2000)
    assert [row["document_id"] for row in preview["ranked_document_chunks"]] == [
        left_doc["document_id"]
    ]
    assert right_doc["document_id"] not in json.dumps(preview)
    assert left.document_index.durable_tree_bytes() == left_tree_before
    assert right.document_index.durable_tree_bytes() == right_tree_before
    assert left.serialized_state_bytes() == left_before

    left.document_index.db.close()
    right.document_index.db.close()
    restarted = TomGateway(data, document_embedding_provider=FixtureEmbeddingProvider(axis=0))
    restored_left = restarted.project("left-project")
    restored_right = restarted.project("right-project")
    assert restored_left.document_index.durable_tree_bytes() == left_tree_before
    assert restored_right.document_index.durable_tree_bytes() == right_tree_before
    assert restored_left.document_index.engine.state.tick == restarted.seed.tick + 1
    assert restored_right.document_index.engine.state.tick == restarted.seed.tick + 1
    restored = restored_left.preview_rank(
        "What must happen before work starts?", 10, 2000,
    )
    assert [row["document_id"] for row in restored["ranked_document_chunks"]] == [
        left_doc["document_id"]
    ]
    assert right_doc["document_id"] not in json.dumps(restored)


def test_legacy_first_preview_is_inert_until_explicit_project_tree_migration(tmp_path):
    provider = FixtureEmbeddingProvider(axis=0)
    data = tmp_path / "data"
    initial = TomGateway(data, document_embedding_provider=provider)
    runtime = initial.project("legacy-project")
    retained = runtime.ingest_document(
        "legacy.txt",
        "Before work starts, the Contractor must lodge the approved plan.",
        "text/plain",
    )
    experience_before = runtime.serialized_state_bytes()
    source_before = runtime.get_document(retained["document_id"])
    runtime.document_index.db.close()
    runtime.library.db.close()

    # Model the accepted historical layout without deleting its evidence.
    shared = data / "document-index"
    shutil.copytree(
        data / "projects/legacy-project/tom/document-index", shared,
    )
    shutil.rmtree(data / "projects/legacy-project/tom/document-index")
    protected = {
        str(path.relative_to(data)): digest_file(path)
        for path in data.rglob("*") if path.is_file()
    }

    restarted = TomGateway(data, document_embedding_provider=FixtureEmbeddingProvider(axis=0))
    status, failure = restarted.handle("POST", "/preview/rank", {
        "project_id": "legacy-project", "user_text": "What must happen before work?",
    })
    assert status == 400
    assert failure["error"] == "DocumentTreeMigrationRequired"
    assert not (data / "projects/legacy-project/tom/document-index").exists()
    assert {
        str(path.relative_to(data)): digest_file(path)
        for path in data.rglob("*") if path.is_file()
    } == protected

    status, migrated = restarted.handle("POST", "/document/tree/migrate", {
        "project_id": "legacy-project", "explicit_user_action": True,
    })
    assert status == 200
    assert migrated["status"] == "migrated"
    assert migrated["document_tree"]["isolation"] == "dedicated_project_tree"
    assert migrated["source_inventory_unchanged"] is True
    assert migrated["experience_tree_unchanged"] is True
    assert migrated["canonical_seed_unchanged"] is True
    assert migrated["legacy_shared_index_preserved"] is True
    assert migrated["metadata_changes"] == []

    restored = restarted.project("legacy-project")
    assert restored.serialized_state_bytes() == experience_before
    assert restored.get_document(retained["document_id"]) == source_before
    assert restored.document_index.path == (
        data / "projects/legacy-project/tom/document-index/tree_state.json"
    )
    legacy_before = {
        path.name: digest_file(path) for path in shared.iterdir() if path.is_file()
    }
    dedicated_before = restored.document_index.durable_tree_bytes()
    restored.preview_rank("What must happen before work?", 10, 2000)
    assert restored.document_index.durable_tree_bytes() == dedicated_before
    assert {
        path.name: digest_file(path) for path in shared.iterdir() if path.is_file()
    } == legacy_before


def test_legacy_first_preview_sees_retained_document_committed_only_in_wal(tmp_path):
    data = tmp_path / "data"
    gateway = TomGateway(
        data, document_embedding_provider=FixtureEmbeddingProvider(),
    )
    state_dir = data / "projects/wal-legacy/tom"
    state_dir.mkdir(parents=True)
    library_path = state_dir / "library.sqlite3"
    library = PermanentLibrary(library_path)
    library.db.execute("PRAGMA wal_autocheckpoint=0")
    source = "Before work starts, the Contractor must lodge the plan."
    source_sha = hashlib.sha256(source.encode()).hexdigest()
    library.db.execute(
        "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "document-" + source_sha[:32], "wal.txt", source_sha, source,
            len(source.encode()), "text/plain", DOCUMENT_CHUNKING_VERSION,
            DOCUMENT_EMBEDDING_VERSION, 1, None,
        ),
    )
    wal_path = Path(str(library_path) + "-wal")
    assert wal_path.is_file() and wal_path.stat().st_size > 0
    protected = {
        library_path: library_path.read_bytes(),
        wal_path: wal_path.read_bytes(),
    }

    status, failure = gateway.handle("POST", "/preview/rank", {
        "project_id": "wal-legacy",
        "user_text": "What must happen before work?",
    })
    assert status == 400
    assert failure["error"] == "DocumentTreeMigrationRequired"
    assert not (state_dir / "document-index").exists()
    assert all(path.read_bytes() == before for path, before in protected.items())
    library.db.close()


def test_document_tree_selects_prerequisite_section_over_completion_and_warranty(tmp_path):
    from gateway.dense_load17 import load_anchor_bank

    bank = load_anchor_bank()
    prerequisite = list(bank["channels"]["L_rule"][0]["vector"])
    completion = list(bank["channels"]["T_memory"][0]["vector"])
    warranty = list(bank["channels"]["T_future"][0]["vector"])

    class MultiSectionProvider:
        def embed_document(self, text):
            if text.startswith("What must"):
                spans = [(0, len(text), prerequisite)]
            else:
                second = text.index("10. Completion")
                third = text.index("20. Warranty")
                spans = [
                    (0, second + 8, prerequisite),
                    (second - 8, third + 8, completion),
                    (third - 8, len(text), warranty),
                ]
            return {
                "model": bank["embedding_model"],
                "revision": bank["embedding_revision"],
                "chunks": [
                    {"index": index, "start": start, "end": end, "values": vector}
                    for index, (start, end, vector) in enumerate(spans)
                ],
            }

    text = (
        "7. Prerequisites\nBefore commencing construction work, the Contractor must "
        "submit the safety plan and obtain the Principal's approval.\n\n"
        "10. Completion\nAfter the works are complete, the Contractor submits its "
        "completion report and final account.\n\n"
        "20. Warranty\nThe warranty remains in force for twelve months after final completion."
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=MultiSectionProvider(),
    ).project("contract")
    experience_before = runtime.serialized_state_bytes()
    retained = runtime.ingest_document("deed.txt", text, "text/plain")
    assert runtime.serialized_state_bytes() == experience_before

    preview = runtime.preview_rank(
        "What must the contractor do before commencing construction work?", 10, 2000,
    )
    assert preview["ranked_document_chunks"][0]["document_id"] == retained["document_id"]
    assert preview["ranked_document_chunks"][0]["chunk_index"] == 0
    assert "Before commencing construction work" in preview["ranked_document_chunks"][0]["text"]
    assert preview["ranked_document_chunks"][0]["structural_rank"] == 1
    assert preview["ranked_document_chunks"][0]["matched_document_branch_id"]
    assert preview["ranked_document_chunks"][0]["score_space"] == (
        "native_document_tree_rank"
    )
    assert [row["chunk_index"] for row in preview["ranked_document_chunks"]] == [0]
    by_chunk = {
        row["chunk_index"]: row
        for row in preview["document_research_trace"]["candidate_recall"]
    }
    assert by_chunk[0]["structural_resonance"] > 0
    retrieval = {row["chunk_index"]: row for row in preview["document_research_trace"]["tree_candidate_retrieval"]}
    for index in (1, 2):
        if index in by_chunk:
            assert by_chunk[0]["structural_resonance"] > by_chunk[index]["structural_resonance"]
        else:
            assert retrieval[index]["decision"] == "EXCLUDED_OUTSIDE_QUERY_TREE_REGION"
            assert retrieval[index]["branch_overlap_count"] == 0
    retained_rows = runtime.library.document_chunks(
        document_id=retained["document_id"],
    )
    assert len({row["analysis_digest"] for row in retained_rows}) == 3
    assert len({row["load_signature_json"] for row in retained_rows}) == 3
    receipts = runtime.document_index.project_commits("contract")
    assert len(receipts) == 3
    assert all(len(row["analysis"]["routing_basis_8d"]["vector_8d"]) == 8 for row in receipts)
    assert all(len(row["address_branches"]) == 32 for row in receipts)
    assert receipts[0]["clause_provenance"]


def test_document_tree_native_ranking_matches_pinned_reader_and_is_restart_stable(tmp_path, monkeypatch):
    from gateway.document_tree import DOCUMENT_ROUTING_BASIS_NAMES

    provider = FixtureEmbeddingProvider()
    gateway = TomGateway(tmp_path / "data", document_embedding_provider=provider)
    from agency.mechanics.preview_readout import rank_by_branch_resonance
    from agency.mechanics.sicd_msr_load import LoadSignature
    from agency.mechanics.sicd_msr_routing_basis import (
        project_load_signature_to_routing_basis,
    )
    from agency.mechanics.sicd_engine import TreeGrowthEngine
    runtime = gateway.project("contract")
    runtime.ingest_document(
        "deed.txt",
        "1.1 Before commencing work, the Contractor must lodge a plan.\n\n"
        "2.1 After completion, the Contractor may archive the plan.",
        "text/plain",
    )
    receipt = runtime.document_index.project_commits("contract")[0]
    load = LoadSignature.from_mapping(
        receipt["analysis"]["load_signature"], strict=True,
    )
    projected = project_load_signature_to_routing_basis(load)
    assert receipt["analysis"]["routing_basis_8d"]["basis_names"] == list(
        DOCUMENT_ROUTING_BASIS_NAMES
    )
    assert receipt["analysis"]["routing_basis_8d"]["vector_8d"] == pytest.approx(
        projected.vector_8d, abs=1e-15,
    )
    assert runtime.document_index.engine.state.last_semantic_routing_basis_8d == (
        pytest.approx(projected.vector_8d, abs=1e-15)
    )
    seed_engine = TreeGrowthEngine.load(
        str(gateway.seed.artifact_path), cfg=runtime._new_engine_config(),
    )
    assert any(
        runtime.document_index.engine.state.branches[branch_id].sem_vec
        != seed_engine.state.branches[branch_id].sem_vec
        for branch_id in seed_engine.state.branches
    )
    query = "What must the contractor do before it starts construction work under the deed?"
    profile = build_document_query_profile(query, provider)
    chunks = runtime.library.document_chunks(active_only=True)
    metadata = runtime.document_index.project_chunk_metadata("contract")
    chunks = [
        {**row, **metadata[(row["document_id"], row["chunk_index"])]}
        for row in chunks
    ]
    _, cohort, _ = runtime.document_index.query_address(query, profile)
    before = runtime.document_index.durable_tree_bytes()
    scores, telemetry = runtime.document_index.structural_scores(
        "contract", chunks, cohort,
    )
    records = {
        f"{row['document_id']}:chunk:{row['chunk_index']}": {
            "leaf_vec": row["routing_basis_8d"]["vector_8d"],
        }
        for row in sorted(chunks, key=lambda value: (
            value["document_id"], value["chunk_index"],
        ))
    }
    direct_ranks, direct_details = rank_by_branch_resonance(records, cohort)
    direct = {row_id: (branch_id, score) for row_id, branch_id, score in direct_details}
    assert set(scores) == set(direct_ranks) == set(direct)
    for row_id, row in scores.items():
        assert row["native_rank"] == direct_ranks[row_id]
        assert (row["matched_branch_id"], row["score"]) == direct[row_id]
        assert row["routing_basis_names"] == list(DOCUMENT_ROUTING_BASIS_NAMES)
        assert row["routing_vector_norm"] == pytest.approx(1.0, abs=1e-12)
        branch_vector = next(
            vector for branch_id, vector, _ in cohort
            if branch_id == row["matched_branch_id"]
        )
        receipt_vector = records[row_id]["leaf_vec"]
        manual_cosine = sum(
            left * right for left, right in zip(branch_vector, receipt_vector)
        ) / (
            math.sqrt(sum(value * value for value in branch_vector))
            * math.sqrt(sum(value * value for value in receipt_vector))
        )
        assert row["score"] == pytest.approx(manual_cosine, abs=1e-15)
    assert telemetry["reader"].endswith("rank_by_branch_resonance")
    assert telemetry["same_basis_validated"] is True
    assert telemetry["ranked_receipt_count"] == len(chunks)
    assert runtime.document_index.durable_tree_bytes() == before

    del runtime, gateway
    restarted_gateway = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    )
    restarted = restarted_gateway.project("contract")
    metadata = restarted.document_index.project_chunk_metadata("contract")
    restarted_chunks = [
        {**row, **metadata[(row["document_id"], row["chunk_index"])]}
        for row in restarted.library.document_chunks(active_only=True)
    ]
    restarted_profile = build_document_query_profile(query, FixtureEmbeddingProvider())
    _, restarted_cohort, _ = restarted.document_index.query_address(
        query, restarted_profile,
    )
    restarted_scores, restarted_telemetry = restarted.document_index.structural_scores(
        "contract", restarted_chunks, restarted_cohort,
    )
    assert restarted_scores == scores
    assert restarted_telemetry == telemetry
    assert restarted.document_index.durable_tree_bytes() == before
    # The real preview endpoint must stop if its native reader cannot run.
    # It must not silently return independently selected semantic evidence.
    import agency.mechanics.preview_readout as native_reader
    def unavailable(*args, **kwargs):
        raise ValueError("native Tree reader unavailable for dependency check")
    request = {"project_id": "contract", "user_text": "When is the plan due?"}
    experience_before = restarted.serialized_state_bytes()
    with monkeypatch.context() as check:
        check.setattr(native_reader, "rank_by_branch_resonance", unavailable)
        status, rejected = restarted_gateway.handle("POST", "/preview/rank", request)
    assert status == 400
    assert "native Tree reader unavailable" in rejected["message"]
    assert "ranked_document_chunks" not in rejected
    status, recovered = restarted_gateway.handle("POST", "/preview/rank", request)
    assert status == 200 and recovered["ranked_document_chunks"]
    assert restarted.serialized_state_bytes() == experience_before
    assert restarted.document_index.durable_tree_bytes() == before


def test_broad_document_research_keeps_composite_units_and_text_free_trace(tmp_path):
    text = (
        "1. Conditions\n"
        "1.1 Before commencing any construction work, the Contractor must:\n"
        "(a) file the secret plan; and\n"
        "(b) obtain the written approval under clause 3.\n\n"
        "2. Access\n"
        "2.1 The Principal is not obliged to give the Contractor access until "
        "the Contractor has:\n"
        "(a) delivered insurance; and\n"
        "(b) submitted the secret method.\n\n"
        "3. Principal insurance\n"
        "3.1 On or before the Condition Precedent Deadline Date, the Principal "
        "must effect its own insurance.\n"
        "3.2 The Principal must keep its own insurance current.\n"
    )
    runtime = TomGateway(
        tmp_path / "data", document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("contract")
    before = runtime.serialized_state_bytes()
    retained = runtime.ingest_document("instrument.txt", text, "text/plain")
    document_tree_before = runtime.document_index.durable_tree_bytes()

    preview = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    assert runtime.serialized_state_bytes() == before
    assert runtime.document_index.durable_tree_bytes() == document_tree_before
    rows = preview["ranked_document_chunks"]
    assert [row["matched_clause_identifier"] for row in rows] == ["1.1", "2.1"]
    assert "(a) file the secret plan" in rows[0]["text"]
    assert "(b) obtain the written approval" in rows[0]["text"]
    assert "(a) delivered insurance" in rows[1]["text"]
    assert "(b) submitted the secret method" in rows[1]["text"]
    assert all(row["truncated"] is False for row in rows)

    trace = preview["document_research_trace"]
    assert trace["intent"]["broad_document_research"] is True
    assert trace["document_tree"]["head"]["chunk_receipt_count"] > 0
    coverage = trace["final_evidence_coverage"]
    assert [row["clause_identifier"] for row in coverage["discovered_units"]] == [
        "1.1", "2.1",
    ]
    assert all(
        row["document_tree_address"]["branch_count"] == 32
        and row["document_tree_address"]["receipt_analysis_digest"].startswith("sha256:")
        for row in coverage["discovered_units"]
    )
    encoded = json.dumps(trace, sort_keys=True)
    assert "secret plan" not in encoded
    assert "secret method" not in encoded
    assert "Principal insurance" not in json.dumps(rows, sort_keys=True)
    first_snapshot = trace["processing_coverage"]["snapshot"]["snapshot_identity"]
    repeated = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    assert repeated["document_research_trace"]["processing_coverage"] == (
        trace["processing_coverage"]
    )
    runtime.ingest_document(
        "later.txt", "4.1 After completion, archive the closeout record.", "text/plain",
    )
    changed_tree = runtime.document_index.durable_tree_bytes()
    changed = runtime.preview_rank(
        "What must the contractor do before it starts construction work under the deed?",
        24,
        12_000,
    )
    changed_coverage = changed["document_research_trace"]["processing_coverage"]
    assert changed_coverage["snapshot"]["snapshot_identity"] != first_snapshot
    assert changed_coverage["cursor"]["complete"] is True
    assert changed_coverage["unexamined_count"] == 0
    assert runtime.document_index.durable_tree_bytes() == changed_tree

    # The tiny fixture's structure resolver reports the forward parent
    # reference as absent. Reclassify that one record as resolved in memory to
    # exercise precise composite traversal deterministically.  The whole parent
    # is read, but neither Principal-only child becomes Contractor evidence.
    source = runtime.library.document(retained["document_id"])
    reference = source["declared_structure"]["references"]["references"][0]
    assert reference["named_identifier"] == "3"
    reference["outcome"] = "resolved"
    parent = next(
        row for row in source["declared_structure"]["clause_index"]["entries"]
        if row["identifier"] == "3"
    )
    parent["kind"] = "clause"
    parent["status"] = "valid"
    metadata = runtime.document_index.project_chunk_metadata("contract")
    document_chunks = [
        {
            **chunk,
            **metadata[(chunk["document_id"], chunk["chunk_index"])],
            "display_name": "instrument.txt",
        }
        for chunk in runtime.library.document_chunks(document_id=retained["document_id"])
    ]
    query = "What must the contractor do before it starts construction work under the deed?"
    _, forced_trace = rank_document_chunks_for_packet(
        query,
        build_document_query_profile(query, FixtureEmbeddingProvider()),
        document_chunks,
        k=24,
        max_chars=12_000,
        document_sources={source["document_id"]: source},
        return_trace=True,
    )
    assert any(
        row["decision"] == "RESOLVED_TARGET_HAS_NO_QUALIFYING_TEMPORAL_DUTY"
        for row in forced_trace["cross_reference_traversal"]
    ), forced_trace["cross_reference_traversal"]


def test_archive_preserves_documents_and_pre_wp39_archive_imports_empty(tmp_path):
    provider = FixtureEmbeddingProvider()
    gateway = TomGateway(tmp_path / "source", document_embedding_provider=provider)
    runtime = gateway.project("documents")
    document = runtime.ingest_document("archive.md", "archived document", "text/markdown")
    archive = tmp_path / "archive"
    export_snapshot(gateway, "documents", archive)
    validate_snapshot(gateway, archive)
    archived_tree = (archive / "document-index/tree_state.json").read_bytes()
    assert archived_tree == runtime.document_index.durable_tree_bytes()
    recovered = _recover(
        TomGateway(tmp_path / "target"), archive,
        tmp_path / "recovery.sqlite3", "sha256:current",
    )
    assert recovered.get_document(document["document_id"]) == runtime.get_document(
        document["document_id"]
    )
    assert recovered.document_index.durable_tree_bytes() == archived_tree
    assert recovered.document_index.project_commit_count("documents") == 1

    old = tmp_path / "old"
    shutil.copytree(archive, old)
    with sqlite3.connect(old / "library.sqlite3") as database:
        database.execute("DROP TABLE document_declared_structures")
        database.execute("DROP TABLE document_chunks")
        database.execute("DROP TABLE documents")
    shutil.rmtree(old / "document-index")
    manifest = json.loads((old / "runtime-manifest.json").read_bytes())
    manifest["format"] = "tom-assist-runtime-archive/1"
    manifest["files"]["library.sqlite3"] = digest_file(old / "library.sqlite3")
    manifest["files"].pop("document-index/tree_state.json")
    manifest["files"].pop("document-index/receipts.sqlite3")
    (old / "runtime-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    )
    validate_snapshot(gateway, old)
    recovered_old = _recover(
        TomGateway(tmp_path / "old-target"), old,
        tmp_path / "old-recovery.sqlite3", "sha256:old",
    )
    assert recovered_old.list_documents(include_withdrawn=True) == []
