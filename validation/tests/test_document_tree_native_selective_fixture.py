import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT / "validation" / "calibration"
    / "document_tree_native_selective_fixture.json"
)
PREREGISTRATION = (
    ROOT / "validation" / "calibration"
    / "NATIVE_DOCUMENT_TREE_SELECTIVE_PREREGISTRATION.md"
)
EXPECTED_SHA256 = "0d42b6bc7b32710db90e1b2c9724557fa815b6477fc67c0c57666f54659226fd"


def test_native_selective_fixture_and_labels_are_frozen_before_execution():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == EXPECTED_SHA256
    frozen = PREREGISTRATION.read_text(encoding="utf-8")
    assert "FROZEN FOR LOCAL DIAGNOSTIC" in frozen
    assert EXPECTED_SHA256 in frozen
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["fixed_k"] == [1, 3, 5]
    passage_ids = [row["id"] for row in payload["passages"]]
    assert len(passage_ids) == len(set(passage_ids)) == 16
    assert len(payload["queries"]) == 10
    families = {}
    for query in payload["queries"]:
        families[query["family"]] = families.get(query["family"], 0) + 1
        assert query["relevant_passage_ids"]
        assert set(query["relevant_passage_ids"]) <= set(passage_ids)
    assert set(families.values()) == {2}


def test_frozen_native_success_definition_excludes_coverage_shortcuts():
    frozen = PREREGISTRATION.read_text(encoding="utf-8")
    for excluded in (
        "scanning or admitting the full corpus",
        "clause/reference expansion",
        "lexical, hybrid, or reranked packet order",
        "25-item packet",
        "nonzero score spread",
    ):
        assert excluded in frozen
