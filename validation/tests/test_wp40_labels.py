from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from validation.calibration.wp40_labels import (
    SYNTHETIC_LABEL,
    TEMPLATE_LABEL,
    validate_label_file,
)


ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC = ROOT / "gateway/tests/fixtures/wp41_synthetic_parser_labels.json"
TEMPLATE = ROOT / "validation/calibration/wp40_label_template.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_two_row_synthetic_plumbing_example_validates_but_is_not_evidence():
    source = _load(SYNTHETIC)
    validated = validate_label_file(source)
    assert validated["label"] == SYNTHETIC_LABEL
    assert len(validated["passages"]) == 2
    assert all(row["labeller_note"] for row in validated["passages"])


def test_label_validator_rejects_a_span_not_bound_exactly_to_source():
    source = _load(SYNTHETIC)
    source["passages"][0]["expected_candidate"]["entities"][0][
        "evidence"
    ]["quote"] = "closed valves"
    with pytest.raises(ValueError, match="does not exactly match"):
        validate_label_file(source)


def test_label_validator_rejects_unknown_relation_kind():
    source = _load(SYNTHETIC)
    source["passages"][1]["expected_candidate"]["orientations"][0][
        "kind"
    ] = "replaces_in_spirit"
    with pytest.raises(ValueError, match="unsupported kind"):
        validate_label_file(source)


def test_empty_template_is_never_accepted_as_evaluation_evidence():
    source = _load(TEMPLATE)
    assert source["label"] == TEMPLATE_LABEL
    with pytest.raises(ValueError, match="not evaluation evidence"):
        validate_label_file(source)
    assert validate_label_file(source, allow_template=True)["passages"] == []


def test_label_validator_does_not_normalize_bad_source_digests():
    source = deepcopy(_load(SYNTHETIC))
    source["passages"][0]["source_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="source digest mismatch"):
        validate_label_file(source)
