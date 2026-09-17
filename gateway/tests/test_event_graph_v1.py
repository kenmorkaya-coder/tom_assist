from copy import deepcopy
import json
from pathlib import Path
import pytest

from gateway.typed_event_graph import validate_graph, semantic_graph, quantity
from gateway.event_graph_extractor import bind_quotes, quote_only
from gateway.event_graph_compiler import compile_graph
from validation.event_graph_v1.build_corpus import case, FAMILIES
from validation.event_graph_v1.experiment import score_extraction

THRESHOLDS = {"valid": 1, "exact": .95, "family_exact": .9, "invented_authority": 0, "contrast_distinct": 1, "paraphrase_equal": .95}


@pytest.mark.parametrize("family", FAMILIES)
def test_authored_contrasts_and_quote_binding(family):
    rows = [case("heldout", family, 0, v) for v in range(3)]
    for row in rows:
        assert bind_quotes(quote_only(row["graph"]), row["source"]) == row["graph"]
    a, b, c = [semantic_graph(r["graph"]) for r in rows]
    assert a == b
    assert a != c


def test_recipient_is_not_authority_and_trigger_is_shared():
    row = case("train", "recipient", 0, 0)
    events = row["graph"]["events"]
    assert len(events) == 2
    assert events[0]["condition"] == events[1]["condition"]
    assert all(e["roles"]["authority"] is None for e in events)
    assert events[1]["roles"]["recipient"] is not None
    assert events[1]["roles"]["actor"] is None


@pytest.mark.parametrize("mutation", ("dangling", "duplicate", "cycle", "evidence", "unsupported_unit", "boolean_quantity", "extra", "wrong_role"))
def test_fail_closed(mutation):
    row = case("train", "recipient", 0, 0); g = deepcopy(row["graph"])
    if mutation == "dangling": g["events"][0]["condition"] = "missing"
    elif mutation == "duplicate": g["entities"][1]["id"] = g["entities"][0]["id"]
    elif mutation == "cycle": g["events"][0]["condition"] = g["events"][0]["id"]
    elif mutation == "evidence": g["events"][0]["evidence"][0]["quote"] = "fabricated"
    elif mutation == "unsupported_unit": g["predicates"][0]["unit"] = "bananas"
    elif mutation == "boolean_quantity": g["predicates"][0]["value"] = True
    elif mutation == "extra": g["matrix"] = [0] * 1024
    else: g["events"][0]["roles"]["object"] = g["predicates"][0]["id"]
    with pytest.raises(ValueError): validate_graph(g, row["source"])


def test_exact_rational_unit_equivalence_and_sign():
    assert quantity("60", "L/min") == quantity("0.001", "m3/s")
    assert quantity("1", "L/min") != quantity("0.001", "m3/s")
    assert quantity("1", "m") == quantity("1000.0", "mm")
    assert quantity("-1", "m") != quantity("1", "m")
    assert quantity("0", "kg") == quantity("0.0", "g")


def test_multiple_loads_and_role_change_affects_numbers():
    row = case("train", "recipient", 0, 0)
    before = compile_graph(row["graph"], row["source"])
    assert before == compile_graph(row["graph"], row["source"])
    assert len(before["loads"]) == 2
    assert all(len(r["matrix"]) == 32 and all(len(v) == 32 for v in r["matrix"]) for r in before["loads"])
    g = deepcopy(row["graph"])
    roles = g["events"][1]["roles"]
    roles["authority"], roles["recipient"] = roles["recipient"], None
    after = compile_graph(g, row["source"])
    assert before["loads"][1]["matrix"] != after["loads"][1]["matrix"]


def test_no_prose_or_evidence_in_numerical_encoding():
    a, b = [case("train", "paragraph", 0, v) for v in (0, 1)]
    first, second = [compile_graph(r["graph"], r["source"]) for r in (a, b)]
    assert [v["matrix"] for v in first["loads"]] == [v["matrix"] for v in second["loads"]]
    assert first["source_sha256"] != second["source_sha256"]


def test_unresolved_does_not_compile_or_disappear_from_denominator():
    rows = [case("heldout", "quantity", 0, v) for v in range(3)]
    predictions = [{"id": r["id"], "graph": deepcopy(r["graph"])} for r in rows]
    predictions[0]["graph"]["unresolved"] = [{"reason": "ambiguous", "evidence": rows[0]["graph"]["events"][0]["evidence"]}]
    with pytest.raises(ValueError): compile_graph(predictions[0]["graph"], rows[0]["source"])
    report = score_extraction(rows, predictions[:2], THRESHOLDS)
    assert report["verdict"] == "RED" and report["total"] == 3 and report["exact"] == 1


def test_oracle_pass_and_bad_scope_fails():
    rows = [case("heldout", "multi_quantity", 0, v) for v in range(3)]
    predictions = [{"id": r["id"], "graph": deepcopy(r["graph"])} for r in rows]
    assert score_extraction(rows, predictions, THRESHOLDS)["verdict"] == "GREEN"
    e = predictions[0]["graph"]["events"]
    e[0]["condition"], e[1]["condition"] = e[1]["condition"], e[0]["condition"]
    assert score_extraction(rows, predictions, THRESHOLDS)["verdict"] == "RED"


def test_authority_invention_gate():
    rows = [case("heldout", "recipient", 0, v) for v in range(3)]
    predictions = [{"id": r["id"], "graph": deepcopy(r["graph"])} for r in rows]
    roles = predictions[0]["graph"]["events"][1]["roles"]
    roles["authority"] = roles["recipient"]
    report = score_extraction(rows, predictions, THRESHOLDS)
    assert report["invented_authority"] == 1 and report["verdict"] == "RED"


def test_duplicate_predictions_rejected():
    row = case("heldout", "quantity", 0, 0)
    p = {"id": row["id"], "graph": row["graph"]}
    with pytest.raises(ValueError): score_extraction([row], [p, p], THRESHOLDS)
