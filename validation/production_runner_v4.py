#!/usr/bin/env python3
"""Frozen-v2-inheriting WP-29 pilot-v4 controller.

This is a new versioned runner so the v2-pinned production_runner.py remains
byte-identical. Its only scientific deltas are the five Review 12 clauses.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sqlite3
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from validation import production_runner as base

ROOT = base.ROOT
V3_DRAFT_MANIFEST = ROOT / "validation/batteries/wp29-v3-draft/manifest.json"
AUTHORIZED_GENERATIONS = base.AUTHORIZED_GENERATIONS
ARMS = base.ARMS
BOOTSTRAP_SEED = base.BOOTSTRAP_SEED
OBSERVATION_TIMEOUT_SECONDS = 600
MAX_UNKNOWN_OUTCOMES = 8
MIN_COMPLETE_CASES = 30

V3_APPROVED_CHANGES = [
    {
        "case_disposition": "exclude-entire-case-from-paired-analysis",
        "continue": True,
        "id": 1,
        "never_resend": True,
        "outcome": "unknown_outcome",
    },
    {
        "id": 2,
        "invalid_when_unknown_outcomes_gt": MAX_UNKNOWN_OUTCOMES,
        "ninth_unknown_is_preserved": True,
        "stop_permanently": True,
    },
    {
        "complete_case_definition": "all-five-arms-captured",
        "h1_interpretable_min_complete_cases": MIN_COMPLETE_CASES,
        "id": 3,
        "selected_cases": 33,
    },
    {
        "id": 4,
        "observation_timeout_seconds": OBSERVATION_TIMEOUT_SECONDS,
        "record_wall_time_every_disposition": True,
    },
    {"byte_inherit_everything_else": True, "id": 5},
]


def verify_v3_delta(registration: dict, require_frozen: bool) -> None:
    """Prove that v3 inherits v2 and contains only Review 12's five clauses."""
    v2 = json.loads(base.V2_DRAFT_MANIFEST.read_text())
    base.verify_v2_freeze(v2)
    if registration.get("base_version") != v2["version"]:
        raise ValueError("WP-29 v3 base version differs from frozen v2")
    if registration.get("base_freeze_sha256") != v2["freeze_sha256"]:
        raise ValueError("WP-29 v3 base freeze differs from frozen v2")
    if registration.get("changes") != V3_APPROVED_CHANGES:
        raise ValueError("WP-29 v3 delta is not exactly the five owner-approved changes")
    if registration.get("generations") != AUTHORIZED_GENERATIONS:
        raise ValueError("WP-29 v3 changed the inherited observation count")
    if registration.get("seed") != BOOTSTRAP_SEED:
        raise ValueError("WP-29 v3 changed the inherited bootstrap seed")
    if registration.get("provider_self_report") != "off":
        raise ValueError("WP-29 v3 changed the inherited self-report condition")
    if require_frozen:
        if registration.get("owner_frozen") is not True or registration.get("status") != "FROZEN-WP29-V3":
            raise ValueError("WP-29 v3 owner freeze is not active")
        if registration.get("version") != "wp29-prereg-frozen/3":
            raise ValueError("WP-29 v3 freeze version mismatch")
        payload = copy.deepcopy(registration)
        expected_sha = payload.pop("freeze_sha256")
        if base.sha256_bytes(base.canonical(payload).encode()) != expected_sha:
            raise ValueError("WP-29 v3 freeze SHA mismatch")
        code_sha = registration.get("code_sha")
        for relative, expected in registration.get("files_sha256", {}).items():
            if base.sha256_frozen_source(code_sha, relative) != expected:
                raise ValueError(f"WP-29 v3 frozen file changed: {relative}")
    elif registration.get("owner_frozen") is not False or registration.get("status") != "DRAFT-PENDING-OWNER-FREEZE":
        raise ValueError("WP-29 v3 draft mechanics are inconsistent")


def substrate_from_receipts(driver_input: dict, receipt_path: Path) -> dict:
    """Recover committed-history telemetry after a provider unknown outcome."""
    if not receipt_path.is_file():
        raise ValueError("unknown outcome lacks preserved runtime receipts")
    receipts = json.loads(receipt_path.read_text())
    ordered = sorted(receipts.values(), key=lambda item: item["engine_tick_before"])
    history = driver_input["history"]
    if len(ordered) != len(history):
        raise ValueError("unknown outcome runtime receipt inventory is incomplete")
    dynamics = ["step", "rgm_write", "leaf_vec_teach", "usage_rotation", "front_row_reseat"]
    if not all(item["commit_dynamics"] == dynamics for item in ordered):
        raise ValueError("unknown outcome history lacks exact five-dynamics receipts")
    if not all(
        item["engine_tick_after"] == item["engine_tick_before"] + 1
        and item["commit_drive"]["applied"] is True
        and len(item["commit_drive"]["plan"]["load_signature_17"]) == 17
        and len(item["commit_drive"]["plan"]["routing_basis_8d"]) == 8
        for item in ordered
    ):
        raise ValueError("unknown outcome history lacks canonical drive telemetry")
    assistant_turns = sum(turn["role"] == "assistant" for turn in history)
    assistant_teaches = sum(bool(item["taught"]) for item in ordered)
    if assistant_teaches != assistant_turns:
        raise ValueError("unknown outcome assistant teaching tripwire failed")
    return {
        "history_turns": len(history),
        "five_dynamics_receipts": len(ordered),
        "assistant_turns": assistant_turns,
        "assistant_teaches": assistant_teaches,
        "canonical_17_channel_applications": len(ordered),
        "routing_basis_8d_applications": len(ordered),
        "tick_before": ordered[0]["engine_tick_before"],
        "tick_after": ordered[-1]["engine_tick_after"],
        "tick_delta": ordered[-1]["engine_tick_after"] - ordered[0]["engine_tick_before"],
        "checkpoint_before": ordered[0]["prior_checkpoint_digest"],
        "checkpoint_after": ordered[-1]["checkpoint_digest"],
        "checkpoint_changed": ordered[0]["prior_checkpoint_digest"] != ordered[-1]["checkpoint_digest"],
        "provider_calls_during_import": 0,
    }


def unknown_outcome_after_send(database: Path, driver_input: dict, runtime_root: Path) -> dict | None:
    """Recognize only an explicit send followed by no captured response."""
    if not database.is_file():
        return None
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True)
    try:
        sent_contexts = connection.execute("SELECT COUNT(*) FROM sent_contexts").fetchone()[0]
        user_turns = connection.execute(
            "SELECT COUNT(*) FROM turns WHERE id=?", (driver_input["user_turn_id"],)
        ).fetchone()[0]
        response_turns = connection.execute(
            "SELECT COUNT(*) FROM turns WHERE id=?", (driver_input["response_turn_id"],)
        ).fetchone()[0]
    finally:
        connection.close()
    if (sent_contexts, user_turns, response_turns) != (1, 1, 0):
        return None
    receipt_path = runtime_root / "projects" / driver_input["project_id"] / "tom" / "turn_idempotency.json"
    return {
        "explicit_send_recorded": True,
        "response_capture_recorded": False,
        "provider_outcome": "unknown",
        "database_sha256": base.sha256_file(database),
        "runtime_receipts_sha256": base.sha256_file(receipt_path),
        "substrate_engagement": substrate_from_receipts(driver_input, receipt_path),
    }


def v3_analysis(captured_rows: list[dict], dispositions: list[dict]) -> tuple[list[dict], dict]:
    captured_arms: dict[str, set[str]] = defaultdict(set)
    for row in captured_rows:
        captured_arms[row["test_id"]].add(row["arm"])
    complete_case_ids = sorted(case_id for case_id, arms in captured_arms.items() if arms == set(ARMS))
    selected_case_ids = sorted({row["test_id"] for row in dispositions})
    excluded_case_ids = sorted(set(selected_case_ids) - set(complete_case_ids))
    complete = set(complete_case_ids)
    analysis_rows = [row for row in captured_rows if row["test_id"] in complete]
    metadata = {
        "selected_cases_reached": len(selected_case_ids),
        "complete_cases": len(complete_case_ids),
        "complete_case_ids": complete_case_ids,
        "excluded_cases": len(excluded_case_ids),
        "excluded_case_ids": excluded_case_ids,
        "unknown_outcomes": sum(row["disposition"] == "unknown_outcome" for row in dispositions),
        "h1_interpretable_min_complete_cases": MIN_COMPLETE_CASES,
    }
    return analysis_rows, metadata


def resolve_v3_hypotheses(captured_rows: list[dict], dispositions: list[dict]) -> tuple[dict, list[dict], dict]:
    analysis_rows, metadata = v3_analysis(captured_rows, dispositions)
    validity = metadata["complete_cases"] >= MIN_COMPLETE_CASES
    represented_families = {row["family"] for row in analysis_rows}
    if validity and represented_families != set(base.FAMILIES):
        raise ValueError(
            "ESCALATE: >=30 complete cases but a family has no complete case; frozen v3 defines no sixth rule"
        )
    if validity:
        hypotheses = base.resolve_hypotheses(analysis_rows, True)
    else:
        family_rates = {
            family: base.rates([
                row for row in analysis_rows if row["mode"] != "no_rot" and row["family"] == family
            ])
            for family in base.FAMILIES
        }
        h3_rows = [row for row in captured_rows if row.get("new_failure_mode")]
        hypotheses = {
            "macro_long_rates": {arm: None for arm in ARMS},
            "family_long_rates": family_rates,
            "paired_differences": {"SUB-D_minus_SUB-A": None, "SUB-D_minus_SUB-B": None},
            "cluster_bootstrap": {
                "SUB-A": base.cluster_bootstrap(analysis_rows, "SUB-A"),
                "SUB-B": base.cluster_bootstrap(analysis_rows, "SUB-B"),
            },
            "H1": {
                "outcome": "INVALID_INCOMPLETE",
                "components": {
                    "at_least_30_complete_cases": False,
                    "complete_cases": metadata["complete_cases"],
                    "required_complete_cases": MIN_COMPLETE_CASES,
                },
            },
            "H0": {
                "outcome": "UNRESOLVED_INCOMPLETE",
                "criterion": "one or more frozen H1 primary components does not hold",
            },
            "H2": {"outcome": "UNRESOLVED_INCOMPLETE", "components": None},
            "H3": {
                "outcome": "OBSERVED_STOP_REQUIRED" if h3_rows else "NOT_OBSERVED",
                "rows": [row["sequence"] for row in h3_rows],
            },
        }
    hypotheses["v3_validity"] = metadata
    return hypotheses, analysis_rows, metadata


def report_v4(
    captured_rows: list[dict],
    dispositions: list[dict],
    analysis_rows: list[dict],
    manifest: dict,
    hypotheses: dict,
) -> str:
    wall_times = [float(row["wall_time_seconds"]) for row in dispositions]
    unknown = [row for row in dispositions if row["disposition"] == "unknown_outcome"]
    analysis = hypotheses["v3_validity"]
    lines = [
        "# WP-29 Appendix C — frozen pre-registration v3 pilot v4", "",
        "> PILOT OUTCOME ONLY. This report issues no specification G-gate verdict.", "",
        "## Run identity", "", "```json",
        json.dumps({key: manifest[key] for key in (
            "run_id", "freeze_sha256", "code_sha", "logical_calls_claimed", "captures",
            "observations_disposed", "unknown_outcomes", "completed",
        )}, indent=2, sort_keys=True), "```", "",
        "## Substrate engagement", "",
        "> Execution telemetry only: this establishes that the corrected ToM substrate was exercised; it is not an efficacy or G-gate verdict.", "",
        "```json", json.dumps(manifest["substrate_engagement"], indent=2, sort_keys=True), "```", "",
        "## Observation dispositions and wall time", "", "```json",
        json.dumps({
            "captured": len(captured_rows),
            "unknown_outcomes": len(unknown),
            "unknown_outcome_cap": MAX_UNKNOWN_OUTCOMES,
            "complete_cases": analysis["complete_cases"],
            "excluded_case_ids": analysis["excluded_case_ids"],
            "wall_time_seconds": {
                "count": len(wall_times),
                "min": min(wall_times) if wall_times else None,
                "median": base.percentile(wall_times, 0.5),
                "p95": base.percentile(wall_times, 0.95),
                "max": max(wall_times) if wall_times else None,
                "total": sum(wall_times),
            },
        }, indent=2, sort_keys=True), "```", "",
        "| # | Test ID | Arm | Disposition | Wall seconds | Reason |",
        "|---:|---|---|---|---:|---|",
    ]
    if unknown:
        for row in unknown:
            lines.append(
                f"| {row['sequence']} | {row['test_id']} | {row['arm']} | unknown_outcome | "
                f"{row['wall_time_seconds']:.6f} | {row['unknown_reason']} |"
            )
    else:
        lines.append("| — | — | — | no unknown outcomes | — | — |")
    lines.extend((
        "", "## Frozen-hypothesis resolution", "",
        f"- **H1:** {hypotheses['H1']['outcome']}",
        f"- **H0:** {hypotheses['H0']['outcome']}",
        f"- **H2:** {hypotheses['H2']['outcome']}",
        f"- **H3:** {hypotheses['H3']['outcome']}", "",
        "```json", json.dumps(hypotheses, indent=2, sort_keys=True), "```", "",
    ))
    for title, key in (("Focus family", "family"), ("Slice", "mode"), ("Domain", "domain")):
        lines.extend((
            f"## Paired-analysis exact action consistency by {title.lower()}", "",
            f"| {title} | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS),
        ))
        for value, grouped in base.fraction_table(analysis_rows, key):
            lines.append(f"| {value} | " + " | ".join(base.fmt_rate(grouped[arm]) for arm in ARMS) + " |")
        lines.append("")
    lines.extend((
        "## Failure taxonomy (paired-analysis cases)", "",
        "| Failure | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E | Total |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ))
    failures = sorted({failure for row in analysis_rows for failure in row["failure_taxonomy"]})
    for failure in failures:
        counts = [sum(failure in row["failure_taxonomy"] for row in analysis_rows if row["arm"] == arm) for arm in ARMS]
        lines.append(f"| {failure} | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")
    if not failures:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 |")
    lines.extend((
        "", "## Full raw observation matrix", "",
        "| # | Test ID | Family | Slice | Domain | Arm | Disposition | Wall seconds | Exact | SUB-E containment | Shape | Evaluation | Gratuitous | Failures | Prompt SHA | Response SHA |",
        "|---:|---|---|---|---|---|---|---:|---|---|---|---|---|---|---|---|",
    ))
    for row in dispositions:
        if row["disposition"] == "captured":
            failures_text = ", ".join(row["failure_taxonomy"]) or "none"
            lines.append(
                f"| {row['sequence']} | {row['test_id']} | {row['family']} | {row['mode']} | {row['domain']} | {row['arm']} | captured | "
                f"{row['wall_time_seconds']:.6f} | {str(row['oracle']['action_consistent']).lower()} | "
                f"{str(row['oracle']['explicit_mismatch']).lower()} | {str(row['oracle']['answer_shape_valid']).lower()} | "
                f"{row['evaluation_result']} | {str(row['telemetry']['gratuitous_packet_injected']).lower()} | {failures_text} | "
                f"{row['prompt_hash']} | {row['response_hash']} |"
            )
        else:
            lines.append(
                f"| {row['sequence']} | {row['test_id']} | {row['family']} | {row['mode']} | {row['domain']} | {row['arm']} | "
                f"unknown_outcome | {row['wall_time_seconds']:.6f} | — | — | — | — | — | {row['unknown_reason']} | — | — |"
            )
    lines.extend((
        "", "All 165 planned dispositions are preserved in `raw_matrix.jsonl` when the run reaches its normal end. "
        "Captured prompts/responses, native ID maps, packet lineage and oracle outputs remain inline; unknown outcomes contain only preserved send/no-capture evidence. "
        "No observation was retried, repaired, selected best-of, or silently discarded.", "",
    ))
    return "\n".join(lines)


def _finish(
    output: Path,
    run_manifest: dict,
    rows: list[dict],
    dispositions: list[dict],
) -> tuple[dict, dict]:
    hypotheses, analysis_rows, analysis_metadata = resolve_v3_hypotheses(rows, dispositions)
    run_manifest["hypotheses"] = hypotheses
    run_manifest["analysis"] = analysis_metadata
    run_manifest["matrix_sha256"] = base.sha256_file(output / "raw_matrix.jsonl")
    run_manifest["claims_sha256"] = base.sha256_file(output / "claims.jsonl")
    oracle_trace = output / "oracle_trace.jsonl"
    run_manifest["oracle_trace_sha256"] = base.sha256_file(oracle_trace) if oracle_trace.is_file() else None
    run_manifest["unknown_outcomes_sha256"] = base.sha256_file(output / "unknown_outcomes.jsonl")
    base.atomic_json(output / "run_manifest.json", run_manifest)
    (output / "APPENDIX_C.md").write_text(
        report_v4(rows, dispositions, analysis_rows, run_manifest, hypotheses), encoding="utf-8"
    )
    run_manifest["appendix_sha256"] = base.sha256_file(output / "APPENDIX_C.md")
    base.atomic_json(output / "run_manifest.json", run_manifest)
    return hypotheses, analysis_metadata


def run(args: argparse.Namespace) -> int:
    registration = json.loads(V3_DRAFT_MANIFEST.read_text())
    verify_v3_delta(registration, require_frozen=True)
    if os.environ.get("TOM_ASSIST_WP29_V4_LIVE") != "1" or args.authorized_generations != AUTHORIZED_GENERATIONS:
        raise ValueError("explicit WP-29 pilot-v4 authorization and exact 165-generation budget required")
    if os.environ.get("TOM_ASSIST_PROVIDER_SELF_REPORT") not in {None, "", "0"}:
        raise ValueError("provider self-report must be off")
    cases, answers = base.all_cases()
    selected = base.pilot_selection(cases)
    corpus_manifest = json.loads(base.MANIFEST.read_text())
    base.verify_freeze(corpus_manifest, cases)
    order = base.observation_order(selected)
    if len(order) != AUTHORIZED_GENERATIONS:
        raise ValueError("frozen matrix is not exactly 165 observations")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("output directory already exists; refusing resume/resend")
    output.mkdir(parents=True)
    (output / "unknown_outcomes.jsonl").write_text("", encoding="utf-8")
    temp = args.temp.resolve()
    temp.mkdir(parents=True, exist_ok=False)
    broker = base.preflight_broker(args.oauth_broker_socket)
    gateway_socket = temp / "gateway.sock"
    gateway_log = (output / "gateway.log").open("wb")
    env = os.environ.copy()
    env["TOM_ASSIST_OAUTH_BROKER_SOCKET"] = str(args.oauth_broker_socket.resolve())
    env["TOM_ASSIST_PROVIDER_SELF_REPORT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    gateway = subprocess.Popen(
        [str(ROOT / ".venv-gateway/bin/python"), "-B", "-m", "gateway.tom_gateway",
         "--socket", str(gateway_socket), "--data-dir", str(temp / "runtime"),
         "--tom-master", str(args.tom_master.resolve())],
        cwd=ROOT, env=env, stdout=gateway_log, stderr=subprocess.STDOUT,
    )
    rows: list[dict] = []
    dispositions: list[dict] = []
    run_manifest = {
        "run_id": "wp29-pilot-v4",
        "label": "PILOT-NOT-A-GATE",
        "freeze_version": registration["version"],
        "freeze_sha256": registration["freeze_sha256"],
        "base_freeze_sha256": registration["base_freeze_sha256"],
        "corpus_freeze_version": base.FREEZE_VERSION,
        "corpus_freeze_sha256": corpus_manifest["freeze"]["freeze_sha256"],
        "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "corpus_manifest_sha256": base.sha256_file(base.MANIFEST),
        "driver_sha256": base.sha256_file(args.driver),
        "oauth_broker": broker,
        "provider": "tom-assist/openai-oauth",
        "model": broker["model"],
        "temperature": "unavailable/not exposed",
        "seed": "unavailable/not exposed",
        "provider_context_limit": "product 48000 characters; provider token limit unavailable",
        "adapter": "gateway/oauth-provider + tom-assist-oauth/1.0 broker",
        "structural_preview_pin": subprocess.check_output(
            ["git", "-C", str(args.tom_master), "rev-parse", "HEAD"], text=True
        ).strip(),
        "state_policy": "context-policy/1.2",
        "renderer": "authoritative-state/1.1",
        "oracle": "typed-action-oracle/2",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": base.BOOTSTRAP_REPLICATES,
        "self_report": "off",
        "authorized_generations": AUTHORIZED_GENERATIONS,
        "observation_timeout_seconds": OBSERVATION_TIMEOUT_SECONDS,
        "unknown_outcome_cap": MAX_UNKNOWN_OUTCOMES,
        "h1_interpretable_min_complete_cases": MIN_COMPLETE_CASES,
        "logical_calls_claimed": 0,
        "captures": 0,
        "observations_disposed": 0,
        "unknown_outcomes": 0,
        "generation_resends": 0,
        "completed": False,
        "substrate_engagement": base.substrate_engagement([]),
        "stop_reason": None,
        "ordered_observations": [
            {"sequence": sequence, "test_id": case["test_id"], "arm": arm,
             "exchange_id": base.native_uuid(case["test_id"], f"exchange:{arm}")}
            for sequence, case, arm in order
        ],
    }
    base.atomic_json(output / "run_manifest.json", run_manifest)
    try:
        gateway_health = base.wait_gateway(gateway, gateway_socket)
        if gateway_health.get("pinned_sha_match") is not True:
            raise ValueError("gateway runtime pin mismatch")
        run_manifest["gateway_health"] = gateway_health
        base.atomic_json(output / "run_manifest.json", run_manifest)
        for sequence, case, arm in order:
            driver_input, expected, id_map, floor = base.native_case(
                case, answers[case["test_id"]], arm
            )
            input_path = temp / f"{sequence:03}-{case['test_id']}-{arm}.json"
            base.atomic_json(input_path, driver_input)
            claim = {
                "sequence": sequence,
                "test_id": case["test_id"],
                "arm": arm,
                "exchange_id": driver_input["exchange_id"],
                "claimed_before_send": True,
            }
            base.append_jsonl(output / "claims.jsonl", claim)
            run_manifest["logical_calls_claimed"] += 1
            base.atomic_json(output / "run_manifest.json", run_manifest)
            database_path = temp / f"{sequence:03}.sqlite3"
            started = time.monotonic()
            timed_out = False
            try:
                completed = subprocess.run(
                    [str(args.driver.resolve()), "--input", str(input_path),
                     "--database", str(database_path), "--gateway-socket", str(gateway_socket)],
                    cwd=ROOT, env=env, text=True, capture_output=True,
                    timeout=OBSERVATION_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired as error:
                timed_out = True
                completed = error
            wall_time = round(time.monotonic() - started, 6)
            driver_failed = timed_out or completed.returncode != 0
            if driver_failed:
                evidence = unknown_outcome_after_send(database_path, driver_input, temp / "runtime")
                if evidence is None:
                    stderr = getattr(completed, "stderr", "") or ""
                    run_manifest["stop_reason"] = "fatal operational/integrity failure before a provable unknown-outcome disposition"
                    run_manifest["stopped_at_sequence"] = sequence
                    run_manifest["driver_stderr"] = str(stderr)[-4000:]
                    base.atomic_json(output / "run_manifest.json", run_manifest)
                    raise RuntimeError(f"driver fatally stopped at observation {sequence}: {str(stderr).strip()}")
                stderr = getattr(completed, "stderr", "") or ""
                reason = (
                    f"{OBSERVATION_TIMEOUT_SECONDS}-second timeout after explicit send"
                    if timed_out else
                    "provider/driver error after explicit send: " + str(stderr).strip()[-500:]
                ).replace("|", "/").replace("\n", " ")
                wal = database_path.with_name(database_path.name + "-wal")
                disposition = {
                    "sequence": sequence,
                    "test_id": case["test_id"],
                    "family": case["focus_family"],
                    "mode": case["mode"],
                    "domain": case["domain"],
                    "arm": arm,
                    "disposition": "unknown_outcome",
                    "unknown_reason": reason,
                    "wall_time_seconds": wall_time,
                    "project_id": driver_input["project_id"],
                    "exchange_id": driver_input["exchange_id"],
                    "user_turn_id": driver_input["user_turn_id"],
                    "response_turn_id": driver_input["response_turn_id"],
                    "database_wal_sha256": base.sha256_file(wal) if wal.is_file() else None,
                    **evidence,
                }
                base.append_jsonl(output / "raw_matrix.jsonl", disposition)
                base.append_jsonl(output / "unknown_outcomes.jsonl", disposition)
                dispositions.append(disposition)
                run_manifest["unknown_outcomes"] += 1
                run_manifest["observations_disposed"] = len(dispositions)
                run_manifest["last_disposed_sequence"] = sequence
                run_manifest["substrate_engagement"] = base.substrate_engagement(dispositions)
                _, analysis_metadata = v3_analysis(rows, dispositions)
                run_manifest["analysis"] = analysis_metadata
                base.atomic_json(output / "run_manifest.json", run_manifest)
                print(json.dumps({
                    "event": "unknown_outcome", "sequence": sequence,
                    "total": AUTHORIZED_GENERATIONS, "test_id": case["test_id"],
                    "arm": arm, "wall_time_seconds": wall_time,
                    "unknown_outcomes": run_manifest["unknown_outcomes"],
                }, sort_keys=True), flush=True)
                if run_manifest["unknown_outcomes"] > MAX_UNKNOWN_OUTCOMES:
                    run_manifest["stop_reason"] = "unknown-outcome cap exceeded at the ninth preserved outcome"
                    run_manifest["stopped_at_sequence"] = sequence
                    run_manifest["invalidated"] = True
                    _finish(output, run_manifest, rows, dispositions)
                    raise RuntimeError("frozen v3 unknown-outcome cap exceeded; run permanently stopped")
                continue
            result = json.loads(completed.stdout)
            telemetry = base.packet_telemetry(result, floor, case["mode"])
            scored = base.oracle_result(expected, arm, result["response_text"], telemetry, case["mode"])
            taxonomy = base.failure_taxonomy(case, scored)
            row = {
                "sequence": sequence,
                "test_id": case["test_id"],
                "family": case["focus_family"],
                "mode": case["mode"],
                "domain": case["domain"],
                "arm": arm,
                "disposition": "captured",
                "wall_time_seconds": wall_time,
                "native_id_map": id_map,
                "expected_answer": expected["expected_answer"],
                "acceptable_mismatch_answer": expected["acceptable_mismatch_answer"],
                "prompt": result["prompt"],
                "prompt_hash": result["prompt_hash"],
                "response_text": result["response_text"],
                "response_hash": result["response_hash"],
                "project_id": result["project_id"],
                "workstream_id": result["workstream_id"],
                "session_id": result["session_id"],
                "exchange_id": result["exchange_id"],
                "user_turn_id": result["user_turn_id"],
                "response_turn_id": result["response_turn_id"],
                "packet_digest": result["packet"]["packet_digest"],
                "packet_state_version": result["packet"]["project_state_version"],
                "packet_state_digest": result["packet"]["project_state_digest"],
                "checkpoint_digest": result["packet"]["tom_checkpoint_digest"],
                "activation_id": result["packet"]["tom_activation_id"],
                "packet_sections": result["packet"]["sections"],
                "packet_excluded": result["packet"]["excluded"],
                "telemetry": telemetry,
                "capture_count": result["capture_count"],
                "evaluation_result": result["evaluation"]["result"],
                "evaluation_id": result["evaluation"]["evaluation_id"],
                "evaluation_intervention_ids": result["evaluation"]["intervention_ids"],
                "evaluation_diagnostics": result["evaluation"]["diagnostics"],
                "oracle": scored,
                "failure_taxonomy": taxonomy,
                "new_failure_mode": False,
                "logical_provider_calls": result["logical_provider_calls"],
                "self_report_enabled": result["self_report_enabled"],
                "substrate_engagement": result["substrate_engagement"],
            }
            base.append_jsonl(output / "raw_matrix.jsonl", row)
            base.append_jsonl(output / "oracle_trace.jsonl", {
                "sequence": sequence, "test_id": case["test_id"], "arm": arm, "result": scored,
            })
            rows.append(row)
            dispositions.append(row)
            run_manifest["substrate_engagement"] = base.substrate_engagement(dispositions)
            run_manifest["captures"] += result["capture_count"]
            run_manifest["last_completed_sequence"] = sequence
            run_manifest["last_disposed_sequence"] = sequence
            run_manifest["observations_disposed"] = len(dispositions)
            _, analysis_metadata = v3_analysis(rows, dispositions)
            run_manifest["analysis"] = analysis_metadata
            base.atomic_json(output / "run_manifest.json", run_manifest)
            print(json.dumps({
                "event": "observation_complete", "sequence": sequence,
                "total": AUTHORIZED_GENERATIONS, "test_id": case["test_id"], "arm": arm,
                "action_consistent": scored["action_consistent"],
                "explicit_mismatch": scored["explicit_mismatch"],
                "gratuitous_packet_injected": telemetry["gratuitous_packet_injected"],
                "wall_time_seconds": wall_time,
            }, sort_keys=True), flush=True)
        run_manifest["completed"] = (
            len(dispositions) == AUTHORIZED_GENERATIONS
            and run_manifest["unknown_outcomes"] <= MAX_UNKNOWN_OUTCOMES
        )
        if not run_manifest["completed"]:
            raise RuntimeError("observation disposition matrix incomplete")
        hypotheses, analysis_metadata = _finish(output, run_manifest, rows, dispositions)
        print(json.dumps({
            "completed": True,
            "observations_disposed": len(dispositions),
            "captures": run_manifest["captures"],
            "unknown_outcomes": run_manifest["unknown_outcomes"],
            "complete_cases": analysis_metadata["complete_cases"],
            "hypotheses": hypotheses,
            "output": str(output),
        }, indent=2, sort_keys=True))
        return 0
    finally:
        gateway.terminate()
        try:
            gateway.wait(timeout=10)
        except subprocess.TimeoutExpired:
            gateway.kill()
            gateway.wait()
        gateway_log.close()


def check() -> int:
    cases, answers = base.all_cases()
    selected = base.pilot_selection(cases)
    manifest = json.loads(base.MANIFEST.read_text())
    base.verify_freeze(manifest, cases)
    registration = json.loads(V3_DRAFT_MANIFEST.read_text())
    verify_v3_delta(registration, require_frozen=registration.get("owner_frozen") is True)
    order = base.observation_order(selected)
    seen = set()
    for sequence, case, arm in order:
        driver_input, expected, mapping, floor = base.native_case(case, answers[case["test_id"]], arm)
        assert sequence >= 1 and len(mapping) == len(set(mapping.values()))
        assert driver_input["project_id"] not in seen
        seen.add(driver_input["project_id"])
        assert driver_input["probe"] != case["probe"]
        assert expected["expected_answer"]["action_id"] == answers[case["test_id"]]["expected_answer"]["action_id"]
        assert floor
    print(json.dumps({
        "freeze": manifest["freeze"]["freeze_sha256"],
        "v3_delta_changes": len(registration["changes"]),
        "cases": len(selected),
        "observations": len(order),
        "answers_byte_checked": 11,
        "provider_calls": 0,
    }, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    live = sub.add_parser("run")
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--temp", type=Path, required=True)
    live.add_argument("--driver", type=Path, required=True)
    live.add_argument("--oauth-broker-socket", type=Path, required=True)
    live.add_argument("--tom-master", type=Path, required=True)
    live.add_argument("--authorized-generations", type=int, required=True)
    args = parser.parse_args()
    return check() if args.command == "check" else run(args)


if __name__ == "__main__":
    raise SystemExit(main())
