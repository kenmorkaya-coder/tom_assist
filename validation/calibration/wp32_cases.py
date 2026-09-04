"""Frozen WP-32 calibration-v2 cases built on the retained WP-31 corpus."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from validation.calibration.wp31_cases import expanded_cases as wp31_expanded_cases


def relation(
    channel: str,
    kind: str,
    source: str,
    target: str,
    *,
    negated: bool = False,
    modalities: tuple[str, ...] = ("asserted",),
) -> dict[str, Any]:
    return {
        "channel": channel,
        "kind": kind,
        "source": source,
        "target": target,
        "negated": negated,
        "modalities": list(modalities),
    }


def case(
    case_id: str,
    family: str,
    text: str,
    *,
    relations: tuple[dict[str, Any], ...] = (),
    signals: tuple[str, ...] = (),
    history_texts: tuple[str, ...] = (),
    history_expectations: tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "family": family,
        "text": text,
        "expected_relations": list(relations),
        "expected_signals": list(signals),
        "min_chunks": 1,
        "origin": "wp32_added",
        "history_texts": list(history_texts),
        "history_expectations": list(history_expectations),
        "max_unexpected_relations": 0,
    }


def dynamic(channel: str, *, minimum: float | None = None, maximum: float | None = None):
    result: dict[str, Any] = {"channel": channel}
    if minimum is not None:
        result["minimum"] = minimum
    if maximum is not None:
        result["maximum"] = maximum
    return result


ADDED_CASES: tuple[dict[str, Any], ...] = (
    # Parser-boundary cases: repeated mentions, passive form, punctuation and modality.
    case(
        "PB-01", "parser_boundary", "Alpha enables Beta. Later, Beta enables Gamma.",
        relations=(
            relation("causal", "enables", "alpha", "beta"),
            relation("causal", "enables", "beta", "gamma"),
        ),
    ),
    case(
        "PB-02", "parser_boundary",
        "The report states Alpha is open; the signed record states Alpha is closed.",
        signals=("contradictions",),
    ),
    case(
        "PB-03", "parser_boundary", '"Alpha" supports "Beta".',
        relations=(relation("orientation", "supports", "alpha", "beta"),),
    ),
    case(
        "PB-04", "parser_boundary",
        "Beta is enabled by Alpha, and Gamma is caused by Beta.",
        relations=(
            relation("causal", "enables", "alpha", "beta"),
            relation("causal", "causes", "beta", "gamma"),
        ),
    ),
    case(
        "PB-05", "parser_boundary",
        "Alpha supports Beta; Alpha does not support Gamma.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "supports", "alpha", "gamma", negated=True),
        ),
    ),
    case(
        "PB-06", "parser_boundary", "The old plan is superseded by the new plan.",
        relations=(
            relation("orientation", "supersedes", "new plan", "old plan"),
        ),
    ),
    case(
        "PB-07", "parser_boundary", "Neither Alpha nor Beta causes Gamma.",
        relations=(
            relation("causal", "causes", "alpha", "gamma", negated=True),
            relation("causal", "causes", "beta", "gamma", negated=True),
        ),
    ),
    case(
        "PB-08", "parser_boundary",
        "Could Alpha enable Beta while Gamma prevents Delta?",
        relations=(
            relation(
                "causal", "enables", "alpha", "beta",
                modalities=("questioned", "hypothetical", "tentative"),
            ),
            relation(
                "causal", "prevents", "gamma", "delta",
                modalities=("questioned", "hypothetical", "tentative"),
            ),
        ),
    ),

    # One unambiguous added sentence for each structural signal family.
    case(
        "S2-01", "signal", "Operating rule: technicians must inspect Valve A before use.",
        signals=("rules",),
    ),
    case(
        "S2-02", "signal",
        "The first signed record says Valve A is open; the second says it is closed.",
        signals=("contradictions",),
    ),
    case(
        "S2-03", "signal",
        "From the matching test results, we explicitly infer that Valve A is stable.",
        signals=("inferences",),
    ),
    case(
        "S2-04", "signal", "First inspect Valve A; then start Pump B.",
        signals=("sequences",),
    ),
    case(
        "S2-05", "signal", "The earlier maintenance log recorded that Valve A failed.",
        signals=("memory_references",),
    ),
    case(
        "S2-06", "signal", "Tomorrow the team will inspect Valve A.",
        signals=("future_references",),
    ),
    case(
        "S2-07", "signal", "The Valve A inspection is complete.",
        signals=("completions",),
    ),
    case(
        "S2-08", "signal", "The owner explicitly rejected the Valve A proposal.",
        signals=("rejections",),
    ),

    # Added three-edge passages stress completeness rather than only one edge.
    case(
        "M2-01", "multi_relation",
        "Alpha supports Beta, Gamma opposes Beta, and Delta controls Gamma.",
        relations=(
            relation("orientation", "supports", "alpha", "beta"),
            relation("orientation", "opposes", "gamma", "beta"),
            relation("orientation", "controls", "delta", "gamma"),
        ),
    ),
    case(
        "M2-02", "multi_relation",
        "Alpha enables Beta, Beta causes Gamma, and Gamma prevents Delta.",
        relations=(
            relation("causal", "enables", "alpha", "beta"),
            relation("causal", "causes", "beta", "gamma"),
            relation("causal", "prevents", "gamma", "delta"),
        ),
    ),
    case(
        "M2-03", "multi_relation",
        "Alpha controls Beta; Beta enables Gamma; the owner rejected Gamma.",
        relations=(
            relation("orientation", "controls", "alpha", "beta"),
            relation("causal", "enables", "beta", "gamma"),
        ),
        signals=("rejections",),
    ),
    case(
        "M2-04", "multi_relation",
        "Alpha depends on Beta, Beta depends on Gamma, and Gamma depends on Delta.",
        relations=(
            relation("orientation", "depends_on", "alpha", "beta"),
            relation("orientation", "depends_on", "beta", "gamma"),
            relation("orientation", "depends_on", "gamma", "delta"),
        ),
    ),

    # Real compiler-history cases. History turns are parsed in order and supplied
    # to build_analysis as committed structural records before the query turn.
    case(
        "HD-01", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=("Alpha causes Beta.",),
        history_expectations=(
            dynamic("recurrence", minimum=0.95),
            dynamic("frequency", minimum=1.0),
            dynamic("persistence", minimum=1.0),
            dynamic("novelty", maximum=0.05),
            dynamic("decay", maximum=0.0),
        ),
    ),
    case(
        "HD-02", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=("Alpha causes Beta.", "Gamma opposes Delta."),
        history_expectations=(
            dynamic("recurrence", minimum=0.75),
            dynamic("frequency", minimum=0.4, maximum=0.6),
            dynamic("persistence", maximum=0.0),
            dynamic("decay", minimum=0.08),
        ),
    ),
    case(
        "HD-03", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=("Alpha causes Beta.",) * 3,
        history_expectations=(
            dynamic("frequency", minimum=1.0),
            dynamic("persistence", minimum=1.0),
            dynamic("recurrence", minimum=0.95),
        ),
    ),
    case(
        "HD-04", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=("Gamma opposes Delta.", "Valve A contains water."),
        history_expectations=(
            dynamic("recurrence", maximum=0.60),
            dynamic("novelty", minimum=0.40),
            dynamic("frequency", maximum=0.0),
        ),
    ),
    case(
        "HD-05", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=(
            "Gamma opposes Delta.", "Valve A contains water.",
            "Alpha causes Beta.", "Alpha causes Beta.",
            "Alpha causes Beta.", "Alpha causes Beta.",
        ),
        history_expectations=(
            dynamic("burstiness", minimum=0.90),
            dynamic("persistence", minimum=1.0),
            dynamic("frequency", minimum=0.60, maximum=0.70),
        ),
    ),
    case(
        "HD-06", "history", "Alpha causes Beta.",
        relations=(relation("causal", "causes", "alpha", "beta"),),
        history_texts=(
            "Alpha causes Beta.", "Gamma opposes Delta.", "Valve A contains water.",
        ),
        history_expectations=(
            dynamic("recurrence", minimum=0.75),
            dynamic("decay", minimum=0.16),
            dynamic("persistence", maximum=0.0),
        ),
    ),
    case(
        "HD-07", "history", "Earlier, we recorded that Alpha failed.",
        signals=("memory_references",),
        history_texts=("Alpha failed.",),
        history_expectations=(
            dynamic("T_memory", minimum=0.10),
            dynamic("recurrence", minimum=0.60),
        ),
    ),
    case(
        "HD-08", "history", "Alpha opposes Beta.",
        relations=(relation("orientation", "opposes", "alpha", "beta"),),
        history_texts=("Alpha supports Beta.",),
        history_expectations=(dynamic("volatility", minimum=0.01),),
    ),
)


def expanded_cases() -> list[dict[str, Any]]:
    retained = []
    for original in wp31_expanded_cases():
        item = deepcopy(original)
        item.update({
            "origin": "wp31_retained",
            "history_texts": [],
            "history_expectations": [],
            "max_unexpected_relations": 0,
        })
        retained.append(item)
    return retained + [deepcopy(item) for item in ADDED_CASES]
