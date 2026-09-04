"""Pre-registered WP-33 parser calibration-v3 cases."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from validation.calibration.wp32_cases import (
    case,
    expanded_cases as wp32_expanded_cases,
    relation,
)


def _added(
    case_id: str,
    family: str,
    text: str,
    *,
    relations: tuple[dict[str, Any], ...] = (),
    signals: tuple[str, ...] = (),
    min_chunks: int = 1,
) -> dict[str, Any]:
    item = case(case_id, family, text, relations=relations, signals=signals)
    item["origin"] = "wp33_added"
    item["min_chunks"] = min_chunks
    return item


def _long(
    case_id: str,
    parts: tuple[Any, ...],
    *,
    relations: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    expanded = []
    for part in parts:
        if isinstance(part, str):
            expanded.append(part)
        else:
            expanded.append(str(part["repeat"]) * int(part["count"]))
    return _added(
        case_id,
        "long_position",
        "".join(expanded).strip(),
        relations=relations,
        min_chunks=2,
    )


ADDED_CASES: tuple[dict[str, Any], ...] = (
    _added(
        "P3-01",
        "parser_boundary",
        "Alpha supports Beta, Gamma, and Delta.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "supports", "alpha", "gamma"),
            relation("orientation", "supports", "alpha", "delta"),
        ),
    ),
    _added(
        "P3-02",
        "parser_boundary",
        "Alpha does not support Beta, but Gamma supports Delta.",
        relations=(
            relation("orientation", "supports", "alpha", "beta", negated=True),
            relation("orientation", "supports", "gamma", "delta"),
        ),
    ),
    _added(
        "P3-03",
        "parser_boundary",
        "Alpha controls Beta; this does not mean Alpha causes Beta.",
        relations=(
            relation("orientation", "controls", "alpha", "beta"),
            relation("causal", "causes", "alpha", "beta", negated=True),
        ),
    ),
    _added(
        "P3-04",
        "parser_boundary",
        "Beta is supported by Alpha, Delta is controlled by Gamma, and Zeta is owned by Epsilon.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "controls", "gamma", "delta"),
            relation("orientation", "owns", "epsilon", "zeta"),
        ),
    ),
    _added(
        "M3-01",
        "multi_relation",
        "Alpha supports Beta; Gamma opposes Delta; Epsilon contains Zeta; Eta owns Theta.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "opposes", "gamma", "delta"),
            relation("orientation", "contains", "epsilon", "zeta"),
            relation("orientation", "owns", "eta", "theta"),
        ),
    ),
    _added(
        "M3-02",
        "multi_relation",
        "Alpha enables Beta; Beta causes Gamma; Gamma prevents Delta; Delta contributes to Epsilon.",
        relations=(
            relation("causal", "enables", "alpha", "beta"),
            relation("causal", "causes", "beta", "gamma"),
            relation("causal", "prevents", "gamma", "delta"),
            relation("causal", "contributes_to", "delta", "epsilon"),
        ),
    ),
    _added(
        "M3-03",
        "multi_relation",
        "Alpha controls Beta; Beta enables Gamma; Gamma supports Delta; Delta prevents Epsilon.",
        relations=(
            relation("orientation", "controls", "alpha", "beta"),
            relation("causal", "enables", "beta", "gamma"),
            relation("orientation", "supports", "gamma", "delta"),
            relation("causal", "prevents", "delta", "epsilon"),
        ),
    ),
    _added(
        "M3-04",
        "multi_relation",
        "Deployment requires approval; approval requires evidence; evidence requires review.",
        relations=(
            relation("causal", "requires", "approval", "deployment"),
            relation("causal", "requires", "evidence", "approval"),
            relation("causal", "requires", "review", "evidence"),
        ),
    ),
    _added(
        "M3-05",
        "multi_relation",
        "Alpha does not cause Beta; Gamma does not enable Delta; Epsilon does not prevent Zeta.",
        relations=(
            relation("causal", "causes", "alpha", "beta", negated=True),
            relation("causal", "enables", "gamma", "delta", negated=True),
            relation("causal", "prevents", "epsilon", "zeta", negated=True),
        ),
    ),
    _added(
        "M3-06",
        "multi_relation",
        "First Alpha supports Beta. Then Gamma prevents Delta. The owner rejected Epsilon, and the inspection is complete.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("causal", "prevents", "gamma", "delta"),
        ),
        signals=("sequences", "rejections", "completions"),
    ),
    _long(
        "L3-01",
        (
            {"repeat": "context ", "count": 185},
            "Alpha enables Beta. ",
            {"repeat": "context ", "count": 40},
        ),
        relations=(relation("causal", "enables", "alpha", "beta"),),
    ),
    _long(
        "L3-02",
        (
            {"repeat": "background ", "count": 175},
            "Alpha supports Beta, and Gamma controls Delta. ",
            {"repeat": "background ", "count": 45},
        ),
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "controls", "gamma", "delta"),
        ),
    ),
    _long(
        "L3-03",
        (
            "Alpha remains recorded. ",
            {"repeat": "neutral context ", "count": 100},
            "Alpha prevents Beta. ",
            {"repeat": "neutral context ", "count": 100},
        ),
        relations=(relation("causal", "prevents", "alpha", "beta"),),
    ),
    _long(
        "L3-04",
        (
            {"repeat": "unchanged context ", "count": 190},
            "Alpha causes Beta; Beta enables Gamma; Gamma prevents Delta.",
        ),
        relations=(
            relation("causal", "causes", "alpha", "beta"),
            relation("causal", "enables", "beta", "gamma"),
            relation("causal", "prevents", "gamma", "delta"),
        ),
    ),
)


def expanded_cases() -> list[dict[str, Any]]:
    retained = [deepcopy(item) for item in wp32_expanded_cases()]
    for item in retained:
        item["origin"] = "wp32_retained"
        if item["case_id"] == "HD-05":
            for condition in item["history_expectations"]:
                if condition["channel"] == "persistence":
                    condition.clear()
                    condition.update({
                        "channel": "persistence",
                        "minimum": 2 / 3,
                        "maximum": 2 / 3,
                    })
    return retained + [deepcopy(item) for item in ADDED_CASES]
