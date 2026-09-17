import json

import numpy as np
import pytest

from validation.calibration import dynamic_matrix_tree_runner as runner


def test_frozen_actual_tree_fixture_is_bound():
    assert runner.sha256_file(runner.FIXTURE_PATH) == runner.EXPECTED_FIXTURE_SHA256
    fixture = runner.validate_fixture(
        json.loads(runner.FIXTURE_PATH.read_text(encoding="utf-8"))
    )
    assert fixture["matrix_native"]["starting_branches"] == 4000
    assert fixture["matrix_native"]["prior_matrix_growth_events"] == 505
    assert "experimental-matrix-growth" not in json.dumps(fixture)


def test_receipt_cosine_uses_historical_tree_branch_coordinates():
    left = np.eye(32, dtype=np.float64)
    right = np.fliplr(left)
    receipt = {"a": left, "b": right}
    score, coverage, surviving = runner.tree_receipt_cosine(
        receipt, {"a": left, "b": right},
    )
    assert score == 1.0
    assert coverage == 1.0
    assert surviving == 2

    score, coverage, surviving = runner.tree_receipt_cosine(
        receipt, {"a": -left},
    )
    assert score == pytest.approx(-(2.0 ** -0.5), abs=1e-15)
    assert coverage == 0.5
    assert surviving == 1


def test_rank_ties_are_deterministic():
    assert [row["passage_id"] for row in runner.rank_scores({"b": 0.5, "a": 0.5})] == [
        "a", "b",
    ]
