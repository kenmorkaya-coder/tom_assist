"""Explicit occurrence binding and typed-only Boolean/comparator normalization.

V1/v2 are preserved. No heuristic role, date, modality or scope repairs.
"""
from copy import deepcopy
import json
import re
from gateway.event_graph_extractor import INSTRUCTION
from gateway.typed_event_graph import validate_graph

VERSION = "event-graph-extraction/3"
INSTRUCTION_V3 = INSTRUCTION.replace(
    '{"quote":"exact unique source substring"}', '{"quote":"verbatim source substring","occurrence":0}'
).replace('{"quote":"unique source substring"}', '{"quote":"verbatim source substring","occurrence":0}')
INSTRUCTION_V3 = INSTRUCTION_V3.replace(
    'Quotes must be verbatim and occur exactly once; select a longer quote to disambiguate repeated words.',
    'Every evidence or mention has exactly quote and occurrence. occurrence is the zero-based occurrence of that exact substring in SOURCE_JSON after JSON decoding. Choose the intended occurrence explicitly; use 0 for the first. Repeated quotes are allowed only with this explicit index.'
)
INSTRUCTION_V3 += '''
Role discipline: for notify, the person receiving notification belongs in recipient, not target or object. An explicitly named person or crew doing the notifying belongs in actor. Authority is only the issuing person/body, never inferred from a notification recipient. Do not duplicate a recipient into target. A calendar date belongs in time; a document revision identifier belongs in revision. Permission words (may, allowed, permitted) mean permission, not assertion. An approval mentioned only as a possible exception is hypothetical, including its complement action. A condition on a prohibited action still belongs in condition, not exception. For a negated numeric comparison, prefer its inverse comparator with negated=false (not GT is LE, not GE is LT, not EQ is NE, and conversely). This never changes action-level negation. Avoid redundant single-argument all/any nodes. Each distinct requirement needs its own event. Return one complete JSON object and no explanation.
'''


def prompt(text):
    return INSTRUCTION_V3 + "\nSOURCE_JSON:\n" + json.dumps(text, ensure_ascii=False)


def to_wire(value, text):
    if isinstance(value, dict):
        if set(value) == {"start", "end", "quote"}:
            matches = list(re.finditer(re.escape(value["quote"]), text))
            choices = [i for i, m in enumerate(matches) if (m.start(), m.end()) == (value["start"], value["end"])]
            if len(choices) != 1:
                raise ValueError("gold span cannot be represented")
            return {"quote": value["quote"], "occurrence": choices[0]}
        return {k: to_wire(v, text) for k, v in value.items()}
    if isinstance(value, list):
        return [to_wire(v, text) for v in value]
    return value


def normalize_graph(graph):
    graph = deepcopy(graph)
    inverse = {"GT": "LE", "GE": "LT", "LT": "GE", "LE": "GT", "EQ": "NE", "NE": "EQ"}
    for predicate in graph["predicates"]:
        if predicate["negated"]:
            predicate["comparator"] = inverse[predicate["comparator"]]
            predicate["negated"] = False
    aliases = {r["id"]: r["args"][0] for r in graph["conditions"] if r["operator"] in ("all", "any") and len(r["args"]) == 1}
    def resolve(key):
        visited = set()
        while key in aliases:
            if key in visited:
                raise ValueError("cyclic Boolean aliases")
            visited.add(key); key = aliases[key]
        return key
    graph["conditions"] = [r for r in graph["conditions"] if r["id"] not in aliases]
    for row in graph["conditions"]:
        row["args"] = list(dict.fromkeys(resolve(v) for v in row["args"]))
    for row in graph["events"]:
        for key in ("condition", "exception", "complement"):
            row[key] = resolve(row[key])
    return graph


def bind(candidate, text):
    def walk(value):
        if isinstance(value, dict):
            if "quote" in value:
                if set(value) != {"quote", "occurrence"}:
                    raise ValueError("evidence must explicitly specify quote and occurrence")
                quote, occurrence = value["quote"], value["occurrence"]
                if not isinstance(quote, str) or not quote or type(occurrence) is not int or occurrence < 0:
                    raise ValueError("invalid occurrence evidence")
                matches = list(re.finditer(re.escape(quote), text))
                if occurrence >= len(matches):
                    raise ValueError("quote occurrence absent")
                match = matches[occurrence]
                return {"start": match.start(), "end": match.end(), "quote": quote}
            if "start" in value or "end" in value:
                raise ValueError("model must not supply offsets")
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value
    original = validate_graph(walk(candidate), text)
    return validate_graph(normalize_graph(original), text)


def parse_output(raw, text):
    stripped = raw.strip()
    match = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*)\r?\n```", stripped, re.DOTALL)
    return bind(json.loads(match.group(1) if match else stripped), text)
