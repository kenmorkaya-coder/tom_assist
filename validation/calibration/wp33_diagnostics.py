"""Zero-generation diagnostic for the preserved WP-33 calibration-v3 run."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.structural_analysis import CHANNELS
from validation.calibration.wp31_runner import canonical_bytes, sha256_file


DIAGNOSTIC_VERSION = "tom-assist-wp33-diagnostic/1.0"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def precise_error(message: str) -> str:
    if "invalid structured value" in message:
        return "invalid_structured_value"
    if "unsupported entity kind" in message:
        return "unsupported_entity_kind"
    if "unsupported vocabulary" in message:
        return "unsupported_relation_vocabulary"
    if "unknown entity" in message:
        return "unknown_relation_endpoint"
    if "fields mismatch" in message:
        return "missing_or_extra_schema_field"
    if "object is not iterable" in message:
        return "malformed_container_type"
    if "evidence quote" in message:
        return "invalid_evidence_binding"
    return "other_fail_closed"


def build_diagnostic(
    observations: Sequence[Mapping[str, Any]],
    wp32_observations: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    observed = [row for row in observations if row["status"] == "observed"]
    errors = [row for row in observations if row["status"] == "parser_error"]
    taxonomy: dict[str, list[str]] = defaultdict(list)
    for row in errors:
        taxonomy[precise_error(str(row["error"]))].append(str(row["case_id"]))
    prior_status = {row["case_id"]: row["status"] for row in wp32_observations}
    current_status = {row["case_id"]: row["status"] for row in observations[:80]}
    recovered = sorted(
        case_id for case_id, status in prior_status.items()
        if status != "observed" and current_status[case_id] == "observed"
    )
    regressed = sorted(
        case_id for case_id, status in prior_status.items()
        if status == "observed" and current_status[case_id] != "observed"
    )
    loads = {}
    for channel in CHANNELS:
        values = [float(row["load_signature"][channel]) for row in observed]
        loads[channel] = {
            "nonzero": sum(value > 0.0 for value in values),
            "observed": len(values),
            "min": min(values),
            "median": statistics.median(values),
            "max": max(values),
        }
    non_exact = [{
        "case_id": row["case_id"],
        "family": row["family"],
        "missing_relations": row["score"]["missing_relations"],
        "missing_signals": row["score"]["missing_signals"],
        "unexpected_relation_count": row["score"]["unexpected_relation_count"],
        "actual_relations": row["score"]["actual_relations"],
        "failed_history_checks": [
            check for check in row["history_checks"] if not check["met"]
        ],
    } for row in observed if not row["score"]["v3_exact"]]
    history = [{
        "case_id": row["case_id"],
        "all_bounds_met": row["history_checks_met"],
        "checks": row["history_checks"],
    } for row in observed if row["family"] == "history"]
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
        },
        "readiness_criteria": summary["readiness_criteria"],
        "ready_for_shadow_review": summary["ready_for_shadow_review"],
        "retained_comparison": {
            "wp32_observed": sum(row["status"] == "observed" for row in wp32_observations),
            "wp33_retained_observed": sum(row["status"] == "observed" for row in observations[:80]),
            "recovered_case_ids": recovered,
            "regressed_case_ids": regressed,
        },
        "error_taxonomy": {
            name: {"count": len(ids), "case_ids": sorted(ids)}
            for name, ids in sorted(taxonomy.items())
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
        "history_cases": history,
        "non_exact_observed_cases": non_exact,
        "load_channel_distribution": loads,
        "reporting_note": (
            "The frozen summary grouped 23 wrapped worker failures under the generic "
            "structureprovidererror label. This post-hoc taxonomy resolves only their "
            "preserved error strings and does not change any row or frozen score."
        ),
        "syntax_interpretation": (
            "Seventeen failures reached the deterministic fallback but still contained an "
            "invalid structured value. Raw generated text was intentionally not retained, "
            "so a narrower token-level repair cannot be justified from this run."
        ),
        "tree_claim_boundary": (
            "This calibration tested parsing, multi-vector compilation and 17D shape only. "
            "It did not advance or measure the Python 10K tree. Existing production tests "
            "separately enforce that only the verified Python msr_8d_native_10k lineage "
            "may consume these loads."
        ),
        "owner_conclusion": (
            "Do not enable shadow mode. V3 retained zero direction reversals and valid "
            "17D shapes, but regressed strict parsing and missed six of nine fixed "
            "readiness criteria."
        ),
    }


def _owner_review(diagnostic: Mapping[str, Any]) -> str:
    comparison = diagnostic["retained_comparison"]
    lines = [
        "# WP-33 owner review",
        "",
        "**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen v3 run is unchanged.**",
        "",
        "## Plain result",
        "",
        f"V3 parsed **{comparison['wp33_retained_observed']}/80** retained cases, compared with "
        f"**{comparison['wp32_observed']}/80** in v2. Across the full expanded corpus it parsed "
        "**70/94**. It is not ready for shadow mode.",
        "",
        "Direction did not reverse, and every accepted result had a valid bounded 17D shape. "
        "Those are necessary safety properties, but the parser still dropped too many passages "
        "and relations to be useful.",
        "",
        "## Frozen readiness matrix",
        "",
        "| Criterion | Value | Required | Met |",
        "|---|---:|---:|---|",
    ]
    for name, row in diagnostic["readiness_criteria"].items():
        lines.append(
            f"| `{name}` | {row['value']:.6f} | {row['threshold']:.6f} | {str(row['met']).lower()} |"
        )
    lines.extend(["", "## Fail-closed causes", ""])
    for name, row in diagnostic["error_taxonomy"].items():
        lines.append(f"- `{name}`: {row['count']} — {', '.join(row['case_ids'])}")
    lines.extend([
        "",
        "## What this means",
        "",
        f"- Recovered retained cases: {', '.join(comparison['recovered_case_ids']) or 'none'}.",
        f"- Regressed retained cases: {', '.join(comparison['regressed_case_ids']) or 'none'}.",
        "- The overlap correction worked on the earlier LP-03/LP-06 cases and the history family reached 8/8, but dense coordination and ordinary paraphrases remained fragile.",
        "- Seventeen failures still contained invalid structured values after syntax fallback. Because raw model output was not retained, adding another guessed repair would not be robust.",
        "- The parser remains inactive. The correct Python 10K tree wiring is separately guarded; this failed calibration is about producing reliable inputs for it, not the tree itself.",
        "",
        "## Recommended next decision",
        "",
        "Do not run v4 yet. First change the local model boundary so constrained structure is "
        "produced reliably—for example, a smaller staged extraction with one relation per bounded "
        "record or a grammar-constrained decoder—then pre-register a retained comparison. Do not "
        "keep adding post-hoc syntax guesses to malformed whole-passage tool calls.",
        "",
    ])
    return "\n".join(lines)


def write_diagnostic(run_dir: Path, wp32_dir: Path) -> dict[str, Any]:
    for name in ("DIAGNOSTIC.json", "OWNER_REVIEW.md", "diagnostic_manifest.json"):
        if (run_dir / name).exists():
            raise RuntimeError(f"refusing to overwrite {name}")
    observations_path = run_dir / "observations.jsonl"
    wp32_path = wp32_dir / "observations.jsonl"
    summary_path = run_dir / "summary.json"
    diagnostic = build_diagnostic(
        _read_jsonl(observations_path),
        _read_jsonl(wp32_path),
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
        "source_wp32_observations_sha256": sha256_file(wp32_path),
        "diagnostic_sha256": sha256_file(diagnostic_path),
        "owner_review_sha256": sha256_file(review_path),
    }
    manifest_path = run_dir / "diagnostic_manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest) + b"\n")
    print(json.dumps(manifest, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("wp32_dir", type=Path)
    args = parser.parse_args()
    write_diagnostic(args.run_dir.resolve(), args.wp32_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
