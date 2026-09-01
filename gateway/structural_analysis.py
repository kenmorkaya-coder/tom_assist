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
from typing import Any, Mapping, Sequence


CANDIDATE_VERSION = "tom-assist-structural-candidate/1.0"
ANALYSIS_VERSION = "tom-assist-structural-analysis/1.0"
COMPILER_VERSION = "tom-assist-evidence-load17/1.0"
EMBEDDING_VERSION = "minilm-l6-v2/384d-mean-pool-max256/1.0"
PARSER_VERSION = "gemma-native-tool-structural-candidate/1.0"
EMBEDDING_DIMENSION = 384
NEAR_SEMANTIC_THRESHOLD = 0.70
HISTORY_WINDOW = 12

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


def validate_candidate(payload: Any, source_text: str) -> dict[str, Any]:
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
    if not isinstance(raw_entities, list) or len(raw_entities) > 64:
        raise ValueError("entities must be an array with at most 64 items")
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
    if not isinstance(raw_orientations, list) or len(raw_orientations) > 64:
        raise ValueError("orientations must be an array with at most 64 items")
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
    if not isinstance(raw_causal, list) or len(raw_causal) > 64:
        raise ValueError("causal_relations must be an array with at most 64 items")
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
        if not isinstance(values, list) or len(values) > 32:
            raise ValueError(f"signals.{signal_name} must have at most 32 items")
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


def validate_semantic_vector(payload: Any) -> dict[str, Any]:
    row = _require_object(
        payload, "semantic_vector", {"version", "model", "revision", "dimension", "values"}
    )
    if row["version"] != EMBEDDING_VERSION or row["dimension"] != EMBEDDING_DIMENSION:
        raise ValueError("semantic vector version or dimension is not supported")
    if not isinstance(row["model"], str) or not row["model"]:
        raise ValueError("semantic vector model is required")
    if not isinstance(row["revision"], str) or not row["revision"]:
        raise ValueError("semantic vector revision is required")
    values = row["values"]
    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSION:
        raise ValueError(f"semantic vector must contain {EMBEDDING_DIMENSION} values")
    vector = []
    for value in values:
        if isinstance(value, bool):
            raise ValueError("semantic vector values must be finite numbers")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("semantic vector values must be finite numbers")
        vector.append(number)
    norm = math.sqrt(sum(value * value for value in vector))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError(f"semantic vector must be unit normalized, got norm {norm}")
    return {
        "version": EMBEDDING_VERSION, "model": row["model"],
        "revision": row["revision"], "dimension": EMBEDDING_DIMENSION,
        "values": vector,
    }


def validate_parser_model(payload: Any) -> dict[str, str]:
    row = _require_object(payload, "parser_model", {"version", "model", "revision"})
    if row["version"] != PARSER_VERSION:
        raise ValueError("parser model version is not supported")
    values = {}
    for name in ("model", "revision"):
        value = row[name]
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"parser_model.{name} must contain 1..256 characters")
        values[name] = value.strip()
    return {"version": PARSER_VERSION, **values}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _saturate(weight: float, scale: float) -> float:
    return _clamp(1.0 - math.exp(-max(0.0, weight) / scale))


def _weights(rows: Sequence[Mapping[str, Any]]) -> float:
    return sum(float(row["confidence"]) for row in rows)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("semantic history vector dimension mismatch")
    denom = math.sqrt(sum(x * x for x in left) * sum(y * y for y in right))
    if denom < 1e-12:
        raise ValueError("semantic history contains a zero vector")
    return _clamp(sum(x * y for x, y in zip(left, right)) / denom)


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
    candidate: Mapping[str, Any], semantic_vector: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Dense RAG score with a separate direction-sensitive structural component."""
    rows = []
    for item in history:
        dense = _cosine(semantic_vector["values"], item["semantic_vector"]["values"])
        directed = directed_graph_similarity(candidate, item["candidate"])
        rows.append({
            "record_id": str(item["record_id"]),
            "dense_semantic_score": dense,
            "directed_graph_score": directed,
            "combined_score": 0.8 * dense + 0.2 * directed,
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
    candidate: Mapping[str, Any], semantic_vector: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compile validated evidence and committed history into canonical channels."""
    static, channel_evidence = _static_load(candidate)
    current = semantic_vector["values"]
    bounded_history = list(history)[-HISTORY_WINDOW:]
    similarities: list[float] = []
    graph_scores: list[float] = []
    for row in bounded_history:
        prior_vector = row.get("semantic_vector", {}).get("values")
        prior_candidate = row.get("candidate")
        if not isinstance(prior_vector, list) or not isinstance(prior_candidate, Mapping):
            raise ValueError("committed structural history is incomplete")
        similarities.append(_cosine(current, prior_vector))
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
    change_evidence = _weights(candidate["signals"]["contradictions"]) + _weights(candidate["signals"]["rejections"])
    change_evidence += _weights([
        row for row in candidate["orientations"] if row["kind"] == "supersedes"
    ])
    volatility = _clamp(0.65 * distance + 0.35 * _saturate(change_evidence, 1.5))
    threat_weight = _weights(candidate["signals"]["contradictions"]) + _weights(candidate["signals"]["rejections"])
    threat_weight += 0.6 * _weights([
        row for row in candidate["orientations"]
        if row["kind"] in {"opposes", "supersedes"} or row["polarity"] == "negative"
    ])
    threat_weight += 0.7 * _weights([
        row for row in candidate["causal_relations"] if row["kind"] == "prevents" and not row["negated"]
    ])
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
            "combined_similarities": combined, "near_threshold": NEAR_SEMANTIC_THRESHOLD,
            "near_count": sum(near), "turns_since_near_match": turns_since_match,
            "static_distance_from_previous": distance,
        },
    }


def build_analysis(
    source_text: str, candidate_payload: Any, semantic_vector_payload: Any,
    parser_model_payload: Any, history: Sequence[Mapping[str, Any]],
    prior_checkpoint_digest: str,
) -> dict[str, Any]:
    candidate = validate_candidate(candidate_payload, source_text)
    semantic_vector = validate_semantic_vector(semantic_vector_payload)
    parser_model = validate_parser_model(parser_model_payload)
    compiled = compile_load(candidate, semantic_vector, history)
    base = {
        "analysis_version": ANALYSIS_VERSION,
        "compiler_version": COMPILER_VERSION,
        "source_text_sha256": text_digest(source_text),
        "prior_checkpoint_digest": str(prior_checkpoint_digest),
        "candidate_digest": digest(candidate),
        "candidate": candidate,
        "parser_model": parser_model,
        "semantic_vector": semantic_vector,
        **compiled,
    }
    return {**base, "analysis_digest": digest(base)}


def validate_frozen_analysis(
    payload: Any, source_text: str, history: Sequence[Mapping[str, Any]],
    prior_checkpoint_digest: str,
) -> dict[str, Any]:
    fields = {
        "analysis_version", "compiler_version", "source_text_sha256",
        "prior_checkpoint_digest", "candidate_digest", "candidate", "parser_model",
        "semantic_vector", "load_signature", "static_load", "channel_evidence",
        "history_metrics", "analysis_digest",
    }
    row = _require_object(payload, "structural_analysis", fields)
    if row["analysis_version"] != ANALYSIS_VERSION or row["compiler_version"] != COMPILER_VERSION:
        raise ValueError("structural analysis version is not supported")
    if row["prior_checkpoint_digest"] != prior_checkpoint_digest:
        raise ValueError("structural analysis is stale; prepare again")
    rebuilt = build_analysis(
        source_text, row["candidate"], row["semantic_vector"], row["parser_model"], history,
        prior_checkpoint_digest,
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
            "schema_version": {"type": "string", "enum": [CANDIDATE_VERSION]},
            "source_text_sha256": {"type": "string"},
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
                "required": list(SIGNAL_NAMES),
            },
            "unknown_fields": {
                "type": "array", "uniqueItems": True,
                "items": {"type": "string", "enum": sorted(UNKNOWN_FIELDS)},
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["schema_version", "source_text_sha256", "entities", "orientations",
                     "causal_relations", "signals", "unknown_fields", "confidence"],
    }
    return {
        "type": "function",
        "function": {
            "name": "record_structural_candidate",
            "description": "Record only evidence present in the current source text. Call exactly once.",
            "parameters": parameters,
        },
    }


def build_gemma_prompt(source_text: str) -> str:
    return f"""You are a local structure parser. Do not answer the user.

Fill record_structural_candidate exactly once from SOURCE_TEXT. Use exact character
offsets and exact quoted substrings. Preserve who or what points toward whom.
Orientation source_entity_id -> target_entity_id means the source bears the named
orientation toward the target. Causality always means cause_entity_id ->
effect_entity_id; never reverse it. For example, "A enables B" maps A -> B, while
"B requires A" also maps A -> B because A is the required condition for B.
Do not infer causation from correlation, proximity, or sequence alone. Mark
negation and modality. Use unknown_fields when evidence is absent or ambiguous.
Do not invent entities, relations, confidence, history, emotion labels, or load
numbers. Return no prose and no additional fields.

SOURCE_TEXT_SHA256: {text_digest(source_text)}
SOURCE_TEXT:
{source_text}
"""
