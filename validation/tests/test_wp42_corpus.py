from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from validation.calibration.wp42_scaw_corpus import (
    CorpusPreparationError,
    FAMILIES,
    SOURCE_SHA256,
    build_passages,
    compact_json,
    extract_defined_terms,
    extract_twice,
    sha256_bytes,
    source_identity,
    validate_manifest_against_text,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "validation/calibration/WP42_SCAW_SHORTLIST_MANIFEST.json"


def test_extraction_is_run_twice_and_must_be_byte_identical(tmp_path):
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"synthetic input")
    text = "Synthetic page one.\n\fSynthetic page two.\n\f"
    calls = []

    def extractor(_source, destination):
        calls.append(destination.name)
        value = text.encode("utf-8")
        destination.write_bytes(value)
        return value

    result = extract_twice(
        source,
        extractor,
        expected_sha256=sha256_bytes(text.encode("utf-8")),
        expected_bytes=len(text.encode("utf-8")),
        expected_pages=2,
    )
    assert result == text
    assert calls == ["run-1.txt", "run-2.txt"]


def test_extraction_difference_fails_closed(tmp_path):
    source = tmp_path / "fixture.pdf"
    source.write_bytes(b"synthetic input")
    calls = 0

    def extractor(_source, _destination):
        nonlocal calls
        calls += 1
        return f"run {calls}\f".encode()

    with pytest.raises(CorpusPreparationError, match="not byte-identical"):
        extract_twice(source, extractor)


def test_surface_term_extraction_never_carries_definition_bodies():
    text = (
        "Alpha Relay means the first synthetic body.\n\n"
        "Constraint Node has the meaning given in a synthetic schedule.\n\n"
        "Synthetic Claim includes a fictional request.\n\n"
        "Decision Gate is the process set out elsewhere.\n\f"
    )
    terms = extract_defined_terms(text, start=(1, 1), end=(1, 7))
    assert terms == [
        "Alpha Relay", "Constraint Node", "Synthetic Claim", "Decision Gate",
    ]
    assert all("synthetic body" not in term.casefold() for term in terms)
    assert all(" means " not in f" {term.casefold()} " for term in terms)
    assert all(" includes " not in f" {term.casefold()} " for term in terms)


def test_passage_offsets_and_hashes_replay_exactly():
    text = "First synthetic paragraph.\nSecond line.\n\fAnother page.\n\f"
    plan = [{
        "passage_id": "SCAW-001",
        "pdf_page": 1,
        "line_start": 1,
        "line_end": 2,
        "clause_identifier": "synthetic-1",
        "families": ["dependency"],
        "difficulty": "easy",
    }]
    manifest_rows, text_rows = build_passages(text, plan)
    manifest = {"passages": manifest_rows}
    validate_manifest_against_text(manifest, text)
    assert text_rows[0]["text"] == "First synthetic paragraph.\nSecond line.\n"
    assert "text" not in manifest_rows[0]


def test_missing_source_fails_closed_without_partial_identity(tmp_path):
    missing = tmp_path / "unmounted.pdf"
    with pytest.raises(CorpusPreparationError, match="source PDF is unavailable"):
        source_identity(missing)


def test_tracked_manifest_is_hash_only_and_self_contained():
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    encoded = compact_json(value)
    assert value["source"]["sha256"] == SOURCE_SHA256
    assert value["contract_text_committed"] is False
    assert value["shortlist"]["passage_count"] == 40
    assert set(value["shortlist"]["family_coverage"]) == FAMILIES
    assert min(value["shortlist"]["family_coverage"].values()) >= 10
    assert set(value["shortlist"]["difficulty_coverage"]) == {
        "easy", "medium", "hard",
    }
    assert b"/Volumes/" not in encoded
    assert b"My Passport" not in encoded
    assert all("text" not in row for row in value["passages"])
    assert all(
        row["text_sha256"].startswith("sha256:")
        and len(row["text_sha256"]) == 71
        for row in value["passages"]
    )
    assert len({row["passage_id"] for row in value["passages"]}) == 40
    assert hashlib.sha256(encoded).hexdigest()
