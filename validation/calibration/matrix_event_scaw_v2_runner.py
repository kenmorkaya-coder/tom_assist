#!/usr/bin/env python3
"""Run the frozen four-generation matrix-event SCAW v2 follow-up."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from validation.calibration import matrix_event_scaw_runner as base  # noqa: E402


FIXTURE_PATH = ROOT / "validation" / "calibration" / "matrix_event_scaw_v2_fixture.json"
PREREGISTRATION_PATH = (
    ROOT / "validation" / "calibration" / "MATRIX_EVENT_SCAW_V2_PREREGISTRATION.md"
)
EXPECTED_FIXTURE_SHA256 = (
    "952ae135480c9e1259e2af475db2a118385865582bf836683e94777cdc045f2b"
)


def validate_fixture(payload: Any) -> dict[str, Any]:
    fields = {
        "version", "purpose", "external_corpus", "models",
        "local_generation_limit", "fixed_k", "tree", "matrix", "queries",
        "diagnostic_expectations",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("matrix-event v2 fixture shape mismatch")
    if payload["external_corpus"].get("passage_ids") != ["SCAW-013", "SCAW-019"]:
        raise ValueError("matrix-event v2 passage inventory changed")
    if len(payload["queries"]) != 2 or payload["local_generation_limit"] != 4:
        raise ValueError("matrix-event v2 source inventory changed")
    if payload["fixed_k"] != [1, 2]:
        raise ValueError("matrix-event v2 fixed-k depths changed")
    if payload["tree"] != {"leaf_capacity": 1, "beam_width": 1}:
        raise ValueError("matrix-event v2 Tree mechanics changed")
    return dict(payload)


def main() -> int:
    base.FIXTURE_PATH = FIXTURE_PATH
    base.PREREGISTRATION_PATH = PREREGISTRATION_PATH
    base.EXPECTED_FIXTURE_SHA256 = EXPECTED_FIXTURE_SHA256
    base.REPORT_VERSION = "tom-assist-matrix-event-scaw-diagnostic/2.0"
    base.INDEX_VERSION = "tom-assist-evidence-matrix-tree/0.2-shadow"
    base.validate_fixture = validate_fixture
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
