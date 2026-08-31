"""Read-only object-anchor resonance. Similarity is not evidence of a violation."""
from __future__ import annotations

import re

from gateway.structural_preview import project_text

POLICY_VERSION = "guardrail-resonance/1"
# An uncalibrated, conservative prior, not a semantic confidence/probability.
NEAR_THRESHOLD = 0.98
SPAN_CHARS = 320
KINDS = {"CONSTRAINT", "REJECTED_PATH", "COMPLETED_WORK"}


def response_spans(text: str):
    """Exact, bounded source slices, including later sentences; never fabricated quotes."""
    for sentence in re.finditer(r"[^.!?\n]+(?:[.!?]+|(?=\n|$))", text):
        for start in range(sentence.start(), sentence.end(), SPAN_CHARS):
            end = min(start + SPAN_CHARS, sentence.end())
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start < end:
                yield start, end, text[start:end]


def resonate_guardrails(payload: dict) -> dict:
    from agency.mechanics.preview_readout import rank_by_branch_resonance

    response = payload.get("response_text")
    anchors = payload.get("anchors")
    if not isinstance(response, str) or len(response) > 512_000:
        raise ValueError("bounded response_text required")
    if not isinstance(anchors, list) or len(anchors) > 2000:
        raise ValueError("at most 2000 guardrail anchors required")
    records = {}
    for anchor in anchors:
        if (not isinstance(anchor, dict) or anchor.get("kind") not in KINDS
                or not isinstance(anchor.get("state_id"), str)
                or not isinstance(anchor.get("text"), str)
                or not 1 <= len(anchor["text"]) <= 16_000
                or anchor["state_id"] in records):
            raise ValueError("invalid or duplicate guardrail anchor")
        records[anchor["state_id"]] = {
            "leaf_vec": list(project_text(anchor["text"])[1].vector_8d),
        }
    records = dict(sorted(records.items()))
    best = {}
    span_count = 0
    for start, end, text in response_spans(response):
        span_count += 1
        vector = list(project_text(text)[1].vector_8d)
        # The upstream pure resonance primitive accepts a vector cohort. Here
        # that cohort is the response teaching vector, not activated tree state.
        _, details = rank_by_branch_resonance(records, [("response-span", vector, 1.0)])
        for state_id, _, score in details:
            if score >= NEAR_THRESHOLD and (state_id not in best or score > best[state_id]["score"]):
                best[state_id] = {"state_id": state_id, "score": score,
                                  "start": start, "end": end, "response_excerpt": text}
    return {"policy_version": POLICY_VERSION, "threshold": NEAR_THRESHOLD,
            "span_count": span_count, "anchor_count": len(records),
            "matches": [best[key] for key in sorted(best)],
            "semantic_verdict": False, "mutates_runtime": False}
