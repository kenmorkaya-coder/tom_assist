#!/usr/bin/env python3
"""Frozen WP-25 production pilot controller.

This controller never chooses or repairs an answer. It freezes the deterministic
selection, maps authored logical IDs to native UUIDs, journals each logical call
before dispatch, runs the Rust product-path driver sequentially, and scores the
single captured response through the existing isolated oracle.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import json
import math
import os
import random
import socket
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from validation.draft_cases import FAMILIES, ROOT as BATTERY, materialize
from validation.draft_contract import load_answers
from validation.harness import canonical, oracle

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("SUB-A", "SUB-B", "SUB-C", "SUB-D", "SUB-E")
FREEZE_VERSION = "wp25-prereg-frozen/1"
FREEZE_RECORD = BATTERY / "FROZEN_V1.md"
MANIFEST = BATTERY / "manifest.json"
NAMESPACE = uuid.UUID("3ed820e0-f06b-5e51-85b7-7a94864c9d6a")
AUTHORIZED_GENERATIONS = 165
BOOTSTRAP_SEED = 1729
BOOTSTRAP_REPLICATES = 10_000
AT = "2026-09-01T00:00:00Z"


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def append_jsonl(path: Path, value: object) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def all_cases() -> tuple[list[dict], dict[str, dict]]:
    cases: list[dict] = []
    answers: dict[str, dict] = {}
    for family in FAMILIES:
        name = f"{family.lower()}.jsonl"
        recipes = [json.loads(line) for line in (BATTERY / "cases" / name).read_text().splitlines() if line]
        cases.extend(materialize(row) for row in recipes)
        answers.update(load_answers(BATTERY / "answers" / name))
    return sorted(cases, key=lambda row: row["test_id"]), answers


def pilot_selection(cases: list[dict]) -> list[dict]:
    chosen: list[dict] = []
    for family in FAMILIES:
        rows = sorted((row for row in cases if row["focus_family"] == family), key=lambda row: row["test_id"])
        long_rows = [row for row in rows if row["mode"] != "no_rot"][:2]
        controls = [row for row in rows if row["mode"] == "no_rot"][:1]
        if len(long_rows) != 2 or len(controls) != 1:
            raise ValueError(f"pilot selection incomplete for {family}")
        chosen.extend(long_rows + controls)
    return sorted(chosen, key=lambda row: row["test_id"])


def observation_order(cases: list[dict]) -> list[tuple[int, dict, str]]:
    ordered = []
    for case_index, case in enumerate(cases):
        for offset in range(len(ARMS)):
            arm = ARMS[(case_index + offset) % len(ARMS)]
            ordered.append((len(ordered) + 1, case, arm))
    return ordered


def native_uuid(case_id: str, logical_id: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{case_id}\0{logical_id}"))


def text_replace(text: str, mapping: dict[str, str]) -> str:
    for source in sorted(mapping, key=len, reverse=True):
        text = text.replace(source, mapping[source])
    return text


def mapped_tree(value: object, mapping: dict[str, str]) -> object:
    if isinstance(value, dict):
        return {key: mapped_tree(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [mapped_tree(item, mapping) for item in value]
    if isinstance(value, str):
        return mapping.get(value, value)
    return value


def native_case(case: dict, expected: dict, arm: str) -> tuple[dict, dict, dict[str, str], set[str]]:
    case_id = case["test_id"]
    logical_ids = {case["objects"][0]["project_id"], case["objects"][0]["workstream_id"]}
    logical_ids.update(row["id"] for row in case["objects"])
    logical_ids.update(turn["turn_id"] for turn in case["history"])
    logical_ids.update(turn["session_id"] for turn in case["history"])
    mapping = {logical: native_uuid(f"{case_id}:{arm}", logical) for logical in sorted(logical_ids)}
    project_id = mapping[case["objects"][0]["project_id"]]
    workstream_id = mapping[case["objects"][0]["workstream_id"]]
    visible = case["history"][-int(case["visible_turns"]):]
    visible_history = json.dumps(
        [{"turn_id": mapping[row["turn_id"]], "role": row["role"], "content": text_replace(row["text"], mapping)} for row in visible],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    source_by_object: dict[str, str] = {}
    for obj in case["objects"]:
        marker = f"[{obj['id']}]"
        turn = next((row for row in case["history"] if marker in row["text"]), None)
        if turn:
            source_by_object[obj["id"]] = mapping[turn["turn_id"]]
    objects = []
    for row in case["objects"]:
        logical = row["id"]
        supersedes = None
        if logical.endswith(":concept"):
            supersedes = mapping.get(logical + "-old")
        elif logical.endswith(":decision"):
            supersedes = mapping.get(logical + "-old")
        objects.append({
            "id": mapping[logical],
            "project_id": project_id,
            "workstream_id": workstream_id,
            "type": row["type"],
            "title": row["text"][:120],
            "canonical_text": row["text"],
            "status": row["status"],
            "authority": row["authority"],
            "confidence": 1.0 if row["authority"] == "user" else 0.5,
            "binding_strength": row["binding_strength"],
            "source_turn_ids": [source_by_object[logical]] if logical in source_by_object else [],
            "evidence_ids": [],
            "branch_refs": [f"wp25:{case_id}"],
            "created_at": AT,
            "updated_at": AT,
            "effective_at": AT,
            **({"supersedes_id": supersedes} if supersedes else {}),
            **({"reconsideration_condition": "explicit owner reconsideration"} if row["type"] == "REJECTED_PATH" else {}),
            "content_hash": sha256_bytes(row["text"].encode()),
            "state_version": 0,
        })
    edges = []
    for index, row in enumerate(case["relationships"]):
        edges.append({
            "id": native_uuid(f"{case_id}:{arm}", f"edge:{index}:{row['from_id']}:{row['relation']}:{row['to_id']}"),
            "project_id": project_id,
            "from_state_id": mapping[row["from_id"]],
            "edge_type": row["relation"],
            "to_state_id": mapping.get(row["to_id"], row["to_id"]),
            "created_event_id": native_uuid(f"{case_id}:{arm}", f"event:edge:{index}"),
        })
    exchange_id = native_uuid(case_id, f"exchange:{arm}")
    session_id = native_uuid(case_id, f"provider-session:{arm}")
    driver_input = {
        "test_id": case_id,
        "arm": arm,
        "project_id": project_id,
        "workstream_id": workstream_id,
        "session_id": session_id,
        "exchange_id": exchange_id,
        "user_turn_id": f"{exchange_id}:user",
        "response_turn_id": f"{exchange_id}:assistant",
        "created_at": AT,
        "visible_history": visible_history,
        "summary": text_replace(case["summary"], mapping),
        "current_state": text_replace(case["current_state"], mapping),
        "stale_state": text_replace(case["stale_state"], mapping),
        "probe": text_replace(case["probe"], mapping),
        "objects": objects,
        "edges": edges,
    }
    mapped_expected = copy.deepcopy(expected)
    mapped_expected["expected_answer"] = mapped_tree(expected["expected_answer"], mapping)
    mapped_expected["acceptable_mismatch_answer"] = mapped_tree(expected["acceptable_mismatch_answer"], mapping)
    floor = {
        row["id"] for row in objects
        if (row["type"] == "OBJECTIVE" and row["status"] == "active")
        or (row["type"] == "CONSTRAINT" and row["status"] == "active" and row["binding_strength"] == "hard")
        or (row["type"] == "REJECTED_PATH" and row["status"] == "rejected")
        or (row["type"] == "COMPLETED_WORK" and row["status"] in {"active", "satisfied"})
    }
    return driver_input, mapped_expected, mapping, floor


def packet_telemetry(result: dict, floor_ids: set[str], mode: str) -> dict:
    packet = result["packet"]
    admitted = [item["state_id"] for section in packet["sections"] for item in section["items"]]
    optional = sorted(set(admitted) - floor_ids)
    floor = sorted(set(admitted) & floor_ids)
    anchors = sorted(packet.get("retrieved_anchor_ids", []))
    optional = sorted(set(optional) | set(anchors))
    return {
        "packet_injected": result["arm"] == "SUB-D" and bool(result["packet_text"]),
        "floor_rule": "active objectives + active hard constraints + rejected/completed guardrails",
        "floor_ids": floor,
        "optional_ids": optional,
        "floor_item_count": len(floor),
        "optional_item_count": len(optional),
        "gratuitous_packet_injected": bool(mode == "no_rot" and result["arm"] == "SUB-D" and optional),
        "packet_chars": len(result["packet_text"]),
        "estimated_tokens": packet["estimated_tokens"],
    }


def oracle_result(expected: dict, arm: str, response: str, telemetry: dict, mode: str) -> dict:
    request = {
        "oracle_version": "typed-action-oracle/1",
        "case_id": expected["test_id"],
        "arm": arm,
        "expected_answer": expected["expected_answer"],
        "answer": response,
    }
    if arm in expected["mismatch_allowed_arms"]:
        request["acceptable_mismatch_answer"] = expected["acceptable_mismatch_answer"]
    if mode == "no_rot" and arm == "SUB-D":
        request["expected_packet_injected"] = False
        request["packet_injected"] = telemetry["gratuitous_packet_injected"]
    return oracle(request)


def failure_taxonomy(case: dict, scored: dict) -> list[str]:
    if scored["action_consistent"] or scored["explicit_mismatch"]:
        return []
    if not scored["answer_shape_valid"]:
        return ["enumeration/format failure"]
    fields = scored["field_matches"]
    failures: list[str] = []
    if not fields["action_id"]:
        failures.append({
            "OBJECTIVE": "objective/workstream substitution",
            "WORKSTREAM": "objective/workstream substitution",
            "REJECTED_PATH": "rejected-path revival",
            "COMPLETED_WORK": "completed-work reproposal",
            "CONSTRAINT": "constraint violation",
            "UNRESOLVED_DEPENDENCY": "dependency ignored",
            "EVIDENCE": "evidence overstatement/assumption promotion",
            "ASSUMPTION": "evidence overstatement/assumption promotion",
            "SUPERSESSION": "supersession/history loss",
        }.get(case["focus_family"], "wrong action"))
    if not fields["rejected_action_ids"]:
        failures.append("enumeration/format failure")
    if not fields["cited_state_ids"]:
        failures.append("capture/lineage mismatch")
    if not fields["historical_state_ids"]:
        failures.append("supersession/history loss")
    if not fields["relationships"]:
        failures.append("wrong relationship direction")
    if not fields["proposed_mutations"]:
        failures.append("unauthorized mutation")
    if not fields["authority"]:
        failures.append("evidence overstatement/assumption promotion")
    return sorted(set(failures or ["wrong action"]))


def preflight_runtime(runtime_url: str) -> dict:
    parsed = urlsplit(runtime_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or not parsed.port:
        raise ValueError("runtime URL must be an explicit loopback HTTP origin")
    if parsed.port == 18790 or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("runtime URL violates the frozen transport boundary")
    result = {}
    for path in ("/health", "/api/oauth/status", "/api/llm/status"):
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            value = json.loads(response.read())
            if response.status != 200 or not isinstance(value, dict):
                raise ValueError(f"runtime preflight failed at {path}")
            result[path] = value
        finally:
            connection.close()
    oauth, llm = result["/api/oauth/status"], result["/api/llm/status"]
    if oauth.get("ready") is not True or oauth.get("mode") != "oauth":
        raise ValueError("persisted OAuth is not ready")
    if llm.get("connected") is not True or llm.get("oauth_ready") is not True or llm.get("auth_mode") != "oauth" or llm.get("provider") != "openai":
        raise ValueError("runtime LLM provider is not connected OAuth OpenAI")
    health = result["/health"]
    return {
        "origin": f"http://{parsed.hostname}:{parsed.port}",
        "health": {key: health.get(key) for key in ("status", "version", "runtime_version", "profile", "python_version")},
        "oauth": {"ready": oauth.get("ready"), "mode": oauth.get("mode")},
        "llm": {key: llm.get(key) for key in ("connected", "oauth_ready", "auth_mode", "provider", "model")},
    }


def unix_get(socket_path: Path, path: str) -> dict:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect(str(socket_path))
        client.sendall(f"GET {path} HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode())
        chunks = []
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    raw = b"".join(chunks)
    header, body = raw.split(b"\r\n\r\n", 1)
    if b" 200 " not in header.splitlines()[0]:
        raise ValueError(f"gateway GET {path} failed")
    return json.loads(body)


def wait_gateway(process: subprocess.Popen, socket_path: Path) -> dict:
    for _ in range(600):
        if process.poll() is not None:
            raise RuntimeError("gateway exited during startup")
        if socket_path.exists():
            try:
                return unix_get(socket_path, "/health")
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        time.sleep(0.1)
    raise TimeoutError("gateway did not become ready")


def verify_freeze(manifest: dict, cases: list[dict]) -> None:
    if manifest.get("owner_frozen") is not True or manifest.get("status") != "FROZEN-WP25-V1":
        raise ValueError("owner freeze is not active")
    if manifest["freeze"]["version"] != FREEZE_VERSION:
        raise ValueError("freeze version mismatch")
    selected = [row["test_id"] for row in pilot_selection(cases)]
    if manifest["freeze"]["pilot_case_ids"] != selected:
        raise ValueError("frozen pilot selection mismatch")
    original = manifest["files_sha256"]
    for relative, expected in original.items():
        if "/cases/" in relative or "/answers/" in relative or relative.endswith("/domains.json") or relative.endswith("/PREREGISTRATION.md"):
            if sha256_file(ROOT / relative) != expected:
                raise ValueError(f"frozen authored input changed: {relative}")
    payload = copy.deepcopy(manifest["freeze"])
    expected_sha = payload.pop("freeze_sha256")
    actual_sha = sha256_bytes(canonical(payload).encode())
    if actual_sha != expected_sha:
        raise ValueError("freeze SHA mismatch")


def wilson(numerator: int, denominator: int) -> tuple[float | None, float | None]:
    if denominator == 0:
        return None, None
    z = 1.959963984540054
    p = numerator / denominator
    scale = 1 + z * z / denominator
    center = (p + z * z / (2 * denominator)) / scale
    width = z * math.sqrt(p * (1 - p) / denominator + z * z / (4 * denominator * denominator)) / scale
    return center - width, center + width


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def cluster_bootstrap(rows: list[dict], baseline: str) -> dict:
    long_rows = [row for row in rows if row["mode"] != "no_rot" and row["arm"] in {"SUB-D", baseline}]
    domains = sorted({row["domain"] for row in long_rows})
    lookup = {(row["test_id"], row["arm"]): int(row["oracle"]["action_consistent"]) for row in long_rows}
    cases = {row["test_id"]: row for row in long_rows}
    rng = random.Random(BOOTSTRAP_SEED)
    estimates, invalid = [], 0
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = rng.choices(domains, k=len(domains))
        multiplicity = Counter(sampled)
        family_diffs = []
        for family in FAMILIES:
            paired = []
            for case_id, row in cases.items():
                if row["family"] != family or row["arm"] != "SUB-D":
                    continue
                count = multiplicity[row["domain"]]
                if count:
                    paired.extend([(lookup[(case_id, "SUB-D")], lookup[(case_id, baseline)])] * count)
            if not paired:
                break
            family_diffs.append(sum(a - b for a, b in paired) / len(paired))
        if len(family_diffs) != len(FAMILIES):
            invalid += 1
        else:
            estimates.append(sum(family_diffs) / len(family_diffs))
    return {
        "baseline": baseline,
        "replicates": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "valid_replicates": len(estimates),
        "invalid_replicates": invalid,
        "ci95": [percentile(estimates, 0.025), percentile(estimates, 0.975)],
    }


def rates(rows: list[dict], field: str = "action_consistent") -> dict:
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(int(row["oracle"][field]))
    return {arm: {"numerator": sum(groups[arm]), "denominator": len(groups[arm]), "rate": sum(groups[arm]) / len(groups[arm]) if groups[arm] else None} for arm in ARMS}


def resolve_hypotheses(rows: list[dict], complete: bool) -> dict:
    long_rows = [row for row in rows if row["mode"] != "no_rot"]
    family_rates = {}
    for family in FAMILIES:
        family_rates[family] = rates([row for row in long_rows if row["family"] == family])
    macro = {arm: sum(family_rates[f][arm]["rate"] for f in FAMILIES) / len(FAMILIES) for arm in ARMS}
    boot_a, boot_b = cluster_bootstrap(rows, "SUB-A"), cluster_bootstrap(rows, "SUB-B")
    h1_components = {
        "complete_matrix": complete,
        "sub_d_minus_sub_a_at_least_0.15": macro["SUB-D"] - macro["SUB-A"] >= 0.15,
        "sub_d_minus_sub_b_at_least_0.15": macro["SUB-D"] - macro["SUB-B"] >= 0.15,
        "sub_d_vs_sub_a_ci_excludes_zero_positive": boot_a["ci95"][0] is not None and boot_a["ci95"][0] > 0,
        "sub_d_vs_sub_b_ci_excludes_zero_positive": boot_b["ci95"][0] is not None and boot_b["ci95"][0] > 0,
        "sub_d_at_least_0.80_every_family": all(family_rates[f]["SUB-D"]["rate"] >= 0.80 for f in FAMILIES),
    }
    h1 = all(h1_components.values())
    no_rot = [row for row in rows if row["mode"] == "no_rot"]
    nr = rates(no_rot)
    long = rates(long_rows)
    e_containment = [row for row in long_rows if row["arm"] == "SUB-E"]
    secondary = {
        "H2.1_no_rot_rate_within_0.05_of_A": nr["SUB-D"]["rate"] >= nr["SUB-A"]["rate"] - 0.05,
        "H2.1_zero_gratuitous_injections": not any(row["telemetry"]["gratuitous_packet_injected"] for row in no_rot if row["arm"] == "SUB-D"),
        "H2.2_long_D_within_0.05_of_C": long["SUB-D"]["rate"] >= long["SUB-C"]["rate"] - 0.05,
        "H2.3_D_exceeds_E_by_0.10_or_containment": (long["SUB-D"]["rate"] - long["SUB-E"]["rate"] >= 0.10) or ((sum(row["oracle"]["explicit_mismatch"] for row in e_containment) / len(e_containment)) >= 0.80 and long["SUB-D"]["rate"] >= 0.80),
        "H2.4_supersession_D_at_least_0.80": None,
    }
    if any(row["mode"] == "supersession" and row["arm"] == "SUB-D" for row in rows):
        values = [row for row in rows if row["mode"] == "supersession" and row["arm"] == "SUB-D"]
        secondary["H2.4_supersession_D_at_least_0.80"] = sum(row["oracle"]["action_consistent"] for row in values) / len(values) >= 0.80
    if not complete:
        h1_outcome, h0_outcome, h2_outcome = "INVALID_INCOMPLETE", "UNRESOLVED_INCOMPLETE", "UNRESOLVED_INCOMPLETE"
    elif h1:
        h1_outcome, h0_outcome = "HOLDS", "DOES_NOT_HOLD"
        if any(value is None for value in secondary.values()):
            h2_outcome = "UNRESOLVED_MISSING_FROZEN_SLICE"
        elif all(secondary.values()):
            h2_outcome = "NOT_OBSERVED_ALL_SECONDARIES_HOLD"
        else:
            h2_outcome = "HOLDS_PARTIAL_ONE_OR_MORE_SECONDARIES_FAIL"
    else:
        h1_outcome, h0_outcome, h2_outcome = "DOES_NOT_HOLD", "HOLDS", "NOT_TRIGGERED_REQUIRES_H1"
    h3_rows = [row for row in rows if row.get("new_failure_mode")]
    return {
        "macro_long_rates": macro,
        "family_long_rates": family_rates,
        "paired_differences": {"SUB-D_minus_SUB-A": macro["SUB-D"] - macro["SUB-A"], "SUB-D_minus_SUB-B": macro["SUB-D"] - macro["SUB-B"]},
        "cluster_bootstrap": {"SUB-A": boot_a, "SUB-B": boot_b},
        "H1": {"outcome": h1_outcome, "components": h1_components},
        "H0": {"outcome": h0_outcome, "criterion": "one or more frozen H1 primary components does not hold"},
        "H2": {"outcome": h2_outcome, "components": secondary},
        "H3": {"outcome": "OBSERVED_STOP_REQUIRED" if h3_rows else "NOT_OBSERVED", "rows": [row["sequence"] for row in h3_rows]},
    }


def fraction_table(rows: list[dict], key: str) -> list[tuple[str, dict]]:
    values = sorted({str(row[key]) for row in rows})
    return [(value, rates([row for row in rows if str(row[key]) == value])) for value in values]


def fmt_rate(cell: dict) -> str:
    return f"{cell['numerator']}/{cell['denominator']} ({cell['rate']:.3f})" if cell["denominator"] else "0/0 (null)"


def report(rows: list[dict], manifest: dict, hypotheses: dict) -> str:
    lines = [
        "# WP-25 Appendix C — frozen 33-case production pilot", "",
        "> PILOT OUTCOME ONLY. This report issues no specification G-gate verdict.", "",
        "## Run identity", "", "```json", json.dumps({key: manifest[key] for key in ("run_id", "freeze_sha256", "code_sha", "logical_calls_claimed", "captures", "completed")}, indent=2, sort_keys=True), "```", "",
        "## Frozen-hypothesis resolution", "",
        f"- **H1:** {hypotheses['H1']['outcome']}",
        f"- **H0:** {hypotheses['H0']['outcome']}",
        f"- **H2:** {hypotheses['H2']['outcome']}",
        f"- **H3:** {hypotheses['H3']['outcome']}", "",
        "```json", json.dumps(hypotheses, indent=2, sort_keys=True), "```", "",
    ]
    for title, key in (("Focus family", "family"), ("Slice", "mode"), ("Domain", "domain")):
        lines.extend((f"## Exact action consistency by {title.lower()}", "", f"| {title} | " + " | ".join(ARMS) + " |", "|---|" + "---|" * len(ARMS)))
        for value, grouped in fraction_table(rows, key):
            lines.append(f"| {value} | " + " | ".join(fmt_rate(grouped[arm]) for arm in ARMS) + " |")
        lines.append("")
    lines.extend(("## Failure taxonomy", "", "| Failure | SUB-A | SUB-B | SUB-C | SUB-D | SUB-E | Total |", "|---|---:|---:|---:|---:|---:|---:|"))
    failures = sorted({failure for row in rows for failure in row["failure_taxonomy"]})
    for failure in failures:
        counts = [sum(failure in row["failure_taxonomy"] for row in rows if row["arm"] == arm) for arm in ARMS]
        lines.append(f"| {failure} | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")
    if not failures:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 |")
    lines.extend(("", "## No-rot SUB-D injection telemetry (floor permitted)", "", "| Test ID | Floor items | Optional items | Gratuitous | Packet chars |", "|---|---:|---:|---|---:|"))
    for row in rows:
        if row["mode"] == "no_rot" and row["arm"] == "SUB-D":
            t = row["telemetry"]
            lines.append(f"| {row['test_id']} | {t['floor_item_count']} | {t['optional_item_count']} | {str(t['gratuitous_packet_injected']).lower()} | {t['packet_chars']} |")
    lines.extend(("", "## Raw paired matrix", "", "| # | Test ID | Family | Slice | Domain | Arm | Exact | SUB-E containment | Shape | Evaluation | Gratuitous | Failures | Prompt SHA | Response SHA |", "|---:|---|---|---|---|---|---|---|---|---|---|---|---|---|"))
    for row in rows:
        failures_text = ", ".join(row["failure_taxonomy"]) or "none"
        lines.append(f"| {row['sequence']} | {row['test_id']} | {row['family']} | {row['mode']} | {row['domain']} | {row['arm']} | {str(row['oracle']['action_consistent']).lower()} | {str(row['oracle']['explicit_mismatch']).lower()} | {str(row['oracle']['answer_shape_valid']).lower()} | {row['evaluation_result']} | {str(row['telemetry']['gratuitous_packet_injected']).lower()} | {failures_text} | {row['prompt_hash']} | {row['response_hash']} |")
    lines.extend(("", "Raw visible prompts, bounded responses, native ID maps, packet lineage and oracle outputs are preserved in `raw_matrix.jsonl`; call claims are preserved in `claims.jsonl`. No row was retried, repaired, selected best-of, or silently discarded.", ""))
    return "\n".join(lines)


def run(args: argparse.Namespace) -> int:
    if os.environ.get("TOM_ASSIST_WP25_LIVE") != "1" or args.authorized_generations != AUTHORIZED_GENERATIONS:
        raise ValueError("explicit WP-25 live authorization and exact 165-generation budget required")
    if os.environ.get("TOM_ASSIST_PROVIDER_SELF_REPORT") not in {None, "", "0"}:
        raise ValueError("provider self-report must be off")
    cases, answers = all_cases()
    selected = pilot_selection(cases)
    manifest = json.loads(MANIFEST.read_text())
    verify_freeze(manifest, cases)
    order = observation_order(selected)
    if len(order) != AUTHORIZED_GENERATIONS:
        raise ValueError("frozen matrix is not exactly 165 observations")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("output directory already exists; refusing resume/resend")
    output.mkdir(parents=True)
    temp = args.temp.resolve()
    temp.mkdir(parents=True, exist_ok=False)
    runtime = preflight_runtime(args.runtime_url)
    gateway_socket = temp / "gateway.sock"
    gateway_log = (output / "gateway.log").open("wb")
    env = os.environ.copy()
    env["TOM_ASSIST_OAUTH_RUNTIME_URL"] = args.runtime_url
    env["TOM_ASSIST_PROVIDER_SELF_REPORT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    gateway = subprocess.Popen(
        [str(ROOT / ".venv-gateway/bin/python"), "-B", "-m", "gateway.tom_gateway", "--socket", str(gateway_socket), "--data-dir", str(temp / "runtime"), "--tom-master", str(args.tom_master.resolve())],
        cwd=ROOT, env=env, stdout=gateway_log, stderr=subprocess.STDOUT,
    )
    rows: list[dict] = []
    run_manifest = {
        "run_id": "wp25-pilot-frozen-v1",
        "label": "PILOT-NOT-A-GATE",
        "freeze_version": FREEZE_VERSION,
        "freeze_sha256": manifest["freeze"]["freeze_sha256"],
        "code_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "corpus_manifest_sha256": sha256_file(MANIFEST),
        "driver_sha256": sha256_file(args.driver),
        "runtime": runtime,
        "provider": "tom-master/openai-oauth",
        "model": runtime["llm"].get("model") or "runtime-managed-unreported",
        "temperature": "unavailable/not exposed",
        "seed": "unavailable/not exposed",
        "provider_context_limit": "product 48000 characters; provider token limit unavailable",
        "adapter": "gateway/oauth-provider + RuntimeOAuthAdapter",
        "runtime_pin": subprocess.check_output(["git", "-C", str(args.tom_master), "rev-parse", "HEAD"], text=True).strip(),
        "state_policy": "context-policy/1.1",
        "renderer": "authoritative-state/1.0",
        "oracle": "typed-action-oracle/1",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "self_report": "off",
        "authorized_generations": AUTHORIZED_GENERATIONS,
        "logical_calls_claimed": 0,
        "captures": 0,
        "completed": False,
        "stop_reason": None,
        "ordered_observations": [{"sequence": sequence, "test_id": case["test_id"], "arm": arm, "exchange_id": native_uuid(case["test_id"], f"exchange:{arm}")} for sequence, case, arm in order],
    }
    atomic_json(output / "run_manifest.json", run_manifest)
    try:
        gateway_health = wait_gateway(gateway, gateway_socket)
        if gateway_health.get("pinned_sha_match") is not True:
            raise ValueError("gateway runtime pin mismatch")
        run_manifest["gateway_health"] = gateway_health
        atomic_json(output / "run_manifest.json", run_manifest)
        for sequence, case, arm in order:
            driver_input, expected, id_map, floor = native_case(case, answers[case["test_id"]], arm)
            input_path = temp / f"{sequence:03}-{case['test_id']}-{arm}.json"
            atomic_json(input_path, driver_input)
            claim = {"sequence": sequence, "test_id": case["test_id"], "arm": arm, "exchange_id": driver_input["exchange_id"], "claimed_before_send": True}
            append_jsonl(output / "claims.jsonl", claim)
            run_manifest["logical_calls_claimed"] += 1
            atomic_json(output / "run_manifest.json", run_manifest)
            completed = subprocess.run(
                [str(args.driver.resolve()), "--input", str(input_path), "--database", str(temp / f"{sequence:03}.sqlite3"), "--gateway-socket", str(gateway_socket)],
                cwd=ROOT, env=env, text=True, capture_output=True, timeout=240,
            )
            if completed.returncode:
                run_manifest["stop_reason"] = "operational failure or unknown provider outcome; no resend"
                run_manifest["stopped_at_sequence"] = sequence
                run_manifest["driver_stderr"] = completed.stderr[-4000:]
                atomic_json(output / "run_manifest.json", run_manifest)
                raise RuntimeError(f"driver stopped at observation {sequence}: {completed.stderr.strip()}")
            result = json.loads(completed.stdout)
            telemetry = packet_telemetry(result, floor, case["mode"])
            scored = oracle_result(expected, arm, result["response_text"], telemetry, case["mode"])
            taxonomy = failure_taxonomy(case, scored)
            row = {
                "sequence": sequence,
                "test_id": case["test_id"],
                "family": case["focus_family"],
                "mode": case["mode"],
                "domain": case["domain"],
                "arm": arm,
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
            }
            append_jsonl(output / "raw_matrix.jsonl", row)
            append_jsonl(output / "oracle_trace.jsonl", {"sequence": sequence, "test_id": case["test_id"], "arm": arm, "result": scored})
            rows.append(row)
            run_manifest["captures"] += result["capture_count"]
            run_manifest["last_completed_sequence"] = sequence
            atomic_json(output / "run_manifest.json", run_manifest)
            print(json.dumps({
                "event": "observation_complete",
                "sequence": sequence,
                "total": AUTHORIZED_GENERATIONS,
                "test_id": case["test_id"],
                "arm": arm,
                "action_consistent": scored["action_consistent"],
                "explicit_mismatch": scored["explicit_mismatch"],
                "gratuitous_packet_injected": telemetry["gratuitous_packet_injected"],
            }, sort_keys=True), flush=True)
        run_manifest["completed"] = len(rows) == AUTHORIZED_GENERATIONS and run_manifest["captures"] == AUTHORIZED_GENERATIONS
        if not run_manifest["completed"]:
            raise RuntimeError("matrix or capture count incomplete")
        hypotheses = resolve_hypotheses(rows, True)
        run_manifest["hypotheses"] = hypotheses
        run_manifest["matrix_sha256"] = sha256_file(output / "raw_matrix.jsonl")
        run_manifest["claims_sha256"] = sha256_file(output / "claims.jsonl")
        run_manifest["oracle_trace_sha256"] = sha256_file(output / "oracle_trace.jsonl")
        atomic_json(output / "run_manifest.json", run_manifest)
        (output / "APPENDIX_C.md").write_text(report(rows, run_manifest, hypotheses), encoding="utf-8")
        print(json.dumps({"completed": True, "generations": len(rows), "captures": run_manifest["captures"], "hypotheses": hypotheses, "output": str(output)}, indent=2, sort_keys=True))
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
    cases, answers = all_cases()
    selected = pilot_selection(cases)
    manifest = json.loads(MANIFEST.read_text())
    verify_freeze(manifest, cases)
    order = observation_order(selected)
    seen = set()
    for sequence, case, arm in order:
        driver_input, expected, mapping, floor = native_case(case, answers[case["test_id"]], arm)
        assert sequence >= 1 and len(mapping) == len(set(mapping.values()))
        assert driver_input["project_id"] not in seen
        seen.add(driver_input["project_id"])
        assert driver_input["probe"] != case["probe"]
        assert expected["expected_answer"]["action_id"] == answers[case["test_id"]]["expected_answer"]["action_id"]
        assert floor
    print(json.dumps({"freeze": manifest["freeze"]["freeze_sha256"], "cases": len(selected), "observations": len(order), "answers_byte_checked": 11, "provider_calls": 0}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    live = sub.add_parser("run")
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--temp", type=Path, required=True)
    live.add_argument("--driver", type=Path, required=True)
    live.add_argument("--runtime-url", required=True)
    live.add_argument("--tom-master", type=Path, required=True)
    live.add_argument("--authorized-generations", type=int, required=True)
    args = parser.parse_args()
    return check() if args.command == "check" else run(args)


if __name__ == "__main__":
    raise SystemExit(main())
