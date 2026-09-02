"""Evidence-backed language structure and deterministic 17-channel loads.

The local model is deliberately limited to filling ``STRUCTURAL_CANDIDATE_SCHEMA``.
It never supplies load values.  This module validates every quoted span, keeps
orientation and causality directional, and derives the load from accepted
evidence plus already-committed semantic history.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from gateway.semantic_chunks import (
    EMBEDDING_VERSION,
    profile_similarity,
    validate_semantic_profile,
)


CANDIDATE_VERSION = "tom-assist-structural-candidate/1.0"
ANALYSIS_VERSION = "tom-assist-structural-analysis/1.2"
COMPILER_VERSION = "tom-assist-evidence-load17/1.1"
SUPPORTED_COMPILER_VERSIONS = {
    "tom-assist-evidence-load17/1.0",
    COMPILER_VERSION,
}
PARSER_VERSION = "gemma-native-tool-structural-candidate/1.2"
GPT_PARSER_VERSION = "gpt-structured-quote-parser/1.0"
SUPPORTED_PARSER_VERSIONS = {
    "gemma-native-tool-structural-candidate/1.0",
    PARSER_VERSION,
    GPT_PARSER_VERSION,
}
NEAR_SEMANTIC_THRESHOLD = 0.70
HISTORY_WINDOW = 12
MAX_MERGED_ENTITIES = 2048
MAX_MERGED_RELATIONS = 4096
MAX_MERGED_SIGNALS = 4096

ENTITY_KINDS = {
    "actor", "object", "concept", "decision", "constraint", "event",
    "state", "outcome", "work", "unknown",
}
ORIENTATION_KINDS = {
    "supports", "opposes", "depends_on", "contains", "owns", "controls",
    "targets", "refers_to", "precedes", "follows", "supersedes",
    "neutral_toward",
}
CAUSAL_KINDS = {"causes", "enables", "prevents", "contributes_to", "requires"}
POLARITIES = {"positive", "negative", "neutral"}
MODALITIES = {"asserted", "inferred", "tentative", "hypothetical", "questioned"}
UNKNOWN_FIELDS = {
    "entities", "orientations", "causal_relations", "rules", "contradictions",
    "inferences", "sequences", "memory_references", "future_references",
    "completions", "rejections",
}
SIGNAL_NAMES = (
    "rules", "contradictions", "inferences", "sequences",
    "memory_references", "future_references", "completions", "rejections",
)
STATIC_CHANNELS = (
    "S_entity", "S_dependency", "S_topology", "L_rule",
    "L_contradiction", "L_inference", "T_sequence", "T_memory", "T_future",
)
DYNAMIC_CHANNELS = (
    "threat_amplitude", "frequency", "persistence", "burstiness",
    "volatility", "novelty", "recurrence", "decay",
)
CHANNELS = STATIC_CHANNELS + DYNAMIC_CHANNELS


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value)).hexdigest()


def text_digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_object(value: Any, name: str, fields: set[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    actual = set(value)
    if actual != fields:
        raise ValueError(
            f"{name} fields mismatch: missing={sorted(fields - actual)}, "
            f"extra={sorted(actual - fields)}"
        )
    return value


def _finite_unit(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number in [0,1]")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number in [0,1]") from None
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and in [0,1]")
    return result


def _validate_span(value: Any, text: str, name: str) -> dict[str, Any]:
    row = _require_object(value, name, {"start", "end", "quote"})
    start, end = row["start"], row["end"]
    if type(start) is not int or type(end) is not int:
        raise ValueError(f"{name} offsets must be integers")
    if start < 0 or end <= start or end > len(text):
        raise ValueError(f"{name} offsets are outside source text")
    quote = row["quote"]
    if not isinstance(quote, str) or text[start:end] != quote:
        raise ValueError(f"{name} quote does not exactly match source text")
    return {"start": start, "end": end, "quote": quote}


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", value):
        raise ValueError(f"{name} must be a stable lower-case identifier")
    return value


def _label(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    result = re.sub(r"\s+", " ", value).strip()
    if not result or len(result) > 160:
        raise ValueError(f"{name} must contain 1..160 characters")
    return result


def validate_candidate(
    payload: Any,
    source_text: str,
    *,
    max_entities: int = 64,
    max_relations: int = 64,
    max_signals: int = 32,
) -> dict[str, Any]:
    """Strictly validate and normalize one model-produced candidate."""
    if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
        raise ValueError("source text must contain 1..48000 characters")
    row = _require_object(
        payload, "candidate",
        {"schema_version", "source_text_sha256", "entities", "orientations",
         "causal_relations", "signals", "unknown_fields", "confidence"},
    )
    if row["schema_version"] != CANDIDATE_VERSION:
        raise ValueError("candidate schema_version is not supported")
    if row["source_text_sha256"] != text_digest(source_text):
        raise ValueError("candidate is not bound to the source text")

    raw_entities = row["entities"]
    if not isinstance(raw_entities, list) or len(raw_entities) > max_entities:
        raise ValueError(f"entities must be an array with at most {max_entities} items")
    entities: list[dict[str, Any]] = []
    entity_ids: set[str] = set()
    for index, value in enumerate(raw_entities):
        item = _require_object(
            value, f"entities[{index}]", {"id", "label", "kind", "evidence", "confidence"}
        )
        entity_id = _identifier(item["id"], f"entities[{index}].id")
        if entity_id in entity_ids:
            raise ValueError(f"duplicate entity id: {entity_id}")
        entity_ids.add(entity_id)
        kind = str(item["kind"])
        if kind not in ENTITY_KINDS:
            raise ValueError(f"unsupported entity kind: {kind}")
        entities.append({
            "id": entity_id,
            "label": _label(item["label"], f"entities[{index}].label"),
            "kind": kind,
            "evidence": _validate_span(item["evidence"], source_text, f"entities[{index}].evidence"),
            "confidence": _finite_unit(item["confidence"], f"entities[{index}].confidence"),
        })

    raw_orientations = row["orientations"]
    if not isinstance(raw_orientations, list) or len(raw_orientations) > max_relations:
        raise ValueError(
            f"orientations must be an array with at most {max_relations} items"
        )
    orientations: list[dict[str, Any]] = []
    relation_ids: set[str] = set()
    for index, value in enumerate(raw_orientations):
        item = _require_object(
            value, f"orientations[{index}]",
            {"id", "source_entity_id", "target_entity_id", "kind", "polarity",
             "modality", "negated", "evidence", "confidence"},
        )
        relation_id = _identifier(item["id"], f"orientations[{index}].id")
        if relation_id in relation_ids:
            raise ValueError(f"duplicate relation id: {relation_id}")
        relation_ids.add(relation_id)
        source, target = str(item["source_entity_id"]), str(item["target_entity_id"])
        if source not in entity_ids or target not in entity_ids or source == target:
            raise ValueError(f"orientation {relation_id} has invalid directed endpoints")
        kind, polarity, modality = str(item["kind"]), str(item["polarity"]), str(item["modality"])
        if kind not in ORIENTATION_KINDS or polarity not in POLARITIES or modality not in MODALITIES:
            raise ValueError(f"orientation {relation_id} has unsupported vocabulary")
        if type(item["negated"]) is not bool:
            raise ValueError(f"orientation {relation_id} negated must be boolean")
        orientations.append({
            "id": relation_id, "source_entity_id": source, "target_entity_id": target,
            "kind": kind, "polarity": polarity, "modality": modality,
            "negated": item["negated"],
            "evidence": _validate_span(item["evidence"], source_text, f"orientations[{index}].evidence"),
            "confidence": _finite_unit(item["confidence"], f"orientations[{index}].confidence"),
        })

    raw_causal = row["causal_relations"]
    if not isinstance(raw_causal, list) or len(raw_causal) > max_relations:
        raise ValueError(
            f"causal_relations must be an array with at most {max_relations} items"
        )
    causal: list[dict[str, Any]] = []
    for index, value in enumerate(raw_causal):
        item = _require_object(
            value, f"causal_relations[{index}]",
            {"id", "cause_entity_id", "effect_entity_id", "kind", "modality",
             "negated", "evidence", "confidence"},
        )
        relation_id = _identifier(item["id"], f"causal_relations[{index}].id")
        if relation_id in relation_ids:
            raise ValueError(f"duplicate relation id: {relation_id}")
        relation_ids.add(relation_id)
        cause, effect = str(item["cause_entity_id"]), str(item["effect_entity_id"])
        if cause not in entity_ids or effect not in entity_ids or cause == effect:
            raise ValueError(f"causal relation {relation_id} has invalid cause-to-effect endpoints")
        kind, modality = str(item["kind"]), str(item["modality"])
        if kind not in CAUSAL_KINDS or modality not in MODALITIES:
            raise ValueError(f"causal relation {relation_id} has unsupported vocabulary")
        if type(item["negated"]) is not bool:
            raise ValueError(f"causal relation {relation_id} negated must be boolean")
        causal.append({
            "id": relation_id, "cause_entity_id": cause, "effect_entity_id": effect,
            "kind": kind, "modality": modality, "negated": item["negated"],
            "evidence": _validate_span(item["evidence"], source_text, f"causal_relations[{index}].evidence"),
            "confidence": _finite_unit(item["confidence"], f"causal_relations[{index}].confidence"),
        })

    signals_row = _require_object(row["signals"], "signals", set(SIGNAL_NAMES))
    signals: dict[str, list[dict[str, Any]]] = {}
    for signal_name in SIGNAL_NAMES:
        values = signals_row[signal_name]
        if not isinstance(values, list) or len(values) > max_signals:
            raise ValueError(
                f"signals.{signal_name} must have at most {max_signals} items"
            )
        normalized = []
        for index, value in enumerate(values):
            item = _require_object(
                value, f"signals.{signal_name}[{index}]", {"evidence", "confidence"}
            )
            normalized.append({
                "evidence": _validate_span(
                    item["evidence"], source_text, f"signals.{signal_name}[{index}].evidence"
                ),
                "confidence": _finite_unit(
                    item["confidence"], f"signals.{signal_name}[{index}].confidence"
                ),
            })
        signals[signal_name] = normalized

    unknowns = row["unknown_fields"]
    if not isinstance(unknowns, list) or len(unknowns) != len(set(map(str, unknowns))):
        raise ValueError("unknown_fields must be a duplicate-free array")
    unknown_fields = sorted(str(value) for value in unknowns)
    if not set(unknown_fields) <= UNKNOWN_FIELDS:
        raise ValueError("unknown_fields contains an unsupported field")
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(source_text),
        "entities": entities,
        "orientations": orientations,
        "causal_relations": causal,
        "signals": signals,
        "unknown_fields": unknown_fields,
        "confidence": _finite_unit(row["confidence"], "candidate.confidence"),
    }


def canonicalize_candidate_ids(payload: Any) -> Any:
    """Rename model-local IDs without weakening evidence or endpoint checks."""
    if not isinstance(payload, Mapping):
        return payload
    candidate = deepcopy(dict(payload))
    entities = candidate.get("entities")
    orientations = candidate.get("orientations")
    causal = candidate.get("causal_relations")
    if not isinstance(entities, list) or not isinstance(orientations, list) or not isinstance(causal, list):
        return candidate
    entity_ids: dict[str, str] = {}
    for index, entity in enumerate(entities):
        if not isinstance(entity, Mapping) or not isinstance(entity.get("id"), str):
            return candidate
        original = entity["id"]
        if not original or original in entity_ids:
            raise ValueError("model candidate contains duplicate or empty entity IDs")
        canonical = f"entity_{index + 1:04d}"
        entity_ids[original] = canonical
        entity["id"] = canonical
    for index, relation in enumerate(orientations):
        if not isinstance(relation, Mapping):
            return candidate
        source = relation.get("source_entity_id")
        target = relation.get("target_entity_id")
        if source not in entity_ids or target not in entity_ids:
            raise ValueError("model orientation refers to an unknown entity")
        relation["id"] = f"orientation_{index + 1:04d}"
        relation["source_entity_id"] = entity_ids[source]
        relation["target_entity_id"] = entity_ids[target]
    for index, relation in enumerate(causal):
        if not isinstance(relation, Mapping):
            return candidate
        cause = relation.get("cause_entity_id")
        effect = relation.get("effect_entity_id")
        if cause not in entity_ids or effect not in entity_ids:
            raise ValueError("model causal relation refers to an unknown entity")
        relation["id"] = f"causal_{index + 1:04d}"
        relation["cause_entity_id"] = entity_ids[cause]
        relation["effect_entity_id"] = entity_ids[effect]
    return candidate


def project_candidate_fields(payload: Any) -> Any:
    """Drop model-only presentation fields without changing any semantic value.

    The runtime validator remains strict after this projection. Missing required
    facts still fail, while harmless annotations such as ``source_text`` or an
    endpoint label cannot poison an otherwise complete structured call.
    """
    if not isinstance(payload, Mapping):
        return payload
    candidate_fields = {
        "schema_version", "source_text_sha256", "entities", "orientations",
        "causal_relations", "signals", "unknown_fields", "confidence",
    }
    entity_fields = {"id", "label", "kind", "evidence", "confidence"}
    orientation_fields = {
        "id", "source_entity_id", "target_entity_id", "kind", "polarity",
        "modality", "negated", "evidence", "confidence",
    }
    causal_fields = {
        "id", "cause_entity_id", "effect_entity_id", "kind", "modality",
        "negated", "evidence", "confidence",
    }
    fact_fields = {"evidence", "confidence"}
    span_fields = {"start", "end", "quote"}

    def project_object(value: Any, fields: set[str]) -> Any:
        if not isinstance(value, Mapping):
            return value
        return {key: deepcopy(value[key]) for key in fields if key in value}

    candidate = project_object(payload, candidate_fields)
    entities = candidate.get("entities")
    if isinstance(entities, list):
        candidate["entities"] = [project_object(value, entity_fields) for value in entities]
        for entity in candidate["entities"]:
            if isinstance(entity, dict) and "evidence" in entity:
                entity["evidence"] = project_object(entity["evidence"], span_fields)
    for name, fields in (("orientations", orientation_fields), ("causal_relations", causal_fields)):
        relations = candidate.get(name)
        if isinstance(relations, list):
            candidate[name] = [project_object(value, fields) for value in relations]
            for relation in candidate[name]:
                if isinstance(relation, dict) and "evidence" in relation:
                    relation["evidence"] = project_object(relation["evidence"], span_fields)
    signals = candidate.get("signals")
    if isinstance(signals, Mapping):
        candidate["signals"] = {
            name: deepcopy(signals[name]) for name in SIGNAL_NAMES if name in signals
        }
        for values in candidate["signals"].values():
            if isinstance(values, list):
                for index, value in enumerate(values):
                    values[index] = project_object(value, fact_fields)
                    if isinstance(values[index], dict) and "evidence" in values[index]:
                        values[index]["evidence"] = project_object(
                            values[index]["evidence"], span_fields
                        )
    return candidate


def bind_candidate_metadata(payload: Any, source_text: str) -> Any:
    """Bind trusted envelope metadata and empty containers, never facts."""
    if not isinstance(payload, Mapping):
        return payload
    candidate = deepcopy(dict(payload))
    candidate["schema_version"] = CANDIDATE_VERSION
    candidate["source_text_sha256"] = text_digest(source_text)
    if "signals" not in candidate:
        candidate["signals"] = {name: [] for name in SIGNAL_NAMES}
    elif isinstance(candidate["signals"], Mapping):
        candidate["signals"] = dict(candidate["signals"])
        for name in SIGNAL_NAMES:
            candidate["signals"].setdefault(name, [])
    return candidate


def canonicalize_candidate_spans(payload: Any, source_text: str) -> Any:
    """Bind model evidence to exact source spans without inventing a fact.

    A valid model offset wins. Otherwise an exact quote may be rebound to its
    sole occurrence, the unique occurrence nearest the model's proposed start,
    or the sole occurrence inside a relation span that references the entity.
    An entity with a missing quote may use its own label only when that label is
    present in the source. Ties and absent text continue to fail closed.
    """
    if not isinstance(payload, Mapping):
        return payload
    candidate = deepcopy(dict(payload))

    def locations_for(quote: str) -> list[tuple[int, int]]:
        return [
            (match.start(), match.end())
            for match in re.finditer(re.escape(quote), source_text)
        ]

    def casefold_locations_for(value: str) -> list[tuple[int, int]]:
        return [
            (match.start(), match.end())
            for match in re.finditer(re.escape(value), source_text, flags=re.IGNORECASE)
        ]

    def bind(
        span: Any,
        name: str,
        *,
        fallback_label: str | None = None,
        anchors: Sequence[tuple[int, int]] = (),
    ) -> None:
        if not isinstance(span, Mapping):
            return
        quote = span.get("quote")
        start, end = span.get("start"), span.get("end")
        if (
            isinstance(quote, str)
            and type(start) is int
            and type(end) is int
            and 0 <= start < end <= len(source_text)
            and source_text[start:end] == quote
        ):
            return
        if (
            (quote is None or quote == "")
            and type(start) is int
            and type(end) is int
            and 0 <= start < end <= len(source_text)
        ):
            # The offsets are already model-supplied evidence. Restoring their
            # redundant quote from immutable source text adds no semantic fact.
            span["quote"] = source_text[start:end]
            return
        if not isinstance(quote, str) or not quote:
            if isinstance(fallback_label, str) and fallback_label.strip():
                label_locations = casefold_locations_for(fallback_label.strip())
                if label_locations:
                    quote = source_text[label_locations[0][0]:label_locations[0][1]]
                    span["quote"] = quote
                else:
                    quote = None
        if not isinstance(quote, str) or not quote:
            raise ValueError(f"{name} has no exact evidence quote")
        locations = locations_for(quote)
        if not locations and isinstance(fallback_label, str) and quote.casefold() == fallback_label.strip().casefold():
            locations = casefold_locations_for(fallback_label.strip())
            if locations:
                quote = source_text[locations[0][0]:locations[0][1]]
                span["quote"] = quote
        selected: tuple[int, int] | None = None
        if len(locations) == 1:
            selected = locations[0]
        elif locations:
            if type(start) is int:
                distances = [abs(item[0] - start) for item in locations]
                nearest = min(distances)
                candidates = [
                    item for item, distance in zip(locations, distances)
                    if distance == nearest
                ]
                if len(candidates) == 1:
                    selected = candidates[0]
            if selected is None and anchors:
                anchored = [
                    item for item in locations
                    if any(anchor_start <= item[0] and item[1] <= anchor_end
                           for anchor_start, anchor_end in anchors)
                ]
                if len(anchored) == 1:
                    selected = anchored[0]
        if selected is None:
            raise ValueError(f"{name} evidence quote is missing or ambiguous")
        span["start"], span["end"] = selected

    entity_anchors: dict[str, list[tuple[int, int]]] = {}
    for name in ("orientations", "causal_relations"):
        for index, relation in enumerate(candidate.get(name, [])):
            if isinstance(relation, Mapping):
                bind(relation.get("evidence"), f"{name}[{index}]")
                evidence = relation.get("evidence")
                if isinstance(evidence, Mapping):
                    anchor = (int(evidence["start"]), int(evidence["end"]))
                    endpoint_names = (
                        ("source_entity_id", "target_entity_id")
                        if name == "orientations"
                        else ("cause_entity_id", "effect_entity_id")
                    )
                    for endpoint_name in endpoint_names:
                        endpoint = relation.get(endpoint_name)
                        if isinstance(endpoint, str):
                            entity_anchors.setdefault(endpoint, []).append(anchor)
    signals = candidate.get("signals")
    if isinstance(signals, Mapping):
        for signal_name in SIGNAL_NAMES:
            for index, fact in enumerate(signals.get(signal_name, [])):
                if isinstance(fact, Mapping):
                    bind(
                        fact.get("evidence"),
                        f"signals.{signal_name}[{index}]",
                    )
    for index, entity in enumerate(candidate.get("entities", [])):
        if isinstance(entity, Mapping):
            bind(
                entity.get("evidence"),
                f"entities[{index}]",
                fallback_label=entity.get("label"),
                anchors=entity_anchors.get(str(entity.get("id")), ()),
            )
    return candidate


def _rebase_span(span: Mapping[str, Any], offset: int) -> dict[str, Any]:
    return {
        "start": int(span["start"]) + offset,
        "end": int(span["end"]) + offset,
        "quote": span["quote"],
    }


def _equivalent_overlap_evidence(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    """Match the same overlapping quote despite punctuation-only boundaries."""
    if max(int(left["start"]), int(right["start"])) >= min(
        int(left["end"]), int(right["end"])
    ):
        return False
    left_text = re.sub(r"[^a-z0-9]+", " ", str(left["quote"]).casefold()).strip()
    right_text = re.sub(r"[^a-z0-9]+", " ", str(right["quote"]).casefold()).strip()
    return bool(left_text) and left_text == right_text


def merge_chunk_candidates(
    source_text: str,
    semantic_profile: Mapping[str, Any],
    payload: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate local chunk parses, rebase spans, and deduplicate overlap."""
    chunks = semantic_profile.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("semantic profile has no chunks")
    if not isinstance(payload, list) or len(payload) != len(chunks):
        raise ValueError("one structural candidate is required per semantic chunk")

    normalized_chunks = []
    entities: list[dict[str, Any]] = []
    entity_indices: dict[tuple[str, str], list[int]] = {}
    orientations: list[dict[str, Any]] = []
    causal_relations: list[dict[str, Any]] = []
    orientation_indices: dict[tuple[Any, ...], list[int]] = {}
    causal_indices: dict[tuple[Any, ...], list[int]] = {}
    signals: dict[str, list[dict[str, Any]]] = {name: [] for name in SIGNAL_NAMES}
    signal_keys: dict[str, dict[tuple[Any, ...], int]] = {
        name: {} for name in SIGNAL_NAMES
    }
    unknown_fields: set[str] = set()
    confidences = []

    for chunk_index, (item, chunk) in enumerate(zip(payload, chunks)):
        if not isinstance(item, Mapping) or set(item) != {"chunk_index", "candidate"}:
            raise ValueError(f"chunk candidate {chunk_index} fields mismatch")
        if item["chunk_index"] != chunk_index or chunk.get("index") != chunk_index:
            raise ValueError("chunk candidate indices must be contiguous")
        start, end = int(chunk["start"]), int(chunk["end"])
        local_text = source_text[start:end]
        candidate = validate_candidate(item["candidate"], local_text)
        normalized_chunks.append({"chunk_index": chunk_index, "candidate": candidate})
        confidences.append(float(candidate["confidence"]))
        unknown_fields.update(candidate["unknown_fields"])

        local_entity_ids: dict[str, str] = {}
        for entity in sorted(
            candidate["entities"],
            key=lambda row: (
                row["evidence"]["start"], row["evidence"]["end"],
                row["label"].casefold(), row["kind"], row["id"],
            ),
        ):
            evidence = _rebase_span(entity["evidence"], start)
            label_key = re.sub(
                r"\s+", " ", str(entity["label"]).casefold()
            ).strip()
            key = (label_key, entity["kind"])
            label_occurrences = {
                (match.start(), match.end())
                for match in re.finditer(
                    re.escape(str(entity["label"])), source_text, flags=re.IGNORECASE
                )
                if evidence["start"] <= match.start()
                and match.end() <= evidence["end"]
            }
            matching_index = None
            for index in entity_indices.get(key, []):
                existing_evidence = entities[index]["evidence"]
                existing_occurrences = {
                    (match.start(), match.end())
                    for match in re.finditer(
                        re.escape(str(entities[index]["label"])),
                        source_text,
                        flags=re.IGNORECASE,
                    )
                    if existing_evidence["start"] <= match.start()
                    and match.end() <= existing_evidence["end"]
                }
                if label_occurrences & existing_occurrences:
                    matching_index = index
                    break
                if _equivalent_overlap_evidence(existing_evidence, evidence):
                    matching_index = index
                    break
            global_id = (
                entities[matching_index]["id"]
                if matching_index is not None
                else None
            )
            if global_id is None:
                if len(entities) >= MAX_MERGED_ENTITIES:
                    raise ValueError("merged candidate exceeds the entity limit")
                global_id = f"entity_{len(entities) + 1:04d}"
                entity_indices.setdefault(key, []).append(len(entities))
                entities.append({
                    "id": global_id,
                    "label": entity["label"],
                    "kind": entity["kind"],
                    "evidence": evidence,
                    "confidence": entity["confidence"],
                })
            else:
                existing = entities[matching_index]
                normalized_label = re.sub(
                    r"[^a-z0-9]+", " ", str(entity["label"]).casefold()
                ).strip()
                normalized_quote = re.sub(
                    r"[^a-z0-9]+", " ", str(evidence["quote"]).casefold()
                ).strip()
                existing_quote = re.sub(
                    r"[^a-z0-9]+", " ",
                    str(existing["evidence"]["quote"]).casefold(),
                ).strip()
                if normalized_quote == normalized_label and existing_quote != normalized_label:
                    existing["evidence"] = evidence
                existing["confidence"] = max(
                    float(existing["confidence"]), float(entity["confidence"])
                )
            local_entity_ids[entity["id"]] = global_id

        for relation in sorted(
            candidate["orientations"],
            key=lambda row: (row["evidence"]["start"], row["id"]),
        ):
            evidence = _rebase_span(relation["evidence"], start)
            source = local_entity_ids[relation["source_entity_id"]]
            target = local_entity_ids[relation["target_entity_id"]]
            key = (
                source, target, relation["kind"], relation["polarity"],
                relation["modality"], relation["negated"],
            )
            duplicate = next(
                (
                    index for index in orientation_indices.get(key, [])
                    if _equivalent_overlap_evidence(
                        orientations[index]["evidence"], evidence
                    )
                ),
                None,
            )
            if duplicate is not None:
                existing = orientations[duplicate]
                if evidence["end"] - evidence["start"] > (
                    existing["evidence"]["end"] - existing["evidence"]["start"]
                ):
                    existing["evidence"] = evidence
                existing["confidence"] = max(
                    float(existing["confidence"]), float(relation["confidence"])
                )
                continue
            if len(orientations) >= MAX_MERGED_RELATIONS:
                raise ValueError("merged candidate exceeds the orientation limit")
            orientation_indices.setdefault(key, []).append(len(orientations))
            orientations.append({
                "id": f"orientation_{len(orientations) + 1:04d}",
                "source_entity_id": source,
                "target_entity_id": target,
                "kind": relation["kind"],
                "polarity": relation["polarity"],
                "modality": relation["modality"],
                "negated": relation["negated"],
                "evidence": evidence,
                "confidence": relation["confidence"],
            })

        for relation in sorted(
            candidate["causal_relations"],
            key=lambda row: (row["evidence"]["start"], row["id"]),
        ):
            evidence = _rebase_span(relation["evidence"], start)
            cause = local_entity_ids[relation["cause_entity_id"]]
            effect = local_entity_ids[relation["effect_entity_id"]]
            key = (
                cause, effect, relation["kind"], relation["modality"],
                relation["negated"],
            )
            duplicate = next(
                (
                    index for index in causal_indices.get(key, [])
                    if _equivalent_overlap_evidence(
                        causal_relations[index]["evidence"], evidence
                    )
                ),
                None,
            )
            if duplicate is not None:
                existing = causal_relations[duplicate]
                if evidence["end"] - evidence["start"] > (
                    existing["evidence"]["end"] - existing["evidence"]["start"]
                ):
                    existing["evidence"] = evidence
                existing["confidence"] = max(
                    float(existing["confidence"]), float(relation["confidence"])
                )
                continue
            if len(causal_relations) >= MAX_MERGED_RELATIONS:
                raise ValueError("merged candidate exceeds the causal-relation limit")
            causal_indices.setdefault(key, []).append(len(causal_relations))
            causal_relations.append({
                "id": f"causal_{len(causal_relations) + 1:04d}",
                "cause_entity_id": cause,
                "effect_entity_id": effect,
                "kind": relation["kind"],
                "modality": relation["modality"],
                "negated": relation["negated"],
                "evidence": evidence,
                "confidence": relation["confidence"],
            })

        for signal_name in SIGNAL_NAMES:
            for fact in candidate["signals"][signal_name]:
                evidence = _rebase_span(fact["evidence"], start)
                key = (evidence["start"], evidence["end"], evidence["quote"])
                existing_index = signal_keys[signal_name].get(key)
                if existing_index is None:
                    if len(signals[signal_name]) >= MAX_MERGED_SIGNALS:
                        raise ValueError(f"merged candidate exceeds {signal_name} limit")
                    signal_keys[signal_name][key] = len(signals[signal_name])
                    signals[signal_name].append({
                        "evidence": evidence,
                        "confidence": fact["confidence"],
                    })
                else:
                    existing = signals[signal_name][existing_index]
                    existing["confidence"] = max(
                        float(existing["confidence"]), float(fact["confidence"])
                    )

    merged = {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(source_text),
        "entities": entities,
        "orientations": orientations,
        "causal_relations": causal_relations,
        "signals": signals,
        "unknown_fields": sorted(unknown_fields),
        "confidence": sum(confidences) / len(confidences),
    }
    return normalized_chunks, validate_candidate(
        merged,
        source_text,
        max_entities=MAX_MERGED_ENTITIES,
        max_relations=MAX_MERGED_RELATIONS,
        max_signals=MAX_MERGED_SIGNALS,
    )


def validate_parser_model(payload: Any) -> dict[str, str]:
    row = _require_object(payload, "parser_model", {"version", "model", "revision"})
    if row["version"] not in SUPPORTED_PARSER_VERSIONS:
        raise ValueError("parser model version is not supported")
    values = {}
    for name in ("model", "revision"):
        value = row[name]
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"parser_model.{name} must contain 1..256 characters")
        values[name] = value.strip()
    return {"version": row["version"], **values}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _saturate(weight: float, scale: float) -> float:
    return _clamp(1.0 - math.exp(-max(0.0, weight) / scale))


def _weights(rows: Sequence[Mapping[str, Any]]) -> float:
    return sum(float(row["confidence"]) for row in rows)


def _entity_labels(candidate: Mapping[str, Any]) -> dict[str, str]:
    return {
        row["id"]: re.sub(r"[^a-z0-9]+", " ", row["label"].casefold()).strip()
        for row in candidate["entities"]
    }


def directed_graph_fingerprint(candidate: Mapping[str, Any]) -> list[list[Any]]:
    """Return direction-sensitive edges retained alongside the scalar load."""
    labels = _entity_labels(candidate)
    edges: list[list[Any]] = []
    for row in candidate["orientations"]:
        edges.append([
            "orientation", row["kind"], labels[row["source_entity_id"]],
            labels[row["target_entity_id"]], row["polarity"], row["modality"],
            row["negated"],
        ])
    for row in candidate["causal_relations"]:
        edges.append([
            "causal", row["kind"], labels[row["cause_entity_id"]],
            labels[row["effect_entity_id"]], row["modality"], row["negated"],
        ])
    return sorted(edges, key=lambda value: _canonical_json(value))


def directed_graph_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    left_edges = {tuple(row) for row in directed_graph_fingerprint(left)}
    right_edges = {tuple(row) for row in directed_graph_fingerprint(right)}
    if not left_edges or not right_edges:
        return 0.0
    return len(left_edges & right_edges) / len(left_edges | right_edges)


def rank_structural_history(
    candidate: Mapping[str, Any], semantic_profile: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Dense RAG score with a separate direction-sensitive structural component."""
    rows = []
    for item in history:
        semantic = profile_similarity(semantic_profile, item["semantic_profile"])
        dense = semantic["query_relevance_score"]
        directed = directed_graph_similarity(candidate, item["candidate"])
        rows.append({
            "record_id": str(item["record_id"]),
            "dense_semantic_score": dense,
            "directed_graph_score": directed,
            "combined_score": 0.8 * dense + 0.2 * directed,
            "semantic_match": semantic,
        })
    return sorted(rows, key=lambda row: (-row["combined_score"], row["record_id"]))


def _static_load(candidate: Mapping[str, Any]) -> tuple[dict[str, float], dict[str, Any]]:
    entities = candidate["entities"]
    orientations = candidate["orientations"]
    causal = candidate["causal_relations"]
    signals = candidate["signals"]
    dependency_rows = [
        row for row in orientations
        if row["kind"] in {"depends_on", "controls", "contains", "owns"} and not row["negated"]
    ]
    directional_rows = [row for row in orientations if not row["negated"]]
    active_causal = [row for row in causal if not row["negated"]]
    rule_orientation = [row for row in orientations if row["kind"] == "depends_on"]
    negative_orientation = [
        row for row in orientations
        if row["kind"] in {"opposes", "supersedes"} or row["polarity"] == "negative"
    ]
    temporal_orientation = [
        row for row in orientations if row["kind"] in {"precedes", "follows", "supersedes"}
    ]
    hypothetical = [
        row for row in [*orientations, *causal]
        if row["modality"] in {"tentative", "hypothetical", "questioned"}
    ]
    constraint_entities = [row for row in entities if row["kind"] == "constraint"]
    outcome_entities = [row for row in entities if row["kind"] in {"outcome", "state"}]

    entity_weight = _weights(entities)
    dependency_weight = _weights(dependency_rows) + _weights(active_causal)
    topology_weight = _weights(directional_rows) + _weights(active_causal)
    rule_weight = _weights(signals["rules"]) + _weights(constraint_entities) + 0.5 * _weights(rule_orientation)
    contradiction_weight = (
        _weights(signals["contradictions"]) + _weights(signals["rejections"])
        + 0.7 * _weights(negative_orientation)
    )
    inference_weight = (
        _weights(signals["inferences"])
        + _weights([row for row in causal if row["modality"] == "inferred"])
        + 0.35 * _weights(active_causal)
    )
    sequence_weight = _weights(signals["sequences"]) + _weights(temporal_orientation) + 0.5 * _weights(active_causal)
    memory_weight = _weights(signals["memory_references"]) + 0.4 * _weights(signals["completions"])
    future_weight = _weights(signals["future_references"]) + 0.5 * _weights(hypothetical) + 0.25 * _weights(outcome_entities)
    values = {
        "S_entity": _saturate(entity_weight, 3.0),
        "S_dependency": _saturate(dependency_weight, 2.0),
        "S_topology": _saturate(topology_weight + 0.25 * entity_weight, 3.0),
        "L_rule": _saturate(rule_weight, 2.0),
        "L_contradiction": _saturate(contradiction_weight, 1.5),
        "L_inference": _saturate(inference_weight, 2.0),
        "T_sequence": _saturate(sequence_weight, 2.0),
        "T_memory": _saturate(memory_weight, 1.5),
        "T_future": _saturate(future_weight, 1.5),
    }
    evidence = {
        "entity_weight": entity_weight, "dependency_weight": dependency_weight,
        "topology_weight": topology_weight, "rule_weight": rule_weight,
        "contradiction_weight": contradiction_weight, "inference_weight": inference_weight,
        "sequence_weight": sequence_weight, "memory_weight": memory_weight,
        "future_weight": future_weight,
        "directed_graph": directed_graph_fingerprint(candidate),
    }
    return values, evidence


def compile_load(
    candidate: Mapping[str, Any],
    semantic_profile: Mapping[str, Any],
    chunk_candidates: Sequence[Mapping[str, Any]],
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compile validated evidence and committed history into canonical channels."""
    per_chunk_static = []
    per_chunk_evidence = []
    for item in chunk_candidates:
        values, evidence = _static_load(item["candidate"])
        per_chunk_static.append(values)
        per_chunk_evidence.append(evidence)
    if not per_chunk_static:
        raise ValueError("structural analysis has no chunk candidates")
    # Neutral extra passage chunks cannot inflate a channel. Each channel
    # reflects the strongest bounded local evidence window.
    static = {
        name: max(row[name] for row in per_chunk_static)
        for name in STATIC_CHANNELS
    }
    channel_evidence = {
        "aggregation": "per_channel_max_across_bounded_chunks",
        "chunk_static_loads": per_chunk_static,
        "chunk_evidence": per_chunk_evidence,
        "directed_graph": directed_graph_fingerprint(candidate),
    }
    bounded_history = list(history)[-HISTORY_WINDOW:]
    similarities: list[float] = []
    graph_scores: list[float] = []
    semantic_matches: list[dict[str, Any]] = []
    for row in bounded_history:
        prior_profile = row.get("semantic_profile")
        prior_candidate = row.get("candidate")
        if not isinstance(prior_profile, Mapping) or not isinstance(prior_candidate, Mapping):
            raise ValueError("committed structural history is incomplete")
        semantic_match = profile_similarity(semantic_profile, prior_profile)
        semantic_matches.append(semantic_match)
        similarities.append(semantic_match["symmetric_score"])
        graph_scores.append(directed_graph_similarity(candidate, prior_candidate))
    combined = [0.8 * semantic + 0.2 * graph for semantic, graph in zip(similarities, graph_scores)]
    max_similarity = max(combined, default=0.0)
    near = [value >= NEAR_SEMANTIC_THRESHOLD for value in combined]
    frequency = sum(near) / len(near) if near else 0.0
    suffix = 0
    for matched in reversed(near):
        if not matched:
            break
        suffix += 1
    persistence = suffix / min(6, len(near)) if near else 0.0
    recent = near[-4:]
    earlier = near[:-4]
    recent_rate = sum(recent) / len(recent) if recent else 0.0
    earlier_rate = sum(earlier) / len(earlier) if earlier else 0.0
    burstiness = _clamp(recent_rate - earlier_rate)
    turns_since_match = None
    for offset, matched in enumerate(reversed(near)):
        if matched:
            turns_since_match = offset
            break
    decay = 1.0 if turns_since_match is None else _clamp(turns_since_match / HISTORY_WINDOW)
    novelty = 1.0 - max_similarity if bounded_history else 1.0
    recurrence = max_similarity if bounded_history else 0.0

    if bounded_history:
        prior_static = bounded_history[-1].get("static_load")
        if not isinstance(prior_static, Mapping) or set(prior_static) != set(STATIC_CHANNELS):
            raise ValueError("committed structural history lacks static load")
        distance = math.sqrt(
            sum((static[name] - float(prior_static[name])) ** 2 for name in STATIC_CHANNELS)
        ) / math.sqrt(len(STATIC_CHANNELS))
    else:
        distance = 0.0
    change_evidence = max(
        _weights(item["candidate"]["signals"]["contradictions"])
        + _weights(item["candidate"]["signals"]["rejections"])
        + _weights([
            row for row in item["candidate"]["orientations"]
            if row["kind"] == "supersedes"
        ])
        for item in chunk_candidates
    )
    volatility = _clamp(0.65 * distance + 0.35 * _saturate(change_evidence, 1.5))
    threat_weight = max(
        _weights(item["candidate"]["signals"]["contradictions"])
        + _weights(item["candidate"]["signals"]["rejections"])
        + 0.6 * _weights([
            row for row in item["candidate"]["orientations"]
            if row["kind"] in {"opposes", "supersedes"}
            or row["polarity"] == "negative"
        ])
        + 0.7 * _weights([
            row for row in item["candidate"]["causal_relations"]
            if row["kind"] == "prevents" and not row["negated"]
        ])
        for item in chunk_candidates
    )
    threat = _saturate(threat_weight, 1.5)

    # Explicit memory evidence and actual semantic recurrence both contribute;
    # neither is allowed to stand in for the other.
    static["T_memory"] = _clamp(1.0 - (1.0 - static["T_memory"]) * (1.0 - 0.65 * recurrence))
    load = {
        **static,
        "threat_amplitude": threat,
        "frequency": frequency,
        "persistence": persistence,
        "burstiness": burstiness,
        "volatility": volatility,
        "novelty": novelty,
        "recurrence": recurrence,
        "decay": decay,
    }
    if set(load) != set(CHANNELS) or not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in load.values()):
        raise ValueError("compiler produced an invalid 17-channel load")
    return {
        "load_signature": {name: float(load[name]) for name in CHANNELS},
        "static_load": {name: float(static[name]) for name in STATIC_CHANNELS},
        "channel_evidence": channel_evidence,
        "history_metrics": {
            "history_count": len(history), "bounded_history_count": len(bounded_history),
            "semantic_similarities": similarities, "directed_graph_similarities": graph_scores,
            "semantic_chunk_matches": semantic_matches,
            "combined_similarities": combined, "near_threshold": NEAR_SEMANTIC_THRESHOLD,
            "near_count": sum(near), "turns_since_near_match": turns_since_match,
            "static_distance_from_previous": distance,
        },
    }


def build_analysis(
    source_text: str,
    chunk_candidates_payload: Any,
    semantic_profile_payload: Any,
    parser_model_payload: Any,
    history: Sequence[Mapping[str, Any]],
    prior_checkpoint_digest: str,
) -> dict[str, Any]:
    semantic_profile = validate_semantic_profile(semantic_profile_payload, source_text)
    chunk_candidates, candidate = merge_chunk_candidates(
        source_text, semantic_profile, chunk_candidates_payload
    )
    parser_model = validate_parser_model(parser_model_payload)
    compiled = compile_load(candidate, semantic_profile, chunk_candidates, history)
    base = {
        "analysis_version": ANALYSIS_VERSION,
        "compiler_version": COMPILER_VERSION,
        "source_text_sha256": text_digest(source_text),
        "prior_checkpoint_digest": str(prior_checkpoint_digest),
        "candidate_digest": digest(candidate),
        "candidate": candidate,
        "chunk_candidates": chunk_candidates,
        "parser_model": parser_model,
        "semantic_profile": semantic_profile,
        **compiled,
    }
    return {**base, "analysis_digest": digest(base)}


def validate_frozen_analysis(
    payload: Any, source_text: str, history: Sequence[Mapping[str, Any]],
    prior_checkpoint_digest: str,
) -> dict[str, Any]:
    fields = {
        "analysis_version", "compiler_version", "source_text_sha256",
        "prior_checkpoint_digest", "candidate_digest", "candidate", "chunk_candidates",
        "parser_model", "semantic_profile", "load_signature", "static_load", "channel_evidence",
        "history_metrics", "analysis_digest",
    }
    row = _require_object(payload, "structural_analysis", fields)
    if row["analysis_version"] != ANALYSIS_VERSION or row["compiler_version"] != COMPILER_VERSION:
        raise ValueError("structural analysis version is not supported")
    if row["prior_checkpoint_digest"] != prior_checkpoint_digest:
        raise ValueError("structural analysis is stale; prepare again")
    rebuilt = build_analysis(
        source_text, row["chunk_candidates"], row["semantic_profile"],
        row["parser_model"], history, prior_checkpoint_digest,
    )
    if rebuilt != dict(row):
        raise ValueError("structural analysis does not replay exactly")
    return rebuilt


def candidate_tool_schema() -> dict[str, Any]:
    """Gemma-native tool definition. The runtime validator remains authoritative."""
    span = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "start": {"type": "integer", "minimum": 0},
            "end": {"type": "integer", "minimum": 1},
            "quote": {"type": "string"},
        },
        "required": ["start", "end", "quote"],
    }
    evidence_fact = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "evidence": span, "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["evidence", "confidence"],
    }
    parameters = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "entities": {
                "type": "array", "maxItems": 64,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"}, "label": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(ENTITY_KINDS)},
                        "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["id", "label", "kind", "evidence", "confidence"],
                },
            },
            "orientations": {
                "type": "array", "maxItems": 64,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"}, "source_entity_id": {"type": "string"},
                        "target_entity_id": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(ORIENTATION_KINDS)},
                        "polarity": {"type": "string", "enum": sorted(POLARITIES)},
                        "modality": {"type": "string", "enum": sorted(MODALITIES)},
                        "negated": {"type": "boolean"}, "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["id", "source_entity_id", "target_entity_id", "kind",
                                 "polarity", "modality", "negated", "evidence", "confidence"],
                },
            },
            "causal_relations": {
                "type": "array", "maxItems": 64,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"}, "cause_entity_id": {"type": "string"},
                        "effect_entity_id": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(CAUSAL_KINDS)},
                        "modality": {"type": "string", "enum": sorted(MODALITIES)},
                        "negated": {"type": "boolean"}, "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["id", "cause_entity_id", "effect_entity_id", "kind",
                                 "modality", "negated", "evidence", "confidence"],
                },
            },
            "signals": {
                "type": "object", "additionalProperties": False,
                "properties": {name: {"type": "array", "maxItems": 32, "items": evidence_fact}
                               for name in SIGNAL_NAMES},
            },
            "unknown_fields": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "enum": sorted(UNKNOWN_FIELDS)},
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["entities", "orientations", "causal_relations", "signals",
                     "unknown_fields", "confidence"],
    }
    return {
        "type": "function",
        "function": {
            "name": "record_structural_candidate",
            "description": "Record only evidence present in the current source text. Call exactly once.",
            "parameters": parameters,
        },
    }


def quote_candidate_response_format() -> dict[str, Any]:
    """Strict provider schema whose evidence contains quotes, never offsets.

    The provider identifies source-backed structure.  Tom Assist subsequently
    resolves every quote against the immutable source text and computes the
    canonical offsets before the existing candidate validator can accept it.
    """
    span = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"quote": {"type": "string", "minLength": 1}},
        "required": ["quote"],
    }
    evidence_fact = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "evidence": span,
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["evidence", "confidence"],
    }
    candidate = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "entities": {
                "type": "array",
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(ENTITY_KINDS)},
                        "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["id", "label", "kind", "evidence", "confidence"],
                },
            },
            "orientations": {
                "type": "array",
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "source_entity_id": {"type": "string"},
                        "target_entity_id": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(ORIENTATION_KINDS)},
                        "polarity": {"type": "string", "enum": sorted(POLARITIES)},
                        "modality": {"type": "string", "enum": sorted(MODALITIES)},
                        "negated": {"type": "boolean"},
                        "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": [
                        "id", "source_entity_id", "target_entity_id", "kind",
                        "polarity", "modality", "negated", "evidence", "confidence",
                    ],
                },
            },
            "causal_relations": {
                "type": "array",
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "cause_entity_id": {"type": "string"},
                        "effect_entity_id": {"type": "string"},
                        "kind": {"type": "string", "enum": sorted(CAUSAL_KINDS)},
                        "modality": {"type": "string", "enum": sorted(MODALITIES)},
                        "negated": {"type": "boolean"},
                        "evidence": span,
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": [
                        "id", "cause_entity_id", "effect_entity_id", "kind",
                        "modality", "negated", "evidence", "confidence",
                    ],
                },
            },
            "signals": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    name: {"type": "array", "maxItems": 32, "items": evidence_fact}
                    for name in SIGNAL_NAMES
                },
                "required": list(SIGNAL_NAMES),
            },
            "unknown_fields": {
                "type": "array",
                "items": {"type": "string", "enum": sorted(UNKNOWN_FIELDS)},
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "entities", "orientations", "causal_relations", "signals",
            "unknown_fields", "confidence",
        ],
    }
    return {
        "type": "json_schema",
        "name": "tom_assist_structural_candidate_v1",
        "strict": True,
        "schema": candidate,
    }


def build_gpt_quote_prompt(source_text: str) -> str:
    """Build the visible, source-bound prompt for the GPT parser candidate."""
    return f"""Parse structure from SOURCE_TEXT. Do not answer or advise the user.

Return only the schema-defined object. Every evidence.quote must be a non-empty,
exact, case-sensitive substring copied from SOURCE_TEXT. Do not calculate or
return character offsets; Tom Assist binds quotes to offsets deterministically.
When a word repeats, quote enough surrounding source text to identify the correct
occurrence. Keep entity labels short. Internal IDs have no semantic meaning but
every relation endpoint must name an entity in this response.

Preserve direction exactly. Orientation source_entity_id -> target_entity_id
means the source bears that orientation toward the target. Causality always means
cause_entity_id -> effect_entity_id. "A enables B" maps A -> B. "B requires A"
also maps A -> B because A is required for B. Explicit causal verbs belong only
in causal_relations. `controls` is only an orientation and must not also become
`causes`. Do not infer causation from correlation, proximity, or sequence.

Mark negation and modality. "A does not support B" remains `supports` with
negated=true, not `opposes`. Record every separately stated relationship exactly
once, including all members of coordinated lists. Use the fixed signal meanings:
- rules: obligation, prohibition, permission, or stated operating rule;
- contradictions: claims in this text that cannot both hold;
- inferences: an explicitly stated conclusion drawn from evidence;
- sequences: explicit ordering such as first/then/before/after;
- memory_references: explicit reference to earlier recorded or remembered state;
- future_references: explicit future time, plan, prediction, or intended action;
- completions: work or a decision explicitly stated as finished;
- rejections: a path, proposal, claim, or decision explicitly rejected.

Use empty arrays when a signal is absent. Confidence is evidence clarity in
[0,1], not a load value. Do not output emotion labels, load numbers,
explanations, source hashes, or text not supported by SOURCE_TEXT.

SOURCE_TEXT:
{source_text}
"""


def build_gemma_prompt(source_text: str) -> str:
    return f"""You are a local structure parser. Do not answer the user.

Fill record_structural_candidate exactly once from SOURCE_TEXT. Use exact character
offsets and exact non-empty quoted substrings. If a word repeats, quote enough
surrounding source text to make the evidence unique, while entity labels remain
short. Never output SOURCE_TEXT itself, schema_version, source_text_sha256,
endpoint labels/references, explanations, or any field not shown by the tool.
Omit empty keys inside signals; the product supplies empty signal containers.
Preserve who or what points toward whom.
Internal IDs should be lower-case identifiers; they will be normalized after the
tool call and carry no semantic meaning.
Orientation source_entity_id -> target_entity_id means the source bears the named
orientation toward the target. Causality always means cause_entity_id ->
effect_entity_id; never reverse it. For example, "A enables B" maps A -> B, while
"B requires A" also maps A -> B because A is the required condition for B.
Orientations may use only: {", ".join(sorted(ORIENTATION_KINDS))}.
Causal relations may use only: {", ".join(sorted(CAUSAL_KINDS))}. Put explicit
causal verbs such as causes, enables, prevents, contributes to, and requires only
in causal_relations; do not duplicate them as orientations. For "A prevents B",
record causal A -> B with kind prevents and leave orientations empty unless the
text separately states a non-causal orientation.
Do not infer causation from correlation, proximity, or sequence alone. Mark
negation and modality. Record every explicit structural signal using these fixed
meanings:
- rules: an obligation, prohibition, permission, or stated operating rule;
- contradictions: two claims in the text that cannot both hold;
- inferences: an explicitly stated conclusion drawn from evidence;
- sequences: an explicit ordering such as first/then/before/after;
- memory_references: explicit reference to earlier recorded or remembered state;
- future_references: an explicit future time, plan, prediction, or intended action;
- completions: work or a decision explicitly stated as finished;
- rejections: a path, proposal, claim, or decision explicitly rejected.
One evidence span may support a relationship and a signal. Do not turn an
inference cue into causal_relations unless the text itself states causation.
Record every separately stated relationship exactly once, including every item
in a coordinated list. `controls` is only an orientation; never also `causes`.
A negated orientation keeps its stated kind with negated=true: for example,
"A does not support B" is `supports` with negated=true, not `opposes`.
Use unknown_fields when evidence is absent or ambiguous.
Do not invent entities, relations, confidence, history, emotion labels, or load
numbers. Keep every string JSON-compatible and close every list and object.
Return no prose and no additional fields.

SOURCE_TEXT_SHA256: {text_digest(source_text)}
SOURCE_TEXT:
{source_text}
"""
