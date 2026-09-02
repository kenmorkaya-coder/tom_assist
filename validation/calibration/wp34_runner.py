"""Locked GPT-vs-Gemma parser comparison over the WP-33 corpus."""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.gpt_structure_parser import GPTStructureParser, GPTStructureParserError
from gateway.oauth_provider import OAuthProvider
from gateway.semantic_chunks import (
    EMBEDDING_DIMENSION,
    MAX_CHUNK_TOKENS,
    build_semantic_profile,
    build_token_chunks,
)
from gateway.structural_analysis import (
    CHANNELS,
    build_analysis,
    quote_candidate_response_format,
    validate_frozen_analysis,
)
from gateway.structure_provider import StructureProviderError
from validation.calibration.wp31_runner import (
    _error_code,
    _pair_metrics,
    canonical_bytes,
    cases_digest,
    score_candidate,
    sha256_bytes,
    sha256_file,
)
from validation.calibration.wp32_runner import _history_checks
from validation.calibration.wp33_cases import expanded_cases
from validation.calibration.wp33_runner import (
    READINESS_THRESHOLDS,
    _case_error,
    _summarize,
    validate_case_contract,
)


RUN_VERSION = "tom-assist-wp34-gpt-parser-comparison/2.0"
RUN_ID = "wp34-gpt-parser-comparison-v2"
LABEL = "LIVE-PARSER-COMPARISON-NOT-A-GATE"
ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = Path(__file__).with_name("WP34_PREREGISTRATION_V2.md")
CASES_SOURCE = Path(__file__).with_name("wp33_cases.py")
BASELINE = ROOT / "validation/runs/wp33-local-calibration-v3/summary.json"
BASELINE_SHA256 = "sha256:de0a971036cbbb7157051b40e16016984a9e6423cd042559aa69684d7b4fb23c"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EXPECTED_MODEL = "gpt-5.5"
EXPECTED_CASES = 94
EXPECTED_LOGICAL_PASSAGES = 113
EXPECTED_LOGICAL_CHUNK_SLOTS = 124
EXPECTED_UNIQUE_PASSAGES = 88
EXPECTED_UNIQUE_CHUNKS = 97
EXPECTED_RESPONSE_FORMAT_SHA256 = (
    "sha256:63001cf4ff74ca064b4e9043547cb2b1bdc31814d7b4aea71b45909bfcc24eb6"
)


class LiveRunStop(RuntimeError):
    """A provider-boundary failure has unknown or unsafe retry disposition."""


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _artifact(path: Path) -> dict[str, Any]:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def _source_texts(cases: Sequence[Mapping[str, Any]]) -> list[str]:
    texts: list[str] = []
    for case in cases:
        texts.extend(str(value) for value in case["history_texts"])
        texts.append(str(case["text"]))
    return texts


class MiniLMEncoder:
    """Calibration-only local encoder; no provider credential enters it."""

    def __init__(self, model_path: Path) -> None:
        if not model_path.is_absolute() or not model_path.is_dir():
            raise RuntimeError("TOM_ASSIST_MINILM_MODEL must be an existing absolute directory")
        if model_path.resolve().name != MINILM_REVISION:
            raise RuntimeError("WP-34 MiniLM revision mismatch")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), local_files_only=True
        )
        self.model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        self.model.eval()
        self.vector_cache: dict[str, list[float]] = {}

    def plan(self, source_text: str) -> list[dict[str, int]]:
        offsets = self.tokenizer(
            source_text, add_special_tokens=False, return_offsets_mapping=True
        )["offset_mapping"]
        return build_token_chunks(source_text, offsets)

    def profile(
        self, source_text: str, plan: Sequence[Mapping[str, int]]
    ) -> dict[str, Any]:
        chunk_texts = [source_text[item["start"] : item["end"]] for item in plan]
        missing = list(dict.fromkeys(text for text in chunk_texts if text not in self.vector_cache))
        for batch_start in range(0, len(missing), 16):
            batch = missing[batch_start : batch_start + 16]
            encoded = self.tokenizer(
                batch, padding=True, truncation=False, return_tensors="pt"
            )
            lengths = encoded["attention_mask"].sum(dim=1).tolist()
            if any(int(length) > MAX_CHUNK_TOKENS + 2 for length in lengths):
                raise RuntimeError("a semantic chunk exceeds the MiniLM token window")
            with self.torch.no_grad():
                hidden = self.model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
            for text, vector in zip(batch, pooled):
                values = [float(value) for value in vector.tolist()]
                if len(values) != EMBEDDING_DIMENSION:
                    raise RuntimeError("MiniLM returned the wrong vector dimension")
                self.vector_cache[text] = values
        return build_semantic_profile(
            source_text,
            [
                {
                    "start": int(item["start"]),
                    "end": int(item["end"]),
                    "values": self.vector_cache[text],
                }
                for item, text in zip(plan, chunk_texts)
            ],
            model="sentence-transformers/all-MiniLM-L6-v2",
            revision=MINILM_REVISION,
        )


class GPTCalibrationClient:
    def __init__(
        self,
        encoder: MiniLMEncoder,
        parser: GPTStructureParser,
        journal,
    ) -> None:
        self.encoder = encoder
        self.parser = parser
        self.journal = journal
        self.source_cache: dict[str, dict[str, Any]] = {}
        self.chunk_cache: dict[str, dict[str, Any]] = {}
        self.provider_calls = 0
        self.successful_provider_calls = 0

    def _journal(self, value: Mapping[str, Any]) -> None:
        self.journal.write(canonical_bytes(value).decode("utf-8") + "\n")
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def prepare_sources(self, source_texts: Sequence[str]) -> None:
        unique_sources = list(dict.fromkeys(source_texts))
        for source_text in unique_sources:
            plan = self.encoder.plan(source_text)
            profile = self.encoder.profile(source_text, plan)
            self.source_cache[source_text] = {"plan": plan, "profile": profile}
        unique_chunks: list[str] = []
        seen: set[str] = set()
        for source_text in unique_sources:
            for item in self.source_cache[source_text]["plan"]:
                chunk = source_text[item["start"] : item["end"]]
                digest = sha256_bytes(chunk.encode("utf-8"))
                if digest not in seen:
                    seen.add(digest)
                    unique_chunks.append(chunk)
        if len(unique_sources) != EXPECTED_UNIQUE_PASSAGES:
            raise RuntimeError("WP-34 unique passage count changed")
        if len(unique_chunks) != EXPECTED_UNIQUE_CHUNKS:
            raise RuntimeError("WP-34 unique semantic chunk count changed")
        for chunk in unique_chunks:
            self._parse_once(chunk)

    def _parse_once(self, chunk: str) -> dict[str, Any]:
        source_sha = sha256_bytes(chunk.encode("utf-8"))
        cached = self.chunk_cache.get(source_sha)
        if cached is not None:
            return cached
        self.provider_calls += 1
        started = time.monotonic()
        try:
            result = self.parser.parse(chunk, explicit_send=True)
        except GPTStructureParserError as error:
            elapsed = time.monotonic() - started
            record = {
                "sequence": self.provider_calls,
                "source_sha256": source_sha,
                "source_chars": len(chunk),
                "status": "provider_stop" if error.provider_failure else "parser_error",
                "error_code": _error_code(str(error)),
                "error": str(error)[:500],
                "elapsed_seconds": elapsed,
                "retry_count": 0,
                "raw_response_retained": False,
            }
            self._journal(record)
            if error.provider_failure:
                raise LiveRunStop(
                    f"provider boundary stopped after attempt {self.provider_calls}: {error}"
                ) from None
            self.chunk_cache[source_sha] = {"error": str(error)[:500], "record": record}
            return self.chunk_cache[source_sha]
        elapsed = time.monotonic() - started
        self.successful_provider_calls += 1
        record = {
            "sequence": self.provider_calls,
            "source_sha256": source_sha,
            "source_chars": len(chunk),
            "status": "observed",
            "elapsed_seconds": elapsed,
            "parser_model": result["parser_model"],
            "telemetry": result["telemetry"],
            "candidate": result["candidate"],
        }
        self._journal(record)
        self.chunk_cache[source_sha] = {"result": result, "record": record}
        return self.chunk_cache[source_sha]

    def analyze(self, source_text: str) -> dict[str, Any]:
        source = self.source_cache[source_text]
        plan = source["plan"]
        telemetry: dict[str, Any] = {
            "planned_chunks": len(plan),
            "attempted_chunks": 0,
            "successful_chunks": 0,
            "failed_chunk_index": None,
            "chunks": [],
        }
        chunk_candidates = []
        parser_model = None
        for index, item in enumerate(plan):
            telemetry["attempted_chunks"] += 1
            telemetry["failed_chunk_index"] = index
            chunk = source_text[item["start"] : item["end"]]
            cached = self.chunk_cache[sha256_bytes(chunk.encode("utf-8"))]
            if "error" in cached:
                raise StructureProviderError(
                    cached["error"], telemetry=deepcopy(telemetry)
                )
            result = cached["result"]
            if parser_model is not None and result["parser_model"] != parser_model:
                raise StructureProviderError(
                    "provider parser model changed within a passage",
                    telemetry=deepcopy(telemetry),
                )
            parser_model = result["parser_model"]
            chunk_candidates.append({
                "chunk_index": index,
                "candidate": deepcopy(result["candidate"]),
            })
            telemetry["successful_chunks"] += 1
            telemetry["failed_chunk_index"] = None
            telemetry["chunks"].append({
                "chunk_index": index,
                "tool_parse_mode": "gpt_structured_quote_cache",
                "schema_projection_applied": result["telemetry"][
                    "schema_projection_applied"
                ],
            })
        return {
            "chunk_candidates": chunk_candidates,
            "semantic_profile": deepcopy(source["profile"]),
            "parser_model": deepcopy(parser_model),
            "worker_telemetry": telemetry,
        }


def _worker_call(
    client: GPTCalibrationClient,
    text: str,
    role: str,
    index: int,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = client.analyze(text)
    except StructureProviderError as error:
        telemetry = deepcopy(error.telemetry)
        calls.append({
            "role": role,
            "index": index,
            "source_sha256": sha256_bytes(text.encode("utf-8")),
            "status": "parser_error",
            "elapsed_seconds": time.monotonic() - started,
            **telemetry,
        })
        raise
    calls.append({
        "role": role,
        "index": index,
        "source_sha256": sha256_bytes(text.encode("utf-8")),
        "status": "observed",
        "elapsed_seconds": time.monotonic() - started,
        **deepcopy(result["worker_telemetry"]),
    })
    return result


def _analyze_case(
    client: GPTCalibrationClient,
    case: Mapping[str, Any],
    calls: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for index, history_text in enumerate(case["history_texts"]):
        result = _worker_call(client, history_text, "history", index, calls)
        checkpoint = f"wp34:{case['case_id']}:history:{index}"
        analysis = build_analysis(
            history_text,
            result["chunk_candidates"],
            result["semantic_profile"],
            result["parser_model"],
            history,
            checkpoint,
        )
        validate_frozen_analysis(analysis, history_text, history, checkpoint)
        history.append({
            "record_id": f"{case['case_id']}:history:{index}",
            "candidate": analysis["candidate"],
            "semantic_profile": analysis["semantic_profile"],
            "static_load": analysis["static_load"],
        })
    result = _worker_call(client, case["text"], "query", len(history), calls)
    checkpoint = f"wp34:{case['case_id']}:query"
    analysis = build_analysis(
        case["text"],
        result["chunk_candidates"],
        result["semantic_profile"],
        result["parser_model"],
        history,
        checkpoint,
    )
    validate_frozen_analysis(analysis, case["text"], history, checkpoint)
    score = score_candidate(case, analysis["candidate"])
    history_checks = _history_checks(case["history_expectations"], analysis["load_signature"])
    exact = (
        score["expectations_exact"]
        and score["unexpected_relation_count"] <= case["max_unexpected_relations"]
        and all(item["met"] for item in history_checks)
    )
    load = analysis["load_signature"]
    load_ok = (
        list(load) == list(CHANNELS)
        and all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in load.values())
    )
    chunks = analysis["semantic_profile"]["chunks"]
    observation = {
        "case_id": case["case_id"],
        "family": case["family"],
        "origin": case["origin"],
        "pair_id": case.get("pair_id"),
        "status": "observed",
        "source_sha256": sha256_bytes(case["text"].encode("utf-8")),
        "source_chars": len(case["text"]),
        "worker_calls": calls,
        "chunk_count": len(chunks),
        "chunk_expectation_met": len(chunks) >= int(case["min_chunks"]),
        "chunks": [
            {
                "index": chunk["index"],
                "start": chunk["start"],
                "end": chunk["end"],
                "text_sha256": chunk["text_sha256"],
            }
            for chunk in chunks
        ],
        "candidate_digest": analysis["candidate_digest"],
        "analysis_digest": analysis["analysis_digest"],
        "score": {**score, "v3_exact": exact},
        "history_checks": history_checks,
        "history_checks_met": all(item["met"] for item in history_checks),
        "load_signature": load,
        "nonzero_channels": [name for name, value in load.items() if value > 0.0],
        "load_shape_valid": load_ok,
    }
    return observation, {"profile": analysis["semantic_profile"], "analysis": analysis}


def _baseline() -> dict[str, Any]:
    if sha256_file(BASELINE) != BASELINE_SHA256:
        raise RuntimeError("frozen WP-33 baseline summary changed")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def _comparison(summary: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    current = summary["readiness_criteria"]
    prior = baseline["readiness_criteria"]
    names = list(READINESS_THRESHOLDS)
    deltas = {
        name: float(current[name]["value"]) - float(prior[name]["value"])
        for name in names
    }
    safety_non_regression = (
        current["maximum_reversed_relations"]["value"]
        <= prior["maximum_reversed_relations"]["value"]
        and current["maximum_unexpected_relation_rate"]["value"]
        <= prior["maximum_unexpected_relation_rate"]["value"]
        and current["load_shape_rate"]["value"] >= prior["load_shape_rate"]["value"]
    )
    core_improvement = all(
        deltas[name] > 0.0
        for name in (
            "strict_observation_rate",
            "end_to_end_relation_recall",
            "end_to_end_signal_recall",
            "multi_relation_exact_rate",
        )
    )
    return {
        "baseline_run_id": baseline["run_id"],
        "baseline_summary_sha256": BASELINE_SHA256,
        "metric_deltas_gpt_minus_gemma": deltas,
        "core_improvement": core_improvement,
        "safety_non_regression": safety_non_regression,
        "gpt_better_on_preregistered_rule": core_improvement and safety_non_regression,
    }


def _report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# WP-34 GPT parser comparison",
        "",
        "**LIVE ENGINEERING COMPARISON — NOT A GATE. No G-gate verdict is issued or implied.**",
        "",
        f"- Cases: {summary['cases']}",
        f"- Explicit provider generations: {summary['provider_calls']}",
        f"- Successful structured generations: {summary['successful_provider_calls']}",
        f"- Strict observations/parser errors: {summary['observed']}/{summary['parser_errors']}",
        f"- Expected relations: {summary['matched_relations']}/{summary['expected_relations_all_attempts']}",
        f"- Reversed/unexpected relations: {summary['reversed_relations']}/{summary['unexpected_relations']}",
        f"- Expected signals: {summary['matched_signals']}/{summary['expected_signals_all_attempts']}",
        f"- Valid 17-channel shapes: {summary['valid_load_shapes']}/{summary['observed']}",
        "",
        "| Metric | GPT | Gemma v3 | Delta |",
        "|---|---:|---:|---:|",
    ]
    comparison = summary["comparison"]
    for name, row in summary["readiness_criteria"].items():
        baseline = row["value"] - comparison["metric_deltas_gpt_minus_gemma"][name]
        lines.append(
            f"| `{name}` | {row['value']:.6f} | {baseline:.6f} | "
            f"{comparison['metric_deltas_gpt_minus_gemma'][name]:+.6f} |"
        )
    lines.extend([
        "",
        f"Pre-registered core improvement: **{str(comparison['core_improvement']).upper()}**.",
        f"Pre-registered safety non-regression: **{str(comparison['safety_non_regression']).upper()}**.",
        f"GPT better on the pre-registered rule: **{str(comparison['gpt_better_on_preregistered_rule']).upper()}**.",
        "",
        "The GPT parser remains candidate-only and inactive pending owner audit. The model supplied quotes and typed facts only; Tom Assist bound offsets and compiled all 17 channels. This run did not advance the Python 10K tree.",
        "",
    ])
    return "\n".join(lines)


def check() -> dict[str, Any]:
    cases = expanded_cases()
    validate_case_contract(cases)
    texts = _source_texts(cases)
    if len(cases) != EXPECTED_CASES or len(texts) != EXPECTED_LOGICAL_PASSAGES:
        raise RuntimeError("WP-34 locked corpus count changed")
    response_format_sha256 = sha256_bytes(
        canonical_bytes(quote_candidate_response_format())
    )
    if response_format_sha256 != EXPECTED_RESPONSE_FORMAT_SHA256:
        raise RuntimeError("WP-34 structured response format changed")
    result = {
        "run_version": RUN_VERSION,
        "run_id": RUN_ID,
        "label": LABEL,
        "cases": len(cases),
        "logical_passages": len(texts),
        "unique_passages": len(set(texts)),
        "expected_logical_chunk_slots": EXPECTED_LOGICAL_CHUNK_SLOTS,
        "expected_provider_calls": EXPECTED_UNIQUE_CHUNKS,
        "response_format_sha256": response_format_sha256,
        "cases_sha256": cases_digest(cases),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "baseline_summary_sha256": sha256_file(BASELINE),
        "provider_calls": 0,
    }
    if result["unique_passages"] != EXPECTED_UNIQUE_PASSAGES:
        raise RuntimeError("WP-34 unique passage count changed")
    print(json.dumps(result, sort_keys=True))
    return result


def run(output: Path) -> dict[str, Any]:
    if os.environ.get("TOM_ASSIST_WP34_GPT_LIVE") != "1":
        raise RuntimeError("set TOM_ASSIST_WP34_GPT_LIVE=1 for the authorized run")
    cases = expanded_cases()
    validate_case_contract(cases)
    texts = _source_texts(cases)
    if len(texts) != EXPECTED_LOGICAL_PASSAGES:
        raise RuntimeError("WP-34 logical passage count changed")
    if sha256_bytes(canonical_bytes(quote_candidate_response_format())) != (
        EXPECTED_RESPONSE_FORMAT_SHA256
    ):
        raise RuntimeError("WP-34 structured response format changed")
    baseline = _baseline()
    model_path = Path(os.environ.get("TOM_ASSIST_MINILM_MODEL", "")).expanduser()
    provider = OAuthProvider()
    status = provider.status()
    if not status["connected"] or status["model"] != EXPECTED_MODEL:
        raise RuntimeError(f"WP-34 OAuth preflight failed: {status['code']}/{status['model']}")
    if output.exists():
        raise RuntimeError("WP-34 output directory already exists; never overwrite a run")
    output.mkdir(parents=True)
    attempts_path = output / "provider_attempts.jsonl"
    observations_path = output / "observations.jsonl"
    encoder = MiniLMEncoder(model_path.resolve())
    with attempts_path.open("x", encoding="utf-8") as journal:
        client = GPTCalibrationClient(encoder, GPTStructureParser(provider), journal)
        try:
            client.prepare_sources(texts)
        except LiveRunStop as error:
            _write_json(output / "STOP.json", {
                "completed": False,
                "reason": str(error),
                "provider_calls": client.provider_calls,
                "retry_count": 0,
                "unknown_outcome_retried": False,
            })
            raise
        if client.provider_calls != EXPECTED_UNIQUE_CHUNKS:
            raise RuntimeError("WP-34 provider call count changed")
        observations: list[dict[str, Any]] = []
        private: dict[str, dict[str, Any]] = {}
        with observations_path.open("x", encoding="utf-8") as stream:
            for sequence, case in enumerate(cases, 1):
                started = time.monotonic()
                calls: list[dict[str, Any]] = []
                try:
                    observation, hidden = _analyze_case(client, case, calls)
                    observation["elapsed_seconds"] = time.monotonic() - started
                    private[str(case["case_id"])] = hidden
                except (StructureProviderError, ValueError, RuntimeError) as error:
                    observation = _case_error(
                        case, error, calls, time.monotonic() - started
                    )
                observations.append(observation)
                stream.write(canonical_bytes(observation).decode("utf-8") + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                print(json.dumps({
                    "sequence": sequence,
                    "total": len(cases),
                    "case_id": case["case_id"],
                    "status": observation["status"],
                }, separators=(",", ":")), flush=True)
    by_id = {row["case_id"]: row for row in observations}
    pairs = _pair_metrics(cases, by_id, private)
    summary = _summarize(cases, observations, pairs)
    summary.update({
        "run_id": RUN_ID,
        "label": LABEL,
        "provider_calls": client.provider_calls,
        "successful_provider_calls": client.successful_provider_calls,
        "unique_passages": EXPECTED_UNIQUE_PASSAGES,
        "unique_semantic_chunks": EXPECTED_UNIQUE_CHUNKS,
        "logical_chunk_slots": EXPECTED_LOGICAL_CHUNK_SLOTS,
        "raw_provider_responses_retained": False,
        "parser_active": False,
        "ready_for_shadow_review": False,
    })
    summary["comparison"] = _comparison(summary, baseline)
    elapsed = [
        json.loads(line)["elapsed_seconds"]
        for line in attempts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary["provider_elapsed_seconds"] = {
        "total": sum(elapsed),
        "min": min(elapsed),
        "median": statistics.median(elapsed),
        "max": max(elapsed),
    }
    pairs_path = output / "pair_metrics.jsonl"
    pairs_path.write_text(
        "".join(canonical_bytes(row).decode("utf-8") + "\n" for row in pairs),
        encoding="utf-8",
    )
    summary_path = output / "summary.json"
    _write_json(summary_path, summary)
    report_path = output / "REPORT.md"
    report_path.write_text(_report(summary), encoding="utf-8")
    artifacts = {
        path.name: _artifact(path)
        for path in (
            attempts_path,
            observations_path,
            pairs_path,
            summary_path,
            report_path,
        )
    }
    manifest = {
        "run_version": RUN_VERSION,
        "run_id": RUN_ID,
        "label": LABEL,
        "completed": True,
        "code_sha": _git_sha(),
        "cases_sha256": cases_digest(cases),
        "cases_source_sha256": sha256_file(CASES_SOURCE),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "runner_sha256": sha256_file(Path(__file__)),
        "baseline_summary_sha256": BASELINE_SHA256,
        "response_format_sha256": EXPECTED_RESPONSE_FORMAT_SHA256,
        "model_revisions": {"minilm": MINILM_REVISION, "gpt": EXPECTED_MODEL},
        "provider_surface": "tom-assist/openai-oauth",
        "credential_owner": "tom-assist-keychain",
        "explicit_send": True,
        "provider_calls": client.provider_calls,
        "retry_count": 0,
        "raw_provider_responses_retained": False,
        "feeling_wheel_enabled": False,
        "parser_active": False,
        "tree_steps": 0,
        "artifacts": artifacts,
    }
    _write_json(output / "run_manifest.json", manifest)
    print(json.dumps(summary, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("check")
    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "check":
        check()
    else:
        run(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
