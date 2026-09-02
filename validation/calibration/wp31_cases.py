"""Pre-registered WP-31 multi-vector calibration cases.

The cases are deliberately compact. Long inputs use explicit repeat parts so the
source remains reviewable while expansion is deterministic and hash-bound.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _relation(
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


def _case(
    case_id: str,
    family: str,
    text: str,
    *,
    relations: tuple[dict[str, Any], ...] = (),
    signals: tuple[str, ...] = (),
    pair_id: str | None = None,
    min_chunks: int = 1,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "case_id": case_id,
        "family": family,
        "text": text,
        "expected_relations": list(relations),
        "expected_signals": list(signals),
        "min_chunks": min_chunks,
    }
    if pair_id is not None:
        result["pair_id"] = pair_id
    return result


CASES: tuple[dict[str, Any], ...] = (
    # Explicit causality, direction, negation and modality (10).
    _case("CD-01", "causal_direction", "Alpha causes Beta.",
          relations=(_relation("causal", "causes", "alpha", "beta"),)),
    _case("CD-02", "causal_direction", "Beta causes Alpha.",
          relations=(_relation("causal", "causes", "beta", "alpha"),)),
    _case("CD-03", "causal_direction", "Alpha enables Beta.",
          relations=(_relation("causal", "enables", "alpha", "beta"),)),
    _case("CD-04", "causal_direction", "Beta requires Alpha.",
          relations=(_relation("causal", "requires", "alpha", "beta"),)),
    _case("CD-05", "causal_direction", "The brake prevents movement.",
          relations=(_relation("causal", "prevents", "brake", "movement"),)),
    _case("CD-06", "causal_direction", "Alpha contributes to Beta.",
          relations=(_relation("causal", "contributes_to", "alpha", "beta"),)),
    _case("CD-07", "causal_direction", "Alpha does not cause Beta.",
          relations=(_relation("causal", "causes", "alpha", "beta", negated=True),)),
    _case("CD-08", "causal_direction", "The brake does not prevent movement.",
          relations=(_relation("causal", "prevents", "brake", "movement", negated=True),)),
    _case("CD-09", "causal_direction", "Alpha may cause Beta.",
          relations=(_relation("causal", "causes", "alpha", "beta",
                               modalities=("tentative", "hypothetical")),)),
    _case("CD-10", "causal_direction", "Could Alpha cause Beta?",
          relations=(_relation("causal", "causes", "alpha", "beta",
                               modalities=("questioned", "hypothetical")),)),

    # All twelve non-causal orientation kinds (12).
    _case("OR-01", "orientation", "Alpha supports Beta.",
          relations=(_relation("orientation", "supports", "alpha", "beta"),)),
    _case("OR-02", "orientation", "Alpha opposes Beta.",
          relations=(_relation("orientation", "opposes", "alpha", "beta"),)),
    _case("OR-03", "orientation", "Alpha depends on Beta.",
          relations=(_relation("orientation", "depends_on", "alpha", "beta"),)),
    _case("OR-04", "orientation", "Alpha contains Beta.",
          relations=(_relation("orientation", "contains", "alpha", "beta"),)),
    _case("OR-05", "orientation", "Alpha owns Beta.",
          relations=(_relation("orientation", "owns", "alpha", "beta"),)),
    _case("OR-06", "orientation", "Alpha controls Beta.",
          relations=(_relation("orientation", "controls", "alpha", "beta"),)),
    _case("OR-07", "orientation", "Alpha targets Beta.",
          relations=(_relation("orientation", "targets", "alpha", "beta"),)),
    _case("OR-08", "orientation", "Alpha refers to Beta.",
          relations=(_relation("orientation", "refers_to", "alpha", "beta"),)),
    _case("OR-09", "orientation", "Alpha precedes Beta.",
          relations=(_relation("orientation", "precedes", "alpha", "beta"),)),
    _case("OR-10", "orientation", "Alpha follows Beta.",
          relations=(_relation("orientation", "follows", "alpha", "beta"),)),
    _case("OR-11", "orientation", "The new plan supersedes the old plan.",
          relations=(_relation("orientation", "supersedes", "new plan", "old plan"),)),
    _case("OR-12", "orientation", "Alpha is neutral toward Beta.",
          relations=(_relation("orientation", "neutral_toward", "alpha", "beta"),)),

    # Eight structural signal families (8).
    _case("SG-01", "signal", "The rule is: operators must inspect Alpha before use.",
          signals=("rules",)),
    _case("SG-02", "signal",
          "The report says Alpha is open, but the signed record says Alpha is closed.",
          signals=("contradictions",)),
    _case("SG-03", "signal",
          "Because both measurements agree, we infer that Alpha is stable.",
          signals=("inferences",)),
    _case("SG-04", "signal", "First inspect Alpha, then start Beta.",
          signals=("sequences",)),
    _case("SG-05", "signal", "Earlier, we recorded that Alpha failed.",
          signals=("memory_references",)),
    _case("SG-06", "signal", "Next week, the team will inspect Alpha.",
          signals=("future_references",)),
    _case("SG-07", "signal", "The team completed the Alpha inspection.",
          signals=("completions",)),
    _case("SG-08", "signal", "The team rejected the Alpha proposal.",
          signals=("rejections",)),

    # Multiple relations in one passage (6).
    _case("MR-01", "multi_relation", "Alpha enables Beta, and Beta causes Gamma.",
          relations=(
              _relation("causal", "enables", "alpha", "beta"),
              _relation("causal", "causes", "beta", "gamma"),
          )),
    _case("MR-02", "multi_relation", "Alpha supports Beta, but Gamma opposes Beta.",
          relations=(
              _relation("orientation", "supports", "alpha", "beta"),
              _relation("orientation", "opposes", "gamma", "beta"),
          )),
    _case("MR-03", "multi_relation", "Alpha controls Beta, and Beta prevents Gamma.",
          relations=(
              _relation("orientation", "controls", "alpha", "beta"),
              _relation("causal", "prevents", "beta", "gamma"),
          )),
    _case("MR-04", "multi_relation", "Alpha precedes Beta, which precedes Gamma.",
          relations=(
              _relation("orientation", "precedes", "alpha", "beta"),
              _relation("orientation", "precedes", "beta", "gamma"),
          )),
    _case("MR-05", "multi_relation",
          "The new plan supersedes the old plan because new evidence contradicts the old assumption.",
          relations=(_relation("orientation", "supersedes", "new plan", "old plan"),),
          signals=("contradictions",)),
    _case("MR-06", "multi_relation", "Alpha may enable Beta, but it does not cause Gamma.",
          relations=(
              _relation("causal", "enables", "alpha", "beta",
                        modalities=("tentative", "hypothetical")),
              _relation("causal", "causes", "alpha", "gamma", negated=True),
          )),

    # Long-position and overlap cases use deterministic text expansion (6).
    {
        **_case("LP-01", "long_position", "", relations=(
            _relation("causal", "prevents", "alpha", "beta"),
        ), min_chunks=2),
        "parts": [{"repeat": "context ", "count": 200}, "Alpha prevents Beta."],
    },
    {
        **_case("LP-02", "long_position", "", relations=(
            _relation("causal", "causes", "alpha", "beta"),
        ), min_chunks=2),
        "parts": ["Alpha causes Beta. ", {"repeat": "context ", "count": 200}],
    },
    {
        **_case("LP-03", "long_position", "", relations=(
            _relation("causal", "enables", "alpha", "beta"),
        ), min_chunks=2),
        "parts": [
            {"repeat": "context ", "count": 100},
            "Alpha enables Beta. ",
            {"repeat": "context ", "count": 100},
        ],
    },
    {
        **_case("LP-04", "long_position", "", relations=(
            _relation("causal", "causes", "alpha", "beta"),
            _relation("causal", "prevents", "gamma", "delta"),
        ), min_chunks=2),
        "parts": [
            "Alpha causes Beta. ",
            {"repeat": "context ", "count": 180},
            "Gamma prevents Delta.",
        ],
    },
    {
        **_case("LP-05", "long_position", "", relations=(
            _relation("orientation", "supersedes", "new plan", "old plan"),
        ), signals=("future_references",), min_chunks=2),
        "parts": [
            {"repeat": "Neutral background remains unchanged. ", "count": 35},
            "The new plan supersedes the old plan. Next week the team will inspect Alpha.",
        ],
    },
    {
        **_case("LP-06", "long_position", "", relations=(
            _relation("causal", "enables", "alpha", "beta"),
        ), min_chunks=2),
        "parts": [
            {"repeat": "context ", "count": 185},
            "Alpha enables Beta. ",
            {"repeat": "context ", "count": 40},
        ],
    },

    # Five meaning-preserving paraphrase pairs (10).
    _case("PP-01A", "paraphrase", "Excess pressure causes the alarm.",
          relations=(_relation("causal", "causes", "excess pressure", "alarm"),),
          pair_id="PP-01"),
    _case("PP-01B", "paraphrase", "The alarm is caused by excess pressure.",
          relations=(_relation("causal", "causes", "excess pressure", "alarm"),),
          pair_id="PP-01"),
    _case("PP-02A", "paraphrase", "Approval enables deployment.",
          relations=(_relation("causal", "enables", "approval", "deployment"),),
          pair_id="PP-02"),
    _case("PP-02B", "paraphrase", "Deployment can proceed because approval enables it.",
          relations=(_relation("causal", "enables", "approval", "deployment"),),
          pair_id="PP-02"),
    _case("PP-03A", "paraphrase", "The lock prevents the door from opening.",
          relations=(_relation("causal", "prevents", "lock", "door"),),
          pair_id="PP-03"),
    _case("PP-03B", "paraphrase", "The door cannot open because the lock prevents it.",
          relations=(_relation("causal", "prevents", "lock", "door"),),
          pair_id="PP-03"),
    _case("PP-04A", "paraphrase", "Deployment requires approval.",
          relations=(_relation("causal", "requires", "approval", "deployment"),),
          pair_id="PP-04"),
    _case("PP-04B", "paraphrase", "Approval is required for deployment.",
          relations=(_relation("causal", "requires", "approval", "deployment"),),
          pair_id="PP-04"),
    _case("PP-05A", "paraphrase", "Evidence supports the decision.",
          relations=(_relation("orientation", "supports", "evidence", "decision"),),
          pair_id="PP-05"),
    _case("PP-05B", "paraphrase", "The decision is supported by the evidence.",
          relations=(_relation("orientation", "supports", "evidence", "decision"),),
          pair_id="PP-05"),
)


def expand_case(case: dict[str, Any]) -> dict[str, Any]:
    """Return an independent case with deterministic long-text parts expanded."""
    result = deepcopy(case)
    parts = result.pop("parts", None)
    if parts is not None:
        text_parts = []
        for part in parts:
            if isinstance(part, str):
                text_parts.append(part)
            else:
                text_parts.append(str(part["repeat"]) * int(part["count"]))
        result["text"] = "".join(text_parts).strip()
    return result


def expanded_cases() -> list[dict[str, Any]]:
    return [expand_case(case) for case in CASES]
