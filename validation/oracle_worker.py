#!/usr/bin/env python3
"""Deterministic one-request stdin/stdout oracle process.

This deliberately mirrors the isolated verifier process pattern: input and output
are JSON, the worker has no network/model access, and scoring is reproducible.
"""
from __future__ import annotations

import json
import sys


def score(request: dict) -> dict:
    if request.get("oracle_version") == "typed-action-oracle/1":
        return score_action(request)
    haystack = f"{request['context']}\n{request['probe']}".casefold()
    required = [str(item).casefold() for item in request.get("required_terms", [])]
    forbidden = [str(item).casefold() for item in request.get("forbidden_terms", [])]
    present = [item for item in required if item in haystack]
    revived = [item for item in forbidden if item in haystack]
    return {
        "oracle_version": "deterministic-term-oracle/1.0",
        "required_total": len(required),
        "required_present": len(present),
        "forbidden_present": len(revived),
        "observed_match": len(present) == len(required) and not revived,
        "present_terms": present,
        "revived_terms": revived,
    }


def score_action(request: dict) -> dict:
    """Frozen exact recorded-answer checks, not context search.

    Context/probe are deliberately ignored. This module never chooses an answer.
    Dict key order is immaterial; pre-registered list order and all values exact.
    """
    keys = {"action_id", "rejected_action_ids", "cited_state_ids", "historical_state_ids", "relationships", "proposed_mutations", "authority"}
    expected = request["expected_answer"]
    if not isinstance(expected, dict) or set(expected) != keys:
        raise ValueError("invalid pre-registered answer contract")
    answer = request.get("answer")
    if isinstance(answer, str):
        try: answer = json.loads(answer)
        except (json.JSONDecodeError, TypeError): answer = None
    shape = isinstance(answer, dict) and set(answer) == keys
    fields = {key: bool(shape and answer[key] == expected[key]) for key in sorted(keys)}
    action_consistent = shape and all(fields.values())
    mismatch = request.get("acceptable_mismatch_answer")
    explicit_mismatch = bool(shape and request.get("arm") == "SUB-E" and mismatch is not None and answer == mismatch)
    packet_policy = None
    if isinstance(request.get("expected_packet_injected"), bool) and isinstance(request.get("packet_injected"), bool):
        packet_policy = request["packet_injected"] == request["expected_packet_injected"]
    return {"oracle_version":"typed-action-oracle/1", "label":"FROZEN-WP25-V1",
            "answer_shape_valid":shape, "field_matches":fields,
            "action_consistent":action_consistent, "explicit_mismatch":explicit_mismatch,
            "packet_policy_match":packet_policy,
            "observed_match":bool(action_consistent or explicit_mismatch),
            "outcome":"action_consistent" if action_consistent else "explicit_mismatch" if explicit_mismatch else "answer_mismatch",
            "gate_verdict":None}


def main() -> int:
    try:
        request = json.load(sys.stdin)
        json.dump({"ok": True, "result": score(request)}, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 0
    except Exception as error:  # protocol failures are data, not tracebacks on stdout
        json.dump({"ok": False, "error": str(error)}, sys.stdout, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
