"""Adversarial build verification; not held-out experimental results."""
from copy import deepcopy
import math
import pytest
from gateway.event_graph_compiler import compile_graph
from gateway.event_graph_extractor import bind_quotes, quote_only
from gateway.typed_event_graph import semantic_graph, validate_graph
from validation.event_graph_v1.build_corpus import case
from validation.event_graph_v1.experiment import score_extraction
from gateway.tests.test_event_graph_v1 import THRESHOLDS


def test_renaming_local_ids_preserves_meaning_and_loads():
    row = case("train", "paragraph", 0, 0)
    graph = row["graph"]
    ids = {r["id"]: f"renamed-{r['id']}" for key in ("entities", "predicates", "conditions", "events", "links") for r in graph[key]}
    def rename(value):
        if isinstance(value, str): return ids.get(value, value)
        if isinstance(value, list): return [rename(v) for v in value]
        if isinstance(value, dict): return {k: rename(v) for k, v in value.items()}
        return value
    other = rename(graph)
    validate_graph(other, row["source"])
    assert semantic_graph(graph) == semantic_graph(other)
    assert [x["matrix"] for x in compile_graph(graph, row["source"])["loads"]] == [x["matrix"] for x in compile_graph(other, row["source"])["loads"]]


def test_approval_preserves_complement_and_does_not_assert_occurrence():
    row = case("train", "approval", 0, 0)
    events = row["graph"]["events"]
    assert events[0]["exception"] == events[1]["id"]
    assert events[1]["complement"] == events[2]["id"]
    assert events[1]["modality"] == events[2]["modality"] == "hypothetical"
    assert events[2]["action"] == "stop"
    assert all(e["roles"]["authority"] is None for e in events)


def test_orphaned_predicate_is_not_silently_discarded():
    row = case("train", "quantity", 0, 0)
    g = deepcopy(row["graph"])
    g["predicates"].append({**g["predicates"][0], "id": "unused"})
    with pytest.raises(ValueError, match="unreferenced"):
        compile_graph(g, row["source"])


def test_ambiguous_quote_and_model_offsets_rejected():
    row = case("train", "revision", 0, 0)
    g = quote_only(row["graph"])
    g["entities"][0]["mentions"] = [{"quote": "Aster works 0"}]
    with pytest.raises(ValueError, match="ambiguous"): bind_quotes(g, row["source"])
    with pytest.raises(ValueError, match="offsets"): bind_quotes(row["graph"], row["source"])


def test_wrong_polarity_and_dropped_event_fail_whole_graph_gate():
    rows = [case("train", "paragraph", 0, v) for v in range(3)]
    p = [{"id": r["id"], "graph": deepcopy(r["graph"])} for r in rows]
    p[0]["graph"]["events"][1]["negated"] = True
    p[1]["graph"]["events"].pop(2)
    result = score_extraction(rows, p, THRESHOLDS)
    assert result["verdict"] == "RED"
    assert result["total"] == 3 and result["exact"] == 1


def test_signed_unit_loads_and_explicit_links_remain_separate():
    row = case("train", "temporal", 0, 0)
    result = compile_graph(row["graph"], row["source"])
    assert [r["kind"] for r in result["loads"]] == ["event", "event", "link"]
    assert result["links"][0]["kind"] == "before"
    for load in result["loads"]:
        values = [v for row in load["matrix"] for v in row]
        assert all(math.isfinite(v) for v in values)
        assert min(values) < 0 < max(values)
        assert sum(v*v for v in values) == pytest.approx(1)
