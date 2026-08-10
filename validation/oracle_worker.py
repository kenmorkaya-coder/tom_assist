#!/usr/bin/env python3
"""Deterministic one-request stdin/stdout oracle process.

This deliberately mirrors the isolated verifier process pattern: input and output
are JSON, the worker has no network/model access, and scoring is reproducible.
"""
from __future__ import annotations

import json
import sys


def score(request: dict) -> dict:
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
