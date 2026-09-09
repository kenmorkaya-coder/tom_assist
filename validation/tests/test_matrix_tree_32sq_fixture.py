import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "validation" / "calibration" / "matrix_tree_32sq_fixture.json"
PREREGISTRATION = (
    ROOT / "validation" / "calibration" / "MATRIX_TREE_32SQ_PREREGISTRATION.md"
)
EXPECTED_SHA256 = "8ad95a36318e6e4e0e29fc43b950e097da70857ff6e1230dfe370a24b00d3a4f"


def test_matrix_tree_fixture_is_frozen_before_the_local_run():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == EXPECTED_SHA256
    preregistration = PREREGISTRATION.read_text(encoding="utf-8")
    assert "FROZEN FOR LOCAL SHADOW DIAGNOSTIC" in preregistration
    assert EXPECTED_SHA256 in preregistration
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["fixed_k"] == [1, 3, 5]
    assert payload["tree"] == {"leaf_capacity": 2, "beam_width": 2}
    assert len(payload["passages"]) == 16
    assert len(payload["queries"]) == 10
    passage_ids = {row["id"] for row in payload["passages"]}
    assert len(passage_ids) == 16
    for query in payload["queries"]:
        assert set(query["relevant_passage_ids"]) <= passage_ids


def test_matrix_tree_fixture_keeps_orientation_explicit():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    forward = payload["orientation_control"]["forward"]
    reversed_event = payload["orientation_control"]["reversed"]
    assert forward["source"] == reversed_event["target"]
    assert forward["target"] == reversed_event["source"]
    assert forward["relation"] == reversed_event["relation"]
    assert forward["context"] == reversed_event["context"]
