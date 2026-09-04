from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import types

import pytest

from gateway.document_ingestion import (
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
)
from gateway.evidence_gateway import EvidenceTomGateway
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
        "tom-assist-shared-document-tree/1.1"
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


def test_shared_document_tree_persists_filters_projects_and_preview_is_byte_pure(tmp_path):
    provider = FixtureEmbeddingProvider(axis=0)
    data = tmp_path / "data"
    gateway = TomGateway(data, document_embedding_provider=provider)
    left = gateway.project("left-project")
    right = gateway.project("right-project")
    assert left.document_index is right.document_index
    assert left.document_index.path == data.resolve() / "document-index/tree_state.json"
    assert left.document_index.durable_tree_bytes() == gateway.seed.artifact_path.read_bytes()

    left_experience_before = left.serialized_state_bytes()
    right_experience_before = right.serialized_state_bytes()
    left_doc = left.ingest_document(
        "left.txt",
        "Before work starts, the left contractor must submit the approved safety plan.",
        "text/plain",
    )
    right_doc = right.ingest_document(
        "right.txt",
        "The right project warranty expires after final completion.",
        "text/plain",
    )
    assert left.serialized_state_bytes() == left_experience_before
    assert right.serialized_state_bytes() == right_experience_before
    assert gateway.document_index.engine.state.tick == gateway.seed.tick + 2
    assert gateway.document_index.project_commit_count("left-project") == 1
    assert gateway.document_index.project_commit_count("right-project") == 1
    assert {
        row[0] for row in gateway.document_index.db.execute(
            "SELECT DISTINCT project_id FROM chunk_commits"
        )
    } == {"left-project", "right-project"}

    shared_before = gateway.document_index.durable_tree_bytes()
    left_before = left.serialized_state_bytes()
    preview = left.preview_rank("What must happen before work starts?", 10, 2000)
    assert [row["document_id"] for row in preview["ranked_document_chunks"]] == [
        left_doc["document_id"]
    ]
    assert right_doc["document_id"] not in json.dumps(preview)
    assert gateway.document_index.durable_tree_bytes() == shared_before
    assert left.serialized_state_bytes() == left_before

    gateway.document_index.db.close()
    restarted = TomGateway(data, document_embedding_provider=FixtureEmbeddingProvider(axis=0))
    restored_left = restarted.project("left-project")
    assert restarted.document_index.durable_tree_bytes() == shared_before
    assert restarted.document_index.engine.state.tick == restarted.seed.tick + 2
    restored = restored_left.preview_rank(
        "What must happen before work starts?", 10, 2000,
    )
    assert [row["document_id"] for row in restored["ranked_document_chunks"]] == [
        left_doc["document_id"]
    ]
    assert right_doc["document_id"] not in json.dumps(restored)


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
        "minilm_dense_plus_exact_relation_plus_document_tree_rrf"
    )
    assert [row["chunk_index"] for row in preview["ranked_document_chunks"]] == [0]
    by_chunk = {
        row["chunk_index"]: row
        for row in preview["document_research_trace"]["candidate_recall"]
    }
    assert by_chunk[0]["structural_resonance"] > by_chunk[1]["structural_resonance"]
    assert by_chunk[0]["structural_resonance"] > by_chunk[2]["structural_resonance"]
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
    runtime.ingest_document("instrument.txt", text, "text/plain")
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

    # The tiny fixture's structure resolver reports the forward parent
    # reference as absent. Reclassify that one record as resolved in memory to
    # exercise the production guard deterministically: a reference to parent
    # clause 3 may not guess between children 3.1 and 3.2.
    source = runtime.library.document(runtime.list_documents()[0]["document_id"])
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
        for chunk in runtime.library.document_chunks()
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
        row["decision"] == "RESOLVED_REFERENCE_TARGET_TOO_BROAD"
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
