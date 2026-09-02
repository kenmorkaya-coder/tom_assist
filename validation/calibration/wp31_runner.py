"""Compact offline runner for the pre-registered WP-31 local calibration."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.semantic_chunks import profile_similarity
from gateway.structural_analysis import (
    CHANNELS,
    build_analysis,
    directed_graph_fingerprint,
    validate_frozen_analysis,
)
from gateway.structure_provider import StructureProviderError, StructureWorkerClient
from validation.calibration.wp31_cases import expanded_cases


RUN_VERSION = "tom-assist-wp31-local-calibration/1.0"
RUN_ID = "wp31-local-calibration-v1"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
GEMMA_REVISION = "0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = Path(__file__).with_name("WP31_PREREGISTRATION.md")
CASES_SOURCE = Path(__file__).with_name("wp31_cases.py")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def cases_digest(cases: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(canonical_bytes(list(cases)))


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def entity_terms(entity: Mapping[str, Any]) -> set[str]:
    return {
        normalize(str(entity.get("label", ""))),
        normalize(str(entity.get("evidence", {}).get("quote", ""))),
    } - {""}


def term_matches(expected: str, entity: Mapping[str, Any]) -> bool:
    wanted = normalize(expected)
    return any(
        wanted == term or wanted in term or term in wanted
        for term in entity_terms(entity)
        if len(term) > 1 or term == wanted
    )


def compact_relations(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    entities = {entity["id"]: entity for entity in candidate["entities"]}
    result = []
    for relation in candidate["orientations"]:
        source = entities[relation["source_entity_id"]]
        target = entities[relation["target_entity_id"]]
        result.append({
            "channel": "orientation",
            "kind": relation["kind"],
            "source_label": source["label"],
            "source_quote": source["evidence"]["quote"],
            "target_label": target["label"],
            "target_quote": target["evidence"]["quote"],
            "modality": relation["modality"],
            "negated": relation["negated"],
            "evidence": relation["evidence"],
            "confidence": relation["confidence"],
        })
    for relation in candidate["causal_relations"]:
        source = entities[relation["cause_entity_id"]]
        target = entities[relation["effect_entity_id"]]
        result.append({
            "channel": "causal",
            "kind": relation["kind"],
            "source_label": source["label"],
            "source_quote": source["evidence"]["quote"],
            "target_label": target["label"],
            "target_quote": target["evidence"]["quote"],
            "modality": relation["modality"],
            "negated": relation["negated"],
            "evidence": relation["evidence"],
            "confidence": relation["confidence"],
        })
    return result


def _compact_entity(relation: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "label": relation[f"{prefix}_label"],
        "evidence": {"quote": relation[f"{prefix}_quote"]},
    }


def relation_matches(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    return (
        expected["channel"] == actual["channel"]
        and expected["kind"] == actual["kind"]
        and bool(expected["negated"]) == bool(actual["negated"])
        and actual["modality"] in expected["modalities"]
        and term_matches(str(expected["source"]), _compact_entity(actual, "source"))
        and term_matches(str(expected["target"]), _compact_entity(actual, "target"))
    )


def relation_is_reversed(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    return (
        expected["channel"] == actual["channel"]
        and expected["kind"] == actual["kind"]
        and term_matches(str(expected["source"]), _compact_entity(actual, "target"))
        and term_matches(str(expected["target"]), _compact_entity(actual, "source"))
    )


def score_candidate(
    case: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    actual = compact_relations(candidate)
    remaining = set(range(len(actual)))
    matched = []
    missing = []
    for expected in case["expected_relations"]:
        match = next(
            (index for index in sorted(remaining)
             if relation_matches(expected, actual[index])),
            None,
        )
        if match is None:
            missing.append(expected)
        else:
            remaining.remove(match)
            matched.append({"expected": expected, "actual_index": match})
    reversed_expected = [
        expected
        for expected in missing
        if any(relation_is_reversed(expected, relation) for relation in actual)
    ]
    signal_counts = {
        name: len(candidate["signals"][name])
        for name in sorted(candidate["signals"])
    }
    missing_signals = [
        name for name in case["expected_signals"] if signal_counts.get(name, 0) == 0
    ]
    expected_relation_count = len(case["expected_relations"])
    return {
        "expected_relation_count": expected_relation_count,
        "matched_relation_count": len(matched),
        "relation_recall": (
            len(matched) / expected_relation_count if expected_relation_count else 1.0
        ),
        "missing_relations": missing,
        "reversed_relations": reversed_expected,
        "unexpected_relation_count": len(remaining),
        "expected_signal_count": len(case["expected_signals"]),
        "matched_signal_count": len(case["expected_signals"]) - len(missing_signals),
        "missing_signals": missing_signals,
        "signal_counts": signal_counts,
        "expectations_exact": not missing and not missing_signals and not reversed_expected,
        "actual_relations": actual,
    }


def validate_case_contract(cases: Sequence[Mapping[str, Any]]) -> None:
    if len(cases) != 52:
        raise ValueError("WP-31 calibration must contain exactly 52 cases")
    ids = [case["case_id"] for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("WP-31 case IDs must be unique")
    family_counts = Counter(case["family"] for case in cases)
    if family_counts != {
        "causal_direction": 10,
        "orientation": 12,
        "signal": 8,
        "multi_relation": 6,
        "long_position": 6,
        "paraphrase": 10,
    }:
        raise ValueError(f"WP-31 family counts changed: {dict(family_counts)}")
    pairs: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        if not case["text"].strip():
            raise ValueError(f"{case['case_id']} has empty source text")
        if case["min_chunks"] < 1:
            raise ValueError(f"{case['case_id']} has invalid chunk expectation")
        if "pair_id" in case:
            pairs[case["pair_id"]].append(case["case_id"])
    if len(pairs) != 5 or any(len(values) != 2 for values in pairs.values()):
        raise ValueError("WP-31 must contain five two-case paraphrase pairs")


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


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
    if result != {"minilm": MINILM_REVISION, "gemma": GEMMA_REVISION}:
        raise RuntimeError(f"WP-31 local model revision mismatch: {result}")
    return result


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def _artifact(path: Path) -> dict[str, Any]:
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def _error_code(message: str) -> str:
    prefix = message.split(":", 1)[0]
    return normalize(prefix).replace(" ", "_") or "unknown"


def _observation(
    case: Mapping[str, Any],
    result: Mapping[str, Any],
    elapsed: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    analysis = build_analysis(
        case["text"],
        result["chunk_candidates"],
        result["semantic_profile"],
        result["parser_model"],
        [],
        f"wp31:{case['case_id']}",
    )
    validate_frozen_analysis(
        analysis, case["text"], [], f"wp31:{case['case_id']}"
    )
    score = score_candidate(case, analysis["candidate"])
    chunks = analysis["semantic_profile"]["chunks"]
    chunk_ok = len(chunks) >= case["min_chunks"]
    load = analysis["load_signature"]
    load_ok = (
        list(load) == list(CHANNELS)
        and all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in load.values())
    )
    observation = {
        "case_id": case["case_id"],
        "family": case["family"],
        "pair_id": case.get("pair_id"),
        "status": "observed",
        "elapsed_seconds": elapsed,
        "source_sha256": sha256_bytes(case["text"].encode("utf-8")),
        "source_chars": len(case["text"]),
        "chunk_count": len(chunks),
        "chunk_expectation_met": chunk_ok,
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
        "score": score,
        "load_signature": load,
        "nonzero_channels": [name for name, value in load.items() if value > 0.0],
        "load_shape_valid": load_ok,
    }
    private = {"profile": analysis["semantic_profile"], "analysis": analysis}
    return observation, private


def _pair_metrics(
    cases: Sequence[Mapping[str, Any]],
    observations: Mapping[str, Mapping[str, Any]],
    private: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pairs: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        if "pair_id" in case:
            pairs[case["pair_id"]].append(case["case_id"])
    available_ids = sorted(private)
    result = []
    for pair_id, case_ids in sorted(pairs.items()):
        left_id, right_id = case_ids
        if left_id not in private or right_id not in private:
            result.append({
                "pair_id": pair_id,
                "case_ids": case_ids,
                "status": "unavailable_parser_error",
            })
            continue
        left = private[left_id]
        right = private[right_id]
        semantic = profile_similarity(left["profile"], right["profile"])
        left_load = observations[left_id]["load_signature"]
        right_load = observations[right_id]["load_signature"]

        def rank(query_id: str, target_id: str) -> int:
            query = private[query_id]["profile"]
            scores = []
            for candidate_id in available_ids:
                if candidate_id == query_id:
                    continue
                score = profile_similarity(
                    query, private[candidate_id]["profile"]
                )["query_relevance_score"]
                scores.append((-score, candidate_id))
            ordered = [candidate_id for _, candidate_id in sorted(scores)]
            return ordered.index(target_id) + 1

        result.append({
            "pair_id": pair_id,
            "case_ids": case_ids,
            "status": "observed",
            "semantic_similarity": semantic,
            "load_l1_distance": sum(
                abs(left_load[name] - right_load[name]) for name in CHANNELS
            ),
            "directed_graph_equal": (
                directed_graph_fingerprint(left["analysis"]["candidate"])
                == directed_graph_fingerprint(right["analysis"]["candidate"])
            ),
            "left_to_right_rank": rank(left_id, right_id),
            "right_to_left_rank": rank(right_id, left_id),
        })
    return result


def _summarize(
    cases: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed = [row for row in observations if row["status"] == "observed"]
    errors = [row for row in observations if row["status"] == "parser_error"]
    families = {}
    for family in sorted({case["family"] for case in cases}):
        rows = [row for row in observations if row["family"] == family]
        good = [row for row in rows if row["status"] == "observed"]
        families[family] = {
            "cases": len(rows),
            "observed": len(good),
            "expectations_exact": sum(
                bool(row["score"]["expectations_exact"]) for row in good
            ),
            "expected_relations": sum(
                row["score"]["expected_relation_count"] for row in good
            ),
            "matched_relations": sum(
                row["score"]["matched_relation_count"] for row in good
            ),
            "expected_signals": sum(
                row["score"]["expected_signal_count"] for row in good
            ),
            "matched_signals": sum(
                row["score"]["matched_signal_count"] for row in good
            ),
            "reversed_relations": sum(
                len(row["score"]["reversed_relations"]) for row in good
            ),
            "unexpected_relations": sum(
                row["score"]["unexpected_relation_count"] for row in good
            ),
        }
    times = sorted(float(row["elapsed_seconds"]) for row in observations)
    pair_rows = [row for row in pairs if row["status"] == "observed"]
    return {
        "run_id": RUN_ID,
        "label": "LOCAL-CALIBRATION-NOT-A-GATE",
        "cases": len(cases),
        "local_candidate_attempts": len(cases),
        "provider_calls": 0,
        "observed": len(observed),
        "parser_errors": len(errors),
        "error_taxonomy": dict(sorted(Counter(
            row["error_code"] for row in errors
        ).items())),
        "expectations_exact": sum(
            bool(row["score"]["expectations_exact"]) for row in observed
        ),
        "chunk_expectations_met": sum(
            bool(row["chunk_expectation_met"]) for row in observed
        ),
        "load_shape_valid": sum(bool(row["load_shape_valid"]) for row in observed),
        "expected_relations": sum(
            row["score"]["expected_relation_count"] for row in observed
        ),
        "matched_relations": sum(
            row["score"]["matched_relation_count"] for row in observed
        ),
        "reversed_relations": sum(
            len(row["score"]["reversed_relations"]) for row in observed
        ),
        "unexpected_relations": sum(
            row["score"]["unexpected_relation_count"] for row in observed
        ),
        "expected_signals": sum(
            row["score"]["expected_signal_count"] for row in observed
        ),
        "matched_signals": sum(
            row["score"]["matched_signal_count"] for row in observed
        ),
        "elapsed_seconds": {
            "total": sum(times),
            "min": min(times),
            "median": times[len(times) // 2],
            "max": max(times),
        },
        "paraphrase_pairs_observed": len(pair_rows),
        "paraphrase_top1_both_directions": sum(
            row["left_to_right_rank"] == 1 and row["right_to_left_rank"] == 1
            for row in pair_rows
        ),
        "families": families,
    }


def _report(
    summary: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
) -> str:
    lines = [
        "# WP-31 local multi-vector calibration",
        "",
        "**LOCAL CALIBRATION — NOT A GATE. No G-gate verdict is issued or implied.**",
        "",
        "## Summary",
        "",
        f"- Cases/local candidate attempts: {summary['cases']}/{summary['local_candidate_attempts']}",
        f"- Observed/parser errors: {summary['observed']}/{summary['parser_errors']}",
        f"- Exact pre-registered expectations: {summary['expectations_exact']}/{summary['observed']}",
        f"- Expected relation matches: {summary['matched_relations']}/{summary['expected_relations']}",
        f"- Reversed/unexpected relations: {summary['reversed_relations']}/{summary['unexpected_relations']}",
        f"- Expected signal matches: {summary['matched_signals']}/{summary['expected_signals']}",
        f"- Chunk expectations: {summary['chunk_expectations_met']}/{summary['observed']}",
        f"- Valid 17-channel shapes: {summary['load_shape_valid']}/{summary['observed']}",
        f"- Provider/OAuth calls: {summary['provider_calls']}",
        "",
        "## Cases",
        "",
        "| Case | Family | Status | Chunks | Relations | Signals | Reversed | Unexpected | Seconds |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in observations:
        if row["status"] == "parser_error":
            lines.append(
                f"| {row['case_id']} | {row['family']} | parser_error:{row['error_code']} "
                f"| — | — | — | — | — | {row['elapsed_seconds']:.3f} |"
            )
            continue
        score = row["score"]
        lines.append(
            f"| {row['case_id']} | {row['family']} | observed "
            f"| {row['chunk_count']} | {score['matched_relation_count']}/{score['expected_relation_count']} "
            f"| {score['matched_signal_count']}/{score['expected_signal_count']} "
            f"| {len(score['reversed_relations'])} | {score['unexpected_relation_count']} "
            f"| {row['elapsed_seconds']:.3f} |"
        )
    lines.extend([
        "",
        "## Paraphrase pairs",
        "",
        "| Pair | Status | Semantic | 17D L1 | Graph equal | Ranks A→B/B→A |",
        "|---|---|---:|---:|---|---|",
    ])
    for row in pairs:
        if row["status"] != "observed":
            lines.append(f"| {row['pair_id']} | {row['status']} | — | — | — | — |")
        else:
            lines.append(
                f"| {row['pair_id']} | observed | "
                f"{row['semantic_similarity']['symmetric_score']:.6f} | "
                f"{row['load_l1_distance']:.6f} | {str(row['directed_graph_equal']).lower()} | "
                f"{row['left_to_right_rank']}/{row['right_to_left_rank']} |"
            )
    lines.extend([
        "",
        "The compact JSONL observation file contains the exact mismatches, evidence spans,",
        "17D values, hashes and timing for owner review. It deliberately contains no 384D",
        "vectors, model weights, runtime trees, databases or provider content.",
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
        "model_revisions": {
            "minilm": MINILM_REVISION,
            "gemma": GEMMA_REVISION,
        },
        "provider_calls": 0,
        "label": "LOCAL-CALIBRATION-NOT-A-GATE",
    }
    print(json.dumps(result, sort_keys=True))
    return result


def run(output: Path) -> dict[str, Any]:
    if os.environ.get("TOM_ASSIST_WP31_LOCAL") != "1":
        raise RuntimeError("set TOM_ASSIST_WP31_LOCAL=1 for the authorized local run")
    cases = expanded_cases()
    validate_case_contract(cases)
    revisions = _assert_run_pin()
    if output.exists():
        raise RuntimeError("WP-31 output directory already exists; never overwrite a run")
    output.mkdir(parents=True)
    observations_path = output / "observations.jsonl"
    observations = []
    private = {}
    client = StructureWorkerClient.from_environment()
    try:
        with observations_path.open("x", encoding="utf-8") as stream:
            for sequence, case in enumerate(cases, 1):
                started = time.monotonic()
                try:
                    worker_result = client.analyze(case["text"])
                    elapsed = time.monotonic() - started
                    observation, hidden = _observation(case, worker_result, elapsed)
                    private[case["case_id"]] = hidden
                except (StructureProviderError, ValueError, RuntimeError) as error:
                    elapsed = time.monotonic() - started
                    message = f"{type(error).__name__}: {str(error)[:500]}"
                    observation = {
                        "case_id": case["case_id"],
                        "family": case["family"],
                        "pair_id": case.get("pair_id"),
                        "status": "parser_error",
                        "elapsed_seconds": elapsed,
                        "source_sha256": sha256_bytes(case["text"].encode("utf-8")),
                        "source_chars": len(case["text"]),
                        "error_code": _error_code(message),
                        "error": message,
                    }
                observations.append(observation)
                stream.write(canonical_bytes(observation).decode("utf-8") + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                print(
                    json.dumps({
                        "sequence": sequence,
                        "total": len(cases),
                        "case_id": case["case_id"],
                        "status": observation["status"],
                        "elapsed_seconds": elapsed,
                    }, separators=(",", ":")),
                    flush=True,
                )
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
    report_path.write_text(_report(summary, observations, pairs), encoding="utf-8")
    artifacts = {
        path.name: _artifact(path)
        for path in (observations_path, pairs_path, summary_path, report_path)
    }
    manifest = {
        "run_version": RUN_VERSION,
        "run_id": RUN_ID,
        "label": "LOCAL-CALIBRATION-NOT-A-GATE",
        "completed": True,
        "code_sha": _git_sha(),
        "cases_sha256": cases_digest(cases),
        "cases_source_sha256": sha256_file(CASES_SOURCE),
        "runner_sha256": sha256_file(Path(__file__)),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "model_revisions": revisions,
        "provider_calls": 0,
        "local_candidate_attempts": len(cases),
        "artifacts": artifacts,
    }
    _write_json(output / "run_manifest.json", manifest)
    print(json.dumps(summary, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check":
        check()
    else:
        run(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
