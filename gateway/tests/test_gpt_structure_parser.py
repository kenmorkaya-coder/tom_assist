import json

import pytest

from gateway.gpt_structure_parser import GPTStructureParser, GPTStructureParserError
from gateway.structural_analysis import SIGNAL_NAMES, quote_candidate_response_format


class FixtureProvider:
    def __init__(self):
        self.calls = []

    def complete_structured(
        self, prompt, response_format, *, explicit_send=False
    ):
        self.calls.append((prompt, response_format, explicit_send))
        payload = {
            "entities": [
                {
                    "id": "alpha",
                    "label": "Alpha",
                    "kind": "concept",
                    "evidence": {"quote": "Alpha"},
                    "confidence": 1.0,
                },
                {
                    "id": "beta",
                    "label": "Beta",
                    "kind": "concept",
                    "evidence": {"quote": "Beta"},
                    "confidence": 1.0,
                },
            ],
            "orientations": [],
            "causal_relations": [
                {
                    "id": "edge",
                    "cause_entity_id": "alpha",
                    "effect_entity_id": "beta",
                    "kind": "enables",
                    "modality": "asserted",
                    "negated": False,
                    "evidence": {"quote": "Alpha enables Beta"},
                    "confidence": 1.0,
                }
            ],
            "signals": {name: [] for name in SIGNAL_NAMES},
            "unknown_fields": [],
            "confidence": 1.0,
        }
        return {
            "text": json.dumps(payload),
            "model": "gpt-fixture",
            "complete": True,
        }


def test_gpt_parser_binds_quotes_and_never_accepts_provider_offsets():
    provider = FixtureProvider()
    result = GPTStructureParser(provider).parse(
        "Alpha enables Beta.", explicit_send=True
    )
    candidate = result["candidate"]
    assert candidate["entities"][0]["evidence"] == {
        "start": 0,
        "end": 5,
        "quote": "Alpha",
    }
    assert candidate["entities"][1]["evidence"] == {
        "start": 14,
        "end": 18,
        "quote": "Beta",
    }
    assert candidate["causal_relations"][0]["evidence"] == {
        "start": 0,
        "end": 18,
        "quote": "Alpha enables Beta",
    }
    assert result["telemetry"]["offset_source"] == "tom-assist-exact-quote-binding"
    assert result["telemetry"]["load_source"] == "tom-assist-deterministic-compiler"
    assert result["telemetry"]["raw_response_retained"] is False
    prompt, response_format, explicit_send = provider.calls[0]
    assert explicit_send is True
    assert "emotion labels" in prompt and "load numbers" in prompt
    assert response_format == quote_candidate_response_format()
    serialized_format = json.dumps(response_format)
    assert '"start"' not in serialized_format
    assert '"end"' not in serialized_format


def test_gpt_parser_cannot_run_without_explicit_send():
    provider = FixtureProvider()
    with pytest.raises(GPTStructureParserError, match="EXPLICIT_SEND_REQUIRED"):
        GPTStructureParser(provider).parse("Alpha enables Beta.")
    assert provider.calls == []
