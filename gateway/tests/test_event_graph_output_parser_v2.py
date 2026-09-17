import json
import pytest
from gateway.event_graph_extractor import quote_only, parse_output as parse_v1
from gateway.event_graph_extractor_v2 import parse_output
from validation.event_graph_v1.build_corpus import case


def sample():
    row = case("train", "recipient", 0, 0)
    return row, json.dumps(quote_only(row["graph"]))


@pytest.mark.parametrize("wrapper", ("{}", "```json\n{}\n```", "```\n{}\n```", "```json\r\n{}\r\n```"))
def test_only_presentation_changes(wrapper):
    row, raw = sample()
    assert parse_output(wrapper.format(raw), row["source"]) == row["graph"]


@pytest.mark.parametrize("wrapper", ("Here is the graph: {}", "```json\n{}\n```\nExtra text", "```json\n{}\n```\n```json\n{{}}\n```", "```json\n{}"))
def test_no_prose_or_partial_container_repair(wrapper):
    row, raw = sample()
    with pytest.raises(ValueError): parse_output(wrapper.format(raw), row["source"])


def test_frozen_v1_behavior_is_retained():
    row, raw = sample()
    with pytest.raises(ValueError): parse_v1("```json\n" + raw + "\n```", row["source"])


def test_no_semantic_repair():
    row, raw = sample()
    payload = json.loads(raw)
    del payload["events"][0]["roles"]["authority"]
    with pytest.raises(ValueError): parse_output("```json\n" + json.dumps(payload) + "\n```", row["source"])
