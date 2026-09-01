#!/usr/bin/env python3
"""Persistent Gemma 4 native-tool worker for structural candidates only."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.structural_analysis import (  # noqa: E402
    build_gemma_prompt,
    candidate_tool_schema,
    validate_candidate,
)
from gateway.structure_provider import WORKER_PROTOCOL  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_absolute() or not args.model.is_dir():
        raise SystemExit("local Gemma checkpoint is missing")
    if any(os.environ.get(name) for name in ("OPENAI_API_KEY", "TOM_LLM_API_KEY", "TOM_AGENT_LLM_API_KEY")):
        raise SystemExit("Gemma structure worker refuses API-key environments")
    with contextlib.redirect_stdout(sys.stderr):
        import mlx.core as mx
        from mlx_lm import generate, load
        from mlx_lm.sample_utils import make_sampler
        model, tokenizer = load(str(args.model))
    mx.random.seed(7)
    random.seed(7)
    sampler = make_sampler(temp=0.0)
    tool = candidate_tool_schema()
    for raw in sys.stdin:
        request_id = "unknown"
        try:
            request = json.loads(raw)
            if set(request) != {"protocol", "request_id", "source_text"}:
                raise ValueError("Gemma request shape mismatch")
            if request["protocol"] != WORKER_PROTOCOL:
                raise ValueError("Gemma protocol mismatch")
            request_id = str(request["request_id"])
            source_text = request["source_text"]
            prompt = build_gemma_prompt(source_text)
            formatted = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tools=[tool],
                add_generation_prompt=True, tokenize=False, enable_thinking=False,
            )
            with contextlib.redirect_stdout(sys.stderr):
                generated = generate(
                    model, tokenizer, prompt=formatted, max_tokens=2048,
                    sampler=sampler, verbose=False,
                )
            call = tokenizer.tool_parser(generated)
            if isinstance(call, list):
                if len(call) != 1:
                    raise ValueError("Gemma must call the structure tool exactly once")
                call = call[0]
            if not isinstance(call, dict) or call.get("name") != "record_structural_candidate":
                raise ValueError("Gemma called the wrong structure tool")
            candidate = validate_candidate(call.get("arguments"), source_text)
            response = {
                "protocol": WORKER_PROTOCOL, "request_id": request_id,
                "candidate": candidate,
            }
        except Exception as error:
            response = {
                "protocol": WORKER_PROTOCOL, "request_id": request_id,
                "error": f"{type(error).__name__}: {str(error)[:400]}",
            }
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
