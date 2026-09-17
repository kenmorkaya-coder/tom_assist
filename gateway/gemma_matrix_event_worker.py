#!/usr/bin/env python3
"""Persistent local Gemma worker for evidence-bound matrix events."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.gemma_structure_worker import parse_generated_tool_call  # noqa: E402
from gateway.matrix_event_provider import MATRIX_EVENT_WORKER_PROTOCOL  # noqa: E402
from gateway.matrix_events import (  # noqa: E402
    MATRIX_EVENT_PARSER_VERSION,
    build_matrix_event_prompt,
    matrix_event_tool_schema,
    project_matrix_event_fields,
    validate_matrix_event_candidate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_absolute() or not args.model.is_dir():
        raise SystemExit("local Gemma checkpoint is missing")
    if any(os.environ.get(name) for name in (
        "OPENAI_API_KEY", "TOM_LLM_API_KEY", "TOM_AGENT_LLM_API_KEY",
    )):
        raise SystemExit("Gemma matrix event worker refuses API-key environments")
    with contextlib.redirect_stdout(sys.stderr):
        import mlx.core as mx
        from mlx_lm import generate, load
        from mlx_lm.sample_utils import make_sampler
        model, tokenizer = load(str(args.model))
    mx.random.seed(7)
    random.seed(7)
    sampler = make_sampler(temp=0.0)
    tool = matrix_event_tool_schema()
    for raw in sys.stdin:
        request_id = "unknown"
        stage = "request"
        try:
            request = json.loads(raw)
            if not isinstance(request, dict) or set(request) != {
                "protocol", "request_id", "source_text",
            }:
                raise ValueError("matrix event request shape mismatch")
            if request["protocol"] != MATRIX_EVENT_WORKER_PROTOCOL:
                raise ValueError("matrix event worker protocol mismatch")
            request_id = str(request["request_id"])
            source_text = request["source_text"]
            stage = "model_invocation"
            prompt = build_matrix_event_prompt(source_text)
            formatted = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tools=[tool], add_generation_prompt=True, tokenize=False,
                enable_thinking=False,
            )
            with contextlib.redirect_stdout(sys.stderr):
                generated = generate(
                    model, tokenizer, prompt=formatted, max_tokens=4096,
                    sampler=sampler, verbose=False,
                )
            stage = "tool_parse"
            call, parse_mode = parse_generated_tool_call(
                generated, tokenizer.tool_parser,
            )
            if isinstance(call, list):
                if len(call) != 1:
                    raise ValueError("Gemma must call the matrix event tool once")
                call = call[0]
            if not isinstance(call, dict) or call.get("name") != "record_matrix_events":
                raise ValueError("Gemma called the wrong matrix event tool")
            arguments = call.get("arguments")
            if not isinstance(arguments, dict):
                raise ValueError("Gemma matrix event arguments must be an object")
            stage = "candidate_validation"
            projected = project_matrix_event_fields(arguments)
            candidate = validate_matrix_event_candidate(projected, source_text)
            response = {
                "protocol": MATRIX_EVENT_WORKER_PROTOCOL,
                "request_id": request_id,
                "candidate": candidate,
                "parser_model": {
                    "version": MATRIX_EVENT_PARSER_VERSION,
                    "provider": "local-gemma-native-tool",
                    "revision": args.model.name,
                },
                "telemetry": {
                    "provider_calls": 0,
                    "local_generations": 1,
                    "retry_count": 0,
                    "tool_parse_mode": parse_mode,
                    "schema_projection_applied": projected != arguments,
                    "matrix_values_from_provider": False,
                },
            }
        except Exception as error:
            response = {
                "protocol": MATRIX_EVENT_WORKER_PROTOCOL,
                "request_id": request_id,
                "error": f"{type(error).__name__}: {error}"[:512],
                "stage": stage,
            }
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
