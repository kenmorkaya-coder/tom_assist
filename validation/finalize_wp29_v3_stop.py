#!/usr/bin/env python3
"""Finalize the permanent WP-29 pilot-v3 timeout record without any generation."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from validation.draft_cases import FAMILIES
from validation.production_runner import (
    ARMS,
    atomic_json,
    cluster_bootstrap,
    rates,
    report,
    sha256_file,
    substrate_engagement,
)


def incomplete_hypotheses(rows: list[dict]) -> dict:
    long_rows = [row for row in rows if row["mode"] != "no_rot"]
    family_rates = {
        family: rates([row for row in long_rows if row["family"] == family])
        for family in FAMILIES
    }
    unavailable = {
        "complete_matrix": False,
        "sub_d_minus_sub_a_at_least_0.15": None,
        "sub_d_minus_sub_b_at_least_0.15": None,
        "sub_d_vs_sub_a_ci_excludes_zero_positive": None,
        "sub_d_vs_sub_b_ci_excludes_zero_positive": None,
        "sub_d_at_least_0.80_every_family": None,
    }
    secondary = {
        "H2.1_no_rot_rate_within_0.05_of_A": None,
        "H2.1_zero_gratuitous_injections": None,
        "H2.2_long_D_within_0.05_of_C": None,
        "H2.3_D_exceeds_E_by_0.10_or_containment": None,
        "H2.4_supersession_D_at_least_0.80": None,
    }
    h3_rows = [row for row in rows if row.get("new_failure_mode")]
    return {
        "macro_long_rates": {arm: None for arm in ARMS},
        "family_long_rates": family_rates,
        "paired_differences": {"SUB-D_minus_SUB-A": None, "SUB-D_minus_SUB-B": None},
        "cluster_bootstrap": {
            "SUB-A": cluster_bootstrap(rows, "SUB-A"),
            "SUB-B": cluster_bootstrap(rows, "SUB-B"),
        },
        "H1": {"outcome": "INVALID_INCOMPLETE", "components": unavailable},
        "H0": {
            "outcome": "UNRESOLVED_INCOMPLETE",
            "criterion": "one or more frozen H1 primary components does not hold",
        },
        "H2": {"outcome": "UNRESOLVED_INCOMPLETE", "components": secondary},
        "H3": {
            "outcome": "OBSERVED_STOP_REQUIRED" if h3_rows else "NOT_OBSERVED",
            "rows": [row["sequence"] for row in h3_rows],
        },
    }


def finalize(output: Path, database: Path, runtime_receipts: Path, driver_input: Path) -> dict:
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (output / "raw_matrix.jsonl").read_text().splitlines() if line]
    claims = [json.loads(line) for line in (output / "claims.jsonl").read_text().splitlines() if line]
    if manifest.get("completed") is not False or len(rows) != 5 or len(claims) != 6:
        raise ValueError("unexpected stopped-run shape; refusing report repair")
    if manifest.get("last_completed_sequence") != 5 or claims[-1]["sequence"] != 6:
        raise ValueError("unexpected stop boundary")

    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    history_turns = connection.execute(
        "SELECT COUNT(*) FROM turns WHERE packet_digest='battery-history-import/1'"
    ).fetchone()[0]
    assistant_turns = connection.execute(
        "SELECT COUNT(*) FROM turns WHERE packet_digest='battery-history-import/1' AND role='assistant'"
    ).fetchone()[0]
    sent_contexts = connection.execute("SELECT COUNT(*) FROM sent_contexts").fetchone()[0]
    response_turns = connection.execute(
        "SELECT COUNT(*) FROM turns WHERE packet_digest!='battery-history-import/1' AND role='assistant'"
    ).fetchone()[0]
    connection.close()
    receipts = json.loads(runtime_receipts.read_text(encoding="utf-8"))
    if history_turns != 144 or assistant_turns != 58 or sent_contexts != 1 or response_turns != 0:
        raise ValueError("stopped observation ledger boundary differs from the preserved evidence")
    if len(receipts) != history_turns:
        raise ValueError("stopped observation receipt inventory is incomplete")
    ordered = sorted(receipts.values(), key=lambda row: row["engine_tick_before"])
    dynamics = ["step", "rgm_write", "leaf_vec_teach", "usage_rotation", "front_row_reseat"]
    if not all(row["commit_dynamics"] == dynamics for row in ordered):
        raise ValueError("stopped observation lacks a five-dynamics receipt")
    if not all(
        row["commit_drive"]["applied"]
        and len(row["commit_drive"]["plan"]["load_signature_17"]) == 17
        and len(row["commit_drive"]["plan"]["routing_basis_8d"]) == 8
        for row in ordered
    ):
        raise ValueError("stopped observation lacks canonical load telemetry")
    if sum(row["taught"] for row in ordered) != assistant_turns:
        raise ValueError("stopped observation assistant teaching tripwire failed")

    combined = substrate_engagement(rows)
    combined.update({
        "rows_observed": combined["rows_observed"] + 1,
        "rows_fully_engaged": combined["rows_fully_engaged"] + 1,
        "all_rows_fully_engaged": True,
        "history_turns": combined["history_turns"] + history_turns,
        "five_dynamics_receipts": combined["five_dynamics_receipts"] + history_turns,
        "canonical_17_channel_applications": combined["canonical_17_channel_applications"] + history_turns,
        "routing_basis_8d_applications": combined["routing_basis_8d_applications"] + history_turns,
        "assistant_turns": combined["assistant_turns"] + assistant_turns,
        "assistant_teaches": combined["assistant_teaches"] + assistant_turns,
        "tick_delta": combined["tick_delta"] + history_turns,
        "checkpoint_changed_rows": combined["checkpoint_changed_rows"] + 1,
        "captured_rows": len(rows),
        "stopped_observation": {
            "sequence": 6,
            "history_turns": history_turns,
            "assistant_turns": assistant_turns,
            "assistant_teaches": assistant_turns,
            "five_dynamics_receipts": history_turns,
            "canonical_17_channel_applications": history_turns,
            "routing_basis_8d_applications": history_turns,
            "tick_before": ordered[0]["engine_tick_before"],
            "tick_after": ordered[-1]["engine_tick_after"],
            "checkpoint_before": ordered[0]["prior_checkpoint_digest"],
            "checkpoint_after": ordered[-1]["checkpoint_digest"],
            "explicit_send_recorded": True,
            "response_capture_recorded": False,
            "provider_outcome": "unknown",
        },
    })
    hypotheses = incomplete_hypotheses(rows)
    stop_audit = {
        "label": "PILOT-V3-PERMANENT-STOP-NOT-A-GATE",
        "sequence": 6,
        "reason": "240-second observation timeout after explicit send; provider outcome unknown; no resend",
        "completed_rows": len(rows),
        "claims": len(claims),
        "captures": manifest["captures"],
        "provider_outcome": "unknown",
        "history_evidence": combined["stopped_observation"],
        "database": str(database.resolve()),
        "database_sha256": sha256_file(database),
        "database_wal_sha256": sha256_file(database.with_name(database.name + "-wal")),
        "driver_input_sha256": sha256_file(driver_input),
        "runtime_receipts_sha256": sha256_file(runtime_receipts),
        "generation_calls_known_complete": 5,
        "generation_calls_unknown_outcome": 1,
        "generation_resends": 0,
        "gate_verdict": None,
    }
    atomic_json(output / "STOP_AUDIT.json", stop_audit)
    manifest.update({
        "completed": False,
        "stop_reason": stop_audit["reason"],
        "stopped_at_sequence": 6,
        "unknown_provider_outcomes": 1,
        "generation_resends": 0,
        "substrate_engagement": combined,
        "hypotheses": hypotheses,
        "matrix_sha256": sha256_file(output / "raw_matrix.jsonl"),
        "claims_sha256": sha256_file(output / "claims.jsonl"),
        "oracle_trace_sha256": sha256_file(output / "oracle_trace.jsonl"),
        "stop_audit_sha256": sha256_file(output / "STOP_AUDIT.json"),
    })
    frozen = json.loads(
        (Path(__file__).parent / "batteries/wp29-v2-draft/manifest.json").read_text()
    )
    manifest["frozen_code_sha"] = frozen["code_sha"]
    appendix = report(rows, manifest, hypotheses)
    appendix = appendix.replace(
        "# WP-25 Appendix C — frozen 33-case production pilot",
        "# WP-29 Appendix C — pilot v3 permanent stop record",
        1,
    )
    appendix = appendix.replace(
        "> PILOT OUTCOME ONLY. This report issues no specification G-gate verdict.",
        "> STOPPED INCOMPLETE: 5/165 captures. Observation 6 timed out after explicit send with an unknown provider outcome; no resume or resend is permitted. This report issues no specification G-gate verdict.",
        1,
    )
    (output / "APPENDIX_C.md").write_text(appendix, encoding="utf-8")
    manifest["appendix_sha256"] = sha256_file(output / "APPENDIX_C.md")
    atomic_json(manifest_path, manifest)
    return {
        "rows": len(rows),
        "claims": len(claims),
        "captures": manifest["captures"],
        "stop_reason": manifest["stop_reason"],
        "hypotheses": hypotheses,
        "substrate_engagement": combined,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--runtime-receipts", type=Path, required=True)
    parser.add_argument("--driver-input", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.output, args.database, args.runtime_receipts, args.driver_input), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
