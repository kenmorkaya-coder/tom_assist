#!/usr/bin/env python3
"""Frozen paired, label-free parser-glossary evaluation."""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import time
from typing import Any, Mapping

from gateway.project_glossary import build_project_glossary
from gateway.structural_analysis import digest, directed_graph_fingerprint, merge_chunk_candidates
from gateway.structure_provider import StructureProviderError, StructureWorkerClient
from gateway.structure_failures import (
    ClassifiedStructureError,
    classify_failure,
    failures_from_error,
    record_for_code,
    taxonomy_summary,
)


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = Path(__file__).with_name("WP40_PREREGISTRATION.md")
DEFAULT_NATIVE = Path("/private/tmp/tom-assist-wp25-pilot-v2")
DEFAULT_OUTPUT = ROOT / "validation/runs/wp40-parser-glossary-v1"
RUN_ID = "wp40-parser-glossary-v1"
RUN_VERSION = "tom-assist-parser-glossary-evaluation/1.0"
MAX_LOCAL_GEMMA_GENERATIONS = 86
CASES_SHA256 = "sha256:e3a27aeae8ed7a38945ce243543b1ed32de2d96b3b5615e956be7fd45cbceee8"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
GEMMA_REVISION = "0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
CURRENT_STATUSES = {"active", "satisfied", "rejected"}
CASES = (
    (1, "001-D23-ASSUMPTION-01-SUB-A.json", "D23-ASSUMPTION-01", "ASSUMPTION", 4, "185965bdbdb9eaad7a69993356a4703b11f42761c0986b294463bec04ec3be88", "14fcd69c8e7d3507e0c8d8207170ecf584db46374ae478e50dffdd8ac09bd251"),
    (18, "018-D23-COMPLETED_WORK-01-SUB-A.json", "D23-COMPLETED_WORK-01", "COMPLETED_WORK", 4, "3fd004a529ad7a02c05445249cab25edc8f28f58f4eceba01d904d8866850dd6", "93a0a2ec1bc43403a746ae68f4183008b884d5f5647349fadd6f16133f0a83ec"),
    (35, "035-D23-CONCEPT-01-SUB-A.json", "D23-CONCEPT-01", "CONCEPT", 4, "2f4fd9271190ef0ab6563b4630ffed0ea05d3f00ec6338ec035713cd1e48b2b7", "a98ec581a44adcfc2000b509fbea4bfe712f179190f94e1981c8feedb5046247"),
    (47, "047-D23-CONSTRAINT-01-SUB-A.json", "D23-CONSTRAINT-01", "CONSTRAINT", 4, "5e6b443465552d950c1ee7e98e5131e239ac48a51bba798020927343bf7bbca5", "0bbb5466dfb71c29977e76b7859bd1fe598f083389bbc5842992b02db4439e7a"),
    (64, "064-D23-DECISION-01-SUB-A.json", "D23-DECISION-01", "DECISION", 3, "de12b7fa802c7b53ac02ca2ec269f506b20f2215db0091a59273f14cf464718a", "90da34880d9e90d2ecf63ae492bdcc8667fa2e9567d93820484c08155b5b06b3"),
    (76, "076-D23-EVIDENCE-01-SUB-A.json", "D23-EVIDENCE-01", "EVIDENCE", 4, "e995f856dd94d572dfcba02ed1b01424d0518a102bb997285e3db7eb36c0eb90", "4940ad20168ee63f19f0057c7b7d32d71db539df2609a55a44dce2806b30ebff"),
    (93, "093-D23-OBJECTIVE-01-SUB-A.json", "D23-OBJECTIVE-01", "OBJECTIVE", 4, "1e5c214f0c9dba8d451415291b42f36e0195b9d516168e564c8b0f51eaf7c2ad", "902c1bbd59cba850309d4d40ccd5c31c2f62a6c89d6963377dd6208c9f79a991"),
    (110, "110-D23-REJECTED_PATH-01-SUB-A.json", "D23-REJECTED_PATH-01", "REJECTED_PATH", 4, "09c833b77dfdc3b60c3c8437aca2275450b3fd413cc4760fbb38d9b0ae185b3c", "827199b61f435aa69eb0f1c014268c55ccb5fcd4282435bbadc8eebd561e2db4"),
    (122, "122-D23-SUPERSESSION-01-SUB-A.json", "D23-SUPERSESSION-01", "SUPERSESSION", 4, "a14e5847090bafbb346f79db1c2a757cccf248c1ae826431709cc92d9465c766", "31a59ff98cf237e8b0649f0f566d45040ef8104464187218431361e751f5240e"),
    (139, "139-D23-UNRESOLVED_DEPENDENCY-01-SUB-A.json", "D23-UNRESOLVED_DEPENDENCY-01", "UNRESOLVED_DEPENDENCY", 4, "f340e08de3f2e4d9054f467741c5d23e99ad0a29f0bd64b404a1b0b618262044", "0c01bd357afd33f8fd5324b1a051717a6d18928f88ee6f3d8f54c05601bb2b91"),
    (151, "151-D23-WORKSTREAM-01-SUB-A.json", "D23-WORKSTREAM-01", "WORKSTREAM", 4, "77237617d3600ea568525dc38a99fa86ea4c4270bb8dadce2e5eb1d726096513", "1506ba338b4e8119d4a17f53f9469f2cd9a02ce40d429ceba0afc7a7661af437"),
)


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()


def _read_native_titles(native: Path, sequence: int) -> list[str]:
    database = native / f"{sequence:03}.sqlite3"
    connection = sqlite3.connect(f"file:{database}?mode=ro&immutable=1", uri=True)
    try:
        rows = connection.execute(
            "SELECT object_json FROM state_objects ORDER BY id"
        ).fetchall()
    finally:
        connection.close()
    objects = [json.loads(row[0]) for row in rows]
    return [row["title"] for row in objects if row["status"] in CURRENT_STATUSES]


def load_cases(native: Path) -> list[dict[str, Any]]:
    descriptor = [
        {
            "sequence": sequence, "file": filename, "test_id": test_id,
            "family": family, "input_sha256": input_hash,
            "source_sha256": source_hash,
        }
        for sequence, filename, test_id, family, _chunks, input_hash, source_hash in CASES
    ]
    if sha256_bytes(compact(descriptor).encode("utf-8")) != CASES_SHA256:
        raise ClassifiedStructureError(record_for_code(
            "evaluation.case_descriptor", "frozen case descriptor digest mismatch",
        ))
    cases = []
    for sequence, filename, test_id, family, chunks, input_hash, source_hash in CASES:
        path = native / filename
        if sha256_file(path) != "sha256:" + input_hash:
            raise ClassifiedStructureError(record_for_code(
                "evaluation.input_hash", f"frozen input changed: {filename}",
            ))
        payload = json.loads(path.read_bytes())
        if payload["test_id"] != test_id or payload["arm"] != "SUB-A":
            raise ClassifiedStructureError(record_for_code(
                "evaluation.identity", f"frozen identity changed: {filename}",
            ))
        source_text = payload["probe"]
        if sha256_bytes(source_text.encode("utf-8")) != "sha256:" + source_hash:
            raise ClassifiedStructureError(record_for_code(
                "evaluation.source_hash", f"frozen source changed: {filename}",
            ))
        json_titles = [
            row["title"] for row in payload["objects"]
            if row["status"] in CURRENT_STATUSES
        ]
        native_titles = _read_native_titles(native, sequence)
        if Counter(json_titles) != Counter(native_titles):
            raise ClassifiedStructureError(record_for_code(
                "evaluation.native_state",
                f"native state objects differ from input: {filename}",
            ))
        glossary = build_project_glossary(native_titles, [])
        if not glossary["terms"]:
            raise ClassifiedStructureError(record_for_code(
                "evaluation.glossary_empty",
                f"native project produced an empty glossary: {filename}",
            ))
        cases.append({
            "sequence": sequence,
            "filename": filename,
            "test_id": test_id,
            "family": family,
            "expected_chunks": chunks,
            "source_text": source_text,
            "source_sha256": "sha256:" + source_hash,
            "input_sha256": "sha256:" + input_hash,
            "native_database_sha256": sha256_file(native / f"{sequence:03}.sqlite3"),
            "glossary": glossary,
        })
    if sum(case["expected_chunks"] for case in cases) * 2 != MAX_LOCAL_GEMMA_GENERATIONS:
        raise ClassifiedStructureError(record_for_code(
            "evaluation.budget_plan",
            "frozen generation budget does not match the case plan",
        ))
    return cases


def _candidate_atoms(candidate: Mapping[str, Any]) -> Counter[str]:
    entities = {row["id"]: row for row in candidate["entities"]}
    atoms: list[dict[str, Any]] = []
    for row in candidate["entities"]:
        atoms.append({"family": "entity", **{key: row[key] for key in (
            "label", "kind", "evidence", "confidence",
        )}})
    for family in ("orientations", "causal_relations"):
        for row in candidate[family]:
            endpoint_keys = (
                ("source_entity_id", "target_entity_id")
                if family == "orientations"
                else ("cause_entity_id", "effect_entity_id")
            )
            item = {key: value for key, value in row.items() if key != "id"}
            for endpoint in endpoint_keys:
                entity = entities[item.pop(endpoint)]
                item[endpoint] = {"label": entity["label"], "kind": entity["kind"]}
            atoms.append({"family": family, **item})
    for signal, rows in candidate["signals"].items():
        atoms.extend({"family": "signal", "signal": signal, **row} for row in rows)
    atoms.extend(
        {"family": "unknown_field", "value": value}
        for value in candidate["unknown_fields"]
    )
    return Counter(compact(atom) for atom in atoms)


def _observation(
    client: StructureWorkerClient, case: Mapping[str, Any], arm: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    glossary = case["glossary"] if arm == "glossary_on" else None
    started = time.monotonic()
    try:
        result = client.analyze(case["source_text"], glossary=glossary)
    except StructureProviderError as error:
        result = None
        candidate = None
        telemetry = error.telemetry or {}
        failures = failures_from_error(error)
        status = "fail_closed"
    else:
        telemetry = result["worker_telemetry"]
        try:
            _chunks, candidate = merge_chunk_candidates(
                case["source_text"], result["semantic_profile"],
                result["chunk_candidates"],
            )
        except Exception as error:
            candidate = None
            failures = [classify_failure(error, stage="merge")]
            status = "fail_closed"
        else:
            failures = []
            status = "observed"
    elapsed = time.monotonic() - started
    planned = int(telemetry.get("planned_chunks", 0))
    attempted = int(telemetry.get("attempted_chunks", 0))
    if planned == 0 and attempted == 0:
        raise ClassifiedStructureError(record_for_code(
            "evaluation.worker_start",
            f"{case['test_id']} {arm} could not start the persistent local worker",
        ))
    if planned != case["expected_chunks"] or attempted > planned:
        raise ClassifiedStructureError(record_for_code(
            "evaluation.chunk_plan",
            f"{case['test_id']} {arm} changed its frozen chunk plan",
        ))
    row = {
        "sequence": case["sequence"],
        "test_id": case["test_id"],
        "family": case["family"],
        "arm": arm,
        "source_sha256": case["source_sha256"],
        "glossary_sha256": None if glossary is None else glossary["sha256"],
        "glossary_term_count": 0 if glossary is None else glossary["term_count"],
        "status": status,
        "failure_count": len(failures),
        "failures": failures,
        "failure_taxonomy": taxonomy_summary(failures),
        "planned_generations": planned,
        "attempted_generations": attempted,
        "successful_generations": int(telemetry.get("successful_chunks", 0)),
        "elapsed_seconds": elapsed,
        "candidate_sha256": None,
        "directed_graph_sha256": None,
        "entity_count": None,
        "mean_entity_span_length": None,
        "relation_count": None,
        "signal_count": None,
        "unknown_field_count": None,
    }
    if candidate is not None:
        spans = [row["evidence"]["end"] - row["evidence"]["start"] for row in candidate["entities"]]
        row.update({
            "candidate_sha256": digest(candidate),
            "directed_graph_sha256": digest(directed_graph_fingerprint(candidate)),
            "entity_count": len(candidate["entities"]),
            "mean_entity_span_length": statistics.fmean(spans) if spans else 0.0,
            "relation_count": len(candidate["orientations"]) + len(candidate["causal_relations"]),
            "signal_count": sum(len(rows) for rows in candidate["signals"].values()),
            "unknown_field_count": len(candidate["unknown_fields"]),
        })
    return row, candidate


def _arm_summary(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    selected = [row for row in rows if row["arm"] == arm]
    observed = [row for row in selected if row["status"] == "observed"]
    failures = [
        failure for row in selected for failure in row.get("failures", [])
    ]
    entities = sum(row["entity_count"] for row in observed)
    weighted_span = sum(
        row["mean_entity_span_length"] * row["entity_count"] for row in observed
    )
    return {
        "logical_parses": len(selected),
        "observed_parses": len(observed),
        "fail_closed_parses": len(selected) - len(observed),
        "fail_closed_rate": (len(selected) - len(observed)) / len(selected),
        "local_gemma_generations": sum(row["attempted_generations"] for row in selected),
        "successful_local_gemma_generations": sum(row["successful_generations"] for row in selected),
        "entity_count": entities,
        "mean_entity_span_length": weighted_span / entities if entities else None,
        "relation_count": sum(row["relation_count"] for row in observed),
        "signal_count": sum(row["signal_count"] for row in observed),
        "unknown_field_count": sum(row["unknown_field_count"] for row in observed),
        "unknown_field_rate": (
            sum(row["unknown_field_count"] > 0 for row in observed) / len(observed)
            if observed else None
        ),
        "failure_taxonomy": taxonomy_summary(failures),
        "elapsed_seconds": sum(row["elapsed_seconds"] for row in selected),
    }


def _pair_diagnostic(
    case: Mapping[str, Any],
    results: Mapping[str, Mapping[str, Any]],
    candidates: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    left, right = candidates["glossary_off"], candidates["glossary_on"]
    if left is not None and right is not None:
        left_atoms, right_atoms = _candidate_atoms(left), _candidate_atoms(right)
        change_size = sum((left_atoms - right_atoms).values()) + sum(
            (right_atoms - left_atoms).values()
        )
        changed = results["glossary_off"]["candidate_sha256"] != results[
            "glossary_on"
        ]["candidate_sha256"]
        graph_agrees = results["glossary_off"]["directed_graph_sha256"] == results[
            "glossary_on"
        ]["directed_graph_sha256"]
    else:
        change_size = None
        changed = None
        graph_agrees = None
    term_present = any(
        term.casefold() in case["source_text"].casefold()
        for term in case["glossary"]["terms"]
    )
    return {
        "sequence": case["sequence"], "test_id": case["test_id"],
        "family": case["family"], "changed": changed,
        "change_size": change_size, "directed_graph_agrees": graph_agrees,
        "glossary_term_present_in_source": term_present,
    }


def run(native: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ClassifiedStructureError(record_for_code(
            "evaluation.output_exists", f"output already exists: {output}",
        ))
    configured_revisions = {
        "minilm": Path(os.environ.get("TOM_ASSIST_MINILM_MODEL", "")).name,
        "gemma": Path(os.environ.get("TOM_ASSIST_GEMMA_MODEL", "")).name,
    }
    if configured_revisions != {
        "minilm": MINILM_REVISION, "gemma": GEMMA_REVISION,
    }:
        raise ClassifiedStructureError(record_for_code(
            "evaluation.model_revision",
            f"local model revision mismatch: {configured_revisions}",
        ))
    cases = load_cases(native)
    output.mkdir(parents=True)
    observations = []
    pairs = []
    generations = 0
    client = StructureWorkerClient.from_environment()
    try:
        for case in cases:
            results = {}
            candidates = {}
            for arm in ("glossary_off", "glossary_on"):
                row, candidate = _observation(client, case, arm)
                generations += row["attempted_generations"]
                if generations > MAX_LOCAL_GEMMA_GENERATIONS:
                    raise ClassifiedStructureError(record_for_code(
                        "evaluation.budget", "local Gemma generation budget exceeded",
                    ))
                observations.append(row)
                results[arm] = row
                candidates[arm] = candidate
            pairs.append(_pair_diagnostic(case, results, candidates))
    finally:
        client.close()

    comparable = [row for row in pairs if row["directed_graph_agrees"] is not None]
    changed = [row for row in pairs if row["changed"] is True]
    summary = {
        "label": "PAIRED-LABEL-FREE-DIAGNOSTIC-NOT-ACCURACY-NOT-A-GATE",
        "run_id": RUN_ID,
        "run_version": RUN_VERSION,
        "case_count": len(cases),
        "logical_parse_count": len(observations),
        "maximum_local_gemma_generations": MAX_LOCAL_GEMMA_GENERATIONS,
        "actual_local_gemma_generations": generations,
        "provider_generations": 0,
        "oauth_calls": 0,
        "arms": {
            arm: _arm_summary(observations, arm)
            for arm in ("glossary_off", "glossary_on")
        },
        "failure_taxonomy": taxonomy_summary([
            failure for row in observations for failure in row.get("failures", [])
        ]),
        "changed_parse_count": len(changed),
        "change_size_distribution": dict(sorted(Counter(
            "not_comparable" if row["change_size"] is None else str(row["change_size"])
            for row in pairs
        ).items())),
        "directed_graph_comparable_pairs": len(comparable),
        "directed_graph_agreement_count": sum(row["directed_graph_agrees"] for row in comparable),
        "directed_graph_agreement_rate": (
            sum(row["directed_graph_agrees"] for row in comparable) / len(comparable)
            if comparable else None
        ),
        "changed_parses_with_glossary_term_in_source": sum(
            row["glossary_term_present_in_source"] for row in changed
        ),
        "correctness_measured": False,
        "accuracy_improvement_claimed": False,
    }
    (output / "observations.jsonl").write_text(
        "".join(compact(row) + "\n" for row in observations), encoding="utf-8",
    )
    (output / "pair_diagnostics.jsonl").write_text(
        "".join(compact(row) + "\n" for row in pairs), encoding="utf-8",
    )
    (output / "summary.json").write_text(compact(summary) + "\n", encoding="utf-8")
    report = f"""# WP-40 paired glossary diagnostic

Status: **LABEL-FREE DIAGNOSTIC — NOT ACCURACY — NOT A GATE**

- Cases: **{len(cases)}**; logical parses: **{len(observations)}**.
- Local Gemma generations: **{generations}/{MAX_LOCAL_GEMMA_GENERATIONS} maximum**.
- Cloud/provider generations: **0**; OAuth calls: **0**.
- Parses changed: **{len(changed)}/{len(pairs)}**.
- Directed-graph agreement: **{summary['directed_graph_agreement_count']}/{len(comparable)} comparable pairs**.
- Change-size distribution: `{compact(summary['change_size_distribution'])}`.
- Failure categories: `{compact(summary['failure_taxonomy']['category_counts'])}`.
- **Unclassified failures: {summary['failure_taxonomy']['unclassified_count']}**;
  taxonomy complete: **{str(summary['failure_taxonomy']['taxonomy_complete']).lower()}**.

The two arms have no owner-authored domain relevance or parse labels. These
results describe whether and how outputs changed; they cannot establish that
either output is more accurate. A correctness verdict requires a separate,
owner-authored labelled set.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    artifacts = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(output.iterdir())
    }
    manifest = {
        "run_id": RUN_ID,
        "run_version": RUN_VERSION,
        "code_sha": _git_sha(),
        "preregistration_sha256": sha256_file(PREREGISTRATION),
        "runner_sha256": sha256_file(Path(__file__)),
        "model_revisions": {"minilm": MINILM_REVISION, "gemma": GEMMA_REVISION},
        "native_store": str(native),
        "cases_sha256": CASES_SHA256,
        "actual_local_gemma_generations": generations,
        "provider_generations": 0,
        "oauth_calls": 0,
        "artifacts": artifacts,
    }
    (output / "run_manifest.json").write_text(compact(manifest) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        cases = load_cases(args.native)
        print(json.dumps({
            "case_count": len(cases),
            "planned_chunks_per_arm": sum(row["expected_chunks"] for row in cases),
            "maximum_local_gemma_generations": MAX_LOCAL_GEMMA_GENERATIONS,
            "provider_generations": 0,
        }, indent=2, sort_keys=True))
        return 0
    print(json.dumps(run(args.native, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
