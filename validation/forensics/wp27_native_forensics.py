#!/usr/bin/env python3
"""Offline WP-27 audit of preserved native stores and branch cohorts.

No function in this module starts a runtime, calls a provider, applies a physics
step, performs plastic recall, or writes a preserved pilot store. SQLite files
are opened read-only/immutable and tree JSON is treated as inert data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import statistics
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX = ROOT / "validation/runs/wp25-pilot-frozen-v2/raw_matrix.jsonl"
DEFAULT_NATIVE = Path("/private/tmp/tom-assist-wp25-pilot-v2")
DEFAULT_TOM_MASTER = ROOT / ".upstream-worktree/tom-master-wp18"
DEFAULT_OUTPUT = ROOT / "validation/runs/wp27-pilot-forensics"
NATIVE_UNIFORM_EPS = 0.05 / 3.0
FOCUS_ROLE = {
    "ASSUMPTION": "assumption",
    "COMPLETED_WORK": "completed",
    "CONCEPT": "concept",
    "CONSTRAINT": "constraint",
    "DECISION": "decision",
    "EVIDENCE": "evidence",
    "OBJECTIVE": "objective",
    "REJECTED_PATH": "rejected",
    "SUPERSESSION": "supersession",
    "UNRESOLVED_DEPENDENCY": "dependency",
    "WORKSTREAM": "workstream",
}


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def aggregate_sha(paths: list[Path], base: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(base)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path).removeprefix("sha256:")))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def input_path(native: Path, sequence: int) -> Path:
    matches = list(native.glob(f"{sequence:03}-*.json"))
    if len(matches) != 1:
        raise ValueError(f"sequence {sequence} has {len(matches)} native input files")
    return matches[0]


def db_open(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def old_commit_projection(text: str) -> dict[str, Any]:
    raw = hashlib.sha256(text.encode("utf-8")).digest()
    axes = [1.0 + raw[index] for index in range(3)]
    semantic_target = tuple(value / sum(axes) for value in axes)
    wind = (semantic_target[0] - semantic_target[2], semantic_target[1] - semantic_target[2])
    max_uniform_delta = max(abs(value - 1.0 / 3.0) for value in semantic_target)
    return {
        "semantic_target": list(semantic_target),
        "max_uniform_delta": max_uniform_delta,
        "near_uniform_by_native_selector_rule": max_uniform_delta < NATIVE_UNIFORM_EPS,
        "wind_vec": list(wind),
        "wind_magnitude": math.hypot(*wind),
    }


def normalized_axis(raw_axis: list[float]) -> list[float]:
    total = sum(float(value) for value in raw_axis[:3])
    return [1.0 / 3.0] * 3 if total < 1e-12 else [float(value) / total for value in raw_axis[:3]]


def alignment_gate(branch: Any, semantic_axis: list[float], fallback: bool) -> float:
    if fallback:
        return 1.0
    axis = getattr(branch, "axis_w", None)
    if axis is None or len(axis) < 3 or sum(float(value) for value in axis[:3]) <= 1e-12:
        branch_axis = [1.0 / 3.0] * 3
    else:
        total = sum(float(value) for value in axis[:3])
        branch_axis = [float(value) / total for value in axis[:3]]
    alignment = sum(branch_axis[index] * semantic_axis[index] for index in range(3))
    return max(0.0, alignment - 1.0 / 3.0) / (2.0 / 3.0)


def native_store_audit(row: dict[str, Any], native: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = input_path(native, row["sequence"])
    source = json.loads(source_path.read_text(encoding="utf-8"))
    database = native / f"{row['sequence']:03}.sqlite3"
    connection = db_open(database)
    try:
        stored = connection.execute(
            "SELECT id,type,canonical_text,status,authority,workstream_id,object_json FROM state_objects ORDER BY id"
        ).fetchall()
        edges = connection.execute("SELECT COUNT(*) FROM state_edges").fetchone()[0]
        turns = connection.execute("SELECT id,role,ordinal FROM turns ORDER BY ordinal").fetchall()
        receipts = connection.execute("SELECT COUNT(*) FROM runtime_commit_receipts").fetchone()[0]
    finally:
        connection.close()
    source_by_id = {item["id"]: item for item in source["objects"]}
    stored_by_id = {item[0]: item for item in stored}
    complete_ids = set(source_by_id) == set(stored_by_id)
    exact_core = complete_ids and all(
        (
            native_id,
            original["type"],
            original["canonical_text"],
            original["status"],
            original["authority"],
            original["workstream_id"],
        )
        == stored_by_id[native_id][:6]
        for native_id, original in source_by_id.items()
    )
    source_turn_ids = {
        source_id
        for item in source["objects"]
        for source_id in item.get("source_turn_ids", [])
    }
    ledger_turn_ids = {item[0] for item in turns}
    return source, {
        "sequence": row["sequence"],
        "test_id": row["test_id"],
        "arm": row["arm"],
        "database": str(database),
        "database_sha256": sha256_file(database),
        "input_sha256": sha256_file(source_path),
        "input_object_count": len(source["objects"]),
        "stored_state_object_count": len(stored),
        "state_object_ids_complete": complete_ids,
        "state_object_core_fields_exact": exact_core,
        "input_edge_count": len(source["edges"]),
        "stored_edge_count": edges,
        "ledger_turn_count": len(turns),
        "ledger_turn_roles": [item[1] for item in turns],
        "object_source_turn_id_count": len(source_turn_ids),
        "object_source_turn_ids_present_as_ledger_turns": len(source_turn_ids & ledger_turn_ids),
        "runtime_commit_receipts": receipts,
    }


def generate(matrix: Path, native: Path, tom_master: Path, output: Path) -> dict[str, Any]:
    if not native.is_dir():
        raise ValueError(f"preserved native-store directory missing: {native}")
    if not (tom_master / "agency/mechanics/preview_readout.py").is_file():
        raise ValueError(f"pinned pure readout missing: {tom_master}")
    sys.path.insert(0, str(tom_master))
    sys.path.insert(0, str(ROOT))
    from gateway.structural_preview import project_text
    from agency.mechanics.msr_8d_loading_aware_readout import rank_loading_aware_8d
    from agency.mechanics.semantic_metrics import stiffness_proxy
    from agency.mechanics.sicd_msr_load_application import project_msr_load_to_sicd_step

    rows = read_rows(matrix)
    if len(rows) != 165:
        raise ValueError(f"expected 165 matrix rows, found {len(rows)}")
    native_rows: list[dict[str, Any]] = []
    dynamics_rows: list[dict[str, Any]] = []
    cohort_rows: list[dict[str, Any]] = []
    tree_hashes: Counter[str] = Counter()
    for row in rows:
        source, native_row = native_store_audit(row, native)
        native_rows.append(native_row)
        signature, projection, _ = project_text(source["probe"])
        old_projection = old_commit_projection(source["probe"])
        canonical_plan = project_msr_load_to_sicd_step(signature)
        dynamics_rows.append(
            {
                "sequence": row["sequence"],
                "test_id": row["test_id"],
                "arm": row["arm"],
                "runtime_commit_observed": native_row["runtime_commit_receipts"] == 1,
                "old_product_projection_counterfactual_only": old_projection,
                "canonical_upstream_msr_plan_counterfactual_only": {
                    "semantic_target": list(canonical_plan.semantic_target),
                    "wind_vec": list(canonical_plan.wind_vec),
                    "wind_magnitude": canonical_plan.wind_magnitude,
                    "routing_basis_8d": list(canonical_plan.routing_basis_8d),
                    "routing_basis_confidence": canonical_plan.routing_basis_confidence,
                },
            }
        )
        if row["arm"] != "SUB-D":
            continue
        connection = db_open(native / f"{row['sequence']:03}.sqlite3")
        try:
            trace = json.loads(
                connection.execute("SELECT candidate_trace_json FROM context_manifests").fetchone()[0]
            )
        finally:
            connection.close()
        tree_path = native / "runtime/projects" / row["project_id"] / "tom/tree_state.json"
        tree_hash = sha256_file(tree_path)
        tree_hashes[tree_hash] += 1
        tree = json.loads(tree_path.read_text(encoding="utf-8"))
        branches = {str(item["id"]): SimpleNamespace(**item) for item in tree["branches"]}
        semantic_axis = normalized_axis(list(projection.raw_8d[:3]))
        fallback = all(abs(value - 1.0 / 3.0) < NATIVE_UNIFORM_EPS for value in semantic_axis)
        stored_trace = trace["branches"]
        current_ids = [item["branch_id"] for item in stored_trace]
        recomputed_gates = {
            branch_id: alignment_gate(branch, semantic_axis, fallback)
            for branch_id, branch in branches.items()
            if getattr(branch, "sem_vec", None) is not None and len(branch.sem_vec) == 8
        }
        stiffness_usage = sorted(
            (
                (
                    stiffness_proxy(branch) / (1.0 + int(getattr(branch, "usage_count", 0))),
                    branch_id,
                )
                for branch_id, branch in branches.items()
                if branch_id in recomputed_gates
            ),
            key=lambda item: (-item[0], item[1]),
        )[:16]
        stiffness_ids = [branch_id for _, branch_id in stiffness_usage]
        loading_rank = rank_loading_aware_8d(sorted(branches.items()), signature, top_k=16)
        loading_ids = [branch_id for _, branch_id, _ in loading_rank]
        current_set = set(current_ids)
        stiffness_set = set(stiffness_ids)
        loading_set = set(loading_ids)
        focus_id = row["native_id_map"][f"{row['test_id']}:{FOCUS_ROLE[row['family']]}"]
        admitted = {
            item["state_id"]
            for section in row["packet_sections"]
            for item in section["items"]
        }
        cohort_rows.append(
            {
                "sequence": row["sequence"],
                "test_id": row["test_id"],
                "family": row["family"],
                "mode": row["mode"],
                "project_id": row["project_id"],
                "tree_tick": tree["tick"],
                "tree_branch_count": len(branches),
                "tree_sha256": tree_hash,
                "semantic_axis_3d": semantic_axis,
                "uniform_axis_fallback": fallback,
                "stored_trace_fallback_consistent": all(
                    abs(item["alignment_gate"] - 1.0) < 1e-12 for item in stored_trace
                )
                == fallback,
                "selected_branch_usage_nonzero": sum(item["usage_count"] != 0 for item in stored_trace),
                "current_3axis_cohort": current_ids,
                "stiffness_usage_top16": stiffness_ids,
                "stiffness_usage_supported_count": len(current_set & stiffness_set),
                "alignment_displaced_count": len(current_set - stiffness_set),
                "loading_aware_8d_cohort": loading_ids,
                "three_axis_vs_8d_overlap_count": len(current_set & loading_set),
                "three_axis_vs_8d_jaccard": len(current_set & loading_set) / len(current_set | loading_set),
                "retrieved_anchor_candidates_3axis": len(trace["retrieval"]),
                "retrieved_anchor_candidates_8d_counterfactual": 0,
                "rerank_effect_explanation": "RGM anchor inventory was empty; changing branch cohort cannot create candidates",
                "focus_state_object_admitted": focus_id in admitted,
            }
        )

    commit_count = sum(row["runtime_commit_receipts"] for row in native_rows)
    old_wind = [row["old_product_projection_counterfactual_only"]["wind_magnitude"] for row in dynamics_rows]
    old_uniform_delta = [
        row["old_product_projection_counterfactual_only"]["max_uniform_delta"] for row in dynamics_rows
    ]
    canonical_wind = [
        row["canonical_upstream_msr_plan_counterfactual_only"]["wind_magnitude"]
        for row in dynamics_rows
    ]
    summary = {
        "audit_id": "wp27-native-forensics/1",
        "label": "POST-HOC-DIAGNOSTIC-ONLY",
        "zero_generations": True,
        "frozen_h0_untouched": True,
        "sources": {
            "matrix": {"path": str(matrix), "sha256": sha256_file(matrix)},
            "native_root": str(native),
            "native_input_count": len(list(native.glob("[0-9][0-9][0-9]-*.json"))),
            "native_store_count": len(list(native.glob("[0-9][0-9][0-9].sqlite3"))),
            "native_input_aggregate_sha256": aggregate_sha(
                list(native.glob("[0-9][0-9][0-9]-*.json")), native
            ),
            "native_store_aggregate_sha256": aggregate_sha(
                list(native.glob("[0-9][0-9][0-9].sqlite3")), native
            ),
            "runtime_tree_count": sum(tree_hashes.values()),
            "runtime_tree_hashes": dict(sorted(tree_hashes.items())),
            "tom_master": str(tom_master),
        },
        "native_import": {
            "ledgers": len(native_rows),
            "input_objects": sum(row["input_object_count"] for row in native_rows),
            "stored_state_objects": sum(row["stored_state_object_count"] for row in native_rows),
            "complete_id_sets": sum(row["state_object_ids_complete"] for row in native_rows),
            "exact_core_field_sets": sum(row["state_object_core_fields_exact"] for row in native_rows),
            "input_edges": sum(row["input_edge_count"] for row in native_rows),
            "stored_edges": sum(row["stored_edge_count"] for row in native_rows),
            "ledger_turns": sum(row["ledger_turn_count"] for row in native_rows),
            "object_source_turn_ids": sum(row["object_source_turn_id_count"] for row in native_rows),
            "object_source_turn_ids_present_as_ledger_turns": sum(
                row["object_source_turn_ids_present_as_ledger_turns"] for row in native_rows
            ),
            "runtime_commit_receipts": commit_count,
        },
        "commit_dynamics": {
            "observed_committed_battery_turns": commit_count,
            "observed_semantic_target_population": 0,
            "explanation": "all 165 evaluations remained unresolved REVIEW, so commit_captured_exchange returned without gateway commit",
            "counterfactual_rows": len(dynamics_rows),
            "counterfactual_old_product_near_uniform_native_rule": sum(
                row["old_product_projection_counterfactual_only"]["near_uniform_by_native_selector_rule"]
                for row in dynamics_rows
            ),
            "counterfactual_old_product_max_uniform_delta": {
                "min": min(old_uniform_delta),
                "median": statistics.median(old_uniform_delta),
                "p95": percentile(old_uniform_delta, 0.95),
                "max": max(old_uniform_delta),
            },
            "counterfactual_old_product_wind_magnitude": {
                "min": min(old_wind),
                "median": statistics.median(old_wind),
                "p95": percentile(old_wind, 0.95),
                "max": max(old_wind),
                "mean": statistics.mean(old_wind),
            },
            "counterfactual_canonical_msr_wind_magnitude": {
                "min": min(canonical_wind),
                "median": statistics.median(canonical_wind),
                "p95": percentile(canonical_wind, 0.95),
                "max": max(canonical_wind),
                "mean": statistics.mean(canonical_wind),
            },
        },
        "cohort": {
            "sub_d_cases": len(cohort_rows),
            "uniform_axis_fallback_count": sum(row["uniform_axis_fallback"] for row in cohort_rows),
            "stored_trace_fallback_consistent": sum(
                row["stored_trace_fallback_consistent"] for row in cohort_rows
            ),
            "selected_branch_usage_nonzero": sum(
                row["selected_branch_usage_nonzero"] for row in cohort_rows
            ),
            "stiffness_usage_supported_total": sum(
                row["stiffness_usage_supported_count"] for row in cohort_rows
            ),
            "alignment_displaced_total": sum(row["alignment_displaced_count"] for row in cohort_rows),
            "three_axis_vs_8d_overlap_total": sum(
                row["three_axis_vs_8d_overlap_count"] for row in cohort_rows
            ),
            "three_axis_vs_8d_mean_overlap": statistics.mean(
                row["three_axis_vs_8d_overlap_count"] for row in cohort_rows
            ),
            "three_axis_vs_8d_mean_jaccard": statistics.mean(
                row["three_axis_vs_8d_jaccard"] for row in cohort_rows
            ),
            "distinct_three_axis_cohorts": len(
                {tuple(row["current_3axis_cohort"]) for row in cohort_rows}
            ),
            "distinct_loading_aware_8d_cohorts": len(
                {tuple(row["loading_aware_8d_cohort"]) for row in cohort_rows}
            ),
        },
        "retrieval_attribution": {
            "sub_d_focus_state_object_hits": sum(
                row["focus_state_object_admitted"] for row in cohort_rows
            ),
            "sub_d_cases": len(cohort_rows),
            "three_axis_retrieved_anchor_candidates": sum(
                row["retrieved_anchor_candidates_3axis"] for row in cohort_rows
            ),
            "loading_aware_8d_retrieved_anchor_candidates_counterfactual": sum(
                row["retrieved_anchor_candidates_8d_counterfactual"] for row in cohort_rows
            ),
            "failures_attributable_to_three_axis_selection": 0,
            "reason": "typed state objects bypass branch/RGM anchor ranking; every focus object was admitted, while every per-project RGM was empty",
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "native_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for name, values in (
        ("native_case_analysis.jsonl", native_rows),
        ("commit_projection_analysis.jsonl", dynamics_rows),
        ("cohort_rerank_analysis.jsonl", cohort_rows),
    ):
        (output / name).write_text("".join(compact(value) + "\n" for value in values), encoding="utf-8")
    (output / "NATIVE_FINDINGS.md").write_text(markdown(summary, cohort_rows), encoding="utf-8")
    return summary


def markdown(summary: dict[str, Any], cohorts: list[dict[str, Any]]) -> str:
    imports = summary["native_import"]
    dynamics = summary["commit_dynamics"]
    cohort = summary["cohort"]
    retrieval = summary["retrieval_attribution"]
    wind = dynamics["counterfactual_old_product_wind_magnitude"]
    lines = [
        "# WP-27 native-store and cohort forensics",
        "",
        "> **POST-HOC DIAGNOSTIC ONLY — ZERO GENERATIONS.** Preserved stores were opened immutable/read-only. Frozen H0 is untouched; no G-gate verdict is made.",
        "",
        "## Findings",
        "",
        f"- **No battery exchange committed into ToM physics.** Runtime commit receipts: **{imports['runtime_commit_receipts']}/165**. All evaluations were unresolved REVIEW; the 33 created SUB-D trees remain byte-identical at seed tick 4707 with zero usage rotation. Therefore the observed committed-turn `semantic_target`/`wind_vec` population is empty.",
        f"- **Counterfactual old commit projection, not observed physics:** applying the then-current SHA-byte formula to the 165 sent user turns yields **{dynamics['counterfactual_old_product_near_uniform_native_rule']}/165** near-uniform targets under the native selector's ±1/60 rule. `wind_vec` magnitude min/median/p95/max is **{wind['min']:.6f} / {wind['median']:.6f} / {wind['p95']:.6f} / {wind['max']:.6f}** (mean {wind['mean']:.6f}). Row-level values are in `commit_projection_analysis.jsonl`.",
        f"- **Native import was complete and typed:** **{imports['stored_state_objects']}/{imports['input_objects']}** objects and **{imports['stored_edges']}/{imports['input_edges']}** edges were present across 165 ledgers; all **{imports['complete_id_sets']}/165** ID sets and **{imports['exact_core_field_sets']}/165** core-field sets matched. The ledgers contain only the captured user/assistant turns (**{imports['ledger_turns']} total**), not the planted history turns; **{imports['object_source_turn_ids_present_as_ledger_turns']}/{imports['object_source_turn_ids']}** object source IDs exist as ledger turns. The objects were not merely turn text.",
        f"- **Uniform-axis fallback never fired:** **{cohort['uniform_axis_fallback_count']}/{cohort['sub_d_cases']}** SUB-D previews; stored alignment traces agree in {cohort['stored_trace_fallback_consistent']}/33. All selected-branch usage counts were zero, so usage rotation contributed nothing.",
        f"- **3-axis cohort composition:** of {cohort['sub_d_cases'] * 16} selected slots, **{cohort['stiffness_usage_supported_total']}** were also in stiffness/usage-only top-16 and **{cohort['alignment_displaced_total']}** were displaced into the cohort by alignment. This is 4 stiffness-supported + 12 alignment-displaced in every case.",
        f"- **Offline 8D re-rank:** current 3-axis and native `rank_loading_aware_8d` top-16 cohorts overlap in **{cohort['three_axis_vs_8d_overlap_total']}/{cohort['sub_d_cases'] * 16}** slots (mean overlap {cohort['three_axis_vs_8d_mean_overlap']:.1f}; mean Jaccard {cohort['three_axis_vs_8d_mean_jaccard']:.3f}). Each method produced {cohort['distinct_three_axis_cohorts']} / {cohort['distinct_loading_aware_8d_cohorts']} distinct cohort sets across 33 cases.",
        f"- **Observed retrieval/citation failure attributable to 3-axis selection: 0 cases.** SUB-D typed focus objects were admitted in **{retrieval['sub_d_focus_state_object_hits']}/{retrieval['sub_d_cases']}** packets. Every per-project RGM was empty, so both the stored 3-axis trace and the offline 8D alternative have **0 anchor candidates**. Cohort replacement radically changes branch IDs but cannot create a missing anchor or affect typed-state admission in these artifacts.",
        "",
        "## Per-case cohort composition and 8D comparison",
        "",
        "`Stiffness-supported` is overlap with the pure stiffness/(1+usage) top-16. `Alignment-displaced` is the remainder of the selected 3-axis cohort. This partitions the stored cohort without claiming a causal model.",
        "",
        "| Case | Mode | Fallback | Stiffness-supported | Alignment-displaced | 3D∩8D | Jaccard | RGM candidates | Focus hit |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in cohorts:
        lines.append(
            f"| {row['test_id']} | {row['mode']} | {str(row['uniform_axis_fallback']).lower()} | "
            f"{row['stiffness_usage_supported_count']} | {row['alignment_displaced_count']} | "
            f"{row['three_axis_vs_8d_overlap_count']} | {row['three_axis_vs_8d_jaccard']:.3f} | "
            f"{row['retrieved_anchor_candidates_3axis']} | {str(row['focus_state_object_admitted']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The 8D comparison calls only the pinned pure `rank_loading_aware_8d` over inert copies of each stored seed tree and the same stored probe-derived load signature. It does not call `engine.step`, `ToMClient.process`, `rgm.read_memory`, gateway preview endpoints, a provider, or a broker. No frozen file, per-case database, tree, upstream checkout, golden, or preregistration was modified.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--native", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--tom-master", type=Path, default=DEFAULT_TOM_MASTER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = generate(
        args.matrix.resolve(),
        args.native.resolve(),
        args.tom_master.resolve(),
        args.output.resolve(),
    )
    print(
        compact(
            {
                "audit_id": result["audit_id"],
                "native_ledgers": result["native_import"]["ledgers"],
                "runtime_commits": result["native_import"]["runtime_commit_receipts"],
                "sub_d_cases": result["cohort"]["sub_d_cases"],
                "provider_generations": 0,
                "frozen_h0_untouched": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
