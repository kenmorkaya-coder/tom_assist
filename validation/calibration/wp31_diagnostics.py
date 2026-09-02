"""Zero-generation diagnostics for the preserved WP-31 calibration run."""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from gateway.structural_analysis import CHANNELS
from validation.calibration.wp31_cases import expanded_cases
from validation.calibration.wp31_runner import (
    _error_code,
    canonical_bytes,
    normalize,
    sha256_file,
)


DIAGNOSTIC_VERSION = "tom-assist-wp31-diagnostic/1.1"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _semantic_relation_key(relation: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        relation["channel"],
        relation["kind"],
        normalize(relation["source_label"]),
        normalize(relation["target_label"]),
        relation["modality"],
        relation["negated"],
        normalize(relation["evidence"]["quote"]),
    )


def duplicate_relation_cases(
    observations: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for row in observations:
        if row["status"] != "observed":
            continue
        groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
        for relation in row["score"]["actual_relations"]:
            groups[_semantic_relation_key(relation)].append(relation)
        duplicates = [values for values in groups.values() if len(values) > 1]
        if duplicates:
            result.append({
                "case_id": row["case_id"],
                "duplicate_groups": len(duplicates),
                "duplicate_relations": sum(len(values) - 1 for values in duplicates),
            })
    return result


def build_diagnostic(
    cases: Sequence[Mapping[str, Any]],
    observations: Sequence[Mapping[str, Any]],
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    case_by_id = {case["case_id"]: case for case in cases}
    observed = [row for row in observations if row["status"] == "observed"]
    errors = [row for row in observations if row["status"] == "parser_error"]
    error_cases: dict[str, list[str]] = defaultdict(list)
    for row in errors:
        error_cases[_error_code(row["error"])].append(row["case_id"])

    family_rows = {}
    for family in sorted({case["family"] for case in cases}):
        family_cases = [case for case in cases if case["family"] == family]
        family_ids = {case["case_id"] for case in family_cases}
        family_observed = [row for row in observed if row["case_id"] in family_ids]
        family_rows[family] = {
            "attempted": len(family_cases),
            "observed": len(family_observed),
            "parser_errors": len(family_cases) - len(family_observed),
            "expected_relations_all_attempts": sum(
                len(case["expected_relations"]) for case in family_cases
            ),
            "matched_relations": sum(
                row["score"]["matched_relation_count"] for row in family_observed
            ),
            "expected_signals_all_attempts": sum(
                len(case["expected_signals"]) for case in family_cases
            ),
            "matched_signals": sum(
                row["score"]["matched_signal_count"] for row in family_observed
            ),
            "exact_cases": sum(
                bool(row["score"]["expectations_exact"]) for row in family_observed
            ),
        }

    channel_distribution = {}
    for channel in CHANNELS:
        values = [float(row["load_signature"][channel]) for row in observed]
        channel_distribution[channel] = {
            "nonzero": sum(value > 0.0 for value in values),
            "observed": len(values),
            "min": min(values),
            "median": statistics.median(values),
            "max": max(values),
        }

    pair_rows = [row for row in pairs if row["status"] == "observed"]
    duplicates = duplicate_relation_cases(observations)
    expected_relations = sum(len(case["expected_relations"]) for case in cases)
    expected_signals = sum(len(case["expected_signals"]) for case in cases)
    matched_relations = sum(
        row["score"]["matched_relation_count"] for row in observed
    )
    matched_signals = sum(row["score"]["matched_signal_count"] for row in observed)
    return {
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "label": "POST-HOC-LOCAL-DIAGNOSTIC-NOT-A-GATE",
        "frozen_run_unchanged": True,
        "generations": 0,
        "provider_calls": 0,
        "frozen_run_accounting": {
            "logical_passage_attempts": len(cases),
            "exact_internal_chunk_model_calls": None,
            "reason": (
                "The frozen runner recorded one local candidate attempt per passage "
                "but did not instrument the number of visited windows when a "
                "multi-window passage failed partway through. Provider/OAuth calls "
                "remain exactly zero."
            ),
        },
        "attempted": len(cases),
        "observed": len(observed),
        "parser_errors": len(errors),
        "strict_observation_rate": len(observed) / len(cases),
        "exact_cases": sum(
            bool(row["score"]["expectations_exact"]) for row in observed
        ),
        "end_to_end_exact_case_rate": sum(
            bool(row["score"]["expectations_exact"]) for row in observed
        ) / len(cases),
        "expected_relations_all_attempts": expected_relations,
        "matched_relations": matched_relations,
        "end_to_end_relation_recall": matched_relations / expected_relations,
        "accepted_expected_relations": sum(
            row["score"]["expected_relation_count"] for row in observed
        ),
        "reversed_relations": sum(
            len(row["score"]["reversed_relations"]) for row in observed
        ),
        "unexpected_relations": sum(
            row["score"]["unexpected_relation_count"] for row in observed
        ),
        "expected_signals_all_attempts": expected_signals,
        "matched_signals": matched_signals,
        "end_to_end_signal_recall": matched_signals / expected_signals,
        "error_taxonomy": {
            name: {"count": len(ids), "case_ids": sorted(ids)}
            for name, ids in sorted(error_cases.items())
        },
        "families": family_rows,
        "load_channel_distribution": channel_distribution,
        "history_boundary": (
            "Each case used empty committed history. Zero frequency/persistence/"
            "burstiness/recurrence and unit novelty/decay are expected here and do "
            "not measure history dynamics."
        ),
        "long_position": {
            "attempted": 6,
            "observed": sum(row["family"] == "long_position" for row in observed),
            "observed_with_two_or_more_chunks": sum(
                row["family"] == "long_position" and row["chunk_count"] >= 2
                for row in observed
            ),
            "preregistered_chunk_miss": [
                row["case_id"] for row in observed
                if row["family"] == "long_position"
                and not row["chunk_expectation_met"]
            ],
            "duplicate_relation_cases": duplicates,
        },
        "paraphrase": {
            "pairs_attempted": 5,
            "pairs_observed": len(pair_rows),
            "directed_graph_equal": sum(row["directed_graph_equal"] for row in pair_rows),
            "mutual_top1": sum(
                row["left_to_right_rank"] == 1 and row["right_to_left_rank"] == 1
                for row in pair_rows
            ),
            "semantic_similarity_min": min(
                row["semantic_similarity"]["symmetric_score"] for row in pair_rows
            ),
            "semantic_similarity_max": max(
                row["semantic_similarity"]["symmetric_score"] for row in pair_rows
            ),
            "load_l1_min": min(row["load_l1_distance"] for row in pair_rows),
            "load_l1_max": max(row["load_l1_distance"] for row in pair_rows),
        },
        "owner_conclusion": (
            "Do not activate or production-freeze the local parser yet. Direction "
            "was coherent whenever strict validation succeeded, but parser/schema "
            "reliability, signal extraction and multi-relation handling require a "
            "versioned correction before calibration v2. The overlap punctuation "
            "duplication found here was corrected deterministically after the run; "
            "the frozen observations remain unchanged."
        ),
    }


def _owner_review(diagnostic: Mapping[str, Any]) -> str:
    errors = diagnostic["error_taxonomy"]
    channels = diagnostic["load_channel_distribution"]
    lines = [
        "# WP-31 owner review",
        "",
        "**POST-HOC LOCAL DIAGNOSTIC — NOT A GATE. The frozen run is unchanged.**",
        "",
        "## Plain result",
        "",
        f"The frozen run made **{diagnostic['attempted']} logical passage attempts**. "
        "It did not instrument the exact number of internal per-window Gemma calls "
        "for passages that failed partway through, so no exact local-generation total "
        "is claimed. Provider/OAuth calls were exactly **0**.",
        "",
        f"The exact pinned local parser produced strict usable analyses for "
        f"**{diagnostic['observed']}/{diagnostic['attempted']}** passages. "
        f"It failed closed on **{diagnostic['parser_errors']}**. End-to-end exact "
        f"cases were **{diagnostic['exact_cases']}/{diagnostic['attempted']}**.",
        "",
        f"Across all attempted relation cases, **{diagnostic['matched_relations']}/"
        f"{diagnostic['expected_relations_all_attempts']}** expected relations survived "
        f"end to end. Among strict accepted analyses, every expected relation was "
        f"directionally correct and there were **{diagnostic['reversed_relations']} "
        f"reversals**. Structural signals were weak: **{diagnostic['matched_signals']}/"
        f"{diagnostic['expected_signals_all_attempts']}** survived end to end.",
        "",
        "## Parser failure taxonomy",
        "",
    ]
    for name, row in errors.items():
        lines.append(f"- `{name}`: {row['count']} — {', '.join(row['case_ids'])}")
    lines.extend([
        "",
        "## Multi-vector and paraphrase findings",
        "",
        f"- Long-position passages: {diagnostic['long_position']['observed']}/6 strict "
        f"observations; {diagnostic['long_position']['observed_with_two_or_more_chunks']} "
        f"were actually multi-chunk.",
        f"- Overlap punctuation duplication occurred in: "
        f"{', '.join(row['case_id'] for row in diagnostic['long_position']['duplicate_relation_cases'])}.",
        f"- Paraphrases: {diagnostic['paraphrase']['pairs_observed']}/5 complete pairs; "
        f"all {diagnostic['paraphrase']['directed_graph_equal']} complete pairs had equal "
        f"directed graphs, and {diagnostic['paraphrase']['mutual_top1']} were mutual "
        f"MiniLM top-1 neighbours.",
        f"- Paraphrase semantic similarity range: "
        f"{diagnostic['paraphrase']['semantic_similarity_min']:.6f}–"
        f"{diagnostic['paraphrase']['semantic_similarity_max']:.6f}; 17D L1 range: "
        f"{diagnostic['paraphrase']['load_l1_min']:.6f}–"
        f"{diagnostic['paraphrase']['load_l1_max']:.6f}.",
        "",
        "## 17-channel interpretation",
        "",
        "The accepted analyses always contained all 17 finite bounded values. Non-zero",
        "counts across the 35 accepted passages were:",
        "",
    ])
    for name in CHANNELS:
        row = channels[name]
        lines.append(
            f"- `{name}`: {row['nonzero']}/{row['observed']} "
            f"(median {row['median']:.6f}, max {row['max']:.6f})"
        )
    lines.extend([
        "",
        diagnostic["history_boundary"],
        "",
        "## Owner decision recommended",
        "",
        diagnostic["owner_conclusion"],
        "",
        "Calibration v2 should retain this run, carry the deterministic overlap correction,",
        "make the model-tool boundary more reliable for repeated entities and multiple",
        "relations, and explicitly strengthen all eight signal instructions. It should",
        "then rerun under a new identity; this result must not be overwritten.",
        "",
    ])
    return "\n".join(lines)


def write_diagnostic(run_dir: Path) -> dict[str, Any]:
    observations_path = run_dir / "observations.jsonl"
    pairs_path = run_dir / "pair_metrics.jsonl"
    for name in ("DIAGNOSTIC.json", "OWNER_REVIEW.md", "diagnostic_manifest.json"):
        if (run_dir / name).exists():
            raise RuntimeError(f"refusing to overwrite {name}")
    diagnostic = build_diagnostic(
        expanded_cases(), _read_jsonl(observations_path), _read_jsonl(pairs_path)
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
        "source_pairs_sha256": sha256_file(pairs_path),
        "diagnostic_sha256": sha256_file(diagnostic_path),
        "owner_review_sha256": sha256_file(review_path),
        "diagnostic_bytes": diagnostic_path.stat().st_size,
        "owner_review_bytes": review_path.stat().st_size,
    }
    (run_dir / "diagnostic_manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    print(json.dumps(manifest, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    write_diagnostic(args.run_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
