"""Inactive deterministic dense q17 and T/S/P construction for WP-36b.

This module is deliberately not wired into preview or commit. It consumes the
already-built multi-vector semantic profile and a replayable structural analysis,
then emits a hash-bound shadow observation for calibration against the pinned
Python 10K tree.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.semantic_chunks import EMBEDDING_DIMENSION, validate_semantic_profile
from gateway.structural_analysis import CHANNELS, digest, text_digest, validate_candidate


DENSE_LOAD_VERSION = "tom-assist-dense-semantic-load17/0.2-shadow"
DOCUMENT_DENSE_LOAD_VERSION = "tom-assist-document-dense-load17/1.0"
ANCHOR_BANK_SCHEMA = "tom-assist-dense-load17-anchor-bank/1.0"
ANCHOR_BANK_PATH = Path(__file__).with_name("data") / "dense_load17_anchor_bank_v1.json"
DRIVERS = ("threat_load", "sustenance_potential", "procreation_potential")
HISTORY_EVIDENCE_CHANNELS = frozenset({
    "frequency", "persistence", "burstiness", "volatility", "novelty",
    "recurrence", "decay",
})


def _finite_unit(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number in [0,1]")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number in [0,1]") from None
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be a finite number in [0,1]")
    return number


def _positive_unit(value: Any, name: str) -> float:
    number = _finite_unit(value, name)
    if number <= 0.0:
        raise ValueError(f"{name} must be strictly positive")
    return number


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _decode_vector(value: str, name: str) -> tuple[float, ...]:
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError(f"{name} is not canonical base64") from error
    if len(raw) != EMBEDDING_DIMENSION * 4:
        raise ValueError(f"{name} does not contain {EMBEDDING_DIMENSION} float32 values")
    vector = struct.unpack(f"<{EMBEDDING_DIMENSION}f", raw)
    if not all(math.isfinite(item) for item in vector):
        raise ValueError(f"{name} contains a non-finite value")
    norm = math.sqrt(sum(item * item for item in vector))
    if abs(norm - 1.0) > 1e-3:
        raise ValueError(f"{name} is not unit normalised")
    return vector


@lru_cache(maxsize=1)
def load_anchor_bank() -> dict[str, Any]:
    raw = json.loads(ANCHOR_BANK_PATH.read_text(encoding="utf-8"))
    fields = {
        "schema_version", "source_sha256", "embedding_model",
        "embedding_revision", "dimension", "formula", "channels", "drivers",
    }
    if not isinstance(raw, Mapping) or set(raw) != fields:
        raise ValueError("dense anchor bank fields mismatch")
    if raw["schema_version"] != ANCHOR_BANK_SCHEMA:
        raise ValueError("dense anchor bank schema is unsupported")
    if raw["dimension"] != EMBEDDING_DIMENSION:
        raise ValueError("dense anchor bank dimension is unsupported")
    if tuple(raw["channels"]) != CHANNELS or tuple(raw["drivers"]) != DRIVERS:
        raise ValueError("dense anchor bank channel order mismatch")
    formula = raw["formula"]
    if set(formula) != {
        "absolute_beta", "contrast_temperature", "chunk_aggregation",
        "evidence_combination",
    }:
        raise ValueError("dense anchor formula fields mismatch")
    beta = float(formula["absolute_beta"])
    temperature = float(formula["contrast_temperature"])
    if beta <= 0.0 or temperature <= 0.0:
        raise ValueError("dense anchor formula constants must be positive")
    if formula["chunk_aggregation"] != "per_channel_max":
        raise ValueError("dense anchor chunk aggregation is unsupported")
    if formula["evidence_combination"] != "probabilistic_or":
        raise ValueError("dense anchor evidence combination is unsupported")
    decoded: dict[str, dict[str, list[dict[str, Any]]]] = {
        "channels": {}, "drivers": {},
    }
    for family, names in (("channels", CHANNELS), ("drivers", DRIVERS)):
        for name in names:
            rows = raw[family][name]
            if not isinstance(rows, list) or len(rows) < 2:
                raise ValueError(f"dense anchor bank {family}.{name} is incomplete")
            decoded[family][name] = []
            for index, row in enumerate(rows):
                expected_fields = {
                    "anchor_id", "text", "text_sha256", "vector_f32_le_base64",
                }
                if not isinstance(row, Mapping) or set(row) != expected_fields:
                    raise ValueError(f"dense anchor {family}.{name}[{index}] fields mismatch")
                if row["anchor_id"] != f"{name}:{index}":
                    raise ValueError("dense anchor ids must be canonical")
                if row["text_sha256"] != text_digest(row["text"]):
                    raise ValueError("dense anchor text digest mismatch")
                decoded[family][name].append({
                    "anchor_id": row["anchor_id"],
                    "text_sha256": row["text_sha256"],
                    "vector": _decode_vector(
                        row["vector_f32_le_base64"],
                        f"{family}.{name}[{index}].vector",
                    ),
                })
    return {
        "source_sha256": raw["source_sha256"],
        "artifact_sha256": _file_sha256(ANCHOR_BANK_PATH),
        "embedding_model": raw["embedding_model"],
        "embedding_revision": raw["embedding_revision"],
        "formula": {
            "absolute_beta": beta,
            "contrast_temperature": temperature,
            "chunk_aggregation": formula["chunk_aggregation"],
            "evidence_combination": formula["evidence_combination"],
        },
        **decoded,
    }


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != EMBEDDING_DIMENSION or len(right) != EMBEDDING_DIMENSION:
        raise ValueError("dense semantic vector dimension mismatch")
    return max(-1.0, min(1.0, sum(float(a) * float(b) for a, b in zip(left, right))))


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        decay = math.exp(-value)
        return 1.0 / (1.0 + decay)
    growth = math.exp(value)
    return growth / (1.0 + growth)


def _combine(semantic_value: float, evidence_value: float | None) -> float:
    if evidence_value is None:
        return semantic_value
    evidence = _finite_unit(evidence_value, "evidence value")
    return 1.0 - ((1.0 - semantic_value) * (1.0 - evidence))


def _semantic_measurements(
    source_text: str,
    semantic_profile: Mapping[str, Any],
    bank: Mapping[str, Any],
    family: str,
) -> dict[str, dict[str, Any]]:
    names = CHANNELS if family == "channels" else DRIVERS
    chunks = semantic_profile["chunks"]
    beta = bank["formula"]["absolute_beta"]
    temperature = bank["formula"]["contrast_temperature"]
    candidates_by_name: dict[str, list[dict[str, Any]]] = {
        name: [] for name in names
    }
    for chunk in chunks:
        vector = chunk["values"]
        # Every anchor cosine is independent of the channel for which it later
        # serves as a positive or contrast. Compute it exactly once, retaining
        # the same Python sum order and tie-break as the original formula.
        scored = {
            name: [
                (_cosine(vector, anchor["vector"]), anchor)
                for anchor in bank[family][name]
            ]
            for name in names
        }
        for name in names:
            positive_cosine, positive_anchor = max(
                scored[name], key=lambda item: (item[0], item[1]["anchor_id"])
            )
            contrasts = [
                item for other in names if other != name for item in scored[other]
            ]
            contrast_cosine, contrast_anchor = max(
                contrasts, key=lambda item: (item[0], item[1]["anchor_id"])
            )
            absolute = math.exp(-beta * (1.0 - positive_cosine))
            specificity = _sigmoid(
                (positive_cosine - contrast_cosine) / temperature
            )
            value = absolute * specificity
            if not 0.0 < value <= 1.0:
                raise ValueError(f"dense semantic value for {name} is not positive")
            candidates_by_name[name].append({
                "value": value,
                "absolute_resonance": absolute,
                "contrast_specificity": specificity,
                "positive_cosine": positive_cosine,
                "contrast_cosine": contrast_cosine,
                "positive_anchor_id": positive_anchor["anchor_id"],
                "positive_anchor_sha256": positive_anchor["text_sha256"],
                "contrast_anchor_id": contrast_anchor["anchor_id"],
                "contrast_anchor_sha256": contrast_anchor["text_sha256"],
                "chunk_index": int(chunk["index"]),
                "start": int(chunk["start"]),
                "end": int(chunk["end"]),
                "chunk_text_sha256": chunk["text_sha256"],
            })
    return {
        name: max(
            candidates_by_name[name],
            key=lambda item: (item["value"], -item["chunk_index"]),
        )
        for name in names
    }


def _history_features(
    analysis: Mapping[str, Any],
) -> tuple[dict[str, float | None], dict[str, Any]]:
    metrics = analysis.get("history_metrics", {})
    similarities = metrics.get("combined_similarities", [])
    if not isinstance(similarities, list):
        raise ValueError("history combined similarities must be an array")
    sims = [_finite_unit(value, f"combined_similarities[{index}]")
            for index, value in enumerate(similarities)]
    features: dict[str, float | None] = {name: None for name in CHANNELS}
    details: dict[str, Any] = {
        "similarities": sims,
        "frequency_mean": None,
        "recurrence_max": None,
        "persistence_soft_recent_run": None,
        "burstiness_signed": None,
        "burstiness_magnitude": None,
        "history_centroid_similarity": None,
        "novelty_centroid_distance": None,
        "classification_confidence_change": None,
    }
    if sims:
        features["frequency"] = sum(sims) / len(sims)
        details["frequency_mean"] = features["frequency"]
        running = 1.0
        persistence_total = 0.0
        for value in reversed(sims[-6:]):
            running *= value
            persistence_total += running
        features["persistence"] = persistence_total / min(6, len(sims))
        details["persistence_soft_recent_run"] = features["persistence"]
        features["recurrence"] = max(sims)
        details["recurrence_max"] = features["recurrence"]
        features["volatility"] = max(
            1.0 - sims[-1],
            _finite_unit(metrics.get("static_distance_from_previous", 0.0),
                         "static_distance_from_previous"),
            _finite_unit(metrics.get("change_evidence", 0.0), "change_evidence"),
        )
    if len(sims) >= 2:
        split = max(1, len(sims) - min(4, len(sims) // 2))
        earlier = sims[:split]
        recent = sims[split:]
        signed = (sum(recent) / len(recent)) - (sum(earlier) / len(earlier))
        features["burstiness"] = abs(signed)
        details["burstiness_signed"] = signed
        details["burstiness_magnitude"] = features["burstiness"]
    centroid_similarity = analysis.get("history_centroid_similarity")
    if centroid_similarity is not None:
        centroid = _finite_unit(
            centroid_similarity, "history centroid similarity"
        )
        features["novelty"] = 1.0 - centroid
        details["history_centroid_similarity"] = centroid
        details["novelty_centroid_distance"] = features["novelty"]
    current_confidence = analysis.get("current_classification_confidence")
    previous_confidence = analysis.get("previous_classification_confidence")
    if current_confidence is not None and previous_confidence is not None:
        current = _finite_unit(current_confidence, "current classification confidence")
        previous = _finite_unit(previous_confidence, "previous classification confidence")
        features["decay"] = max(0.0, current - previous)
        details["classification_confidence_change"] = current - previous
    return features, details


def _structural_values(analysis: Mapping[str, Any]) -> dict[str, float]:
    load = analysis.get("load_signature")
    if not isinstance(load, Mapping) or set(load) != set(CHANNELS):
        raise ValueError("shadow source load must contain the canonical 17 channels")
    return {name: _finite_unit(load[name], f"load_signature.{name}") for name in CHANNELS}


def _driver_support(path: str, row: Mapping[str, Any]) -> dict[str, Any]:
    evidence = row["evidence"]
    return {
        "path": path,
        "start": int(evidence["start"]),
        "end": int(evidence["end"]),
        "quote": str(evidence["quote"]),
        "confidence": float(row["confidence"]),
    }


def derive_driver_evidence(
    source_text: str,
    candidate_payload: Any,
) -> dict[str, dict[str, Any]]:
    """Compile T/S/P from validated, exact quote-bound candidate facts."""
    candidate = validate_candidate(candidate_payload, source_text)
    support: dict[str, list[dict[str, Any]]] = {name: [] for name in DRIVERS}
    signal_routes = {
        "contradictions": "threat_load",
        "rejections": "threat_load",
        "completions": "sustenance_potential",
        "memory_references": "sustenance_potential",
        "future_references": "procreation_potential",
        "inferences": "procreation_potential",
    }
    for signal_name, driver in signal_routes.items():
        for index, row in enumerate(candidate["signals"][signal_name]):
            support[driver].append(
                _driver_support(f"signals.{signal_name}[{index}].evidence", row)
            )
    for index, row in enumerate(candidate["orientations"]):
        if row["negated"]:
            continue
        if row["polarity"] == "negative" or row["kind"] == "opposes":
            support["threat_load"].append(
                _driver_support(f"orientations[{index}].evidence", row)
            )
        if row["polarity"] == "positive" and row["kind"] in {
            "supports", "contains", "owns",
        }:
            support["sustenance_potential"].append(
                _driver_support(f"orientations[{index}].evidence", row)
            )
    for index, row in enumerate(candidate["causal_relations"]):
        if row["negated"]:
            continue
        if row["kind"] == "prevents":
            support["threat_load"].append(
                _driver_support(f"causal_relations[{index}].evidence", row)
            )
        if row["modality"] in {"inferred", "tentative", "hypothetical"}:
            support["procreation_potential"].append(
                _driver_support(f"causal_relations[{index}].evidence", row)
            )
    return {
        name: {
            "value": max((row["confidence"] for row in support[name]), default=0.0),
            "support": sorted(support[name], key=lambda row: row["path"]),
        }
        for name in DRIVERS
    }


def _driver_values(
    source_text: str,
    analysis: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if "driver_evidence" in analysis:
        raise ValueError(
            "numeric driver_evidence overrides are not accepted; provide a validated candidate"
        )
    candidate = analysis.get("candidate")
    if candidate is None:
        return {name: {"value": 0.0, "support": []} for name in DRIVERS}
    return derive_driver_evidence(source_text, candidate)


def _structural_corroboration(
    source_text: str,
    structural: Mapping[str, float],
    analysis: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    records = analysis.get("channel_records", [])
    if not isinstance(records, list):
        raise ValueError("source channel records must be an array")
    by_channel = {
        row.get("channel"): row
        for row in records
        if isinstance(row, Mapping) and isinstance(row.get("channel"), str)
    }
    profile = analysis.get("semantic_profile", {})
    profile_chunks = profile.get("chunks", []) if isinstance(profile, Mapping) else []
    chunk_starts = {
        item.get("index"): item.get("start")
        for item in profile_chunks
        if isinstance(item, Mapping)
        and type(item.get("index")) is int
        and type(item.get("start")) is int
    }
    result = {}
    for channel in ("L_contradiction", "L_inference"):
        row = by_channel.get(channel, {})
        raw_support = row.get("support", []) if isinstance(row, Mapping) else []
        if not isinstance(raw_support, list):
            raise ValueError(f"source channel record {channel} support must be an array")
        spans = []
        for index, item in enumerate(raw_support):
            if not isinstance(item, Mapping) or item.get("kind") != "span":
                continue
            start, end, quote = item.get("start"), item.get("end"), item.get("quote")
            chunk_index = item.get("chunk")
            offset = chunk_starts.get(chunk_index, 0)
            global_start = offset + start if type(start) is int else start
            global_end = offset + end if type(end) is int else end
            if (
                type(start) is not int or type(end) is not int
                or not isinstance(quote, str)
                or not 0 <= global_start < global_end <= len(source_text)
                or source_text[global_start:global_end] != quote
            ):
                raise ValueError(
                    f"source channel record {channel} support[{index}] is not exact"
                )
            spans.append({
                "path": str(item.get("path", "")),
                "chunk_index": chunk_index if type(chunk_index) is int else None,
                "local_start": start,
                "local_end": end,
                "start": global_start,
                "end": global_end,
                "quote": quote,
                "confidence": _finite_unit(
                    item.get("confidence"),
                    f"source channel record {channel} support[{index}].confidence",
                ),
            })
        result[channel] = {
            "required_for_future_authority": True,
            "structural_value": structural[channel],
            "quoted_support": spans,
            "present": structural[channel] > 0.0 and bool(spans),
        }
    return result


def compile_dense_shadow_load(
    source_text: str,
    semantic_profile_payload: Mapping[str, Any],
    source_analysis: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a replayable dense observation without touching runtime state."""
    profile = validate_semantic_profile(semantic_profile_payload, source_text)
    bank = load_anchor_bank()
    if profile["model"] != bank["embedding_model"]:
        raise ValueError("semantic profile model does not match dense anchor bank")
    if profile["revision"] != bank["embedding_revision"]:
        raise ValueError("semantic profile revision does not match dense anchor bank")
    structural = _structural_values(source_analysis)
    history, history_details = _history_features(source_analysis)
    semantic = _semantic_measurements(source_text, profile, bank, "channels")
    channel_records = []
    load_signature: dict[str, float] = {}
    for name in CHANNELS:
        history_value = history[name]
        evidence_value = (
            history_value
            if name in HISTORY_EVIDENCE_CHANNELS
            else structural[name]
        )
        final = _combine(semantic[name]["value"], evidence_value)
        _positive_unit(final, f"dense load.{name}")
        load_signature[name] = final
        channel_records.append({
            "channel": name,
            "semantic": semantic[name],
            "structural_evidence": structural[name],
            "history_feature": history_value,
            "history_feature_details": history_details,
            "combined_evidence": evidence_value,
            "value": final,
            "derivation": (
                "semantic=exp(-beta*(1-positive_cosine))*"
                "sigmoid((positive_cosine-contrast_cosine)/temperature);"
                " value=1-(1-semantic)*(1-evidence)"
            ),
        })

    driver_semantic = _semantic_measurements(source_text, profile, bank, "drivers")
    driver_evidence = _driver_values(source_text, source_analysis)
    driver_records = []
    drivers: dict[str, float] = {}
    for name in DRIVERS:
        final = _combine(
            driver_semantic[name]["value"], driver_evidence[name]["value"]
        )
        _positive_unit(final, f"dense driver.{name}")
        drivers[name] = final
        driver_records.append({
            "driver": name,
            "semantic": driver_semantic[name],
            "direct_evidence": driver_evidence[name]["value"],
            "direct_support": driver_evidence[name]["support"],
            "value": final,
            "derivation": (
                "semantic=exp(-beta*(1-positive_cosine))*"
                "sigmoid((positive_cosine-contrast_cosine)/temperature);"
                " value=1-(1-semantic)*(1-direct_evidence)"
            ),
        })

    graph = source_analysis.get("directed_graph")
    if graph is None:
        channel_evidence = source_analysis.get("channel_evidence", {})
        graph = channel_evidence.get("directed_graph", []) if isinstance(
            channel_evidence, Mapping
        ) else []
    if not isinstance(graph, list):
        raise ValueError("directed graph fingerprint must be an array")
    result = {
        "version": DENSE_LOAD_VERSION,
        "status": "shadow_only_not_authoritative",
        "source_text_sha256": text_digest(source_text),
        "semantic_profile_digest": digest(profile),
        "anchor_bank_sha256": bank["artifact_sha256"],
        "anchor_source_sha256": bank["source_sha256"],
        "formula": bank["formula"],
        "load_signature": load_signature,
        "driver_loads": drivers,
        "channel_records": channel_records,
        "driver_records": driver_records,
        "structural_corroboration": _structural_corroboration(
            source_text, structural, source_analysis
        ),
        "directed_graph": graph,
        "directed_graph_digest": digest(graph),
    }
    result["analysis_digest"] = digest(result)
    return result


def compile_document_dense_load(
    source_text: str,
    vector: Sequence[float],
    *,
    source_embedding_version: str,
    directed_graph: Sequence[Sequence[str]] = (),
) -> dict[str, Any]:
    """Compile one immutable document chunk into a replayable positive 17D drive.

    This is the production form of the owner-approved vector-first construction.
    The source vector is already retained with the immutable chunk.  No keyword
    projection and no language-model inference participates in this function.
    Authored reference/precedence edges may accompany the address, but are never
    invented here and do not silently alter the scalar load.
    """
    if not isinstance(source_text, str) or not source_text.strip():
        raise ValueError("document dense load requires non-empty source text")
    if not isinstance(source_embedding_version, str) or not source_embedding_version:
        raise ValueError("document dense load requires an embedding version")
    values = tuple(float(value) for value in vector)
    if len(values) != EMBEDDING_DIMENSION or not all(math.isfinite(value) for value in values):
        raise ValueError("document dense load vector must contain 384 finite values")
    norm = math.sqrt(sum(value * value for value in values))
    if abs(norm - 1.0) > 2e-3:
        raise ValueError("document dense load vector must be unit normalised")
    graph = []
    for index, edge in enumerate(directed_graph):
        if (
            not isinstance(edge, (list, tuple))
            or len(edge) != 3
            or not all(isinstance(item, str) and item for item in edge)
        ):
            raise ValueError(f"document directed graph edge {index} is invalid")
        graph.append([str(item) for item in edge])

    bank = load_anchor_bank()
    profile = {
        "chunks": [{
            "index": 0,
            "start": 0,
            "end": len(source_text),
            "text_sha256": text_digest(source_text),
            "values": list(values),
        }]
    }
    semantic = _semantic_measurements(source_text, profile, bank, "channels")
    load_signature = {name: _positive_unit(
        semantic[name]["value"], f"document dense load.{name}"
    ) for name in CHANNELS}
    driver_semantic = _semantic_measurements(source_text, profile, bank, "drivers")
    driver_loads = {name: _positive_unit(
        driver_semantic[name]["value"], f"document dense driver.{name}"
    ) for name in DRIVERS}
    # The pinned runtime's routing projection is the canonical bridge between
    # the 17-channel load and the 10K Tree's eight-dimensional branch vectors.
    # Keep both forms in the immutable receipt so an address can be replayed
    # without treating the mutable Tree as the only copy of the evidence.
    from agency.mechanics.sicd_msr_load import LoadSignature
    from agency.mechanics.sicd_msr_routing_basis import (
        project_load_signature_to_routing_basis,
    )

    routing = project_load_signature_to_routing_basis(
        LoadSignature.from_mapping(load_signature, strict=True)
    )
    result = {
        "version": DOCUMENT_DENSE_LOAD_VERSION,
        "status": "authoritative_document_index_drive",
        "source_text_sha256": text_digest(source_text),
        "source_embedding_version": source_embedding_version,
        "source_vector_sha256": "sha256:" + hashlib.sha256(
            struct.pack(f"<{EMBEDDING_DIMENSION}f", *values)
        ).hexdigest(),
        "anchor_bank_sha256": bank["artifact_sha256"],
        "anchor_source_sha256": bank["source_sha256"],
        "formula": bank["formula"],
        "load_signature": load_signature,
        "routing_basis_8d": routing.as_dict(),
        "driver_loads": driver_loads,
        "channel_records": [{
            "channel": name,
            "semantic": semantic[name],
            "value": load_signature[name],
            "derivation": (
                "semantic=exp(-beta*(1-positive_cosine))*"
                "sigmoid((positive_cosine-contrast_cosine)/temperature)"
            ),
        } for name in CHANNELS],
        "driver_records": [{
            "driver": name,
            "semantic": driver_semantic[name],
            "value": driver_loads[name],
            "derivation": (
                "semantic=exp(-beta*(1-positive_cosine))*"
                "sigmoid((positive_cosine-contrast_cosine)/temperature)"
            ),
        } for name in DRIVERS],
        "directed_graph": graph,
        "directed_graph_digest": digest(graph),
    }
    result["analysis_digest"] = digest(result)
    return result


def validate_document_dense_load(
    payload: Any,
    source_text: str,
    vector: Sequence[float],
    *,
    source_embedding_version: str,
    directed_graph: Sequence[Sequence[str]] = (),
) -> dict[str, Any]:
    """Replay a document drive exactly from retained source evidence."""
    rebuilt = compile_document_dense_load(
        source_text,
        vector,
        source_embedding_version=source_embedding_version,
        directed_graph=directed_graph,
    )
    if payload != rebuilt:
        raise ValueError("document dense load does not replay exactly")
    return rebuilt


def validate_dense_shadow_load(
    payload: Any,
    source_text: str,
    semantic_profile: Mapping[str, Any],
    source_analysis: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the whole observation exactly; never repair or re-score it."""
    if not isinstance(payload, Mapping):
        raise ValueError("dense shadow analysis must be an object")
    rebuilt = compile_dense_shadow_load(source_text, semantic_profile, source_analysis)
    if payload != rebuilt:
        raise ValueError("dense shadow analysis does not replay exactly")
    return rebuilt
