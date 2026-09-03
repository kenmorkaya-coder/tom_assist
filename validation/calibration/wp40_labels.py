#!/usr/bin/env python3
"""Validate owner-authored structural labels without invoking any model."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping

from gateway.structural_analysis import text_digest, validate_candidate


LABEL_SCHEMA_VERSION = "tom-assist-parser-labels/1.0"
OWNER_LABEL = "OWNER-AUTHORED-PENDING-FREEZE"
SYNTHETIC_LABEL = "PLUMBING-ONLY-SYNTHETIC-NOT-EVIDENCE"
TEMPLATE_LABEL = "TEMPLATE-NO-LABELS"
MAX_LABELLER_NOTE_CHARACTERS = 2_000


def validate_label_file(value: Any, *, allow_template: bool = False) -> dict[str, Any]:
    fields = {"schema_version", "label", "corpus_id", "provenance", "passages"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError("label file fields mismatch")
    if value["schema_version"] != LABEL_SCHEMA_VERSION:
        raise ValueError("label schema version is unsupported")
    label = value["label"]
    if label not in {OWNER_LABEL, SYNTHETIC_LABEL, TEMPLATE_LABEL}:
        raise ValueError("label authority marker is unsupported")
    passages = value["passages"]
    if not isinstance(passages, list):
        raise ValueError("label passages must be an array")
    if label == TEMPLATE_LABEL:
        if not allow_template or passages:
            raise ValueError("the empty label template is not evaluation evidence")
        return dict(value)
    corpus_id = value["corpus_id"]
    provenance = value["provenance"]
    if not isinstance(corpus_id, str) or not corpus_id.strip():
        raise ValueError("label corpus_id is required")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("label provenance is required")
    if not passages:
        raise ValueError("at least one labelled passage is required")

    normalized = []
    passage_ids: set[str] = set()
    for index, item in enumerate(passages):
        expected_fields = {
            "passage_id", "source_text", "source_sha256",
            "expected_candidate", "labeller_note",
        }
        if not isinstance(item, Mapping) or set(item) != expected_fields:
            raise ValueError(f"label passage {index} fields mismatch")
        passage_id = item["passage_id"]
        if not isinstance(passage_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", passage_id,
        ):
            raise ValueError(f"label passage {index} ID is invalid")
        if passage_id in passage_ids:
            raise ValueError(f"duplicate label passage ID: {passage_id}")
        passage_ids.add(passage_id)
        source_text = item["source_text"]
        if not isinstance(source_text, str) or not source_text.strip():
            raise ValueError(f"label passage {passage_id} source is required")
        if item["source_sha256"] != text_digest(source_text):
            raise ValueError(f"label passage {passage_id} source digest mismatch")
        note = item["labeller_note"]
        if not isinstance(note, str) or len(note) > MAX_LABELLER_NOTE_CHARACTERS:
            raise ValueError(f"label passage {passage_id} note is invalid")
        candidate = validate_candidate(item["expected_candidate"], source_text)
        normalized.append({
            "passage_id": passage_id,
            "source_text": source_text,
            "source_sha256": text_digest(source_text),
            "expected_candidate": candidate,
            "labeller_note": note,
        })
    return {
        "schema_version": LABEL_SCHEMA_VERSION,
        "label": label,
        "corpus_id": corpus_id.strip(),
        "provenance": provenance.strip(),
        "passages": normalized,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--allow-empty-template", action="store_true")
    args = parser.parse_args()
    value = json.loads(args.labels.read_text(encoding="utf-8"))
    result = validate_label_file(value, allow_template=args.allow_empty_template)
    print(json.dumps({
        "schema_version": result["schema_version"],
        "label": result["label"],
        "passage_count": len(result["passages"]),
        "model_generations": 0,
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
