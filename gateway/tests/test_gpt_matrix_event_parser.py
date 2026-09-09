import json

import pytest

from gateway.gpt_matrix_event_parser import (
    GPTMatrixEventParser,
    GPTMatrixEventParserError,
)


class FixtureProvider:
    def __init__(self):
        self.calls = []

    def complete_structured(self, prompt, response_format, *, explicit_send=False):
        self.calls.append((prompt, response_format, explicit_send))
        return {
            "text": json.dumps({
                "events": [{
                    "source_evidence": {"quote": "The Contractor"},
                    "target_evidence": {"quote": "pay the levy"},
                    "relation_kind": "obligation",
                    "relation_evidence": {
                        "quote": "The Contractor must pay the levy"
                    },
                    "context_evidence": None,
                    "modality": "asserted",
                    "negated": False,
                    "confidence": 1.0,
                }],
                "unknown_relations": [],
            }),
            "model": "gpt-fixture",
            "complete": True,
        }


def test_gpt_matrix_parser_is_explicit_and_source_bound():
    provider = FixtureProvider()
    result = GPTMatrixEventParser(provider).parse(
        "The Contractor must pay the levy.", explicit_send=True,
    )
    assert result["candidate"]["events"][0]["target_evidence"] == {
        "start": 20, "end": 32, "quote": "pay the levy",
    }
    assert result["telemetry"]["matrix_values_from_provider"] is False
    prompt, response_format, explicit = provider.calls[0]
    assert explicit is True
    assert "Never invent the answer" in prompt
    assert response_format["name"] == "tom_assist_matrix_events_v1"


def test_gpt_matrix_parser_refuses_implicit_send():
    provider = FixtureProvider()
    with pytest.raises(GPTMatrixEventParserError, match="EXPLICIT_SEND_REQUIRED"):
        GPTMatrixEventParser(provider).parse("The Contractor must pay the levy.")
    assert provider.calls == []
