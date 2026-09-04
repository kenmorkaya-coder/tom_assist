"""Candidate-only GPT structural parser using Tom Assist-owned OAuth.

The model supplies typed facts and exact source quotes.  This boundary never
accepts provider-supplied offsets or load numbers: Tom Assist binds the quotes
and compiles the existing deterministic 17-channel load downstream.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from gateway.oauth_provider import OAuthProvider, ProviderFailure
from gateway.structural_analysis import (
    GPT_PARSER_VERSION,
    bind_candidate_metadata,
    build_gpt_quote_prompt,
    canonicalize_candidate_ids,
    canonicalize_candidate_spans,
    project_candidate_fields,
    quote_candidate_response_format,
    validate_candidate,
)


class GPTStructureParserError(RuntimeError):
    def __init__(self, message: str, *, provider_failure: bool = False) -> None:
        super().__init__(message)
        self.provider_failure = provider_failure


class GPTStructureParser:
    """One-attempt parser; callers must explicitly authorize every send."""

    def __init__(self, provider: OAuthProvider | None = None) -> None:
        self.provider = provider or OAuthProvider()

    def parse(self, source_text: str, *, explicit_send: bool = False) -> dict[str, Any]:
        if explicit_send is not True:
            raise GPTStructureParserError("EXPLICIT_SEND_REQUIRED")
        if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
            raise GPTStructureParserError("source text must contain 1..48000 characters")
        prompt = build_gpt_quote_prompt(source_text)
        try:
            response = self.provider.complete_structured(
                prompt,
                quote_candidate_response_format(),
                explicit_send=True,
            )
        except ProviderFailure as error:
            raise GPTStructureParserError(
                str(error), provider_failure=True
            ) from None
        text = response["text"]
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise GPTStructureParserError("provider returned invalid structured JSON") from None
        try:
            projected = project_candidate_fields(payload)
            candidate = validate_candidate(
                canonicalize_candidate_spans(
                    canonicalize_candidate_ids(
                        bind_candidate_metadata(
                            projected, source_text
                        )
                    ),
                    source_text,
                ),
                source_text,
            )
        except ValueError as error:
            raise GPTStructureParserError(f"candidate validation failed: {error}") from None
        return {
            "candidate": candidate,
            "parser_model": {
                "version": GPT_PARSER_VERSION,
                "model": "tom-assist/openai-oauth-structured-parser",
                "revision": response["model"],
            },
            "telemetry": {
                "provider_calls": 1,
                "retry_count": 0,
                "response_bytes": len(text.encode("utf-8")),
                "response_sha256": "sha256:"
                + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "raw_response_retained": False,
                "schema_projection_applied": projected != payload,
                "offset_source": "tom-assist-exact-quote-binding",
                "load_source": "tom-assist-deterministic-compiler",
            },
        }
