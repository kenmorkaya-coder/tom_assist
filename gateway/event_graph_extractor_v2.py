"""Versioned presentation-only repair; not used by frozen v1 experiment.

Accept bare JSON or exactly one complete JSON fence. No prose removal,
container repair, semantic defaults, model retry or ambiguous quote repair.
"""
import re
from gateway.event_graph_extractor import parse_output as parse_bare_json

VERSION = "event-graph-output-parser/2"
_FENCE = re.compile(r"```(?:json)?[ \t]*\r?\n(.*)\r?\n```", re.DOTALL)


def parse_output(generated, text):
    if not isinstance(generated, str):
        raise ValueError("generated output must be text")
    candidate = generated.strip()
    match = _FENCE.fullmatch(candidate)
    if match is not None:
        candidate = match.group(1)
    return parse_bare_json(candidate, text)
