#!/usr/bin/env python3
"""Persistent local MiniLM embedding worker for document inventory only."""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.document_ingestion import (  # noqa: E402
    DOCUMENT_WORKER_PROTOCOL,
    MAX_DOCUMENT_CHUNKS,
    MAX_DOCUMENT_SOURCE_CHARS,
)
from gateway.semantic_chunks import (  # noqa: E402
    EMBEDDING_DIMENSION,
    MAX_CHUNK_TOKENS,
    build_token_chunks,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    if not args.model.is_absolute() or not args.model.exists():
        raise SystemExit("local MiniLM model path is missing")
    if any(os.environ.get(name) for name in (
        "OPENAI_API_KEY", "TOM_LLM_API_KEY", "TOM_AGENT_LLM_API_KEY",
    )):
        raise SystemExit("document worker refuses API-key environments")
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from transformers import AutoModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(args.model), local_files_only=True)
        model = AutoModel.from_pretrained(str(args.model), local_files_only=True)
        model.eval()
    revision = args.model.resolve().name
    for raw in sys.stdin:
        request_id = "unknown"
        try:
            request = json.loads(raw)
            if set(request) != {"protocol", "request_id", "source_text"}:
                raise ValueError("document worker request shape mismatch")
            if request["protocol"] != DOCUMENT_WORKER_PROTOCOL:
                raise ValueError("document worker protocol mismatch")
            request_id = str(request["request_id"])
            source_text = request["source_text"]
            if not isinstance(source_text, str) or not source_text.strip():
                raise ValueError("document source text is required")
            offsets = tokenizer(
                source_text, add_special_tokens=False, return_offsets_mapping=True,
            )["offset_mapping"]
            plan = build_token_chunks(
                source_text,
                offsets,
                max_source_chars=MAX_DOCUMENT_SOURCE_CHARS,
                max_chunks=MAX_DOCUMENT_CHUNKS,
            )
            texts = [source_text[row["start"]:row["end"]] for row in plan]
            vectors = []
            for start in range(0, len(texts), 16):
                batch = tokenizer(
                    texts[start:start + 16], padding=True, truncation=False,
                    return_tensors="pt",
                )
                if any(int(length) > MAX_CHUNK_TOKENS + 2 for length in batch["attention_mask"].sum(dim=1).tolist()):
                    raise ValueError("a document chunk exceeds the MiniLM token window")
                with torch.no_grad():
                    hidden = model(**batch).last_hidden_state
                mask = batch["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                vectors.extend([float(value) for value in vector.tolist()] for vector in pooled)
            if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
                raise ValueError("document embedding dimension mismatch")
            response = {
                "protocol": DOCUMENT_WORKER_PROTOCOL,
                "request_id": request_id,
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "revision": revision,
                "chunks": [
                    {
                        "index": index,
                        "start": row["start"],
                        "end": row["end"],
                        "values": vector,
                    }
                    for index, (row, vector) in enumerate(zip(plan, vectors))
                ],
            }
        except Exception as error:
            response = {
                "protocol": DOCUMENT_WORKER_PROTOCOL,
                "request_id": request_id,
                "error": f"{type(error).__name__}: {str(error)[:400]}",
            }
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
