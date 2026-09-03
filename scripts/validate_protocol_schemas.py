#!/usr/bin/env python3
"""Validate shared fixtures against the draft-2020-12 source schemas."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "crates" / "protocol" / "schemas"
FIXTURE = ROOT / "tests" / "fixtures" / "protocol" / "examples.json"

MAPPING = {
    "envelope": "envelope.schema.json",
    "provider_capabilities": "provider-capabilities.schema.json",
    "tom_capabilities": "tom-capabilities.schema.json",
    "state_object": "state-object.schema.json",
    "state_edge": "state-edge.schema.json",
    "continuity_packet": "continuity-packet.schema.json",
    "state_mutation_candidate": "state-mutation-candidate.schema.json",
    "structural_candidate": "structural-candidate.schema.json",
    "document": "document.schema.json",
    "intervention": "intervention.schema.json",
    "error": "error.schema.json",
}

SOURCE_ID_VERSION = "source-id.v1.1.schema.json"
VALID_SOURCE_IDS = (
    "60000000-0000-4000-8000-000000000001",
    "60000000-0000-4000-8000-000000000001:user",
    "60000000-0000-4000-8000-000000000001:assistant",
)
INVALID_SOURCE_IDS = (
    "conversation-turn-1",
    "60000000-0000-4000-8000-000000000001:",
    "60000000-0000-4000-8000-000000000001:system",
    "60000000-0000-4000-8000-000000000001:assistant:extra",
    "not-a-uuid:assistant",
)


def main() -> None:
    schemas = {path.name: json.loads(path.read_text()) for path in SCHEMA_DIR.glob("*.json")}
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema))
        for schema in schemas.values()
        if "$id" in schema
    )
    examples = json.loads(FIXTURE.read_text())
    for fixture_name, schema_name in MAPPING.items():
        schema = schemas[schema_name]
        validator = Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        validator.validate(examples[fixture_name])

    source_id_validator = Draft202012Validator(
        schemas[SOURCE_ID_VERSION],
        registry=registry,
        format_checker=FormatChecker(),
    )
    for source_id in VALID_SOURCE_IDS:
        source_id_validator.validate(source_id)
    for source_id in INVALID_SOURCE_IDS:
        if source_id_validator.is_valid(source_id):
            raise AssertionError(f"invalid source ID accepted: {source_id}")

    methods = schemas["core-methods.schema.json"]["enum"]
    if len(methods) != 47 or len(methods) != len(set(methods)):
        raise AssertionError(f"expected 47 unique core methods, got {len(methods)}")
    print(
        f"validated {len(MAPPING)} fixtures, {len(methods)} core methods, "
        f"and source-id/1.1 ({len(VALID_SOURCE_IDS)} valid, "
        f"{len(INVALID_SOURCE_IDS)} invalid cases)"
    )


if __name__ == "__main__":
    main()
