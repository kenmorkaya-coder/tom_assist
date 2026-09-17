import json

from validation.calibration.matrix_event_scaw_v2_runner import (
    EXPECTED_FIXTURE_SHA256,
    FIXTURE_PATH,
    validate_fixture,
)
from validation.calibration.matrix_tree_32sq_runner import sha256_file


def test_matrix_event_scaw_v2_is_frozen_and_bounded():
    assert sha256_file(FIXTURE_PATH) == EXPECTED_FIXTURE_SHA256
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    assert fixture["local_generation_limit"] == 4
    assert fixture["external_corpus"]["passage_ids"] == ["SCAW-013", "SCAW-019"]
    assert len(fixture["queries"]) == 2
