#!/usr/bin/env python3
"""Persistent local MiniLM encoder coordinating an isolated Gemma child."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.structural_analysis import (  # noqa: E402
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
    PARSER_VERSION,
    validate_candidate,
    validate_semantic_vector,
)
from gateway.structure_provider import WORKER_PROTOCOL  # noqa: E402


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--gemma-python", type=Path, required=True)
    parser.add_argument("--gemma-model", type=Path, required=True)
    return parser.parse_args()


def _safe_models(args: argparse.Namespace) -> None:
    for path in (args.embedding_model, args.gemma_python, args.gemma_model):
        if not path.is_absolute() or not path.exists():
            raise SystemExit(f"local model dependency is missing: {path}")
    if any(os.environ.get(name) for name in ("OPENAI_API_KEY", "TOM_LLM_API_KEY", "TOM_AGENT_LLM_API_KEY")):
        raise SystemExit("local structure worker refuses API-key environments")


class GemmaChild:
    def __init__(self, python: Path, model: Path) -> None:
        script = Path(__file__).with_name("gemma_structure_worker.py").resolve()
        self.process = subprocess.Popen(
            [str(python), str(script), "--model", str(model)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
            text=True, encoding="utf-8", bufsize=1,
            env={key: value for key, value in os.environ.items()
                 if key not in {"OPENAI_API_KEY", "TOM_LLM_API_KEY", "TOM_AGENT_LLM_API_KEY"}},
        )

    def analyze(self, request_id: str, source_text: str) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("Gemma child has no pipes")
        self.process.stdin.write(json.dumps({
            "protocol": WORKER_PROTOCOL, "request_id": request_id, "source_text": source_text,
        }, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"Gemma child ended unexpectedly ({self.process.poll()})")
        result = json.loads(line)
        if result.get("protocol") != WORKER_PROTOCOL or result.get("request_id") != request_id:
            raise RuntimeError("Gemma child protocol mismatch")
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        return result["candidate"]

    def close(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def main() -> int:
    args = _arguments()
    _safe_models(args)
    # Imports are intentionally confined to this subprocess.
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from transformers import AutoModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(args.embedding_model), local_files_only=True)
        model = AutoModel.from_pretrained(str(args.embedding_model), local_files_only=True)
        model.eval()
    revision = args.embedding_model.resolve().name
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    gemma = GemmaChild(args.gemma_python, args.gemma_model)
    try:
        for raw in sys.stdin:
            request_id = "unknown"
            try:
                request = json.loads(raw)
                if set(request) != {"protocol", "request_id", "source_text"}:
                    raise ValueError("worker request shape mismatch")
                if request["protocol"] != WORKER_PROTOCOL:
                    raise ValueError("worker protocol mismatch")
                request_id = str(request["request_id"])
                source_text = request["source_text"]
                if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
                    raise ValueError("source text must contain 1..48000 characters")
                encoded = tokenizer(
                    [source_text], padding=True, truncation=True, max_length=256,
                    return_tensors="pt",
                )
                with torch.no_grad():
                    hidden = model(**encoded).last_hidden_state
                mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                vector = ((hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9))[0]
                vector = torch.nn.functional.normalize(vector, p=2, dim=0)
                values = [float(value) for value in vector.tolist()]
                if len(values) != EMBEDDING_DIMENSION:
                    raise ValueError(f"embedding model returned {len(values)} dimensions")
                semantic_vector = validate_semantic_vector({
                    "version": EMBEDDING_VERSION, "model": model_name, "revision": revision,
                    "dimension": EMBEDDING_DIMENSION, "values": values,
                })
                candidate = validate_candidate(gemma.analyze(request_id, source_text), source_text)
                response = {
                    "protocol": WORKER_PROTOCOL, "request_id": request_id,
                    "candidate": candidate, "semantic_vector": semantic_vector,
                    "parser_model": {
                        "version": PARSER_VERSION,
                        "model": "local/gemma-instruct-tool-parser",
                        "revision": args.gemma_model.resolve().name,
                    },
                }
            except Exception as error:
                response = {
                    "protocol": WORKER_PROTOCOL, "request_id": request_id,
                    "error": f"{type(error).__name__}: {str(error)[:400]}",
                }
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        gemma.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
