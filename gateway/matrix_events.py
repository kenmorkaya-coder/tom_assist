"""Evidence-bound directed events for the shadow 32x32 document route.

The model may identify spans and choose a fixed relation kind.  It may not
provide vectors, matrix values, offsets, or an ungrounded replacement for an
unknown endpoint.  Tom Assist binds exact quotes to the immutable source text
and assigns deterministic IDs before any numerical compilation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re
from typing import Any, Mapping


MATRIX_EVENT_SCHEMA_VERSION = "tom-assist-matrix-event/0.1-shadow"
MATRIX_EVENT_PARSER_VERSION = "evidence-quote-matrix-event-parser/0.3-shadow"
MATRIX_EVENT_RELATIONS = (
    "causes",
    "condition_precedent",
    "dependency",
    "enables",
    "obligation",
    "permission",
    "precedence",
    "precedes",
    "prevents",
    "prohibition",
    "responsibility",
    "supersedes",
)
MATRIX_EVENT_MODALITIES = (
    "asserted", "hypothetical", "inferred", "questioned", "tentative",
)
MATRIX_EVENT_UNKNOWN_REASONS = (
    "ambiguous_direction",
    "ambiguous_endpoints",
    "missing_endpoint",
    "unsupported_relation",
)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _source_digest(source_text: str) -> str:
    return "sha256:" + hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _unit(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0,1]")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number in [0,1]") from None
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0,1]")
    return result


def _object(value: Any, name: str, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{name} fields mismatch")
    return value


def _bind_quote(
    value: Any,
    source_text: str,
    name: str,
    *,
    anchor: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    if value is None:
        return None
    row = _object(value, name, {"quote"})
    quote = row["quote"]
    if not isinstance(quote, str) or not quote:
        raise ValueError(f"{name}.quote must be non-empty exact source text")
    locations = [match.span() for match in re.finditer(re.escape(quote), source_text)]
    if len(locations) != 1 and anchor is not None:
        anchored = [
            (start, end) for start, end in locations
            if int(anchor["start"]) <= start and end <= int(anchor["end"])
        ]
        if len(anchored) == 1:
            locations = anchored
    if len(locations) != 1:
        raise ValueError(f"{name}.quote must occur exactly once in source text")
    start, end = locations[0]
    return {"start": start, "end": end, "quote": quote}


def matrix_event_response_format() -> dict[str, Any]:
    """Strict quote-only response schema for local or OAuth providers."""
    quote_or_null = {
        "anyOf": [
            {
                "type": "object", "additionalProperties": False,
                "properties": {"quote": {"type": "string", "minLength": 1}},
                "required": ["quote"],
            },
            {"type": "null"},
        ]
    }
    event = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "source_evidence": quote_or_null,
            "target_evidence": quote_or_null,
            "relation_kind": {"type": "string", "enum": list(MATRIX_EVENT_RELATIONS)},
            "relation_evidence": {
                "type": "object", "additionalProperties": False,
                "properties": {"quote": {"type": "string", "minLength": 1}},
                "required": ["quote"],
            },
            "context_evidence": quote_or_null,
            "modality": {"type": "string", "enum": list(MATRIX_EVENT_MODALITIES)},
            "negated": {"type": "boolean"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "source_evidence", "target_evidence", "relation_kind",
            "relation_evidence", "context_evidence", "modality", "negated",
            "confidence",
        ],
    }
    unknown = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "evidence": {
                "type": "object", "additionalProperties": False,
                "properties": {"quote": {"type": "string", "minLength": 1}},
                "required": ["quote"],
            },
            "reason": {"type": "string", "enum": list(MATRIX_EVENT_UNKNOWN_REASONS)},
        },
        "required": ["evidence", "reason"],
    }
    return {
        "type": "json_schema",
        "name": "tom_assist_matrix_events_v1",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "events": {"type": "array", "maxItems": 64, "items": event},
                "unknown_relations": {
                    "type": "array", "maxItems": 64, "items": unknown,
                },
            },
            "required": ["events", "unknown_relations"],
        },
    }


def matrix_event_tool_schema() -> dict[str, Any]:
    response = matrix_event_response_format()
    return {
        "type": "function",
        "function": {
            "name": "record_matrix_events",
            "description": (
                "Record evidence-bound directed events from the source. "
                "Call exactly once."
            ),
            "parameters": response["schema"],
        },
    }


def build_matrix_event_prompt(source_text: str) -> str:
    """Build one shared, visible parser prompt for Gemma and GPT."""
    if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
        raise ValueError("source text must contain 1..48000 characters")
    relations = ", ".join(MATRIX_EVENT_RELATIONS)
    return f"""Extract directed events from SOURCE_TEXT. Do not answer the text.

Call or return record_matrix_events exactly once. Every evidence quote must be
an exact, case-sensitive substring of SOURCE_TEXT and must be long enough to
occur only once. Do not return offsets, vectors, matrices, summaries, advice,
emotion labels, or any words presented as source evidence unless they occur in
SOURCE_TEXT.

Use only these relation kinds: {relations}.

Direction is fixed and must never be reversed:
- obligation, prohibition, permission, responsibility: actor -> action or duty;
- condition_precedent, dependency: prerequisite -> gated/dependent action;
- causes: cause -> effect; enables: enabler -> enabled outcome;
- prevents: preventer -> prevented outcome;
- precedes: earlier -> later;
- supersedes: controlling/new item -> displaced/old item;
- precedence: higher-priority item -> lower-priority item.

Split coordinated duties into separate events. If a clause states both an
actor's duty and that the duty is required before another activity, record both
the actor -> duty event and the prerequisite -> gated-activity event when both
directions are explicit. relation_evidence quotes the smallest unique span that
states the relationship. context_evidence captures an explicit condition,
time, trigger, subject or scope when present; otherwise use null.

For a question, use modality questioned and keep the relation kind being asked
about. An unanswered endpoint must be null. Never invent the answer to fill it.
For a non-question assertion, both endpoints must be supported. Keep a stated
negation as negated=true; do not reverse the relation. Use unknown_relations
when the text signals a relation but its direction or endpoints cannot be
supported. Empty arrays are valid and preferred to guesses. Confidence measures
only clarity of the quoted evidence in [0,1].

Question examples (shape only; copy evidence from the actual SOURCE_TEXT):
- "What must the Contractor do before work starts?" is obligation,
  source=the Contractor, target=null, context=before work starts.
- "What must happen before excavation starts?" is condition_precedent,
  source=null, target=excavation starts, with the before-clause as context.
- "How may the deed be amended?" is permission, source=null,
  target=the deed be amended. Do not put a question with one known endpoint in
  unknown_relations.

SOURCE_TEXT_SHA256: {_source_digest(source_text)}
SOURCE_TEXT:
{source_text}
"""


def validate_matrix_event_candidate(payload: Any, source_text: str) -> dict[str, Any]:
    """Bind quote-only model output to exact spans and fail closed on ambiguity."""
    if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
        raise ValueError("source text must contain 1..48000 characters")
    row = _object(payload, "matrix event candidate", {"events", "unknown_relations"})
    raw_events = row["events"]
    raw_unknowns = row["unknown_relations"]
    if not isinstance(raw_events, list) or len(raw_events) > 64:
        raise ValueError("events must contain at most 64 items")
    if not isinstance(raw_unknowns, list) or len(raw_unknowns) > 64:
        raise ValueError("unknown_relations must contain at most 64 items")
    event_fields = {
        "source_evidence", "target_evidence", "relation_kind",
        "relation_evidence", "context_evidence", "modality", "negated",
        "confidence",
    }
    events = []
    for index, value in enumerate(raw_events):
        item = _object(value, f"events[{index}]", event_fields)
        relation = str(item["relation_kind"])
        modality = str(item["modality"])
        if relation not in MATRIX_EVENT_RELATIONS:
            raise ValueError(f"events[{index}].relation_kind is unsupported")
        if modality not in MATRIX_EVENT_MODALITIES:
            raise ValueError(f"events[{index}].modality is unsupported")
        if type(item["negated"]) is not bool:
            raise ValueError(f"events[{index}].negated must be boolean")
        relation_evidence = _bind_quote(
            item["relation_evidence"], source_text,
            f"events[{index}].relation_evidence",
        )
        source = _bind_quote(
            item["source_evidence"], source_text,
            f"events[{index}].source_evidence", anchor=relation_evidence,
        )
        target = _bind_quote(
            item["target_evidence"], source_text,
            f"events[{index}].target_evidence", anchor=relation_evidence,
        )
        context = _bind_quote(
            item["context_evidence"], source_text,
            f"events[{index}].context_evidence", anchor=relation_evidence,
        )
        if source is None and target is None:
            raise ValueError(f"events[{index}] cannot have two unknown endpoints")
        if modality != "questioned" and (source is None or target is None):
            raise ValueError(
                f"events[{index}] may omit an endpoint only when modality is questioned"
            )
        events.append({
            "id": "event_pending",
            "source_evidence": source,
            "target_evidence": target,
            "relation_kind": relation,
            "relation_evidence": relation_evidence,
            "context_evidence": context,
            "modality": modality,
            "negated": item["negated"],
            "confidence": _unit(item["confidence"], f"events[{index}].confidence"),
        })
    events.sort(key=lambda item: (
        item["relation_evidence"]["start"],
        item["relation_evidence"]["end"],
        item["relation_kind"],
        item["source_evidence"]["start"] if item["source_evidence"] else -1,
        item["target_evidence"]["start"] if item["target_evidence"] else -1,
    ))
    for index, event in enumerate(events, 1):
        event["id"] = f"matrix_event_{index:04d}"

    unknowns = []
    for index, value in enumerate(raw_unknowns):
        item = _object(value, f"unknown_relations[{index}]", {"evidence", "reason"})
        reason = str(item["reason"])
        if reason not in MATRIX_EVENT_UNKNOWN_REASONS:
            raise ValueError(f"unknown_relations[{index}].reason is unsupported")
        unknowns.append({
            "evidence": _bind_quote(
                item["evidence"], source_text, f"unknown_relations[{index}].evidence"
            ),
            "reason": reason,
        })
    unknowns.sort(key=lambda item: (
        item["evidence"]["start"], item["evidence"]["end"], item["reason"],
    ))
    result = {
        "schema_version": MATRIX_EVENT_SCHEMA_VERSION,
        "source_text_sha256": _source_digest(source_text),
        "events": events,
        "unknown_relations": unknowns,
    }
    result["digest"] = "sha256:" + hashlib.sha256(_canonical_json(result)).hexdigest()
    return result


def project_matrix_event_fields(payload: Any) -> Any:
    """Drop provider presentation noise without repairing semantic omissions."""
    if not isinstance(payload, Mapping):
        return payload
    candidate = {
        key: deepcopy(payload[key])
        for key in ("events", "unknown_relations") if key in payload
    }
    event_fields = {
        "source_evidence", "target_evidence", "relation_kind",
        "relation_evidence", "context_evidence", "modality", "negated",
        "confidence",
    }
    if isinstance(candidate.get("events"), list):
        candidate["events"] = [
            {key: deepcopy(item[key]) for key in event_fields if key in item}
            if isinstance(item, Mapping) else item
            for item in candidate["events"]
        ]
        for item in candidate["events"]:
            if not isinstance(item, dict):
                continue
            for key in ("source_evidence", "target_evidence", "relation_evidence", "context_evidence"):
                evidence = item.get(key)
                if isinstance(evidence, Mapping):
                    item[key] = {"quote": deepcopy(evidence["quote"])} if "quote" in evidence else {}
    if isinstance(candidate.get("unknown_relations"), list):
        candidate["unknown_relations"] = [
            {
                key: deepcopy(item[key])
                for key in ("evidence", "reason") if key in item
            } if isinstance(item, Mapping) else item
            for item in candidate["unknown_relations"]
        ]
        for item in candidate["unknown_relations"]:
            if isinstance(item, dict) and isinstance(item.get("evidence"), Mapping):
                evidence = item["evidence"]
                item["evidence"] = {"quote": deepcopy(evidence["quote"])} if "quote" in evidence else {}
    return candidate


def matrix_event_semantic_fields(event: Mapping[str, Any]) -> dict[str, str | None]:
    """Return only evidence-derived text plus the fixed typed relation string."""
    relation = " ".join((
        str(event["relation_kind"]), str(event["modality"]),
        "negated" if event["negated"] else "affirmed",
    ))
    return {
        "source": (
            None if event["source_evidence"] is None
            else str(event["source_evidence"]["quote"])
        ),
        "target": (
            None if event["target_evidence"] is None
            else str(event["target_evidence"]["quote"])
        ),
        "relation": relation,
        "context": (
            str(event["relation_evidence"]["quote"])
            if event["context_evidence"] is None
            else str(event["context_evidence"]["quote"])
        ),
    }
