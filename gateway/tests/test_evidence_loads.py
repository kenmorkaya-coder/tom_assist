from __future__ import annotations

from copy import deepcopy
import json
import re
import sqlite3

import pytest

from gateway.structural_analysis import (
    ALLOWED_ZERO_KINDS,
    CANDIDATE_VERSION,
    CHANNELS,
    CHANNEL_DERIVATIONS,
    DISALLOWED_ZERO_KINDS,
    LOAD_EVIDENCE_POLICY,
    PARSER_VERSION,
    bind_candidate_metadata,
    build_analysis,
    canonicalize_candidate_ids,
    canonicalize_candidate_spans,
    candidate_tool_schema,
    directed_graph_fingerprint,
    directed_graph_similarity,
    evidenced_load_policy_result,
    rank_structural_history,
    project_candidate_fields,
    render_channel_reason,
    require_evidenced_load,
    require_strictly_positive_load,
    text_digest,
    validate_candidate,
    validate_frozen_analysis,
)
from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    build_semantic_profile,
    build_token_chunks,
    profile_similarity,
)
from gateway.evidence_gateway import EvidenceProjectRuntime, EvidenceTomGateway as TomGateway
from gateway.runtime_archive import export_snapshot, validate_snapshot
from gateway.structure_provider import isolated_worker_environment


_STATIC_ZERO_KINDS = {
    "S_entity": None,
    "S_dependency": None,
    "S_topology": None,
    "L_rule": "absent_evidence",
    "L_contradiction": "absent_evidence",
    "L_inference": None,
    "T_sequence": None,
    "T_memory": "absent_evidence",
    "T_future": None,
    "threat_amplitude": "absent_evidence",
}
EXPECTED_ZERO_KINDS = {
    "case_1_first": {
        **_STATIC_ZERO_KINDS,
        "frequency": "empty_history",
        "persistence": "empty_history",
        "burstiness": "empty_history",
        "volatility": "empty_history",
        "novelty": None,
        "recurrence": "empty_history",
        "decay": None,
    },
    "case_2_repeat": {
        **_STATIC_ZERO_KINDS,
        "T_memory": None,
        "frequency": None,
        "persistence": None,
        "burstiness": None,
        "volatility": "no_change",
        "novelty": "exact_recurrence",
        "recurrence": None,
        "decay": "fresh_match",
    },
    "case_3_reversal": {
        **_STATIC_ZERO_KINDS,
        "frequency": "no_match_in_window",
        "persistence": "no_match_in_window",
        "burstiness": "rate_unchanged",
        # Existing arithmetic stores recurrence-blended T_memory in static_load.
        "volatility": None,
        "novelty": None,
        "recurrence": "no_match_in_window",
        "decay": None,
    },
    "case_4_return": {
        **_STATIC_ZERO_KINDS,
        "T_memory": None,
        "frequency": None,
        "persistence": "streak_broken",
        "burstiness": None,
        "volatility": "no_change",
        "novelty": "exact_recurrence",
        "recurrence": None,
        "decay": None,
    },
    "case_5_declining": {
        **_STATIC_ZERO_KINDS,
        "T_memory": None,
        "frequency": None,
        "persistence": "streak_broken",
        "burstiness": "clamped_negative",
        "volatility": "no_change",
        "novelty": "exact_recurrence",
        "recurrence": None,
        "decay": None,
    },
}


def _span(text: str, quote: str, occurrence: int = 0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _fact(text: str, quote: str, confidence=1.0):
    return {"evidence": _span(text, quote), "confidence": confidence}


def _candidate(
    text: str,
    *,
    cause="A",
    effect="B",
    kind="causes",
    negated=False,
    memory=False,
    contradiction=False,
):
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [
            {"id": "entity_a", "label": "A", "kind": "event", "evidence": _span(text, "A"), "confidence": 1.0},
            {"id": "entity_b", "label": "B", "kind": "outcome", "evidence": _span(text, "B"), "confidence": 1.0},
        ],
        "orientations": [],
        "causal_relations": [{
            "id": "cause_1",
            "cause_entity_id": "entity_a" if cause == "A" else "entity_b",
            "effect_entity_id": "entity_b" if effect == "B" else "entity_a",
            "kind": kind,
            "modality": "asserted",
            "negated": negated,
            "evidence": _span(text, text),
            "confidence": 1.0,
        }],
        "signals": {
            "rules": [],
            "contradictions": [_fact(text, text)] if contradiction else [],
            "inferences": [],
            "sequences": [_fact(text, text)],
            "memory_references": [_fact(text, text)] if memory else [],
            "future_references": [],
            "completions": [],
            "rejections": [],
        },
        "unknown_fields": [],
        "confidence": 1.0,
    }


def _values(axis=0):
    values = [0.0] * EMBEDDING_DIMENSION
    values[axis] = 1.0
    return values


def _profile(text: str, axis=0):
    return build_semantic_profile(
        text,
        [{"start": 0, "end": len(text), "values": _values(axis)}],
        model="sentence-transformers/all-MiniLM-L6-v2",
        revision="fixture",
    )


def _chunk_candidates(candidate):
    return [{"chunk_index": 0, "candidate": candidate}]


def _empty_candidate(text: str):
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": [],
        "orientations": [],
        "causal_relations": [],
        "signals": {name: [] for name in (
            "rules", "contradictions", "inferences", "sequences",
            "memory_references", "future_references", "completions", "rejections",
        )},
        "unknown_fields": [],
        "confidence": 1.0,
    }


def _multi_profile(text: str, spans, axes):
    return build_semantic_profile(
        text,
        [
            {"start": start, "end": end, "values": _values(axis)}
            for (start, end), axis in zip(spans, axes)
        ],
        model="sentence-transformers/all-MiniLM-L6-v2",
        revision="fixture",
    )


def _parser():
    return {
        "version": PARSER_VERSION,
        "model": "local/gemma-fixture",
        "revision": "fixture-revision",
    }


def _analysis(text: str, axis: int, history, checkpoint: str):
    cause, effect = ("B", "A") if text == "B causes A." else ("A", "B")
    return build_analysis(
        text,
        _chunk_candidates(_candidate(text, cause=cause, effect=effect)),
        _profile(text, axis),
        _parser(),
        history,
        checkpoint,
    )


def _history_item(record_id: str, analysis):
    return {
        "record_id": record_id,
        "commit_key": record_id,
        "candidate": analysis["candidate"],
        "semantic_profile": analysis["semantic_profile"],
        "static_load": analysis["static_load"],
    }


def _zero_kind_table(analysis):
    return {
        record["channel"]: record["zero_kind"]
        for record in analysis["channel_records"]
    }


class _Provider:
    def __init__(self):
        self.calls = []

    def analyze(self, text):
        self.calls.append(text)
        if text == "A causes B.":
            return {
                "chunk_candidates": _chunk_candidates(_candidate(text)),
                "semantic_profile": _profile(text, 0),
                "parser_model": _parser(),
            }
        if text == "B causes A.":
            return {
                "chunk_candidates": _chunk_candidates(
                    _candidate(text, cause="B", effect="A")
                ),
                "semantic_profile": _profile(text, 1),
                "parser_model": _parser(),
            }
        if text == "A prevents B.":
            return {
                "chunk_candidates": _chunk_candidates(
                    _candidate(text, kind="prevents", contradiction=True)
                ),
                "semantic_profile": _profile(text, 2),
                "parser_model": _parser(),
            }
        raise AssertionError(f"unexpected fixture text: {text}")


def test_causal_direction_is_preserved_not_collapsed_into_magnitude():
    forward_text, reverse_text = "A causes B.", "B causes A."
    forward = validate_candidate(_candidate(forward_text), forward_text)
    reverse = validate_candidate(
        _candidate(reverse_text, cause="B", effect="A"), reverse_text
    )
    assert directed_graph_fingerprint(forward) != directed_graph_fingerprint(reverse)
    assert directed_graph_similarity(forward, reverse) == 0.0
    assert directed_graph_fingerprint(forward)[0][2:4] == ["a", "b"]
    assert directed_graph_fingerprint(reverse)[0][2:4] == ["b", "a"]


def test_token_chunking_overlaps_a_hard_boundary_without_losing_tail_text():
    words = [f"w{index}" for index in range(10)] + [
        "brake", "prevents", "cart", "movement", "safely", "today."
    ]
    text = " ".join(words)
    offsets = [(match.start(), match.end()) for match in re.finditer(r"\S+", text)]
    chunks = build_token_chunks(
        text, offsets, max_tokens=12, overlap_tokens=3, min_boundary_tokens=6
    )
    assert len(chunks) == 2
    assert chunks[0]["start"] == 0 and chunks[-1]["end"] == len(text)
    assert chunks[1]["start"] < chunks[0]["end"]
    bridge = text[chunks[1]["start"]:chunks[1]["end"]]
    assert "brake prevents cart" in bridge
    assert "today." in bridge


def test_overlap_candidates_rebase_and_deduplicate_exact_causal_evidence():
    text = "Opening words. A causes B. Closing words."
    relation_start = text.index("A causes B.")
    relation_end = relation_start + len("A causes B.")
    spans = [(0, relation_end), (relation_start, len(text))]
    profile = _multi_profile(text, spans, [0, 1])
    local_texts = [text[start:end] for start, end in spans]
    local_candidates = [_candidate(value) for value in local_texts]
    for local_text, candidate in zip(local_texts, local_candidates):
        candidate["causal_relations"][0]["evidence"] = _span(
            local_text, "A causes B."
        )
    analysis = build_analysis(
        text,
        [
            {"chunk_index": 0, "candidate": local_candidates[0]},
            {"chunk_index": 1, "candidate": local_candidates[1]},
        ],
        profile,
        _parser(),
        [],
        "checkpoint-overlap",
    )
    assert len(analysis["semantic_profile"]["chunks"]) == 2
    assert len(analysis["candidate"]["entities"]) == 2
    assert len(analysis["candidate"]["causal_relations"]) == 1
    relation = analysis["candidate"]["causal_relations"][0]
    assert relation["evidence"] == {
        "start": relation_start,
        "end": relation_end,
        "quote": "A causes B.",
    }
    assert directed_graph_fingerprint(analysis["candidate"])[0][2:4] == ["a", "b"]


def test_overlap_deduplicates_punctuation_only_relation_boundaries():
    text = "Opening. A enables B. Closing."
    relation_start = text.index("A enables B")
    relation_end = relation_start + len("A enables B.")
    spans = [(0, relation_end), (relation_start, len(text))]
    profile = _multi_profile(text, spans, [0, 1])
    candidates = []
    for index, (start, end) in enumerate(spans):
        local = text[start:end]
        candidate = _candidate(local, kind="enables")
        quote = "A enables B." if index == 0 else "A enables B"
        candidate["causal_relations"][0]["evidence"] = _span(local, quote)
        candidates.append({"chunk_index": index, "candidate": candidate})
    analysis = build_analysis(
        text, candidates, profile, _parser(), [], "checkpoint-punctuation-overlap"
    )
    assert len(analysis["candidate"]["causal_relations"]) == 1
    assert analysis["candidate"]["causal_relations"][0]["evidence"] == {
        "start": relation_start,
        "end": relation_end,
        "quote": "A enables B.",
    }


def test_overlap_merges_same_entity_when_one_window_quotes_the_whole_clause():
    text = "Opening. A enables B. Closing."
    relation_start = text.index("A enables B")
    relation_end = relation_start + len("A enables B.")
    spans = [(0, relation_end), (relation_start, len(text))]
    profile = _multi_profile(text, spans, [0, 1])
    candidates = []
    for index, (start, end) in enumerate(spans):
        local = text[start:end]
        candidate = _candidate(local, kind="enables")
        candidate["causal_relations"][0]["evidence"] = _span(
            local, "A enables B." if index == 0 else "A enables B"
        )
        if index == 0:
            for entity in candidate["entities"]:
                entity["evidence"] = _span(local, "A enables B.")
        candidates.append({"chunk_index": index, "candidate": candidate})
    analysis = build_analysis(
        text, candidates, profile, _parser(), [], "checkpoint-entity-granularity"
    )
    assert len(analysis["candidate"]["entities"]) == 2
    assert len(analysis["candidate"]["causal_relations"]) == 1
    assert [row["evidence"]["quote"] for row in analysis["candidate"]["entities"]] == [
        "A", "B"
    ]


def test_multivector_retrieval_finds_relevant_tail_chunk_without_centroid_collapse():
    query_text = "tail query"
    query = _profile(query_text, 5)
    long_text = "front material. tail material."
    split = long_text.index("tail")
    long_profile = _multi_profile(
        long_text, [(0, split + 5), (split, len(long_text))], [0, 5]
    )
    unrelated = _profile("front only", 0)
    semantic = profile_similarity(query, long_profile)
    assert semantic["best_chunk_score"] == 1.0
    assert semantic["best_right_chunk_index"] == 1
    empty_query = _empty_candidate(query_text)
    ranked = rank_structural_history(empty_query, query, [
        {"record_id": "long", "candidate": _empty_candidate(long_text),
         "semantic_profile": long_profile},
        {"record_id": "front", "candidate": _empty_candidate("front only"),
         "semantic_profile": unrelated},
    ])
    assert [row["record_id"] for row in ranked] == ["long", "front"]
    assert ranked[0]["semantic_match"]["pair_count"] == 2


def test_neutral_extra_chunks_do_not_inflate_the_17d_load():
    short = "A prevents B."
    short_analysis = build_analysis(
        short,
        _chunk_candidates(_candidate(short, kind="prevents", contradiction=True)),
        _profile(short, 0),
        _parser(),
        [],
        "checkpoint-short",
    )
    long = short + " " + ("Neutral background material. " * 30)
    boundary = 80
    second_start = 60
    spans = [(0, boundary), (second_start, len(long))]
    local_first = long[:boundary]
    local_second = long[second_start:]
    long_analysis = build_analysis(
        long,
        [
            {"chunk_index": 0, "candidate": _candidate(
                local_first, kind="prevents", contradiction=True
            )},
            {"chunk_index": 1, "candidate": _empty_candidate(local_second)},
        ],
        _multi_profile(long, spans, [0, 1]),
        _parser(),
        [],
        "checkpoint-long",
    )
    assert long_analysis["static_load"] == short_analysis["static_load"]
    assert long_analysis["load_signature"] == short_analysis["load_signature"]
    assert long_analysis["channel_evidence"]["aggregation"] == (
        "per_channel_max_across_bounded_chunks"
    )


def test_orientation_direction_is_preserved_separately_from_load_magnitude():
    text = "A supports B."
    forward = _candidate(text)
    forward["causal_relations"] = []
    forward["orientations"] = [{
        "id": "orientation_1",
        "source_entity_id": "entity_a",
        "target_entity_id": "entity_b",
        "kind": "supports",
        "polarity": "positive",
        "modality": "asserted",
        "negated": False,
        "evidence": _span(text, text),
        "confidence": 1.0,
    }]
    reverse = deepcopy(forward)
    reverse["orientations"][0]["source_entity_id"] = "entity_b"
    reverse["orientations"][0]["target_entity_id"] = "entity_a"
    validated_forward = validate_candidate(forward, text)
    validated_reverse = validate_candidate(reverse, text)
    assert directed_graph_fingerprint(validated_forward)[0][2:4] == ["a", "b"]
    assert directed_graph_fingerprint(validated_reverse)[0][2:4] == ["b", "a"]
    assert directed_graph_similarity(validated_forward, validated_reverse) == 0.0


def test_exact_evidence_binding_and_endpoint_validation_fail_closed():
    text = "A causes B."
    bad_quote = _candidate(text)
    bad_quote["causal_relations"][0]["evidence"]["quote"] = "B causes A."
    with pytest.raises(ValueError, match="quote does not exactly match"):
        validate_candidate(bad_quote, text)
    bad_endpoint = _candidate(text)
    bad_endpoint["causal_relations"][0]["effect_entity_id"] = "missing"
    with pytest.raises(ValueError, match="invalid cause-to-effect endpoints"):
        validate_candidate(bad_endpoint, text)
    extra_load = _candidate(text)
    extra_load["load_signature"] = {"S_entity": 1.0}
    with pytest.raises(ValueError, match="extra=.*load_signature"):
        validate_candidate(extra_load, text)


def test_model_local_ids_are_canonicalized_but_unknown_endpoints_still_fail():
    text = "A causes B."
    candidate = _candidate(text)
    candidate["entities"][0]["id"] = "A"
    candidate["entities"][1]["id"] = "B"
    candidate["causal_relations"][0]["cause_entity_id"] = "A"
    candidate["causal_relations"][0]["effect_entity_id"] = "B"
    normalized = validate_candidate(canonicalize_candidate_ids(candidate), text)
    assert [row["id"] for row in normalized["entities"]] == [
        "entity_0001", "entity_0002"
    ]
    assert normalized["causal_relations"][0]["cause_entity_id"] == "entity_0001"
    bad = deepcopy(candidate)
    bad["causal_relations"][0]["effect_entity_id"] = "missing"
    with pytest.raises(ValueError, match="unknown entity"):
        canonicalize_candidate_ids(bad)


def test_trusted_worker_binds_only_candidate_envelope_metadata():
    text = "A causes B."
    candidate = _candidate(text)
    del candidate["schema_version"]
    del candidate["signals"]
    candidate["source_text_sha256"] = "model-cannot-compute-this"
    bound = bind_candidate_metadata(candidate, text)
    assert bound["schema_version"] == CANDIDATE_VERSION
    assert bound["source_text_sha256"] == text_digest(text)
    assert all(value == [] for value in bound["signals"].values())
    assert bound["causal_relations"] == candidate["causal_relations"]
    assert validate_candidate(bound, text)["causal_relations"]


def test_quote_offsets_use_unique_or_nearest_model_intent_but_ties_fail():
    text = "A causes B."
    candidate = _candidate(text)
    candidate["entities"][1]["evidence"]["start"] = 0
    candidate["entities"][1]["evidence"]["end"] = 1
    repaired = validate_candidate(canonicalize_candidate_spans(candidate, text), text)
    assert repaired["entities"][1]["evidence"] == _span(text, "B")

    repeated = "A causes B. A remains."
    ambiguous = _candidate(repeated)
    ambiguous["entities"][0]["evidence"] = {"start": 99, "end": 100, "quote": "A"}
    rebound = canonicalize_candidate_spans(ambiguous, repeated)
    assert rebound["entities"][0]["evidence"] == _span(repeated, "A", 1)

    tied = _candidate("A A causes B.")
    tied["entities"][0]["evidence"] = {"start": 1, "end": 2, "quote": "A"}
    with pytest.raises(ValueError, match="missing or ambiguous"):
        canonicalize_candidate_spans(tied, "A A causes B.")


def test_missing_entity_quote_uses_only_its_exact_source_label():
    text = "A does not prevent B."
    candidate = _candidate(text, cause="A", effect="B", kind="prevents", negated=True)
    candidate["entities"][0]["label"] = "a"
    candidate["entities"][0]["evidence"] = {"start": 0, "end": 0, "quote": ""}
    repaired = canonicalize_candidate_spans(candidate, text)
    assert repaired["entities"][0]["evidence"] == _span(text, "A")
    candidate["entities"][0]["label"] = "invented entity"
    with pytest.raises(ValueError, match="no exact evidence quote"):
        canonicalize_candidate_spans(candidate, text)


def test_missing_quote_is_restored_only_from_valid_model_offsets():
    text = "Alpha causes Beta."
    candidate = _candidate(text, cause="Alpha", effect="Beta")
    relation_span = candidate["causal_relations"][0]["evidence"]
    del relation_span["quote"]
    repaired = canonicalize_candidate_spans(candidate, text)
    assert repaired["causal_relations"][0]["evidence"] == _span(text, text)

    unsafe = _candidate(text, cause="Alpha", effect="Beta")
    unsafe["causal_relations"][0]["evidence"] = {"start": -1, "end": 99}
    with pytest.raises(ValueError, match="no exact evidence quote"):
        canonicalize_candidate_spans(unsafe, text)


def test_model_only_extra_fields_are_projected_but_required_facts_stay_strict():
    text = "A supports B."
    candidate = _candidate(text)
    candidate["causal_relations"] = []
    candidate["orientations"] = [{
        "id": "relation_1",
        "source_entity_id": "entity_a",
        "target_entity_id": "entity_b",
        "target_entity_id_label": "B",
        "kind": "supports",
        "polarity": "positive",
        "modality": "asserted",
        "negated": False,
        "evidence": {**_span(text, text), "explanation": "not canonical"},
        "confidence": 1.0,
    }]
    candidate["source_text"] = text
    projected = project_candidate_fields(candidate)
    assert "source_text" not in projected
    assert "target_entity_id_label" not in projected["orientations"][0]
    assert "explanation" not in projected["orientations"][0]["evidence"]
    assert validate_candidate(projected, text)["orientations"]
    del projected["orientations"][0]["target_entity_id"]
    with pytest.raises(ValueError, match="missing=.*target_entity_id"):
        validate_candidate(projected, text)


def test_tool_schema_leaves_trusted_metadata_and_empty_signal_keys_to_product():
    parameters = candidate_tool_schema()["function"]["parameters"]
    assert "schema_version" not in parameters["properties"]
    assert "source_text_sha256" not in parameters["properties"]
    assert "required" not in parameters["properties"]["signals"]


def test_channel_record_shape_identity_support_and_reason_replay():
    analysis = _analysis("A causes B.", 0, [], "checkpoint-record-shape")
    records = analysis["channel_records"]
    assert len(records) == 17
    assert [record["channel"] for record in records] == list(CHANNELS)
    for record in records:
        channel = record["channel"]
        assert record["value"] == analysis["load_signature"][channel]
        assert record["derivation"] == CHANNEL_DERIVATIONS[channel]
        assert record["reason"] == render_channel_reason(record)
        assert 0.0 <= record["confidence"] <= 1.0
        if record["value"] > 0.0:
            assert record["support"]
            assert record["zero_kind"] is None
        else:
            assert record["zero_kind"] in (
                ALLOWED_ZERO_KINDS | DISALLOWED_ZERO_KINDS
            )
    assert require_evidenced_load(analysis) == analysis["load_signature"]


def test_five_predeclared_zero_kind_sequences_and_history_arithmetic():
    forward_1 = _analysis("A causes B.", 0, [], "case-1")
    history_a = [_history_item("turn-a1", forward_1)]
    forward_2 = _analysis("A causes B.", 0, history_a, "case-2")
    history_aa = [*history_a, _history_item("turn-a2", forward_2)]
    reversal = _analysis("B causes A.", 1, history_aa, "case-3")

    reverse_first = _analysis("B causes A.", 1, [], "case-4-reverse")
    history_ab = [
        _history_item("turn-a", forward_1),
        _history_item("turn-b", reverse_first),
    ]
    returned = _analysis("A causes B.", 0, history_ab, "case-4")

    declining_history = [
        _history_item("turn-a1", forward_1),
        _history_item("turn-a2", forward_2),
        *[
            _history_item(f"turn-b{index}", reverse_first)
            for index in range(1, 5)
        ],
    ]
    declining = _analysis("A causes B.", 0, declining_history, "case-5")

    cases = {
        "case_1_first": forward_1,
        "case_2_repeat": forward_2,
        "case_3_reversal": reversal,
        "case_4_return": returned,
        "case_5_declining": declining,
    }
    assert all(set(table) == set(CHANNELS) for table in EXPECTED_ZERO_KINDS.values())
    for name, analysis in cases.items():
        assert _zero_kind_table(analysis) == EXPECTED_ZERO_KINDS[name]

    assert reversal["history_metrics"]["combined_similarities"] == [0.0, 0.0]
    assert reversal["history_metrics"]["near_count"] == 0
    assert reversal["load_signature"]["recurrence"] == 0.0
    assert reversal["history_metrics"]["static_distance_from_previous"] > 0.0
    assert returned["history_metrics"]["combined_similarities"] == [1.0, 0.0]
    assert returned["load_signature"]["frequency"] == 0.5
    assert declining["history_metrics"]["recent_rate"] == 0.0
    assert declining["history_metrics"]["earlier_rate"] == 1.0
    assert declining["history_metrics"]["signed_rate_change"] == -1.0
    assert evidenced_load_policy_result(declining)["passes"] is False
    with pytest.raises(
        ValueError,
        match=rf"{LOAD_EVIDENCE_POLICY} failed:.*burstiness.*clamped_negative",
    ):
        require_evidenced_load(declining)


def test_positive_volatility_lists_history_and_all_change_spans():
    first = _analysis("A causes B.", 0, [], "volatility-0")
    history = [_history_item("turn-a", first)]
    text = "A prevents B."
    changed = build_analysis(
        text,
        _chunk_candidates(_candidate(text, kind="prevents", contradiction=True)),
        _profile(text, 2),
        _parser(),
        history,
        "volatility-1",
    )
    record = next(
        item for item in changed["channel_records"] if item["channel"] == "volatility"
    )
    assert record["value"] > 0.0
    history_items = [item for item in record["support"] if item["kind"] == "history"]
    span_items = [item for item in record["support"] if item["kind"] == "span"]
    assert len(history_items) == 1
    assert "static_distance_from_previous" in history_items[0]
    assert [item["path"] for item in span_items] == [
        "signals.contradictions[0].evidence"
    ]


def test_history_dynamics_are_distinct_and_replay_exactly():
    text = "A causes B."
    first = build_analysis(
        text, _chunk_candidates(_candidate(text)), _profile(text, 0),
        _parser(), [], "checkpoint-0"
    )
    assert first["load_signature"]["novelty"] == 1.0
    assert first["load_signature"]["decay"] == 1.0
    assert first["load_signature"]["frequency"] == 0.0
    assert first["load_signature"]["recurrence"] == 0.0
    history = [{
        "record_id": "turn-1",
        "candidate": first["candidate"],
        "semantic_profile": first["semantic_profile"],
        "static_load": first["static_load"],
    }]
    repeated = build_analysis(
        text, _chunk_candidates(_candidate(text, memory=True)), _profile(text, 0),
        _parser(), history, "checkpoint-1"
    )
    load = repeated["load_signature"]
    assert load["recurrence"] == 1.0
    assert load["frequency"] == 1.0
    assert load["persistence"] == 1.0
    assert load["novelty"] == 0.0
    assert load["decay"] == 0.0
    assert load["T_memory"] > first["load_signature"]["T_memory"]
    assert validate_frozen_analysis(repeated, text, history, "checkpoint-1") == repeated
    tampered = deepcopy(repeated)
    tampered["load_signature"]["frequency"] = 0.25
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_frozen_analysis(tampered, text, history, "checkpoint-1")
    tampered = deepcopy(repeated)
    tampered["channel_records"][0]["reason"] = "hand-edited"
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_frozen_analysis(tampered, text, history, "checkpoint-1")

    mixed_history = [
        history[0],
        {
            "record_id": "turn-2",
            "candidate": first["candidate"],
            "semantic_profile": _profile(text, 1),
            "static_load": first["static_load"],
        },
    ]
    mixed = build_analysis(
        text, _chunk_candidates(_candidate(text)), _profile(text, 0),
        _parser(), mixed_history, "checkpoint-2"
    )
    assert mixed["load_signature"]["recurrence"] == 1.0
    assert mixed["load_signature"]["frequency"] == 0.5
    assert mixed["load_signature"]["frequency"] != mixed["load_signature"]["recurrence"]
    assert mixed["load_signature"]["persistence"] == 0.0
    assert mixed["load_signature"]["decay"] > 0.0


def test_existing_parser_v1_analysis_still_replays_after_boundary_upgrade():
    text = "A causes B."
    parser = {
        "version": "gemma-native-tool-structural-candidate/1.0",
        "model": "local/gemma-fixture",
        "revision": "fixture-revision",
    }
    analysis = build_analysis(
        text, _chunk_candidates(_candidate(text)), _profile(text), parser, [],
        "checkpoint-parser-v1",
    )
    assert analysis["parser_model"] == parser
    assert validate_frozen_analysis(
        analysis, text, [], "checkpoint-parser-v1"
    ) == analysis


def test_structural_evidence_activates_dimensions_without_keyword_wheel():
    text = "A prevents B."
    analysis = build_analysis(
        text, _chunk_candidates(_candidate(text, kind="prevents", contradiction=True)),
        _profile(text, 0), _parser(), [], "checkpoint"
    )
    load = analysis["load_signature"]
    for channel in (
        "S_entity", "S_dependency", "S_topology", "L_contradiction",
        "L_inference", "T_sequence", "threat_amplitude", "novelty", "decay",
    ):
        assert load[channel] > 0.0, channel
    assert load["frequency"] != load["recurrence"] or load["frequency"] == 0.0


def test_shadow_gateway_binds_preview_to_commit_and_restart(tmp_path):
    provider = _Provider()
    gateway = TomGateway(
        tmp_path, structure_mode="shadow", structure_provider=provider
    )
    runtime = gateway.project("evidence-load")
    assert type(runtime.engine).__module__ == "agency.mechanics.sicd_engine"
    assert len(runtime.engine.state.branches) == 10_000
    before = runtime.serialized_state_bytes()
    before_library = runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0]
    previews = [runtime.preview_rank("A causes B.", 10, 2000) for _ in range(100)]
    preview = previews[0]
    assert all(item == preview for item in previews)
    assert runtime.serialized_state_bytes() == before
    assert runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0] == before_library
    assert preview["structural_load_mode"] == "shadow"
    assert any(
        value == 0.0
        for value in preview["structural_analysis"]["load_signature"].values()
    )
    assert preview["structural_analysis"]["parser_model"] == _parser()
    assert preview["load_evidence_policy_result"]["passes"] is True
    assert preview["strict_positive_load_policy_result"]["passes"] is False
    result = runtime.commit_turn(
        "user", "A causes B.", "turn-1",
        activated_branch_ids=preview["activated_branch_ids"],
        structural_analysis=preview["structural_analysis"],
    )
    assert result["structural_load"]["mode"] == "shadow"
    assert result["structural_load"]["causal_relation_count"] == 1
    assert result["structural_load"]["channel_records"] == (
        preview["structural_analysis"]["channel_records"]
    )
    assert result["structural_load"]["candidate_load_signature"] == (
        preview["structural_analysis"]["load_signature"]
    )
    assert result["structural_load"]["load_evidence_policy_result"]["passes"] is True
    assert result["structural_load"]["strict_positive_load_policy_result"]["passes"] is False
    assert result["commit_drive"]["branch_count_before"] == 10_000
    assert result["commit_drive"]["plan"]["load_signature_17"] == preview["load_signature"]
    assert len(result["commit_drive"]["plan"]["driver_vec"]) == 3
    assert any(value > 0.0 for value in result["commit_drive"]["plan"]["driver_vec"])
    assert len(result["commit_drive"]["plan"]["routing_basis_8d"]) == 8
    assert runtime.library.structural_analysis("turn-1") == preview["structural_analysis"]

    archive = tmp_path / "runtime-archive"
    export_snapshot(gateway, "evidence-load", archive)
    validate_snapshot(gateway, archive)
    with sqlite3.connect(archive / "library.sqlite3") as database:
        archived = json.loads(database.execute(
            "SELECT analysis_json FROM structural_commits WHERE commit_key='turn-1'"
        ).fetchone()[0])
    assert archived == preview["structural_analysis"]
    assert archived["channel_records"] == preview["structural_analysis"]["channel_records"]

    restarted = TomGateway(
        tmp_path, structure_mode="shadow", structure_provider=provider
    ).project("evidence-load")
    second = restarted.preview_rank("A causes B.", 10, 2000)
    assert second["structural_analysis"]["history_metrics"]["history_count"] == 1
    assert second["structural_analysis"]["load_signature"]["recurrence"] == 1.0
    assert second["shadow_structural_retrieval"][0]["record_id"] == result["anchor_id"]

    stale = second["structural_analysis"]
    reverse = restarted.preview_rank("B causes A.", 10, 2000)
    restarted.commit_turn(
        "user", "B causes A.", "turn-2",
        activated_branch_ids=reverse["activated_branch_ids"],
        structural_analysis=reverse["structural_analysis"],
    )
    with pytest.raises(ValueError, match="stale; prepare again"):
        restarted.commit_turn("user", "A causes B.", "turn-stale", structural_analysis=stale)


def test_strict_positive_load_guard_names_zeros_and_never_invents_a_floor():
    all_positive = {channel: 0.25 for channel in (
        "S_entity", "S_dependency", "S_topology", "L_rule",
        "L_contradiction", "L_inference", "T_sequence", "T_memory", "T_future",
        "threat_amplitude", "frequency", "persistence", "burstiness",
        "volatility", "novelty", "recurrence", "decay",
    )}
    assert require_strictly_positive_load(all_positive) == all_positive
    all_positive["T_memory"] = 0.0
    all_positive["recurrence"] = -0.0
    with pytest.raises(
        ValueError,
        match=r"zero_channels=\['T_memory', 'recurrence'\].*no synthetic floor",
    ):
        require_strictly_positive_load(all_positive)
    assert all_positive["T_memory"] == 0.0
    assert all_positive["recurrence"] == 0.0


def test_authoritative_build_rejects_zero_17d_before_tree_or_library_mutation(tmp_path):
    provider = _Provider()
    gateway = TomGateway(
        tmp_path, structure_mode="authoritative", structure_provider=provider
    )
    capabilities = gateway.capabilities()
    assert capabilities["strict_positive_load_policy"] == (
        "tom-assist-strict-positive-load17/1.0"
    )
    assert capabilities["authoritative_requires_all_17_channels_positive"] is True
    assert capabilities["load_evidence_policy"] == LOAD_EVIDENCE_POLICY
    assert capabilities["authoritative_requires_all_17_channels_evidenced"] is True
    assert capabilities["authoritative_disallowed_zero_kinds"] == ["clamped_negative"]
    runtime = gateway.project("telemetry")
    assert __import__("os").environ["TOM_FEELING_WHEEL_ENABLED"] == "0"
    before = runtime.serialized_state_bytes()
    before_tick = runtime.engine.state.tick
    before_library = runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0]
    with pytest.raises(
        ValueError,
        match=r"authoritative 17-channel load cannot reach the 10K tree: "
        r"zero_channels=.*no synthetic floor",
    ):
        runtime.preview_rank("A prevents B.", 10, 2000)
    proposed = provider.analyze("A prevents B.")
    analysis = build_analysis(
        "A prevents B.",
        proposed["chunk_candidates"],
        proposed["semantic_profile"],
        proposed["parser_model"],
        [],
        runtime._current_checkpoint_digest(),
    )
    with pytest.raises(
        ValueError,
        match=r"authoritative 17-channel load cannot reach the 10K tree: "
        r"zero_channels=.*no synthetic floor",
    ):
        runtime.commit_turn(
            "user",
            "A prevents B.",
            "direct-bypass-attempt",
            structural_analysis=analysis,
        )
    assert runtime.serialized_state_bytes() == before
    assert runtime.engine.state.tick == before_tick
    assert runtime.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0] == before_library


def test_declining_rate_fails_evidence_then_strict_authority_but_shadow_commits(
    tmp_path,
):
    provider = _Provider()
    shadow = TomGateway(
        tmp_path, structure_mode="shadow", structure_provider=provider
    ).project("declining-rate")
    sequence = [
        "A causes B.",
        "A causes B.",
        "B causes A.",
        "B causes A.",
        "B causes A.",
        "B causes A.",
    ]
    for index, text in enumerate(sequence):
        preview = shadow.preview_rank(text, 10, 2000)
        shadow.commit_turn(
            "user",
            text,
            f"history-{index}",
            structural_analysis=preview["structural_analysis"],
        )

    authoritative = TomGateway(
        tmp_path, structure_mode="authoritative", structure_provider=provider
    ).project("declining-rate")
    before = authoritative.serialized_state_bytes()
    before_tick = authoritative.engine.state.tick
    before_library = authoritative.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0]
    with pytest.raises(
        ValueError,
        match=rf"{LOAD_EVIDENCE_POLICY} failed:.*burstiness.*clamped_negative",
    ):
        authoritative.preview_rank("A causes B.", 10, 2000)

    proposed = provider.analyze("A causes B.")
    analysis = build_analysis(
        "A causes B.",
        proposed["chunk_candidates"],
        proposed["semantic_profile"],
        proposed["parser_model"],
        authoritative._active_structural_history(),
        authoritative._current_checkpoint_digest(),
    )
    with pytest.raises(
        ValueError,
        match=rf"{LOAD_EVIDENCE_POLICY} failed:.*burstiness.*clamped_negative",
    ):
        authoritative.commit_turn(
            "user",
            "A causes B.",
            "direct-declining-bypass",
            structural_analysis=analysis,
        )
    assert authoritative.serialized_state_bytes() == before
    assert authoritative.engine.state.tick == before_tick
    assert authoritative.library.db.execute(
        "SELECT COUNT(*) FROM structural_commits"
    ).fetchone()[0] == before_library

    preview = shadow.preview_rank("A causes B.", 10, 2000)
    assert preview["load_evidence_policy_result"]["passes"] is False
    assert preview["strict_positive_load_policy_result"]["passes"] is False
    result = shadow.commit_turn(
        "user",
        "A causes B.",
        "shadow-declining",
        structural_analysis=preview["structural_analysis"],
    )
    assert result["structural_load"]["load_evidence_policy_result"]["passes"] is False
    assert result["structural_load"]["strict_positive_load_policy_result"]["passes"] is False


def test_structure_path_contains_no_emotion_lexicon_import():
    root = __import__("pathlib").Path(__file__).parents[1]
    for name in (
        "structural_analysis.py", "structure_provider.py", "structure_worker.py",
        "gemma_structure_worker.py",
    ):
        source = (root / name).read_text(encoding="utf-8").casefold()
        assert "agency.excitation.feeling_wheel" not in source
        assert "feeling_wheel_mapper" not in source
        assert "emotion_wheel" not in source


def test_local_model_environment_is_offline_and_credential_free(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-cross")
    monkeypatch.setenv("HF_TOKEN", "must-not-cross")
    monkeypatch.setenv("TOM_ASSIST_OAUTH_BROKER_SOCKET", "/must/not/cross")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-cross")
    environment = isolated_worker_environment()
    assert environment["TRANSFORMERS_OFFLINE"] == "1"
    assert environment["HF_HUB_OFFLINE"] == "1"
    assert environment["TOM_FEELING_WHEEL_ENABLED"] == "0"
    assert not any("must-not-cross" in value for value in environment.values())


def test_evidence_preview_contains_no_forbidden_runtime_mutation_calls():
    import inspect

    source = inspect.getsource(EvidenceProjectRuntime.preview_rank)
    for forbidden in ("rgm.read_memory", "ToMClient.process", "engine.step"):
        assert forbidden not in source
