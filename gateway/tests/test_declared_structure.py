from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from gateway.declared_structure import (
    DECLARED_STRUCTURE_VERSION,
    DeclaredStructureError,
    build_declared_structure,
    render_defined_term_surfaces,
    resolve_references,
    validate_declared_structure,
)
from gateway.evidence_gateway import EvidenceTomGateway
from gateway.tests.test_document_ingestion import FixtureEmbeddingProvider, _state


ROOT = Path(__file__).parents[2]
HELD_SCAW = Path(
    os.environ.get(
        "TOM_ASSIST_WP42_EXTRACTION",
        "/private/tmp/tom-assist-wp42-scaw-corpus-prep-a9dda3b6/"
        "SCAW_DEED_PDFTOTEXT_LAYOUT.txt",
    )
)
DEFINITION_SENTINEL = "DEFINITION_BODY_SENTINEL must remain private to the index."
SYNTHETIC_INSTRUMENT = f"""THIS DEED is made for a synthetic test.

RECITALS:
(A)      This fixture contains no project facts.

THE PARTIES AGREE AS FOLLOWS:
1.       DEFINITIONS AND REFERENCES
1.1      Definitions

Orbital Coupler means {DEFINITION_SENTINEL}

Signal Datum means another synthetic definition body.

1.2      Reference examples

         (a)      Use Orbital Coupler under clause 2.1, clause 9.9 and clause twenty-three.

         (b)      Apply Schedule A1 and section 9.1 of the General Specification.

         (c)      orbital Coupler is an intentional exact-case near miss.

1.3      Plain clause

         This clause declares no ordering.

2.       PRIORITY
2.1      Order of precedence

         (a)      the documents have the following order:

                  (i)     Main Terms; and

                  (ii)    Schedule A1.

2.2      Special rule

         Notwithstanding clause 1.2(a), this synthetic rule applies.

3,       MALFORMED HEADING

Schedule A1 — Fixture schedule

         Synthetic schedule body.
"""


def _schema_validator():
    directory = ROOT / "crates/protocol/schemas"
    schemas = [json.loads(path.read_text()) for path in directory.glob("*.json")]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas if "$id" in schema
    )
    schema = next(row for row in schemas if row.get("title") == "DeclaredDocumentStructure")
    return Draft202012Validator(schema, registry=registry)


def test_clause_index_is_deterministic_hashed_parented_and_records_malformed_numbering():
    first = build_declared_structure(SYNTHETIC_INSTRUMENT)
    second = build_declared_structure(SYNTHETIC_INSTRUMENT)
    assert first == second
    assert first["schema_version"] == DECLARED_STRUCTURE_VERSION
    assert first["structure_digest"] == second["structure_digest"]
    assert first["clause_index"]["index_digest"] == second["clause_index"]["index_digest"]
    entries = first["clause_index"]["entries"]
    assert all(
        SYNTHETIC_INSTRUMENT.startswith(row["display_identifier"], row["span"]["start"])
        for row in entries
    )
    by_identifier = {row["identifier"]: row for row in entries}
    assert by_identifier["1.2(a)"]["parent_entry_id"] == by_identifier["1.2"]["entry_id"]
    malformed = [row for row in entries if row["status"] == "malformed"]
    assert any(
        row["display_identifier"] == "3,"
        and row["malformed_reason"] == "top_level_separator_is_not_period"
        for row in malformed
    )
    _schema_validator().validate(first)


def test_reference_resolution_has_only_exact_resolved_absent_and_unparsed_outcomes():
    structure = build_declared_structure(SYNTHETIC_INSTRUMENT)
    references = structure["references"]["references"]
    by_text = {row["reference_text"]: row for row in references}
    assert by_text["clause 2.1"]["outcome"] == "resolved"
    assert by_text["clause 9.9"]["outcome"] == "unresolved_absent"
    assert by_text["clause twenty-three"]["outcome"] == "unparsed"
    assert by_text["Schedule A1"]["outcome"] == "resolved"
    assert by_text["section 9.1 of the General Specification"]["outcome"] == "unresolved_absent"
    assert set(row["outcome"] for row in references) == {
        "resolved", "unresolved_absent", "unparsed",
    }
    assert all(
        SYNTHETIC_INSTRUMENT[row["span"]["start"]:row["span"]["end"]]
        == row["reference_text"]
        for row in references
    )


def test_unrecognised_reference_form_is_retained_not_guessed_or_dropped():
    structure = build_declared_structure(SYNTHETIC_INSTRUMENT)
    passage = "The result follows clause twenty three."
    report = resolve_references(passage, structure["clause_index"])
    assert report["reference_count"] == report["unparsed_count"] == 1
    assert report["references"][0]["named_identifier"] is None
    assert report["references"][0]["target_entry_id"] is None


def test_defined_term_binding_is_case_sensitive_exact_and_prompt_is_surface_only():
    structure = build_declared_structure(SYNTHETIC_INSTRUMENT)
    terms = structure["defined_terms"]
    assert terms["case_rule"] == "exact-unicode-codepoints-case-sensitive-whole-surface/1.0"
    assert {row["surface"] for row in terms["terms"]} == {
        "Orbital Coupler", "Signal Datum",
    }
    assert any(row["surface"] == "Orbital Coupler" for row in terms["bindings"])
    near_miss_start = SYNTHETIC_INSTRUMENT.index("orbital Coupler")
    assert all(row["span"]["start"] != near_miss_start for row in terms["bindings"])
    prompt = render_defined_term_surfaces(structure)
    assert '"Orbital Coupler"' in prompt
    assert DEFINITION_SENTINEL not in prompt
    assert all(row["definition_body"] not in prompt for row in terms["terms"])


def test_declared_precedence_reproduces_order_and_only_named_notwithstanding_target():
    structure = build_declared_structure(SYNTHETIC_INSTRUMENT)
    relations = structure["declared_precedence"]["relations"]
    ordered = [row for row in relations if row["relation_kind"] == "precedes"]
    overrides = [row for row in relations if row["relation_kind"] == "notwithstanding"]
    assert [(row["higher_identifier"], row["lower_identifier"]) for row in ordered] == [
        ("Main Terms", "Schedule A1"),
    ]
    assert [(row["target_identifier"], row["target_outcome"]) for row in overrides] == [
        ("1.2(a)", "resolved"),
    ]
    plain = "THIS DEED is made.\n\n1.       PLAIN\n1.1      No declared order\nText only.\n"
    assert build_declared_structure(plain)["declared_precedence"]["relations"] == []
    assert structure["causation"] == {"derived": False, "reason": "not_self_declared"}


def test_ingestion_builds_and_persists_structure_without_touching_runtime_state(tmp_path):
    provider = FixtureEmbeddingProvider()
    gateway = EvidenceTomGateway(tmp_path, document_embedding_provider=provider)
    runtime = gateway.project("declared")
    before = _state(runtime)
    document = runtime.ingest_document(
        "synthetic-deed.txt", SYNTHETIC_INSTRUMENT, "text/plain",
    )
    assert _state(runtime) == before
    assert document["declared_structure"]["schema_version"] == DECLARED_STRUCTURE_VERSION
    assert runtime.library.db.execute(
        "SELECT COUNT(*) FROM document_declared_structures"
    ).fetchone() == (1,)
    # Simulate a pre-WP-43 library: immutable text exists, derived structure does not.
    runtime.library.db.execute("DELETE FROM document_declared_structures")
    restarted = EvidenceTomGateway(
        tmp_path, document_embedding_provider=FixtureEmbeddingProvider(),
    ).project("declared")
    assert restarted.get_document(document["document_id"])["declared_structure"] == document["declared_structure"]
    assert restarted.library.db.execute(
        "SELECT COUNT(*) FROM document_declared_structures"
    ).fetchone() == (1,)


def test_validation_rejects_a_relabelled_exact_reference_even_if_outer_digest_is_recomputed():
    structure = build_declared_structure(SYNTHETIC_INSTRUMENT)
    tampered = copy.deepcopy(structure)
    reference = next(
        row for row in tampered["references"]["references"]
        if row["reference_text"] == "clause 2.1"
    )
    reference["outcome"] = "unresolved_absent"
    reference["target_entry_id"] = None
    unsigned = {key: value for key, value in tampered.items() if key != "structure_digest"}
    from gateway.declared_structure import digest
    tampered["structure_digest"] = digest(unsigned)
    with pytest.raises(DeclaredStructureError, match="exact index"):
        validate_declared_structure(tampered, SYNTHETIC_INSTRUMENT)


def test_declared_structure_has_no_preview_packet_load_or_tree_path():
    mechanism = (ROOT / "gateway/declared_structure.py").read_text(encoding="utf-8")
    for forbidden in (
        "compile_load", "LoadSignature", "engine.step", "rgm.read_memory",
        "ToMClient.process", "apply_msr_load_to_sicd_engine",
    ):
        assert forbidden not in mechanism
    for relative in (
        "gateway/structural_preview.py",
        "gateway/shadow_retrieval.py",
        "crates/context-admission/src/lib.rs",
        "crates/assistd/src/lib.rs",
    ):
        assert "declared_structure" not in (ROOT / relative).read_text(encoding="utf-8")


@pytest.mark.skipif(not HELD_SCAW.is_file(), reason="WP-42 held extraction is unavailable")
def test_wp42_scaw_extraction_builds_twice_hash_identically_and_every_span_replays():
    text = HELD_SCAW.read_text(encoding="utf-8")
    first = build_declared_structure(text)
    second = build_declared_structure(text)
    assert first["structure_digest"] == second["structure_digest"]
    assert first["clause_index"]["index_digest"] == second["clause_index"]["index_digest"]
    assert first["defined_terms"]["term_count"] == 531
    assert all(
        text.startswith(row["display_identifier"], row["span"]["start"])
        for row in first["clause_index"]["entries"]
    )
    assert sum(
        first["references"][key]
        for key in ("resolved_count", "unresolved_absent_count", "unparsed_count")
    ) == first["references"]["reference_count"]
