from __future__ import annotations

import subprocess
import types

import pytest

from gateway.evidence_gateway import EvidenceTomGateway
from gateway.project_glossary import (
    DOCUMENT_TOP_UP_TARGET,
    GLOSSARY_VERSION,
    MAX_GLOSSARY_CHARACTERS,
    MAX_GLOSSARY_TERMS,
    build_project_glossary,
    render_glossary,
    validate_glossary,
)
from gateway.structural_analysis import (
    GLOSSARY_PARSER_VERSION,
    PARSER_VERSION,
    build_analysis,
    build_gemma_prompt,
    validate_frozen_analysis,
    validate_parser_model,
)
from gateway.tests.test_document_ingestion import FixtureEmbeddingProvider, ROOT
from gateway.tests.test_evidence_loads import _Provider as StructureProvider


PARENT = "3d4a1a692cd984f72fae240ffa25c39db622ed96"


class GlossaryStructureProvider:
    def __init__(self, *, wrong_hash=False):
        self.base = StructureProvider()
        self.calls = []
        self.wrong_hash = wrong_hash

    def analyze(self, text, *, glossary=None):
        self.calls.append(glossary)
        result = self.base.analyze(text)
        if glossary is not None:
            result["parser_model"] = {
                "version": GLOSSARY_PARSER_VERSION,
                "model": "fixture/glossary",
                "revision": "fixture-v1",
                "glossary_sha256": (
                    "sha256:" + "0" * 64
                    if self.wrong_hash else glossary["sha256"]
                ),
            }
        return result


def _parent_module():
    source = subprocess.check_output(
        ["git", "show", f"{PARENT}:gateway/structural_analysis.py"],
        cwd=ROOT,
        text=True,
    )
    module = types.ModuleType("wp39_structural_analysis")
    exec(compile(source, "wp39_structural_analysis.py", "exec"), module.__dict__)
    return module


def test_flag_off_prompt_is_byte_identical_to_wp39():
    text = "The orbital coupler enables phase lock."
    parent = _parent_module()
    assert build_gemma_prompt(text) == parent.build_gemma_prompt(text)


def test_glossary_is_deterministic_hashed_and_survives_project_restart(tmp_path):
    documents = FixtureEmbeddingProvider()
    structure = GlossaryStructureProvider()
    gateway = EvidenceTomGateway(
        tmp_path,
        structure_mode="shadow",
        structure_provider=structure,
        document_embedding_provider=documents,
        parser_glossary_enabled=True,
    )
    runtime = gateway.project("glossary")
    runtime.ingest_document(
        "terms.txt",
        "orbital coupler phase lock orbital coupler phase lock",
        "text/plain",
    )
    titles = ["Frame Tagged Trace", "frame tagged trace", "Signal Datum"]
    first = runtime.project_glossary(titles)
    restarted = EvidenceTomGateway(
        tmp_path,
        structure_mode="shadow",
        structure_provider=GlossaryStructureProvider(),
        document_embedding_provider=FixtureEmbeddingProvider(),
        parser_glossary_enabled=True,
    ).project("glossary")
    second = restarted.project_glossary(titles)
    assert first == second == validate_glossary(first)
    assert first["version"] == GLOSSARY_VERSION
    assert first["term_count"] <= DOCUMENT_TOP_UP_TARGET
    assert first["total_characters"] <= MAX_GLOSSARY_CHARACTERS
    assert first["sha256"].startswith("sha256:")


def test_prompt_addition_contains_surface_forms_and_no_object_metadata():
    glossary = build_project_glossary(["Orbital Coupler"], [])
    block = render_glossary(glossary)
    prompt = build_gemma_prompt("Orbital Coupler enables lock.", glossary)
    assert prompt.startswith(build_gemma_prompt("Orbital Coupler enables lock."))
    assert prompt.endswith(block + "\n")
    assert '"Orbital Coupler"' in block
    for forbidden in (
        "OBJECTIVE_SENTINEL", "SUPERSEDED_SENTINEL", "TOM_VERIFIED_SENTINEL",
        "0.731234", "DEPENDS_ON_SENTINEL",
    ):
        assert forbidden not in block
    for forbidden_enum_value in (
        "objective", "constraint", "rejected_path", "completed_work",
        "unresolved_dependency", "evidence", "assumption", "supersession",
        "workstream", "proposed", "active", "satisfied", "rejected",
        "superseded", "archived", "tom_verified", "imported",
        "provider_candidate", "local_model_candidate", "hard", "soft",
        "depends_on", "blocks", "supports", "conflicts_with",
    ):
        assert forbidden_enum_value not in block.casefold()


def test_bounds_frequency_spelling_and_lexicographic_tie_break_hold():
    titles = [f"Project Term {index:03}" for index in range(100)]
    glossary = build_project_glossary(titles, [])
    assert glossary["term_count"] == MAX_GLOSSARY_TERMS
    assert glossary["terms"] == titles[:MAX_GLOSSARY_TERMS]
    spelling = build_project_glossary(
        ["Signal Datum", "signal datum", "signal datum", "Other Term"], []
    )
    assert "signal datum" in spelling["terms"]
    assert "Signal Datum" not in spelling["terms"]


def test_parser_model_accepts_old_and_hashed_shapes_but_rejects_wrong_hash():
    old = {"version": PARSER_VERSION, "model": "fixture", "revision": "v1"}
    hashed = {
        "version": GLOSSARY_PARSER_VERSION,
        "model": "fixture",
        "revision": "v2",
        "glossary_sha256": "sha256:" + "a" * 64,
    }
    assert validate_parser_model(old) == old
    assert validate_parser_model(hashed) == hashed
    with pytest.raises(ValueError, match="glossary_sha256"):
        validate_parser_model({**hashed, "glossary_sha256": "sha256:wrong"})
    with pytest.raises(ValueError, match="only the glossary"):
        validate_parser_model({**old, "glossary_sha256": "sha256:" + "a" * 64})


def test_parent_analysis_replays_exactly_independent_of_glossary_flag():
    text = "A causes B."
    proposed = StructureProvider().analyze(text)
    parent = _parent_module()
    retained = parent.build_analysis(
        text,
        proposed["chunk_candidates"],
        proposed["semantic_profile"],
        proposed["parser_model"],
        [],
        "checkpoint",
    )
    assert validate_frozen_analysis(retained, text, [], "checkpoint") == retained


def test_enabled_preview_binds_exact_glossary_hash_and_wrong_hash_fails(tmp_path):
    provider = GlossaryStructureProvider()
    gateway = EvidenceTomGateway(
        tmp_path / "valid",
        structure_mode="shadow",
        structure_provider=provider,
        parser_glossary_enabled=True,
    )
    preview = gateway.project("glossary").preview_rank(
        "A causes B.", 10, 2000, ["Causal Coupler"],
    )
    provenance = preview["parser_glossary"]
    assert provider.calls[0]["terms"] == ["Causal Coupler"]
    assert preview["structural_analysis"]["parser_model"][
        "glossary_sha256"
    ] == provenance["sha256"]
    assert gateway.capabilities()["parser_glossary_enabled"] is True
    assert gateway.capabilities()["parser_glossary_term_count"] == 0
    assert gateway.capabilities()["parser_glossary_max_terms"] == 64

    broken = EvidenceTomGateway(
        tmp_path / "broken",
        structure_mode="shadow",
        structure_provider=GlossaryStructureProvider(wrong_hash=True),
        parser_glossary_enabled=True,
    ).project("glossary")
    before = broken.serialized_state_bytes()
    with pytest.raises(ValueError, match="glossary provenance"):
        broken.preview_rank("A causes B.", 10, 2000, ["Causal Coupler"])
    assert broken.serialized_state_bytes() == before


def test_tombstoned_document_contributes_no_glossary_terms(tmp_path):
    gateway = EvidenceTomGateway(
        tmp_path,
        structure_mode="shadow",
        structure_provider=GlossaryStructureProvider(),
        document_embedding_provider=FixtureEmbeddingProvider(),
        parser_glossary_enabled=True,
    )
    runtime = gateway.project("glossary")
    document = runtime.ingest_document(
        "terms.txt", "phase lattice phase lattice phase lattice", "text/plain",
    )
    assert runtime.project_glossary([])["document_term_count"] > 0
    runtime.withdraw_document(document["document_id"], "2026-09-03T00:00:00Z")
    assert runtime.project_glossary([]) == build_project_glossary([], [])


def test_glossary_enabled_analysis_replays_without_rerunning_parser():
    text = "A causes B."
    glossary = build_project_glossary(["A", "B"], [])
    proposed = GlossaryStructureProvider().analyze(text, glossary=glossary)
    analysis = build_analysis(
        text,
        proposed["chunk_candidates"],
        proposed["semantic_profile"],
        proposed["parser_model"],
        [],
        "checkpoint",
    )
    assert validate_frozen_analysis(analysis, text, [], "checkpoint") == analysis
