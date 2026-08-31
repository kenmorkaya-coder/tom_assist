from pathlib import Path

import pytest

from gateway.guardrail_resonance import resonate_guardrails, response_spans
from gateway.tom_gateway import TomGateway

TOM_MASTER = Path("/Users/kenmorkaya/PycharmProjects/tom_master")


def test_native_teaching_projection_matches_later_paraphrase_with_exact_quote(tmp_path, monkeypatch):
    gateway = TomGateway(tmp_path / "data", TOM_MASTER)
    runtime = gateway.project("guardrail-purity")
    before = runtime.serialized_state_bytes(), list(runtime.library.db.iterdump())

    def forbidden(*args, **kwargs):
        raise AssertionError("evaluation touched a mutating runtime surface")

    runtime.engine.step = forbidden
    runtime.rgm.read_memory = forbidden
    runtime.engine.apply_leaf_vec_update = forbidden
    import agency.mechanics.leaf_vectors as leaves
    monkeypatch.setattr(leaves, "select_activated_branches", forbidden)
    response = "First, then after, sequence stage. The beam transfers force through the connected columns."
    anchors = [{"state_id": kind, "kind": kind, "text": "A beam connects two columns and supports load."}
               for kind in ["REJECTED_PATH", "CONSTRAINT", "COMPLETED_WORK"]]
    payload = {"response_text": response, "anchors": anchors}
    status, result = gateway.handle("POST", "/verify/guardrails", payload)
    assert status == 200
    assert len(result["matches"]) == 3
    for hit in result["matches"]:
        assert hit["response_excerpt"] == response[hit["start"]:hit["end"]]
        assert hit["response_excerpt"] == "The beam transfers force through the connected columns."
        assert hit["score"] >= 0.98
    assert result["semantic_verdict"] is False
    assert result == resonate_guardrails({**payload, "anchors": list(reversed(anchors))})
    assert before == (runtime.serialized_state_bytes(), list(runtime.library.db.iterdump()))


def test_distinct_native_channels_empty_and_invalid_inputs(tmp_path):
    TomGateway(tmp_path / "data", TOM_MASTER)
    anchor = {"state_id": "a", "kind": "CONSTRAINT", "text": "beam columns load connected structural geometry"}
    result = resonate_guardrails({"response_text": "First then after stage sequence ordering before later.", "anchors": [anchor]})
    assert result["matches"] == []
    assert resonate_guardrails({"response_text": "", "anchors": [anchor]})["matches"] == []
    assert resonate_guardrails({"response_text": "hello", "anchors": []})["matches"] == []
    for anchors in [[anchor, anchor], [{**anchor, "kind": "DECISION"}], [{**anchor, "text": ""}]]:
        with pytest.raises(ValueError):
            resonate_guardrails({"response_text": "hello", "anchors": anchors})


def test_span_boundaries_cover_late_and_unicode_text_without_rewriting():
    response = " \n" + "é" * 900 + ". Next rejected plan? Last line\n"
    spans = list(response_spans(response))
    assert len(spans) == 5
    assert all(response[start:end] == text and len(text) <= 320 for start, end, text in spans)
    assert spans[-1][2] == "Last line"
