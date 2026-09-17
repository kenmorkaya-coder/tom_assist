import json
from pathlib import Path

import pytest

from gateway.matrix_events import validate_matrix_event_candidate
from validation.calibration.matrix_event_scaw_runner import (
    EXPECTED_FIXTURE_SHA256,
    FIXTURE_PATH,
    compile_event_views,
    sha256_file,
    validate_fixture,
)


def test_frozen_fixture_digest_and_inventory():
    assert sha256_file(FIXTURE_PATH) == EXPECTED_FIXTURE_SHA256
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    assert fixture["local_generation_limit"] == 15
    assert len(fixture["external_corpus"]["passage_ids"]) == 10
    assert len(fixture["queries"]) == 5


def test_question_compiles_only_evidence_available_views():
    source = "What must the Contractor do before work starts?"
    candidate = validate_matrix_event_candidate({
        "events": [{
            "source_evidence": {"quote": "the Contractor"},
            "target_evidence": None,
            "relation_kind": "obligation",
            "relation_evidence": {"quote": "must the Contractor do"},
            "context_evidence": {"quote": "before work starts"},
            "modality": "questioned",
            "negated": False,
            "confidence": 1.0,
        }],
        "unknown_relations": [],
    }, source)
    event = candidate["events"][0]
    semantic = {
        event["source_evidence"]["quote"],
        event["relation_evidence"]["quote"],
        event["context_evidence"]["quote"],
        "obligation questioned affirmed",
    }
    vectors = {
        text: [1.0 if index == offset else 0.01 for index in range(384)]
        for offset, text in enumerate(sorted(semantic))
    }
    config = {
        "size": 32,
        "source_target_weight": 1.0,
        "relation_weight": 0.5,
        "context_weight": 0.25,
        "projection": "splitmix64-rademacher-jl-384-to-32/1.0",
        "projection_seed": 539362568,
        "views": ["full", "source_context", "context_target"],
    }
    views = compile_event_views(event, vectors, config)
    assert [row["view"] for row in views] == ["source_context"]
    assert len(views[0]["matrix"]) == 1024
    assert all(value != 0.0 for value in views[0]["matrix"])


def test_contract_text_is_not_committed_in_fixture():
    fixture_text = Path(FIXTURE_PATH).read_text(encoding="utf-8")
    assert "Before commencing any construction work under this deed" not in fixture_text
    assert "/private/tmp/" in fixture_text
