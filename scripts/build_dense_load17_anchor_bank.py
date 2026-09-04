#!/usr/bin/env python3
"""Build the compact, pinned WP-36b semantic anchor vector bank."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "validation" / "calibration" / "wp36b_anchor_source.json"
DEFAULT_OUTPUT = ROOT / "gateway" / "data" / "dense_load17_anchor_bank_v1.json"
CHANNELS = (
    "S_entity", "S_dependency", "S_topology", "L_rule", "L_contradiction",
    "L_inference", "T_sequence", "T_memory", "T_future", "threat_amplitude",
    "frequency", "persistence", "burstiness", "volatility", "novelty",
    "recurrence", "decay",
)
DRIVERS = ("threat_load", "sustenance_potential", "procreation_potential")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    source_bytes = args.source.read_bytes()
    source = json.loads(source_bytes)
    if tuple(source.get("channels", {})) != CHANNELS:
        raise SystemExit("anchor source channel order does not match canonical q17")
    if tuple(source.get("drivers", {})) != DRIVERS:
        raise SystemExit("anchor source driver order does not match T/S/P")
    if args.model.resolve().name != source["embedding_revision"]:
        raise SystemExit("embedding model revision does not match anchor source")

    anchors: list[tuple[str, str, str, int]] = []
    for family in ("channels", "drivers"):
        for name, texts in source[family].items():
            if not isinstance(texts, list) or len(texts) < 2:
                raise SystemExit(f"{family}.{name} requires at least two prototypes")
            for index, text in enumerate(texts):
                if not isinstance(text, str) or not text.strip():
                    raise SystemExit(f"{family}.{name}[{index}] must be nonempty")
                anchors.append((family, name, text, index))

    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(args.model), local_files_only=True)
    model = AutoModel.from_pretrained(str(args.model), local_files_only=True)
    model.eval()
    encoded = tokenizer(
        [row[2] for row in anchors], padding=True, truncation=True,
        return_tensors="pt",
    )
    with torch.no_grad():
        hidden = model(**encoded).last_hidden_state
    mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
    pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)

    groups = {"channels": {name: [] for name in CHANNELS},
              "drivers": {name: [] for name in DRIVERS}}
    for (family, name, text, index), vector in zip(anchors, pooled):
        values = [float(value) for value in vector.tolist()]
        if len(values) != 384:
            raise SystemExit(f"unexpected embedding dimension: {len(values)}")
        packed = struct.pack("<384f", *values)
        groups[family][name].append({
            "anchor_id": f"{name}:{index}",
            "text": text,
            "text_sha256": "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "vector_f32_le_base64": base64.b64encode(packed).decode("ascii"),
        })

    output = {
        "schema_version": "tom-assist-dense-load17-anchor-bank/1.0",
        "source_sha256": "sha256:" + hashlib.sha256(_canonical_json(source)).hexdigest(),
        "embedding_model": source["embedding_model"],
        "embedding_revision": source["embedding_revision"],
        "dimension": 384,
        "formula": source["formula"],
        **groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
