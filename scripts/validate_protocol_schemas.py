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
    "intervention": "intervention.schema.json",
    "error": "error.schema.json",
}


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

    methods = schemas["core-methods.schema.json"]["enum"]
    if len(methods) != 43 or len(methods) != len(set(methods)):
        raise AssertionError(f"expected 43 unique core methods, got {len(methods)}")
    print(f"validated {len(MAPPING)} fixtures and {len(methods)} core methods")


if __name__ == "__main__":
    main()
