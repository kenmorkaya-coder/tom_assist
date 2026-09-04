"""Zero-generation forensic report for the preserved WP-32 calibration-v2 run."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.structural_analysis import CHANNELS
from validation.calibration.wp31_runner import canonical_bytes, sha256_file


DIAGNOSTIC_VERSION = "tom-assist-wp32-diagnostic/1.0"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _precise_error(message: str) -> str:
    if "JSONDecodeError" in message:
        return "invalid_tool_json"
    if "has no exact evidence quote" in message:
        return "missing_evidence_quote"
    if "unsupported entity kind" in message:
        return "unsupported_entity_kind"
    if "unbalanced braces" in message:
        return "unbalanced_tool_call"
    return "other_fail_closed"


def build_diagnostic(
    observations: Sequence[Mapping[str, Any]],
    wp31_observations: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    observed = [row for row in observations if row["status"] == "observed"]
    errors = [row for row in observations if row["status"] == "parser_error"]
    error_cases: dict[str, list[str]] = defaultdict(list)
    for row in errors:
        error_cases[_precise_error(str(row["error"]))].append(str(row["case_id"]))
    wp31_status = {row["case_id"]: row["status"] for row in wp31_observations}
    retained = {row["case_id"]: row["status"] for row in observations[:52]}
    fixed = sorted(
        case_id for case_id, status in wp31_status.items()
        if status != "observed" and retained[case_id] == "observed"
    )
    regressed = sorted(
        case_id for case_id, status in wp31_status.items()
        if status == "observed" and retained[case_id] != "observed"
    )
    load_distribution = {}
    for channel in CHANNELS:
        values = [float(row["load_signature"][channel]) for row in observed]
        load_distribution[channel] = {
            "nonzero": sum(value > 0 for value in values),
            "observed": len(values),
            "min": min(values),
            "median": statistics.median(values),
            "max": max(values),
        }
    history = []
    for row in observations:
        if row["family"] == "history" and row["status"] == "observed":
            history.append({
                "case_id": row["case_id"],
                "all_bounds_met": row["history_checks_met"],
                "checks": row["history_checks"],
            })
    unexpected = {
        row["case_id"]: row["score"]["actual_relations"]
        for row in observed if row["score"]["unexpected_relation_count"]
    }
    non_exact = [{
        "case_id": row["case_id"],
        "family": row["family"],
        "missing_relations": row["score"]["missing_relations"],
        "missing_signals": row["score"]["missing_signals"],
        "unexpected_relation_count": row["score"]["unexpected_relation_count"],
        "failed_history_checks": [
            check for check in row["history_checks"] if not check["met"]
        ],
    } for row in observed if not row["score"]["v2_exact"]]
    return {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "label": "POST-HOC-LOCAL-DIAGNOSTIC-NOT-A-GATE",
        "frozen_run_unchanged": True,
        "generations": 0,
        "provider_calls": 0,
        "accounting": {
            "cases": summary["cases"],
            "logical_passage_attempts": summary["logical_passage_attempts"],
            "local_chunk_model_attempts": summary["local_chunk_model_attempts"],
            "successful_chunk_model_calls": summary["successful_chunk_model_calls"],
            "parse_modes_on_success": summary["parse_modes"],
            "schema_projection_calls_on_success": summary["schema_projection_calls"],
        },
        "readiness_criteria": summary["readiness_criteria"],
        "ready_for_owner_freeze": summary["ready_for_owner_freeze"],
        "retained_comparison": {
            "wp31_observed": sum(row["status"] == "observed" for row in wp31_observations),
            "wp32_retained_observed": sum(
                row["status"] == "observed" for row in observations[:52]
            ),
            "fixed_case_ids": fixed,
            "regressed_case_ids": regressed,
        },
        "error_taxonomy": {
            name: {"count": len(case_ids), "case_ids": sorted(case_ids)}
            for name, case_ids in sorted(error_cases.items())
        },
        "direction": {
            "matched_expected_relations": summary["matched_relations"],
            "expected_relations_all_attempts": summary["expected_relations_all_attempts"],
            "reversed_relations": summary["reversed_relations"],
        },
        "signals": {
            "matched": summary["matched_signals"],
            "expected_all_attempts": summary["expected_signals_all_attempts"],
        },
        "unexpected_relations_by_case": unexpected,
        "non_exact_observed_cases": non_exact,
        "history_cases": history,
        "history_interpretation": (
            "Seven of eight history cases met every bound. HD-05 produced the "
            "mechanically correct four-turn suffix divided by the six-turn "
            "persistence denominator (4/6). Its preregistered minimum of 1.0 was "
            "a case-design error; the frozen miss remains a miss."
        ),
        "overlap_interpretation": (
            "LP-03 still emitted a duplicate because overlapping windows attached "
            "different entity-evidence granularity to the same Alpha/Beta endpoints. "
            "The punctuation relation merge therefore saw different global entity IDs."
        ),
        "syntax_interpretation": (
            "The deterministic syntax fallback recovered 26 successful chunk calls. "
            "Eight other calls still ended in JSON value errors and one in unbalanced "
            "braces. Raw generated text was deliberately not retained, so a narrower "
            "token-level cause cannot be claimed post hoc."
        ),
        "load_channel_distribution": load_distribution,
        "owner_conclusion": (
            "Do not activate or freeze the local parser. Version 2 materially improved "
            "the retained corpus and met signal, history, direction and load-shape "
            "criteria, but missed five of nine preregistered readiness criteria."
        ),
    }


def _owner_review(diagnostic: Mapping[str, Any]) -> str:
    criteria = diagnostic["readiness_criteria"]
    comparison = diagnostic["retained_comparison"]
    errors = diagnostic["error_taxonomy"]
    lines = [
        "# WP-32 owner review",
        "",
        "**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen v2 run is unchanged.**",
        "",
        "## Plain result",
        "",
        f"The parser improved the retained corpus from **{comparison['wp31_observed']}/52** "
        f"strict observations to **{comparison['wp32_retained_observed']}/52**, but the "
        "full v2 corpus produced only **67/80** strict observations. It is not ready "
        "to activate or freeze.",
        "",
        f"Direction remained coherent: **{diagnostic['direction']['matched_expected_relations']}/"
        f"{diagnostic['direction']['expected_relations_all_attempts']}** expected relations "
        f"survived end to end and there were **{diagnostic['direction']['reversed_relations']} "
        "reversals**. Signal recovery reached **17/21**. History bounds passed in "
        "**7/8** cases, and all 67 strict observations carried valid bounded 17D shapes.",
        "",
        "## Frozen readiness matrix",
        "",
        "| Criterion | Value | Required | Met |",
        "|---|---:|---:|---|",
    ]
    for name, row in criteria.items():
        lines.append(
            f"| `{name}` | {row['value']:.6f} | {row['threshold']:.6f} | "
            f"{str(row['met']).lower()} |"
        )
    lines.extend(["", "## Fail-closed taxonomy", ""])
    for name, row in errors.items():
        lines.append(f"- `{name}`: {row['count']} — {', '.join(row['case_ids'])}")
    lines.extend([
        "",
        "## What improved and what remains",
        "",
        f"- Previously failing cases recovered: {', '.join(comparison['fixed_case_ids'])}.",
        f"- Previously strict cases that regressed: {', '.join(comparison['regressed_case_ids'])}.",
        "- The syntax-only fallback successfully recovered 26 calls; eight JSON-value",
        "  errors and one unbalanced call remained. No raw generated text was retained.",
        "- LP-03 exposed a second overlap issue: the same endpoint labels were assigned",
        "  different evidence granularity, so relation deduplication saw different entity IDs.",
        "- HD-05's persistence result was mechanically correct at 4/6; its frozen 1.0",
        "  expectation was a preregistration mistake and remains scored as a miss.",
        "- Some 'unexpected' relations were plausible extra structure (SG-02, MR-05),",
        "  while MR-06, PB-05 and M2-03 added or transformed relations contrary to the",
        "  fixed ontology. The frozen unexpected-rate failure is therefore retained.",
        "",
        "## Recommended next version",
        "",
        "Retain v2. Before any new run, version the overlap entity merge, add safe binding",
        "from valid model-supplied offsets when a quote field is absent, and instrument",
        "syntax failure categories without retaining raw prose. Correct the HD-05 case",
        "bound explicitly as a preregistration amendment. Then freeze a v3 corpus and run",
        "only under fresh authorization. Do not activate the parser from this result.",
        "",
    ])
    return "\n".join(lines)


def write_diagnostic(run_dir: Path, wp31_dir: Path) -> dict[str, Any]:
    for name in ("DIAGNOSTIC.json", "OWNER_REVIEW.md", "diagnostic_manifest.json"):
        if (run_dir / name).exists():
            raise RuntimeError(f"refusing to overwrite {name}")
    observations_path = run_dir / "observations.jsonl"
    wp31_path = wp31_dir / "observations.jsonl"
    summary_path = run_dir / "summary.json"
    diagnostic = build_diagnostic(
        _read_jsonl(observations_path),
        _read_jsonl(wp31_path),
        json.loads(summary_path.read_text(encoding="utf-8")),
    )
    diagnostic_path = run_dir / "DIAGNOSTIC.json"
    diagnostic_path.write_bytes(canonical_bytes(diagnostic) + b"\n")
    review_path = run_dir / "OWNER_REVIEW.md"
    review_path.write_text(_owner_review(diagnostic), encoding="utf-8")
    manifest = {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "label": "POST-HOC-LOCAL-DIAGNOSTIC-NOT-A-GATE",
        "generations": 0,
        "provider_calls": 0,
        "source_observations_sha256": sha256_file(observations_path),
        "source_summary_sha256": sha256_file(summary_path),
        "source_wp31_observations_sha256": sha256_file(wp31_path),
        "diagnostic_sha256": sha256_file(diagnostic_path),
        "owner_review_sha256": sha256_file(review_path),
        "diagnostic_bytes": diagnostic_path.stat().st_size,
        "owner_review_bytes": review_path.stat().st_size,
    }
    manifest_path = run_dir / "diagnostic_manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest) + b"\n")
    print(json.dumps(manifest, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("wp31_dir", type=Path)
    args = parser.parse_args()
    write_diagnostic(args.run_dir.resolve(), args.wp31_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
