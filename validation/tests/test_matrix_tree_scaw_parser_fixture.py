from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT / "validation" / "calibration" / "matrix_tree_scaw_parser_fixture.json"
)
PREREGISTRATION = (
    ROOT / "validation" / "calibration"
    / "MATRIX_TREE_SCAW_PARSER_PREREGISTRATION.md"
)
EXPECTED_SHA256 = "d1d8f35065379b18f7f6070cbb8cb3736b86f82c5db8cddb7a025e69769dad4f"


def test_scaw_parser_matrix_tree_inputs_are_frozen_without_contract_text():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == EXPECTED_SHA256
    preregistration = PREREGISTRATION.read_text(encoding="utf-8")
    assert "FROZEN — OWNER AUTHORISED LOCAL GEMMA GENERATION" in preregistration
    assert EXPECTED_SHA256 in preregistration
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["external_corpus"]["passage_count"] == 41
    assert payload["external_corpus"]["expected_parser_chunk_attempts"] == 66
    assert payload["generation_limit"] == 76
    assert len(payload["queries"]) == 10
    assert payload["tree"] == {"leaf_capacity": 2, "beam_width": 2}
    serialized = FIXTURE.read_text(encoding="utf-8")
    assert "Before commencing any construction work under this deed" not in serialized


def test_scaw_parser_relevance_ids_are_declared_before_generation():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = {
        "SCAW-013", "SCAW-022", "SCAW-019", "SCAW-039", "SCAW-008",
    }
    observed = {
        passage_id
        for query in payload["queries"]
        for passage_id in query["relevant_passage_ids"]
    }
    assert observed == expected
    families = Counter(query["family"] for query in payload["queries"])
    assert set(families.values()) == {2}
