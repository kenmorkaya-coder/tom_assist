import json

from validation.calibration.matrix_event_gpt_runner import (
    EXPECTED_FIXTURE_SHA256,
    FIXTURE_PATH,
    sha256_file,
    validate_fixture,
)


def test_gpt_matrix_event_fixture_is_frozen_and_minimal():
    assert sha256_file(FIXTURE_PATH) == EXPECTED_FIXTURE_SHA256
    fixture = validate_fixture(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))
    assert fixture["provider_call_limit"] == 4
    assert len(fixture["external_corpus"]["passage_ids"]) == 2
    assert len(fixture["queries"]) == 2
