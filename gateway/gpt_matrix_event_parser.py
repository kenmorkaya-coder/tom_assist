"""Explicit-send GPT adapter for evidence-bound 32x32 matrix events."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from gateway.matrix_events import (
    MATRIX_EVENT_PARSER_VERSION,
    build_matrix_event_prompt,
    matrix_event_response_format,
    project_matrix_event_fields,
    validate_matrix_event_candidate,
)
from gateway.oauth_provider import OAuthProvider, ProviderFailure


class GPTMatrixEventParserError(RuntimeError):
    def __init__(self, message: str, *, provider_failure: bool = False) -> None:
        super().__init__(message)
        self.provider_failure = provider_failure


class GPTMatrixEventParser:
    """One provider call per source; credentials remain inside the broker."""

    def __init__(self, provider: OAuthProvider | None = None) -> None:
        self.provider = provider or OAuthProvider()

    def parse(self, source_text: str, *, explicit_send: bool = False) -> dict[str, Any]:
        if explicit_send is not True:
            raise GPTMatrixEventParserError("EXPLICIT_SEND_REQUIRED")
        try:
            prompt = build_matrix_event_prompt(source_text)
        except ValueError as error:
            raise GPTMatrixEventParserError(str(error)) from None
        try:
            response = self.provider.complete_structured(
                prompt, matrix_event_response_format(), explicit_send=True,
            )
        except ProviderFailure as error:
            raise GPTMatrixEventParserError(
                str(error), provider_failure=True,
            ) from None
        text = response["text"]
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            raise GPTMatrixEventParserError(
                "provider returned invalid structured JSON"
            ) from None
        try:
            projected = project_matrix_event_fields(payload)
            candidate = validate_matrix_event_candidate(projected, source_text)
        except ValueError as error:
            raise GPTMatrixEventParserError(
                f"candidate validation failed: {error}"
            ) from None
        return {
            "candidate": candidate,
            "parser_model": {
                "version": MATRIX_EVENT_PARSER_VERSION,
                "provider": "tom-assist/openai-oauth",
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
                "matrix_values_from_provider": False,
            },
        }
