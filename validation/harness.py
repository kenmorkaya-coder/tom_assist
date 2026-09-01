#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from validation.arms import Arm, render_arm

ROOT = Path(__file__).resolve().parents[1]
ORACLE = Path(__file__).with_name("oracle_worker.py")
ARMS = tuple(Arm)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


@dataclass(frozen=True)
class Observation:
    test_id: str
    arm: str
    scenario: str
    expected_observation: str
    observed_result: str
    evidence: dict


def oracle(request: dict) -> dict:
    completed = subprocess.run(
        [sys.executable, str(ORACLE)],
        input=canonical(request), text=True, capture_output=True, check=False, timeout=10,
    )
    response = json.loads(completed.stdout)
    if completed.returncode or not response.get("ok"):
        raise RuntimeError(response.get("error", completed.stderr or "oracle failed"))
    return response["result"]


def load_histories(path: Path) -> list[dict]:
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    from validation.draft_cases import FORMAT, materialize
    cases = [materialize(case) if case.get("battery_format") == FORMAT else case for case in cases]
    ids = [case["test_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("test_id values must be unique")
    return cases


def replay(path: Path) -> tuple[list[Observation], list[dict]]:
    observations: list[Observation] = []
    traces: list[dict] = []
    for case in load_histories(path):
        if case.get("status") == "DRAFT-PENDING-OWNER-FREEZE":
            raise ValueError("DRAFT-PENDING-OWNER-FREEZE: battery replay disabled; static contract checks only")
        for arm in ARMS:
            arm_input = render_arm(arm, case)
            request = {
                "case_id": case["test_id"], "arm": arm.value, "context": arm_input.context,
                "probe": arm_input.probe, "required_terms": case["required_terms"],
                "forbidden_terms": case.get("forbidden_terms", []),
            }
            result = oracle(request)
            observations.append(Observation(
                test_id=case["test_id"], arm=arm.value, scenario=case["scenario"],
                expected_observation=case["expected_observation"],
                observed_result="OBSERVED_MATCH" if result["observed_match"] else "OBSERVED_MISS",
                evidence=result,
            ))
            traces.append({"request": request, "response": result})
    return observations, traces


def report_markdown(observations: list[Observation], manifest: dict) -> str:
    lines = [
        "# Tom Assist Harness Dry-Run — NOT-A-GATE", "",
        "> Instrumentation smoke only. This report is not a G-gate verdict and the toy cases are not a validation battery.", "",
        "## Run manifest", "", "```json", json.dumps(manifest, indent=2, sort_keys=True), "```", "",
        "## Appendix-C-format observations", "",
        "| Test ID | Arm | Scenario | Expected observation | Observed result | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for item in observations:
        evidence = f"required={item.evidence['required_present']}/{item.evidence['required_total']}; forbidden={item.evidence['forbidden_present']}"
        lines.append(f"| {item.test_id} | {item.arm} | {item.scenario} | {item.expected_observation} | {item.observed_result} | {evidence} |")
    lines.extend(("", "## Result summary", "", f"Recorded {len(observations)} arm observations. No acceptance threshold was evaluated.", ""))
    return "\n".join(lines)


def run(input_path: Path, output_dir: Path, clock: str | None = None) -> tuple[Path, Path]:
    started = clock or datetime.now(timezone.utc).isoformat()
    observations, traces = replay(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    event_trace = output_dir / "event_trace.jsonl"
    packet_trace = output_dir / "packet_trace.jsonl"
    event_trace.write_text("".join(canonical({"test_id": row.test_id, "arm": row.arm, "observed_result": row.observed_result}) + "\n" for row in observations), encoding="utf-8")
    packet_trace.write_text("".join(canonical(trace) + "\n" for trace in traces), encoding="utf-8")
    manifest = {
        "label": "NOT-A-GATE", "harness_version": "validation-harness/1.0", "code_sha": git_sha(),
        "provider_version": "fixture-provider/1.0", "adapter_version": "chatgpt-visible-dom/1.0",
        "state_policy": "context-policy/1.2", "packet_renderer_version": "authoritative-state/1.1",
        "exact_arms": [arm.value for arm in ARMS], "input": str(input_path.relative_to(ROOT)),
        "input_digest": digest_file(input_path), "event_trace": event_trace.name,
        "packet_trace": packet_trace.name, "result_summary": {"cases": len(load_histories(input_path)), "observations": len(observations), "gate_verdicts": 0},
        "started_at": started, "completed_at": started,
    }
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = output_dir / "report.md"
    report_path.write_text(report_markdown(observations, manifest), encoding="utf-8")
    return report_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tom Assist validation harness instrumentation (NOT-A-GATE)")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report, manifest = run(args.input.resolve(), args.output_dir.resolve())
    print(f"NOT-A-GATE report: {report}")
    print(f"run manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
