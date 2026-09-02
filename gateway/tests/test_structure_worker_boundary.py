from __future__ import annotations

import json

import pytest

from gateway.gemma_structure_worker import parse_generated_tool_call
from gateway.structure_provider import StructureProviderError, WORKER_PROTOCOL


def _native_failure(_: str):
    raise json.JSONDecodeError("fixture native failure", "{bad}", 1)


def test_gemma4_syntax_fallback_repairs_only_container_syntax():
    generated = """prefix call:record_structural_candidate{
      entities:[{id:<|"|>Alpha<|"|>, label:<|"|>Alpha<|"|>, active:True,}],
      unknown_fields:[], confidence:1.0,
    } suffix"""
    call, mode = parse_generated_tool_call(generated, _native_failure)
    assert mode == "deterministic_gemma4_reparse"
    assert call == {
        "name": "record_structural_candidate",
        "arguments": {
            "entities": [{"id": "Alpha", "label": "Alpha", "active": True}],
            "unknown_fields": [],
            "confidence": 1.0,
        },
    }


def test_native_tool_parser_is_preferred_and_multiple_fallback_calls_fail():
    expected = {"name": "record_structural_candidate", "arguments": {}}
    assert parse_generated_tool_call("ignored", lambda _: expected) == (expected, "native")
    with pytest.raises(ValueError, match="exactly one"):
        parse_generated_tool_call(
            "call:first{} call:second{}",
            _native_failure,
        )


def test_worker_protocol_and_errors_carry_exact_attempt_telemetry():
    assert WORKER_PROTOCOL == "tom-assist-structure-worker/1.1"
    telemetry = {
        "planned_chunks": 3,
        "attempted_chunks": 2,
        "successful_chunks": 1,
        "failed_chunk_index": 1,
        "chunks": [{"chunk_index": 0, "tool_parse_mode": "native"}],
    }
    error = StructureProviderError("failed", telemetry=telemetry)
    assert error.telemetry == telemetry
