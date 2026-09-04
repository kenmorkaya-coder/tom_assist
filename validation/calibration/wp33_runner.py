"""One-shot, pre-registered WP-33 local parser calibration-v3 runner."""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.structural_analysis import CHANNELS, build_analysis, validate_frozen_analysis
from gateway.structure_provider import StructureProviderError, StructureWorkerClient
from validation.calibration.wp31_runner import (
    _error_code,
    _pair_metrics,
    canonical_bytes,
    cases_digest,
    score_candidate,
    sha256_bytes,
    sha256_file,
)
from validation.calibration.wp32_cases import expanded_cases as wp32_expanded_cases
from validation.calibration.wp32_runner import _history_checks, _validated_telemetry
from validation.calibration.wp33_cases import expanded_cases


RUN_VERSION = "tom-assist-wp33-local-calibration/3.0"
RUN_ID = "wp33-local-calibration-v3"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
GEMMA_REVISION = "0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = Path(__file__).with_name("WP33_PREREGISTRATION.md")
CASES_SOURCE = Path(__file__).with_name("wp33_cases.py")
READINESS_THRESHOLDS = {
    "strict_observation_rate": 0.90,
    "minimum_family_observation_rate": 0.75,
    "end_to_end_relation_recall": 0.90,
    "maximum_reversed_relations": 0,
    "maximum_unexpected_relation_rate": 0.05,
    "end_to_end_signal_recall": 0.80,
    "multi_relation_exact_rate": 0.80,
    "history_case_rate": 0.875,
    "load_shape_rate": 1.0,
}


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _artifact(path: Path) -> dict[str, Any]:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def _assert_run_pin() -> dict[str, str]:
    variables = {
        "minilm": "TOM_ASSIST_MINILM_MODEL",
        "gemma": "TOM_ASSIST_GEMMA_MODEL",
    }
    result = {}
    for label, variable in variables.items():
        path = Path(os.environ.get(variable, "")).expanduser()
        if not path.is_absolute() or not path.is_dir():
            raise RuntimeError(f"{variable} must be an existing absolute directory")
        result[label] = path.resolve().name
    expected = {"minilm": MINILM_REVISION, "gemma": GEMMA_REVISION}
    if result != expected:
        raise RuntimeError(f"WP-33 local model revision mismatch: {result}")
    return result


def validate_case_contract(cases: Sequence[Mapping[str, Any]]) -> None:
    if len(cases) != 94:
        raise ValueError("WP-33 calibration-v3 must contain exactly 94 cases")
    ids = [str(case["case_id"]) for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("WP-33 case IDs must be unique")
    counts = Counter(str(case["family"]) for case in cases)
    expected_counts = {
        "causal_direction": 10,
        "orientation": 12,
        "signal": 16,
        "multi_relation": 16,
        "long_position": 10,
        "paraphrase": 10,
        "parser_boundary": 12,
        "history": 8,
    }
    if counts != expected_counts:
        raise ValueError(f"WP-33 family counts changed: {dict(counts)}")
    prior = wp32_expanded_cases()
    for retained, original in zip(cases[:80], prior):
        comparable = dict(retained)
        comparable["origin"] = original["origin"]
        if original["case_id"] == "HD-05":
            expected = deepcopy(original)
            for condition in expected["history_expectations"]:
                if condition["channel"] == "persistence":
                    condition.clear()
                    condition.update({
                        "channel": "persistence",
                        "minimum": 2 / 3,
                        "maximum": 2 / 3,
                    })
            if comparable != expected:
                raise ValueError("HD-05 differs by more than its corrected persistence bound")
        elif comparable != original:
            raise ValueError(f"retained WP-32 case changed: {original['case_id']}")
    for case in cases:
        if not str(case["text"]).strip() or int(case["min_chunks"]) < 1:
            raise ValueError(f"{case['case_id']} has invalid source or chunk expectation")
        for condition in case["history_expectations"]:
            if condition.get("channel") not in CHANNELS:
                raise ValueError(f"{case['case_id']} has an unknown history channel")
            if not ({"minimum", "maximum"} & set(condition)):
                raise ValueError(f"{case['case_id']} history condition has no bound")


def _worker_call(
    client: StructureWorkerClient,
    text: str,
    role: str,
    index: int,
    calls: list[dict[str, Any]],
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = client.analyze(text)
    except StructureProviderError as error:
        telemetry = _validated_telemetry(error.telemetry)
        calls.append({
            "role": role,
            "index": index,
            "source_sha256": sha256_bytes(text.encode("utf-8")),
            "status": "parser_error",
            "elapsed_seconds": time.monotonic() - started,
            **telemetry,
        })
        raise
    telemetry = _validated_telemetry(result.get("worker_telemetry"))
    if not (
        telemetry["planned_chunks"]
        == telemetry["attempted_chunks"]
        == telemetry["successful_chunks"]
    ) or telemetry["failed_chunk_index"] is not None:
        raise ValueError("successful worker response has incomplete chunk accounting")
    calls.append({
        "role": role,
        "index": index,
        "source_sha256": sha256_bytes(text.encode("utf-8")),
        "status": "observed",
        "elapsed_seconds": time.monotonic() - started,
        **telemetry,
    })
    return result


def _analyze_case(
    client: StructureWorkerClient,
    case: Mapping[str, Any],
    calls: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for index, history_text in enumerate(case["history_texts"]):
        result = _worker_call(client, history_text, "history", index, calls)
        checkpoint = f"wp33:{case['case_id']}:history:{index}"
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
    checkpoint = f"wp33:{case['case_id']}:query"
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
        "chunks": [{
            "index": chunk["index"],
            "start": chunk["start"],
            "end": chunk["end"],
            "text_sha256": chunk["text_sha256"],
        } for chunk in chunks],
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


def _case_error(
    case: Mapping[str, Any],
    error: Exception,
    calls: Sequence[Mapping[str, Any]],
    elapsed: float,
) -> dict[str, Any]:
    message = f"{type(error).__name__}: {str(error)[:500]}"
    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "origin": case["origin"],
        "pair_id": case.get("pair_id"),
        "status": "parser_error",
        "elapsed_seconds": elapsed,
        "source_sha256": sha256_bytes(case["text"].encode("utf-8")),
        "source_chars": len(case["text"]),
        "worker_calls": list(calls),
        "error_code": _error_code(message),
        "error": message,
    }


def _summarize(
    cases: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed = [row for row in observations if row["status"] == "observed"]
    errors = [row for row in observations if row["status"] == "parser_error"]
    expected_relations = sum(len(case["expected_relations"]) for case in cases)
    expected_signals = sum(len(case["expected_signals"]) for case in cases)
    matched_relations = sum(row["score"]["matched_relation_count"] for row in observed)
    matched_signals = sum(row["score"]["matched_signal_count"] for row in observed)
    actual_relations = sum(len(row["score"]["actual_relations"]) for row in observed)
    unexpected = sum(row["score"]["unexpected_relation_count"] for row in observed)
    all_calls = [call for row in observations for call in row["worker_calls"]]
    chunks = [chunk for call in all_calls for chunk in call["chunks"]]
    families = {}
    for family in sorted({case["family"] for case in cases}):
        family_cases = [case for case in cases if case["family"] == family]
        ids = {case["case_id"] for case in family_cases}
        rows = [row for row in observations if row["case_id"] in ids]
        good = [row for row in rows if row["status"] == "observed"]
        families[family] = {
            "cases": len(rows),
            "observed": len(good),
            "observation_rate": len(good) / len(rows),
            "v3_exact": sum(row["score"]["v3_exact"] for row in good),
            "expected_relations_all_attempts": sum(len(case["expected_relations"]) for case in family_cases),
            "matched_relations": sum(row["score"]["matched_relation_count"] for row in good),
            "expected_signals_all_attempts": sum(len(case["expected_signals"]) for case in family_cases),
            "matched_signals": sum(row["score"]["matched_signal_count"] for row in good),
        }
    strict_rate = len(observed) / len(cases)
    relation_recall = matched_relations / expected_relations
    signal_recall = matched_signals / expected_signals
    reversed_count = sum(len(row["score"]["reversed_relations"]) for row in observed)
    unexpected_rate = unexpected / actual_relations if actual_relations else 0.0
    multi_rate = families["multi_relation"]["v3_exact"] / families["multi_relation"]["cases"]
    history_cases = [case for case in cases if case["family"] == "history"]
    history_rows = [row for row in observed if row["family"] == "history"]
    history_rate = sum(row["history_checks_met"] for row in history_rows) / len(history_cases)
    load_rate = sum(row["load_shape_valid"] for row in observed) / len(observed) if observed else 0.0
    values = {
        "strict_observation_rate": strict_rate,
        "minimum_family_observation_rate": min(row["observation_rate"] for row in families.values()),
        "end_to_end_relation_recall": relation_recall,
        "maximum_reversed_relations": reversed_count,
        "maximum_unexpected_relation_rate": unexpected_rate,
        "end_to_end_signal_recall": signal_recall,
        "multi_relation_exact_rate": multi_rate,
        "history_case_rate": history_rate,
        "load_shape_rate": load_rate,
    }
    criteria = {}
    for name, value in values.items():
        threshold = READINESS_THRESHOLDS[name]
        maximum = name.startswith("maximum_")
        criteria[name] = {
            "value": value,
            "threshold": threshold,
            "met": value <= threshold if maximum else value >= threshold,
        }
    elapsed = [float(row["elapsed_seconds"]) for row in observations]
    return {
        "run_id": RUN_ID,
        "label": "LOCAL-CALIBRATION-V3-NOT-A-GATE",
        "cases": len(cases),
        "retained_wp32_cases": 80,
        "added_wp33_cases": 14,
        "logical_passage_attempts": len(all_calls),
        "local_chunk_model_attempts": sum(call["attempted_chunks"] for call in all_calls),
        "successful_chunk_model_calls": sum(call["successful_chunks"] for call in all_calls),
        "provider_calls": 0,
        "observed": len(observed),
        "parser_errors": len(errors),
        "error_taxonomy": dict(sorted(Counter(row["error_code"] for row in errors).items())),
        "v3_exact_cases": sum(row["score"]["v3_exact"] for row in observed),
        "expected_relations_all_attempts": expected_relations,
        "matched_relations": matched_relations,
        "reversed_relations": reversed_count,
        "unexpected_relations": unexpected,
        "actual_relations": actual_relations,
        "expected_signals_all_attempts": expected_signals,
        "matched_signals": matched_signals,
        "valid_load_shapes": sum(row["load_shape_valid"] for row in observed),
        "parse_modes": dict(sorted(Counter(row["tool_parse_mode"] for row in chunks).items())),
        "schema_projection_calls": sum(row["schema_projection_applied"] for row in chunks),
        "paraphrase_pairs_observed": sum(row["status"] == "observed" for row in pairs),
        "families": families,
        "readiness_criteria": criteria,
        "ready_for_shadow_review": all(row["met"] for row in criteria.values()),
        "elapsed_seconds": {
            "total": sum(elapsed),
            "min": min(elapsed),
            "median": statistics.median(elapsed),
            "max": max(elapsed),
        },
    }


def _report(summary: Mapping[str, Any]) -> str:
    lines = [
        "# WP-33 local parser calibration v3",
        "",
        "**LOCAL CALIBRATION — NOT A GATE. No G-gate verdict is issued or implied.**",
        "",
        f"- Cases: {summary['cases']} ({summary['retained_wp32_cases']} retained + {summary['added_wp33_cases']} added)",
        f"- Exact local chunk-model attempts/successes: {summary['local_chunk_model_attempts']}/{summary['successful_chunk_model_calls']}",
        f"- Provider/OAuth calls: {summary['provider_calls']}",
        f"- Strict observations/parser errors: {summary['observed']}/{summary['parser_errors']}",
        f"- Expected relations: {summary['matched_relations']}/{summary['expected_relations_all_attempts']}",
        f"- Reversed/unexpected relations: {summary['reversed_relations']}/{summary['unexpected_relations']}",
        f"- Expected signals: {summary['matched_signals']}/{summary['expected_signals_all_attempts']}",
        f"- Valid 17-channel shapes: {summary['valid_load_shapes']}/{summary['observed']}",
        "",
        "| Criterion | Value | Required | Met |",
        "|---|---:|---:|---|",
    ]
    for name, row in summary["readiness_criteria"].items():
        lines.append(
            f"| `{name}` | {row['value']:.6f} | {row['threshold']:.6f} | {str(row['met']).lower()} |"
        )
    lines.extend([
        "",
        f"Ready for owner consideration of shadow mode: **{str(summary['ready_for_shadow_review']).upper()}**.",
        "This result cannot activate the parser, establish whole-tree efficacy, or pass a G-gate.",
        "",
    ])
    return "\n".join(lines)


def check() -> dict[str, Any]:
    cases = expanded_cases()
    validate_case_contract(cases)
    result = {
        "run_version": RUN_VERSION,
        "run_id": RUN_ID,
        "cases": len(cases),
        "cases_sha256": cases_digest(cases),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "model_revisions": {"minilm": MINILM_REVISION, "gemma": GEMMA_REVISION},
        "readiness_thresholds": READINESS_THRESHOLDS,
        "provider_calls": 0,
        "label": "LOCAL-CALIBRATION-V3-NOT-A-GATE",
    }
    print(json.dumps(result, sort_keys=True))
    return result


def run(output: Path) -> dict[str, Any]:
    if os.environ.get("TOM_ASSIST_WP33_LOCAL") != "1":
        raise RuntimeError("set TOM_ASSIST_WP33_LOCAL=1 for the authorized local run")
    cases = expanded_cases()
    validate_case_contract(cases)
    revisions = _assert_run_pin()
    if output.exists():
        raise RuntimeError("WP-33 output directory already exists; never overwrite a run")
    output.mkdir(parents=True)
    observations_path = output / "observations.jsonl"
    observations: list[dict[str, Any]] = []
    private: dict[str, dict[str, Any]] = {}
    client = StructureWorkerClient.from_environment()
    try:
        with observations_path.open("x", encoding="utf-8") as stream:
            for sequence, case in enumerate(cases, 1):
                started = time.monotonic()
                calls: list[dict[str, Any]] = []
                try:
                    observation, hidden = _analyze_case(client, case, calls)
                    observation["elapsed_seconds"] = time.monotonic() - started
                    private[str(case["case_id"])] = hidden
                except (StructureProviderError, ValueError, RuntimeError) as error:
                    observation = _case_error(case, error, calls, time.monotonic() - started)
                observations.append(observation)
                stream.write(canonical_bytes(observation).decode("utf-8") + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                print(json.dumps({
                    "sequence": sequence,
                    "total": len(cases),
                    "case_id": case["case_id"],
                    "status": observation["status"],
                    "elapsed_seconds": observation["elapsed_seconds"],
                }, separators=(",", ":")), flush=True)
    finally:
        client.close()
    by_id = {row["case_id"]: row for row in observations}
    pairs = _pair_metrics(cases, by_id, private)
    summary = _summarize(cases, observations, pairs)
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
        for path in (observations_path, pairs_path, summary_path, report_path)
    }
    manifest = {
        "run_version": RUN_VERSION,
        "run_id": RUN_ID,
        "label": "LOCAL-CALIBRATION-V3-NOT-A-GATE",
        "completed": True,
        "code_sha": _git_sha(),
        "cases_sha256": cases_digest(cases),
        "cases_source_sha256": sha256_file(CASES_SOURCE),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "runner_sha256": sha256_file(Path(__file__)),
        "model_revisions": revisions,
        "logical_passage_attempts": summary["logical_passage_attempts"],
        "local_chunk_model_attempts": summary["local_chunk_model_attempts"],
        "successful_chunk_model_calls": summary["successful_chunk_model_calls"],
        "provider_calls": 0,
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
