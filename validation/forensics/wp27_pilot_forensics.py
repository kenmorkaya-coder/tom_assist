#!/usr/bin/env python3
"""WP-27 post-hoc audit of the frozen WP-25 v2 pilot artifacts.

This program is deliberately offline: it reads the preserved pilot artifacts and
writes diagnostic derivatives.  It has no provider, gateway, broker, socket, or
generation code path, and it never rewrites the frozen inputs.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "validation/runs/wp25-pilot-frozen-v2"
DEFAULT_OUTPUT = ROOT / "validation/runs/wp27-pilot-forensics"
ARMS = ("SUB-A", "SUB-B", "SUB-C", "SUB-D", "SUB-E")
FIELDS = (
    "action_id",
    "rejected_action_ids",
    "cited_state_ids",
    "historical_state_ids",
    "relationships",
    "proposed_mutations",
    "authority",
)
LIST_FIELDS = {
    "rejected_action_ids",
    "cited_state_ids",
    "historical_state_ids",
    "relationships",
    "proposed_mutations",
}
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


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_value_sha(value: Any) -> str:
    return sha256_bytes(compact(value).encode("utf-8"))


def raw_text_sha(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8")


def item_key(value: Any) -> str:
    return compact(value)


def list_delta(expected: list[Any], actual: Any) -> dict[str, Any]:
    if not isinstance(actual, list):
        return {
            "exact": False,
            "multiset_equal": False,
            "order_only": False,
            "missing": expected,
            "extra": [],
        }
    expected_counter = collections.Counter(item_key(item) for item in expected)
    actual_counter = collections.Counter(item_key(item) for item in actual)
    missing_keys = list((expected_counter - actual_counter).elements())
    extra_keys = list((actual_counter - expected_counter).elements())
    exact = actual == expected
    multiset_equal = expected_counter == actual_counter
    return {
        "exact": exact,
        "multiset_equal": multiset_equal,
        "order_only": bool(multiset_equal and not exact),
        "missing": [json.loads(item) for item in missing_keys],
        "extra": [json.loads(item) for item in extra_keys],
    }


def parse_answer(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def row_field_audit(row: dict[str, Any]) -> dict[str, Any]:
    expected = row["expected_answer"]
    answer = parse_answer(row["response_text"])
    fields: dict[str, Any] = {}
    for field in FIELDS:
        actual = answer.get(field) if answer is not None else None
        if field in LIST_FIELDS:
            fields[field] = list_delta(expected[field], actual)
        else:
            fields[field] = {
                "exact": actual == expected[field],
                "expected": expected[field],
                "actual": actual,
            }
    set_normalized_all = bool(
        answer is not None
        and all(
            fields[field]["multiset_equal"] if field in LIST_FIELDS else fields[field]["exact"]
            for field in FIELDS
        )
    )
    return {
        "sequence": row["sequence"],
        "test_id": row["test_id"],
        "family": row["family"],
        "mode": row["mode"],
        "arm": row["arm"],
        "capture_count": row["capture_count"],
        "answer_shape_valid": row["oracle"]["answer_shape_valid"],
        "frozen_action_consistent": row["oracle"]["action_consistent"],
        "frozen_explicit_mismatch": row["oracle"]["explicit_mismatch"],
        "taxonomy": row["failure_taxonomy"],
        "set_normalized_all_fields_match_diagnostic_only": set_normalized_all,
        "fields": fields,
    }


def summarize_fields(field_rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm in ARMS:
        rows = [row for row in field_rows if row["arm"] == arm]
        arm_result: dict[str, Any] = {
            "rows": len(rows),
            "shape_valid": sum(row["answer_shape_valid"] for row in rows),
            "captures": sum(row["capture_count"] for row in rows),
            "set_normalized_all_fields_match_diagnostic_only": sum(
                row["set_normalized_all_fields_match_diagnostic_only"] for row in rows
            ),
        }
        for field in FIELDS:
            details = [row["fields"][field] for row in rows]
            field_result = {"exact": sum(detail["exact"] for detail in details)}
            if field in LIST_FIELDS:
                field_result.update(
                    {
                        "multiset_equal": sum(detail["multiset_equal"] for detail in details),
                        "order_only": sum(detail["order_only"] for detail in details),
                        "missing_items": sum(len(detail["missing"]) for detail in details),
                        "extra_items": sum(len(detail["extra"]) for detail in details),
                    }
                )
            arm_result[field] = field_result
        answers = [parse_answer(row_source["response_text"]) for row_source in SOURCE_ROWS_BY_ARM[arm]]
        arm_result["request_current_project_state"] = sum(
            bool(answer and answer.get("action_id") == "REQUEST_CURRENT_PROJECT_STATE")
            for answer in answers
        )
        result[arm] = arm_result
    return result


def extract_between(text: str, opener: str, closer: str) -> str:
    if opener not in text or closer not in text:
        return ""
    return text.split(opener, 1)[1].split(closer, 1)[0]


def logical_role(logical_id: str) -> str:
    return logical_id.rsplit(":", 1)[-1]


def invert_map(mapping: dict[str, str]) -> dict[str, str]:
    return {native: logical for logical, native in mapping.items()}


def classify_reference(value: str, inverse: dict[str, str]) -> str:
    if value in inverse:
        return "own_arm_native"
    if value.startswith("FOREIGN-"):
        return "foreign_ablation"
    if value.startswith("D23-"):
        return "logical_unmapped"
    return "unknown"


def answer_references(answer: dict[str, Any] | None) -> list[str]:
    if answer is None:
        return []
    values: list[str] = []
    for field in ("cited_state_ids", "historical_state_ids"):
        values.extend(item for item in answer.get(field, []) if isinstance(item, str))
    for relationship in answer.get("relationships", []):
        if isinstance(relationship, dict):
            values.extend(
                relationship[key]
                for key in ("from_id", "to_id")
                if isinstance(relationship.get(key), str)
            )
    return values


def id_space_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for arm in ("SUB-D", "SUB-E"):
        counts: collections.Counter[str] = collections.Counter()
        row_summaries = []
        for row in (item for item in rows if item["arm"] == arm):
            inverse = invert_map(row["native_id_map"])
            refs = answer_references(parse_answer(row["response_text"]))
            row_counts = collections.Counter(classify_reference(ref, inverse) for ref in refs)
            counts.update(row_counts)
            row_summaries.append(
                {
                    "test_id": row["test_id"],
                    "mode": row["mode"],
                    "explicit_mismatch": row["oracle"]["explicit_mismatch"],
                    "foreign_context": "FOREIGN-" in row["prompt"],
                    "reference_count": len(refs),
                    "reference_spaces": dict(sorted(row_counts.items())),
                }
            )
        result[arm] = {
            "references": sum(counts.values()),
            "spaces": dict(sorted(counts.items())),
            "rows": row_summaries,
        }
    return result


def packet_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in (item for item in rows if item["arm"] == "SUB-D"):
        inverse = invert_map(row["native_id_map"])
        admitted_items = [
            {
                **item,
                "section": section.get("section_type", section.get("type")),
                "logical_id": inverse.get(item["state_id"]),
                "role": logical_role(inverse[item["state_id"]]) if item["state_id"] in inverse else "unknown",
            }
            for section in row["packet_sections"]
            for item in section["items"]
        ]
        admitted_ids = {item["state_id"] for item in admitted_items}
        admitted_by_id = {item["state_id"]: item for item in admitted_items}
        focus_role = FOCUS_ROLE[row["family"]]
        focus_id = row["native_id_map"][f"{row['test_id']}:{focus_role}"]
        current_ids = row["expected_answer"]["cited_state_ids"]
        historical_ids = row["expected_answer"]["historical_state_ids"]
        state_block = "[TOM_ASSIST_STATE" + extract_between(
            row["prompt"], "[TOM_ASSIST_STATE", "[/TOM_ASSIST_STATE]"
        )
        prior_history = extract_between(
            row["prompt"], "[PRIOR_CONVERSATION", "[/PRIOR_CONVERSATION]"
        )
        current_request = extract_between(
            row["prompt"], "[CURRENT_USER_REQUEST]", "[/CURRENT_USER_REQUEST]"
        )
        excluded = [
            {
                **item,
                "logical_id": inverse.get(item["id"]),
                "role": logical_role(inverse[item["id"]]) if item["id"] in inverse else "unknown",
            }
            for item in row["packet_excluded"]
        ]
        result.append(
            {
                "sequence": row["sequence"],
                "test_id": row["test_id"],
                "family": row["family"],
                "mode": row["mode"],
                "domain": row["domain"],
                "focus_role": focus_role,
                "focus_id": focus_id,
                "focus_admitted": focus_id in admitted_ids,
                "focus_section": admitted_by_id.get(focus_id, {}).get("section"),
                "focus_selection_reason": admitted_by_id.get(focus_id, {}).get("reason_selected"),
                "admitted_count": len(admitted_items),
                "floor_item_count": row["telemetry"]["floor_item_count"],
                "optional_item_count": row["telemetry"]["optional_item_count"],
                "admitted_roles": [item["role"] for item in admitted_items],
                "expected_current_count": len(current_ids),
                "expected_current_admitted": [item for item in current_ids if item in admitted_ids],
                "expected_current_rendered_in_state_block": [item for item in current_ids if item in state_block],
                "expected_current_visible_anywhere_in_prompt": [item for item in current_ids if item in row["prompt"]],
                "expected_historical_count": len(historical_ids),
                "expected_historical_admitted": [item for item in historical_ids if item in admitted_ids],
                "expected_historical_rendered_in_state_block": [item for item in historical_ids if item in state_block],
                "expected_historical_visible_anywhere_in_prompt": [item for item in historical_ids if item in row["prompt"]],
                "current_ids_in_prior_history": [item for item in current_ids if item in prior_history],
                "current_ids_in_current_request": [item for item in current_ids if item in current_request],
                "excluded": excluded,
                "packet_budget_exclusion_count": sum(item["reason"] == "packet-budget" for item in excluded),
                "packet_chars": row["telemetry"]["packet_chars"],
                "estimated_tokens": row["telemetry"]["estimated_tokens"],
                "configured_budget_tokens": 500,
            }
        )
    return result


def summarize_packets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    excluded_reasons: collections.Counter[str] = collections.Counter()
    excluded_roles: collections.Counter[str] = collections.Counter()
    for row in rows:
        excluded_reasons.update(item["reason"] for item in row["excluded"])
        excluded_roles.update(item["role"] for item in row["excluded"])
    return {
        "cases": len(rows),
        "focus_retrieval_hits": sum(row["focus_admitted"] for row in rows),
        "focus_retrieval_rate": sum(row["focus_admitted"] for row in rows) / len(rows),
        "expected_current_objects": sum(row["expected_current_count"] for row in rows),
        "expected_current_admitted": sum(len(row["expected_current_admitted"]) for row in rows),
        "expected_current_rendered_in_state_block": sum(
            len(row["expected_current_rendered_in_state_block"]) for row in rows
        ),
        "expected_current_visible_anywhere_in_prompt": sum(
            len(row["expected_current_visible_anywhere_in_prompt"]) for row in rows
        ),
        "expected_historical_objects": sum(row["expected_historical_count"] for row in rows),
        "expected_historical_admitted": sum(len(row["expected_historical_admitted"]) for row in rows),
        "expected_historical_rendered_in_state_block": sum(
            len(row["expected_historical_rendered_in_state_block"]) for row in rows
        ),
        "expected_historical_visible_anywhere_in_prompt": sum(
            len(row["expected_historical_visible_anywhere_in_prompt"]) for row in rows
        ),
        "admitted_items": sum(row["admitted_count"] for row in rows),
        "excluded_items": sum(len(row["excluded"]) for row in rows),
        "packet_budget_exclusions": sum(row["packet_budget_exclusion_count"] for row in rows),
        "excluded_reasons": dict(sorted(excluded_reasons.items())),
        "excluded_roles": dict(sorted(excluded_roles.items())),
        "packet_chars_range": [min(row["packet_chars"] for row in rows), max(row["packet_chars"] for row in rows)],
        "estimated_tokens_range": [
            min(row["estimated_tokens"] for row in rows),
            max(row["estimated_tokens"] for row in rows),
        ],
        "by_mode": {
            mode: {
                "cases": len(mode_rows),
                "expected_current": sum(row["expected_current_count"] for row in mode_rows),
                "expected_current_admitted": sum(len(row["expected_current_admitted"]) for row in mode_rows),
                "expected_current_visible_anywhere_in_prompt": sum(
                    len(row["expected_current_visible_anywhere_in_prompt"]) for row in mode_rows
                ),
                "expected_historical": sum(row["expected_historical_count"] for row in mode_rows),
                "expected_historical_visible_anywhere_in_prompt": sum(
                    len(row["expected_historical_visible_anywhere_in_prompt"]) for row in mode_rows
                ),
            }
            for mode in sorted({row["mode"] for row in rows})
            for mode_rows in [[row for row in rows if row["mode"] == mode]]
        },
    }


def response_sha_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "sequence": row["sequence"],
            "test_id": row["test_id"],
            "arm": row["arm"],
            "appendix_reported_response_sha": row["response_hash"],
            "canonical_json_string_sha": canonical_value_sha(row["response_text"]),
            "raw_utf8_response_sha": raw_text_sha(row["response_text"]),
            "reported_matches_canonical_json_string": row["response_hash"]
            == canonical_value_sha(row["response_text"]),
            "reported_matches_raw_utf8": row["response_hash"] == raw_text_sha(row["response_text"]),
        }
        for row in rows
    ]


def markdown_report(report: dict[str, Any], packet_details: list[dict[str, Any]]) -> str:
    field_summary = report["field_mismatch_summary"]
    packet = report["sub_d_packet_summary"]
    id_spaces = report["id_space_mapping"]
    lines = [
        "# WP-27 — post-hoc forensic audit of WP-25 frozen pilot v2",
        "",
        "> **POST-HOC DIAGNOSTIC ONLY — ZERO GENERATIONS.** The frozen oracle, matrix, Appendix C, and hypothesis resolution were not changed. **H0 remains HOLDS exactly as frozen.** This report makes no G-gate verdict.",
        "",
        "## Owner-review findings",
        "",
        "1. **The `capture/lineage mismatch` label does not describe a failed capture.** All 165 responses were captured exactly once. The taxonomy attaches that label whenever `cited_state_ids` is not byte-for-byte/list-order equal and the row is neither exact nor an accepted SUB-E mismatch. Citation equality failed in all 165 rows, but 22 accepted SUB-E stale-version fallbacks exit taxonomy early; therefore Appendix C reports 143 label occurrences. The universal condition is citation-list inequality, not capture loss.",
        "2. **Native-ID list order is the dominant exact-oracle failure.** Authored answers were sorted in logical ID space, then UUIDv5-mapped without re-sorting. The prompt asks providers to return sorted lists, so responses commonly sort the resulting UUID strings. The frozen oracle correctly applies its preregistered exact list-order rule; a diagnostic multiset comparison finds all fields semantically equal in 33/33 SUB-C rows. This observation is not a rescore and does not alter H0.",
        "3. **SUB-D retrieved the load-bearing objects, but its renderer hid their object IDs.** The focus object was admitted in 33/33 packets, and all 207/207 expected current citation objects were admitted. Yet only 3/207 expected current IDs appear in the rendered state block (the WORKSTREAM ID in its header); object rows render text without `state_id`. Across the whole prompt, the 22 long cases expose only 2/138 current IDs and 0/44 historical IDs. The 11 no-rot controls expose all IDs through visible history, not through the packet renderer.",
        "4. **Packet budget did not cause the misses.** Every SUB-D packet admitted 12/14 objects. The other 2 were the superseded old concept and old decision, excluded by `superseded-positive`, not budget. There were 0 `packet-budget` exclusions; packets used 453–484 estimated tokens of the configured 500-token budget.",
        "5. **Appendix `Response SHA` is a mislabeled canonical-value digest.** The Rust driver applies `canonical_sha256` to a string, hashing its canonical JSON string encoding (quotes and escaping included). All 165 reported values match that encoding and 0/165 match SHA-256 of the raw UTF-8 response bytes. The correction table preserves both. The same label/encoding issue applies to `Prompt SHA`.",
        "6. **SUB-D/SUB-E ID spaces are deterministic and distinct.** SUB-D response references are entirely its own arm-native UUID space. SUB-E's 22 stale-version cases use own-arm IDs and correctly return the accepted fallback; its 11 wrong-project cases are deliberately prefixed `FOREIGN-`, and their responses copy that foreign space rather than leaking another arm's UUIDs.",
        "7. **Additional reporting defect:** the cluster-bootstrap implementation collapses the two arm rows for each case into one dictionary entry before pairing, producing 0 valid / 10,000 invalid replicates. Fixing that reporting code cannot rescue frozen H1 here: every arm's frozen exact rate is zero and the other primary H1 conditions still fail. H0 remains untouched.",
        "",
        "## Capture/taxonomy accounting",
        "",
        f"- Captures: **{report['capture_lineage']['captures']}/165**; rows with `capture_count == 1`: **{report['capture_lineage']['rows_captured_once']}/165**.",
        f"- Rows with exact `cited_state_ids`: **{report['capture_lineage']['citation_exact_rows']}/165**.",
        f"- Rows labeled `capture/lineage mismatch`: **{report['capture_lineage']['taxonomy_rows']}**.",
        f"- Accepted SUB-E explicit mismatches omitted from failure taxonomy: **{report['capture_lineage']['accepted_mismatch_rows']}**.",
        "",
        "## Per-field mismatch breakdown",
        "",
        "`set/order` means multiset-equal rows / order-only rows. Missing and extra are item counts across the 33 rows. These columns are diagnostic only.",
        "",
        "| Arm | Field | Exact | Set/order | Missing | Extra |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        for field in FIELDS:
            value = field_summary[arm][field]
            set_order = (
                f"{value['multiset_equal']}/{value['order_only']}" if field in LIST_FIELDS else "—"
            )
            missing = value.get("missing_items", "—")
            extra = value.get("extra_items", "—")
            lines.append(f"| {arm} | `{field}` | {value['exact']}/33 | {set_order} | {missing} | {extra} |")
    lines.extend(
        [
            "",
            "Fallback action counts: "
            + ", ".join(
                f"{arm} {field_summary[arm]['request_current_project_state']}/33" for arm in ARMS
            )
            + ". All 165 answer shapes were valid; `proposed_mutations` and `authority` matched in every row.",
            "",
            "## Native ID-space mapping",
            "",
            f"- SUB-D: {id_spaces['SUB-D']['references']} citation/relationship reference occurrences; {compact(id_spaces['SUB-D']['spaces'])}.",
            f"- SUB-E: {id_spaces['SUB-E']['references']} occurrences; {compact(id_spaces['SUB-E']['spaces'])}.",
            "- Mapping rule: per case and arm, each logical ID is converted with UUIDv5 namespace `3ed820e0-f06b-5e51-85b7-7a94864c9d6a` and name `<test_id>:<arm>\\0<logical_id>`. Action IDs are not state-object IDs and remain authored strings.",
            "- SUB-E ablation split: 22 stale-state/version rows (accepted explicit mismatch) and 11 wrong-project rows with planted `FOREIGN-` IDs (not contained). There is no observed cross-arm UUID leakage.",
            "",
            "## SUB-D packet-content accounting",
            "",
            f"- Load-bearing focus retrieval: **{packet['focus_retrieval_hits']}/{packet['cases']} ({packet['focus_retrieval_rate']:.0%})**.",
            f"- Expected current objects admitted: **{packet['expected_current_admitted']}/{packet['expected_current_objects']}**; object IDs rendered in state block: **{packet['expected_current_rendered_in_state_block']}/{packet['expected_current_objects']}**; visible anywhere in full prompt: **{packet['expected_current_visible_anywhere_in_prompt']}/{packet['expected_current_objects']}**.",
            f"- Expected historical objects admitted: **{packet['expected_historical_admitted']}/{packet['expected_historical_objects']}**; IDs rendered in state block: **{packet['expected_historical_rendered_in_state_block']}/{packet['expected_historical_objects']}**; visible anywhere in full prompt: **{packet['expected_historical_visible_anywhere_in_prompt']}/{packet['expected_historical_objects']}**.",
            f"- Total admitted/excluded: **{packet['admitted_items']} / {packet['excluded_items']}**. Exclusion reasons: `{compact(packet['excluded_reasons'])}`. Budget exclusions: **{packet['packet_budget_exclusions']}**.",
            "",
            "| Case | Mode | Focus (section; selection) | Focus hit | Current admitted | Current ID visible | Historical ID visible | Tokens | Excluded |",
            "|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in packet_details:
        excluded = ", ".join(f"{item['role']}:{item['reason']}" for item in row["excluded"])
        lines.append(
            f"| {row['test_id']} | {row['mode']} | {row['focus_role']} "
            f"({row['focus_section']}; {row['focus_selection_reason']}) | "
            f"{'yes' if row['focus_admitted'] else 'no'} | "
            f"{len(row['expected_current_admitted'])}/{row['expected_current_count']} | "
            f"{len(row['expected_current_visible_anywhere_in_prompt'])}/{row['expected_current_count']} | "
            f"{len(row['expected_historical_visible_anywhere_in_prompt'])}/{row['expected_historical_count']} | "
            f"{row['estimated_tokens']} | {excluded} |"
        )
    lines.extend(
        [
            "",
            "The packet manifest and provider-visible text are different evidence surfaces. `packet_sections` proves retrieval/admission; only `prompt` proves what the provider could cite. The renderer includes project/workstream metadata in the header but omits `PacketItem.state_id` from ordinary object lines.",
            "",
            "## Response-SHA correction",
            "",
            f"- Reported equals canonical JSON-string SHA: **{report['response_sha']['reported_matches_canonical_json_string']}/165**.",
            f"- Reported equals raw UTF-8 response SHA: **{report['response_sha']['reported_matches_raw_utf8']}/165**.",
            f"- Distinct response texts / reported digests: **{report['response_sha']['distinct_response_texts']} / {report['response_sha']['distinct_reported_hashes']}**; no digest-to-multiple-text binding was observed.",
            f"- Sequence 1 example: reported `{report['response_sha']['example']['reported']}`; raw UTF-8 `{report['response_sha']['example']['raw_utf8']}`.",
            "",
            "## Reproducibility and boundaries",
            "",
            f"- Frozen source matrix: `{report['sources']['raw_matrix']['sha256']}` ({report['sources']['raw_matrix']['rows']} rows).",
            f"- Frozen Appendix C: `{report['sources']['appendix_c']['sha256']}`.",
            f"- Frozen run manifest: `{report['sources']['run_manifest']['sha256']}`.",
            "- Derived row-level evidence: `field_mismatch_rows.jsonl`, `sub_d_packet_analysis.jsonl`, and `response_sha_audit.jsonl`. `report.json` contains the machine-readable summaries.",
            "- The forensic program only reads frozen files and writes this derivative directory. Provider calls/generations: **0**. No gateway, broker, runtime, OAuth, preview, upstream checkout, frozen golden, or frozen artifact was invoked or modified. Port 18790 was not used.",
            "",
            "## Frozen outcome boundary",
            "",
            "**H1 DOES_NOT_HOLD; H0 HOLDS; H2 NOT_TRIGGERED_REQUIRES_H1; H3 NOT_OBSERVED — unchanged from the frozen Appendix C.** Ordering-normalized comparisons, renderer answerability, SHA corrections, and bootstrap-code diagnosis are post-hoc explanations only. They are not substituted metrics, not amended preregistration, not a rerun, and not a G-gate verdict.",
            "",
        ]
    )
    return "\n".join(lines)


def build(source: Path, output: Path) -> dict[str, Any]:
    global SOURCE_ROWS_BY_ARM
    raw_path = source / "raw_matrix.jsonl"
    rows = load_jsonl(raw_path)
    if len(rows) != 165:
        raise ValueError(f"expected 165 frozen rows, found {len(rows)}")
    if [row["sequence"] for row in rows] != list(range(1, 166)):
        raise ValueError("frozen sequence is not complete and ordered")
    SOURCE_ROWS_BY_ARM = {arm: [row for row in rows if row["arm"] == arm] for arm in ARMS}
    if any(len(SOURCE_ROWS_BY_ARM[arm]) != 33 for arm in ARMS):
        raise ValueError("frozen arm balance is not 33 each")

    field_rows = [row_field_audit(row) for row in rows]
    field_summary = summarize_fields(field_rows)
    packet_details = packet_rows(rows)
    packet_summary = summarize_packets(packet_details)
    sha_rows = response_sha_rows(rows)
    id_spaces = id_space_audit(rows)
    taxonomy_rows = sum("capture/lineage mismatch" in row["failure_taxonomy"] for row in rows)
    response_binding: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        response_binding[row["response_hash"]].add(row["response_text"])

    report = {
        "audit_id": "wp27-pilot-forensics/1",
        "label": "POST-HOC-DIAGNOSTIC-ONLY",
        "zero_generations": True,
        "frozen_outcome_unchanged": {
            "H1": "DOES_NOT_HOLD",
            "H0": "HOLDS",
            "H2": "NOT_TRIGGERED_REQUIRES_H1",
            "H3": "NOT_OBSERVED",
            "gate_verdict": None,
        },
        "sources": {
            "raw_matrix": {"path": str(raw_path.relative_to(ROOT)), "rows": len(rows), "sha256": sha256_file(raw_path)},
            "appendix_c": {"path": str((source / "APPENDIX_C.md").relative_to(ROOT)), "sha256": sha256_file(source / "APPENDIX_C.md")},
            "run_manifest": {"path": str((source / "run_manifest.json").relative_to(ROOT)), "sha256": sha256_file(source / "run_manifest.json")},
        },
        "capture_lineage": {
            "captures": sum(row["capture_count"] for row in rows),
            "rows_captured_once": sum(row["capture_count"] == 1 for row in rows),
            "citation_exact_rows": sum(row["oracle"]["field_matches"]["cited_state_ids"] for row in rows),
            "taxonomy_rows": taxonomy_rows,
            "accepted_mismatch_rows": sum(row["oracle"]["explicit_mismatch"] for row in rows),
            "taxonomy_definition": "emitted when cited_state_ids exact match is false after exact/accepted-mismatch early return",
        },
        "field_mismatch_summary": field_summary,
        "id_space_mapping": id_spaces,
        "sub_d_packet_summary": packet_summary,
        "response_sha": {
            "reported_matches_canonical_json_string": sum(row["reported_matches_canonical_json_string"] for row in sha_rows),
            "reported_matches_raw_utf8": sum(row["reported_matches_raw_utf8"] for row in sha_rows),
            "distinct_response_texts": len({row["response_text"] for row in rows}),
            "distinct_reported_hashes": len({row["response_hash"] for row in rows}),
            "reported_hashes_bound_to_multiple_texts": sum(len(texts) > 1 for texts in response_binding.values()),
            "example": {
                "sequence": rows[0]["sequence"],
                "reported": sha_rows[0]["appendix_reported_response_sha"],
                "canonical_json_string": sha_rows[0]["canonical_json_string_sha"],
                "raw_utf8": sha_rows[0]["raw_utf8_response_sha"],
            },
        },
        "additional_reporting_defect": {
            "cluster_bootstrap_case_overwrite": True,
            "cause": "cases = {test_id: row for row in two-arm rows} retains one arm, then filters retained rows for SUB-D",
            "frozen_report": {"valid_replicates": 0, "invalid_replicates": 10000},
            "h0_effect": "none; all exact arm rates remain zero and other H1 primary components fail",
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "field_mismatch_rows.jsonl", field_rows)
    write_jsonl(output / "sub_d_packet_analysis.jsonl", packet_details)
    write_jsonl(output / "response_sha_audit.jsonl", sha_rows)
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "REPORT.md").write_text(markdown_report(report, packet_details), encoding="utf-8")
    return report


SOURCE_ROWS_BY_ARM: dict[str, list[dict[str, Any]]] = {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build(args.source.resolve(), args.output.resolve())
    print(
        compact(
            {
                "audit_id": report["audit_id"],
                "rows": report["sources"]["raw_matrix"]["rows"],
                "sub_d_focus_hits": report["sub_d_packet_summary"]["focus_retrieval_hits"],
                "generations": 0,
                "frozen_H0": report["frozen_outcome_unchanged"]["H0"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
