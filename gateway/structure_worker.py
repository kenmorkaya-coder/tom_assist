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

from gateway.semantic_chunks import (  # noqa: E402
    EMBEDDING_DIMENSION,
    MAX_CHUNK_TOKENS,
    build_semantic_profile,
    build_token_chunks,
)
from gateway.structural_analysis import (  # noqa: E402
    GLOSSARY_PARSER_VERSION,
    PARSER_VERSION,
    validate_candidate,
)
from gateway.project_glossary import validate_glossary  # noqa: E402
from gateway.structure_failures import (  # noqa: E402
    ClassifiedStructureError,
    classify_failure,
    record_for_code,
    taxonomy_summary,
    validate_failure_record,
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

    def analyze(
        self, request_id: str, source_text: str,
        glossary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("Gemma child has no pipes")
        request = {
            "protocol": WORKER_PROTOCOL, "request_id": request_id, "source_text": source_text,
        }
        if glossary is not None:
            request["glossary"] = glossary
        self.process.stdin.write(json.dumps(
            request, ensure_ascii=False, separators=(",", ":")
        ) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"Gemma child ended unexpectedly ({self.process.poll()})")
        try:
            result = json.loads(line)
        except json.JSONDecodeError:
            raise ClassifiedStructureError(record_for_code(
                "gemma.response_json", "Gemma child returned invalid JSON",
            )) from None
        if not isinstance(result, dict):
            raise RuntimeError("Gemma child response shape mismatch")
        if result.get("protocol") != WORKER_PROTOCOL or result.get("request_id") != request_id:
            raise RuntimeError("Gemma child protocol mismatch")
        if "failure" in result:
            if set(result) != {"protocol", "request_id", "failure"}:
                raise RuntimeError("Gemma child failure shape mismatch")
            try:
                failure = validate_failure_record(result["failure"])
            except ValueError:
                raise RuntimeError("Gemma child failure shape mismatch") from None
            raise ClassifiedStructureError(failure)
        if set(result) != {"protocol", "request_id", "candidate", "boundary_telemetry"}:
            raise RuntimeError("Gemma child response shape mismatch")
        if not isinstance(result["boundary_telemetry"], dict):
            raise RuntimeError("Gemma child response shape mismatch")
        return {
            "candidate": result["candidate"],
            "boundary_telemetry": result.get("boundary_telemetry", {}),
        }

    def close(self) -> None:
        if self.process.stdin is not None:
            self.process.stdin.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


def attempt_all_chunks(
    gemma: Any,
    request_id: str,
    chunk_texts: list[str],
    glossary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Observe every planned chunk exactly once; any failure fails the passage."""
    chunk_candidates = []
    chunks = []
    attempts = []
    failures = []
    for chunk_index, chunk_text in enumerate(chunk_texts):
        attempt_ordinal = chunk_index + 1
        try:
            try:
                gemma_result = gemma.analyze(
                    f"{request_id}:{chunk_index}", chunk_text, glossary,
                )
            except Exception as error:
                raise ClassifiedStructureError(classify_failure(
                    error,
                    stage="gemma_transport",
                    chunk_index=chunk_index,
                    attempt_ordinal=attempt_ordinal,
                )) from None
            try:
                candidate = validate_candidate(
                    gemma_result["candidate"],
                    chunk_text,
                )
            except Exception as error:
                raise ClassifiedStructureError(classify_failure(
                    error,
                    stage="candidate_validation",
                    chunk_index=chunk_index,
                    attempt_ordinal=attempt_ordinal,
                )) from None
        except Exception as error:
            failure = classify_failure(
                error,
                stage="candidate_validation",
                chunk_index=chunk_index,
                attempt_ordinal=attempt_ordinal,
            )
            failures.append(failure)
            attempts.append({
                "chunk_index": chunk_index,
                "attempt_ordinal": attempt_ordinal,
                "outcome": "failed",
                "failure": failure,
            })
            continue
        chunk_detail = {
            "chunk_index": chunk_index,
            **gemma_result["boundary_telemetry"],
        }
        chunks.append(chunk_detail)
        attempts.append({
            "chunk_index": chunk_index,
            "attempt_ordinal": attempt_ordinal,
            "outcome": "succeeded",
            "failure": None,
        })
        chunk_candidates.append({
            "chunk_index": chunk_index,
            "candidate": candidate,
        })
    return {
        "attempted_chunks": len(attempts),
        "successful_chunks": len(chunk_candidates),
        "failed_chunk_index": failures[0]["chunk_index"] if failures else None,
        "passage_failed": bool(failures),
        "chunks": chunks,
        "attempts": attempts,
        "failures": failures,
        "taxonomy": taxonomy_summary(failures),
        "chunk_candidates": chunk_candidates,
    }


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
            worker_telemetry: dict[str, Any] = {
                "planned_chunks": 0,
                "attempted_chunks": 0,
                "successful_chunks": 0,
                "failed_chunk_index": None,
                "passage_failed": False,
                "chunks": [],
                "attempts": [],
                "failures": [],
                "taxonomy": taxonomy_summary([]),
            }
            stage = "worker_request"
            try:
                request = json.loads(raw)
                if not isinstance(request, dict) or set(request) not in (
                    {"protocol", "request_id", "source_text"},
                    {"protocol", "request_id", "source_text", "glossary"},
                ):
                    raise ValueError("worker request shape mismatch")
                if request["protocol"] != WORKER_PROTOCOL:
                    raise ValueError("worker protocol mismatch")
                request_id = str(request["request_id"])
                source_text = request["source_text"]
                glossary = (
                    validate_glossary(request["glossary"])
                    if "glossary" in request else None
                )
                if not isinstance(source_text, str) or not source_text.strip() or len(source_text) > 48_000:
                    raise ValueError("source text must contain 1..48000 characters")
                stage = "chunk_plan"
                try:
                    offset_payload = tokenizer(
                        source_text, add_special_tokens=False, return_offsets_mapping=True,
                    )
                except Exception as error:
                    raise ClassifiedStructureError(record_for_code(
                        "chunk.tokenizer", f"{type(error).__name__}: {error}",
                    )) from None
                plan = build_token_chunks(source_text, offset_payload["offset_mapping"])
                worker_telemetry["planned_chunks"] = len(plan)
                chunk_texts = [source_text[item["start"]:item["end"]] for item in plan]
                vectors: list[list[float]] = []
                stage = "embedding"
                for batch_start in range(0, len(chunk_texts), 16):
                    batch = chunk_texts[batch_start:batch_start + 16]
                    try:
                        encoded = tokenizer(
                            batch, padding=True, truncation=False, return_tensors="pt",
                        )
                        lengths = encoded["attention_mask"].sum(dim=1).tolist()
                        if any(int(length) > MAX_CHUNK_TOKENS + 2 for length in lengths):
                            raise ValueError("a semantic chunk exceeds the MiniLM token window")
                        with torch.no_grad():
                            hidden = model(**encoded).last_hidden_state
                    except ValueError:
                        raise
                    except Exception as error:
                        raise ClassifiedStructureError(record_for_code(
                            "embedding.invoke", f"{type(error).__name__}: {error}",
                        )) from None
                    mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
                    pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                    for vector in pooled:
                        values = [float(value) for value in vector.tolist()]
                        if len(values) != EMBEDDING_DIMENSION:
                            raise ValueError(
                                f"embedding model returned {len(values)} dimensions"
                            )
                        vectors.append(values)
                stage = "semantic_profile"
                semantic_profile = build_semantic_profile(
                    source_text,
                    [
                        {"start": item["start"], "end": item["end"], "values": vector}
                        for item, vector in zip(plan, vectors)
                    ],
                    model=model_name,
                    revision=revision,
                )
                chunk_observation = attempt_all_chunks(
                    gemma, request_id, chunk_texts, glossary,
                )
                chunk_candidates = chunk_observation.pop("chunk_candidates")
                worker_telemetry.update(chunk_observation)
                if worker_telemetry["failures"]:
                    response = {
                        "protocol": WORKER_PROTOCOL,
                        "request_id": request_id,
                        "error": "one or more chunks failed closed",
                        "worker_telemetry": worker_telemetry,
                    }
                    print(json.dumps(
                        response, ensure_ascii=False, separators=(",", ":")
                    ), flush=True)
                    continue
                response = {
                    "protocol": WORKER_PROTOCOL, "request_id": request_id,
                    "chunk_candidates": chunk_candidates,
                    "semantic_profile": semantic_profile,
                    "parser_model": {
                        "version": (
                            GLOSSARY_PARSER_VERSION
                            if glossary is not None else PARSER_VERSION
                        ),
                        "model": "local/gemma-instruct-tool-parser",
                        "revision": args.gemma_model.resolve().name,
                    },
                    "worker_telemetry": worker_telemetry,
                }
                if glossary is not None:
                    response["parser_model"]["glossary_sha256"] = glossary["sha256"]
            except Exception as error:
                failure = classify_failure(error, stage=stage)
                worker_telemetry["failures"].append(failure)
                worker_telemetry["passage_failed"] = True
                worker_telemetry["taxonomy"] = taxonomy_summary(
                    worker_telemetry["failures"]
                )
                response = {
                    "protocol": WORKER_PROTOCOL, "request_id": request_id,
                    "error": "passage preparation failed closed",
                    "worker_telemetry": worker_telemetry,
                }
            print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        gemma.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
