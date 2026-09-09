"""Experimental registry-bound identity adapter for the unchanged typed compiler.

Registry CSV is supplied project-record evidence, not inferred from names.
This adapter neither creates identities nor resolves ambiguous labels by guessing.
The experiment uses synthetic authored registers, not a production registry.
"""
from __future__ import annotations

import csv
from copy import deepcopy
import hashlib
import io
import re

from gateway.typed_matrix_compiler import UnsupportedTypedEvent, prepare_candidate


VERSION = "tom-assist-project-identity-compiler/1-experimental"
HEADERS = ["project_id", "entity_id", "kind", "label"]


def read_registry(text, project_id):
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != HEADERS:
        raise UnsupportedTypedEvent("REGISTRY_SCHEMA_MISMATCH")
    rows = list(reader)
    if not rows or len(rows) > 4096:
        raise UnsupportedTypedEvent("REGISTRY_SIZE_INVALID")
    identities = {}
    selected = []
    for index, row in enumerate(rows, 2):
        if set(row) != set(HEADERS) or any(not isinstance(v, str) or not v or len(v) > 256 for v in row.values()):
            raise UnsupportedTypedEvent("REGISTRY_ROW_INVALID")
        key = (row["project_id"], row["entity_id"])
        previous = identities.setdefault(key, row["kind"])
        if previous != row["kind"]:
            raise UnsupportedTypedEvent("REGISTRY_IDENTITY_KIND_CONFLICT")
        if row["project_id"] == project_id:
            selected.append({**row, "record_ordinal": index - 2})
    if not selected:
        raise UnsupportedTypedEvent("PROJECT_ABSENT_FROM_REGISTRY")
    return selected


def prepare_identity_candidate(candidate, source_text, *, project_id=None, registry_csv=None):
    prepared = prepare_candidate(candidate, source_text)
    # Unannotated inputs are byte-for-byte the same prepared input as v1.
    if registry_csv is None:
        if project_id is not None:
            raise UnsupportedTypedEvent("PROJECT_IDENTITY_REGISTRY_REQUIRED")
        return prepared
    if not isinstance(project_id, str) or not project_id:
        raise UnsupportedTypedEvent("ACTIVE_PROJECT_REQUIRED")
    registry = read_registry(registry_csv, project_id)
    registry_digest = hashlib.sha256(registry_csv.encode()).hexdigest()
    result = deepcopy(prepared)
    evidence = []
    for event in result["events"]:
        for field_name in ("source", "target", "context"):
            field = event["fields"][field_name]
            hits = {}
            for record in registry:
                pattern = r"(?<!\w)" + re.escape(record["label"]) + r"(?!\w)"
                for match in re.finditer(pattern, field["text"]):
                    hits.setdefault(match.span(), []).append(record)
            accepted = []
            for span, records in sorted(hits.items(), key=lambda pair: (-(pair[0][1] - pair[0][0]), pair[0][0])):
                identities = {(r["project_id"], r["entity_id"], r["kind"]) for r in records}
                if len(identities) != 1:
                    raise UnsupportedTypedEvent("AMBIGUOUS_PROJECT_LABEL")
                if any(span[0] < other[1] and other[0] < span[1] for other, _ in accepted):
                    raise UnsupportedTypedEvent("OVERLAPPING_IDENTITY_LABELS")
                accepted.append((span, records[0]))
            for span, record in sorted(accepted, reverse=True):
                label = field["text"][span[0]:span[1]]
                if field["semantic_text"].count(label) != 1:
                    raise UnsupportedTypedEvent("IDENTITY_MASK_SCOPE_AMBIGUOUS")
                field["semantic_text"] = field["semantic_text"].replace(label, "registered " + record["kind"], 1)
                symbol = {"kind": "project_identity", "project_id": record["project_id"], "entity_id": record["entity_id"], "entity_kind": record["kind"]}
                field["symbols"].append(symbol)
                proof = {"event_id": event["event"]["id"], "field": field_name, "start": span[0], "end": span[1], "quote": label,
                         "registry_sha256": registry_digest, "registry_record_ordinal": record["record_ordinal"], "identity": symbol}
                evidence.append(proof)
                field["evidence"].append(proof)
    if not evidence:
        raise UnsupportedTypedEvent("NO_REGISTERED_IDENTITY_IN_EVENT")
    result["identity_compiler_version"] = VERSION
    result["identity_evidence"] = evidence
    return result
