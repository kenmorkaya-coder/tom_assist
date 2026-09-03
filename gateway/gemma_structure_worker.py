#!/usr/bin/env python3
"""Persistent Gemma 4 native-tool worker for structural candidates only."""
from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.structural_analysis import (  # noqa: E402
    bind_candidate_metadata,
    build_gemma_prompt,
    canonicalize_candidate_ids,
    canonicalize_candidate_spans,
    candidate_tool_schema,
    project_candidate_fields,
    validate_candidate,
)
from gateway.project_glossary import validate_glossary  # noqa: E402
from gateway.structure_provider import WORKER_PROTOCOL  # noqa: E402


_CALL_START = re.compile(r"call:([A-Za-z_][A-Za-z0-9_]*)\s*\{")


def _balanced_call_object(text: str, opening: int) -> str:
    stack: list[str] = []
    index = opening
    standard_string = False
    gemma_string = False
    escaped = False
    while index < len(text):
        if text.startswith('<|"|>', index):
            gemma_string = not gemma_string
            index += 5
            continue
        character = text[index]
        if gemma_string:
            index += 1
            continue
        if standard_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                standard_string = False
            index += 1
            continue
        if character == '"':
            standard_string = True
        elif character in "{[":
            stack.append(character)
        elif character in "}]":
            expected = "{" if character == "}" else "["
            if not stack or stack[-1] != expected:
                raise ValueError("Gemma tool call has mismatched containers")
            stack.pop()
            if not stack:
                return text[opening:index + 1]
        index += 1
    if standard_string or gemma_string:
        raise ValueError("Gemma tool call has an unterminated string")
    if not stack:
        raise ValueError("Gemma tool call has no complete object")
    # Closing only open syntax cannot invent a semantic field or value. The
    # strict candidate validator still checks that the complete shape exists.
    closers = "".join("}" if value == "{" else "]" for value in reversed(stack))
    return text[opening:] + closers


def _gemma4_arguments(value: str) -> dict:
    strings: list[str] = []

    def capture(match: re.Match[str]) -> str:
        strings.append(match.group(1))
        return f'"__TOM_STRING_{len(strings) - 1}__"'

    converted = re.sub(r'<\|"\|>(.*?)<\|"\|>', capture, value, flags=re.DOTALL)
    converted = re.sub(
        r"(?<=[{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:",
        lambda match: f'"{match.group(1)}":',
        converted,
    )
    converted = re.sub(r",\s*([}\]])", r"\1", converted)
    converted = re.sub(r"\bTrue\b", "true", converted)
    converted = re.sub(r"\bFalse\b", "false", converted)
    converted = re.sub(r"\bNone\b", "null", converted)
    converted = re.sub(
        r"(:\s*)([A-Za-z_][A-Za-z0-9_-]*)(?=\s*[,}\]])",
        lambda match: match.group(1) + (
            match.group(2)
            if match.group(2) in {"true", "false", "null"}
            else json.dumps(match.group(2))
        ),
        converted,
    )
    try:
        parsed = json.loads(converted)
    except json.JSONDecodeError:
        python_literal = re.sub(r"\btrue\b", "True", converted)
        python_literal = re.sub(r"\bfalse\b", "False", python_literal)
        python_literal = re.sub(r"\bnull\b", "None", python_literal)
        try:
            parsed = ast.literal_eval(python_literal)
        except (SyntaxError, ValueError):
            raise ValueError("Gemma fallback contains an invalid structured value") from None
    if not isinstance(parsed, dict):
        raise ValueError("Gemma tool arguments must be an object")

    def restore(item):
        if isinstance(item, str):
            match = re.fullmatch(r"__TOM_STRING_(\d+)__", item)
            return strings[int(match.group(1))] if match else item
        if isinstance(item, list):
            return [restore(child) for child in item]
        if isinstance(item, dict):
            return {key: restore(child) for key, child in item.items()}
        return item

    return restore(parsed)


def parse_generated_tool_call(generated: str, native_parser) -> tuple[dict, str]:
    """Use the native parser first, then a deterministic syntax-only fallback."""
    try:
        call = native_parser(generated)
        return call, "native"
    except (json.JSONDecodeError, ValueError):
        starts = list(_CALL_START.finditer(generated))
        if len(starts) != 1:
            raise ValueError("Gemma must emit exactly one recognizable tool call") from None
        match = starts[0]
        opening = generated.find("{", match.start())
        return {
            "name": match.group(1),
            "arguments": _gemma4_arguments(_balanced_call_object(generated, opening)),
        }, "deterministic_gemma4_reparse"


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
            if set(request) not in (
                {"protocol", "request_id", "source_text"},
                {"protocol", "request_id", "source_text", "glossary"},
            ):
                raise ValueError("Gemma request shape mismatch")
            if request["protocol"] != WORKER_PROTOCOL:
                raise ValueError("Gemma protocol mismatch")
            request_id = str(request["request_id"])
            source_text = request["source_text"]
            glossary = (
                validate_glossary(request["glossary"])
                if "glossary" in request else None
            )
            prompt = build_gemma_prompt(source_text, glossary)
            formatted = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tools=[tool],
                add_generation_prompt=True, tokenize=False, enable_thinking=False,
            )
            with contextlib.redirect_stdout(sys.stderr):
                generated = generate(
                    model, tokenizer, prompt=formatted, max_tokens=3072,
                    sampler=sampler, verbose=False,
                )
            call, parse_mode = parse_generated_tool_call(generated, tokenizer.tool_parser)
            if isinstance(call, list):
                if len(call) != 1:
                    raise ValueError("Gemma must call the structure tool exactly once")
                call = call[0]
            if not isinstance(call, dict) or call.get("name") != "record_structural_candidate":
                raise ValueError("Gemma called the wrong structure tool")
            arguments = call.get("arguments")
            projected = project_candidate_fields(arguments)
            candidate = validate_candidate(
                canonicalize_candidate_spans(
                    canonicalize_candidate_ids(
                        bind_candidate_metadata(projected, source_text)
                    ),
                    source_text,
                ),
                source_text,
            )
            response = {
                "protocol": WORKER_PROTOCOL, "request_id": request_id,
                "candidate": candidate,
                "boundary_telemetry": {
                    "tool_parse_mode": parse_mode,
                    "schema_projection_applied": projected != arguments,
                },
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
