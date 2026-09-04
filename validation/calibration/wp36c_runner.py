#!/usr/bin/env python3
"""Run the frozen WP-36c zero-generation shadow correction."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from gateway.dense_load17 import (
    HISTORY_EVIDENCE_CHANNELS,
    compile_dense_shadow_load,
    validate_dense_shadow_load,
)
from gateway.structural_analysis import (
    CANDIDATE_VERSION,
    CHANNELS,
    PARSER_VERSION,
    SIGNAL_NAMES,
    build_analysis,
    text_digest,
)
from validation.calibration.wp36b_runner import Encoder, MODEL_PATH, _tree_observation


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "validation" / "calibration" / "wp36c_cases.json"
PREREG_PATH = ROOT / "validation" / "calibration" / "WP36C_PREREGISTRATION_V2.md"
DEFAULT_OUTPUT = ROOT / "validation" / "runs" / "wp36c-history-driver-shadow-v2"
CHECKPOINT = "sha256:" + ("0" * 64)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _span(text: str, quote: str) -> dict[str, Any]:
    start = text.index(quote)
    return {"start": start, "end": start + len(quote), "quote": quote}


def _candidate(
    text: str,
    signal_specs: dict[str, list[dict[str, Any]]] | None = None,
    relation: dict[str, str] | None = None,
) -> dict[str, Any]:
    signals = {name: [] for name in SIGNAL_NAMES}
    for name, rows in (signal_specs or {}).items():
        if name not in signals:
            raise ValueError(f"unsupported fixture signal: {name}")
        for row in rows:
            if row["quote"] in text:
                signals[name].append({
                    "evidence": _span(text, row["quote"]),
                    "confidence": float(row["confidence"]),
                })
    entities = []
    causal = []
    if relation is not None:
        cause = relation["cause"]
        effect = relation["effect"]
        entities = [
            {"id": "cause", "label": cause, "kind": "event",
             "evidence": _span(text, cause), "confidence": 1.0},
            {"id": "effect", "label": effect, "kind": "outcome",
             "evidence": _span(text, effect), "confidence": 1.0},
        ]
        causal = [{
            "id": "causal", "cause_entity_id": "cause", "effect_entity_id": "effect",
            "kind": "causes", "modality": "asserted", "negated": False,
            "evidence": _span(text, text), "confidence": 1.0,
        }]
    return {
        "schema_version": CANDIDATE_VERSION,
        "source_text_sha256": text_digest(text),
        "entities": entities,
        "orientations": [],
        "causal_relations": causal,
        "signals": signals,
        "unknown_fields": [],
        "confidence": 1.0,
    }


def _source_analysis(
    text: str,
    profile: dict[str, Any],
    *,
    signals: dict[str, list[dict[str, Any]]] | None = None,
    relation: dict[str, str] | None = None,
) -> dict[str, Any]:
    chunks = []
    for chunk in profile["chunks"]:
        chunk_text = text[chunk["start"]:chunk["end"]]
        local_relation = relation if relation is not None and len(profile["chunks"]) == 1 else None
        chunks.append({
            "chunk_index": chunk["index"],
            "candidate": _candidate(chunk_text, signals, local_relation),
        })
    return build_analysis(
        text,
        chunks,
        profile,
        {"version": PARSER_VERSION, "model": "fixture/wp36c", "revision": "frozen-v1"},
        [],
        CHECKPOINT,
    )


def _observe(
    case_id: str,
    text: str,
    profile: dict[str, Any],
    analysis: dict[str, Any],
    family: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    dense = compile_dense_shadow_load(text, profile, analysis)
    validate_dense_shadow_load(dense, text, profile, analysis)
    if tuple(dense["load_signature"]) != CHANNELS:
        raise RuntimeError(f"{case_id} q17 order mismatch")
    if not all(0.0 < value <= 1.0 for value in dense["load_signature"].values()):
        raise RuntimeError(f"{case_id} q17 is not strictly positive")
    if not all(0.0 < value <= 1.0 for value in dense["driver_loads"].values()):
        raise RuntimeError(f"{case_id} T/S/P is not strictly positive")
    return dense, {
        "case_id": case_id,
        "family": family,
        "source_text_sha256": dense["source_text_sha256"],
        "analysis_digest": dense["analysis_digest"],
        "chunk_count": len(profile["chunks"]),
        "load_signature": dense["load_signature"],
        "driver_loads": dense["driver_loads"],
        "elapsed_seconds": time.monotonic() - started,
    }


def _channel_record(dense: dict[str, Any], channel: str) -> dict[str, Any]:
    return next(row for row in dense["channel_records"] if row["channel"] == channel)


def _driver_record(dense: dict[str, Any], driver: str) -> dict[str, Any]:
    return next(row for row in dense["driver_records"] if row["driver"] == driver)


def _history_feature(dense: dict[str, Any], channel: str) -> float | None:
    return _channel_record(dense, channel)["history_feature"]


def _history_details(dense: dict[str, Any]) -> dict[str, Any]:
    return dense["channel_records"][0]["history_feature_details"]


def _missing_history_exact(dense: dict[str, Any]) -> bool:
    records = {row["channel"]: row for row in dense["channel_records"]}
    return all(
        records[name]["combined_evidence"] is None
        and records[name]["value"] == records[name]["semantic"]["value"]
        and records[name]["value"] < 1.0
        for name in HISTORY_EVIDENCE_CHANNELS
    )


def _history_variant(
    encoder: Encoder,
    experiment: dict[str, Any],
    variant_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    variant = experiment[variant_name]
    text = experiment["text"]
    profile = encoder.profile(text)
    analysis = _source_analysis(text, profile)
    analysis = deepcopy(analysis)
    analysis["history_metrics"] = {
        **analysis["history_metrics"],
        "combined_similarities": list(variant["similarities"]),
        "static_distance_from_previous": 0.0,
        "change_evidence": 0.0,
    }
    if "history_centroid_similarity" in variant:
        analysis["history_centroid_similarity"] = variant["history_centroid_similarity"]
    dense, row = _observe(
        f"{experiment['id']}:{variant['id']}", text, profile, analysis, "history"
    )
    row["variant"] = variant["id"]
    row["history_features"] = {
        name: _history_feature(dense, name)
        for name in ("frequency", "persistence", "burstiness", "novelty", "recurrence")
    }
    row["history_details"] = _history_details(dense)
    return dense, row


def _evaluate_history(
    experiment: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    left = outputs["left"]
    right = outputs["right"]
    if experiment["id"] == "HX-FREQ-REC":
        checks = [
            ("left.frequency > right.frequency", _history_feature(left, "frequency") > _history_feature(right, "frequency")),
            ("right.recurrence > left.recurrence", _history_feature(right, "recurrence") > _history_feature(left, "recurrence")),
        ]
    elif experiment["id"] == "HX-PERSIST":
        checks = [
            ("left.frequency == right.frequency", _history_feature(left, "frequency") == _history_feature(right, "frequency")),
            ("left.recurrence == right.recurrence", _history_feature(left, "recurrence") == _history_feature(right, "recurrence")),
            ("left.persistence > right.persistence", _history_feature(left, "persistence") > _history_feature(right, "persistence")),
        ]
    elif experiment["id"] == "HX-BURST":
        control = outputs["control"]
        left_signed = _history_details(left)["burstiness_signed"]
        right_signed = _history_details(right)["burstiness_signed"]
        checks = [
            ("left.burstiness == right.burstiness", _history_feature(left, "burstiness") == _history_feature(right, "burstiness")),
            ("left.burstiness > control.burstiness", _history_feature(left, "burstiness") > _history_feature(control, "burstiness")),
            ("left.burstiness_signed > 0", left_signed > 0.0),
            ("right.burstiness_signed < 0", right_signed < 0.0),
        ]
    elif experiment["id"] == "HX-NOVELTY":
        checks = [
            ("left.recurrence == right.recurrence", _history_feature(left, "recurrence") == _history_feature(right, "recurrence")),
            ("left.novelty > right.novelty", _history_feature(left, "novelty") > _history_feature(right, "novelty")),
        ]
    else:
        raise ValueError(f"unknown frozen history experiment: {experiment['id']}")
    if [name for name, _ in checks] != experiment["expect"]:
        raise RuntimeError("runner checks differ from frozen history expectations")
    return [{"expectation": name, "met": met} for name, met in checks]


def _write_output(
    output: Path,
    observations: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    if output.exists():
        raise SystemExit(f"output directory already exists: {output}")
    output.mkdir(parents=True)
    observation_path = output / "observations.jsonl"
    observation_path.write_bytes(b"".join(_canonical_json(row) + b"\n" for row in observations))
    summary_path = output / "summary.json"
    summary_path.write_bytes(_canonical_json(summary) + b"\n")
    report = [
        "# WP-36c history/driver shadow correction v2",
        "",
        "**LOCAL SHADOW CORRECTION — NOT A GATE**",
        "",
        f"- Observations: {summary['total_observations']}",
        f"- Strictly positive q17 and T/S/P: {summary['all_values_strictly_positive']}",
        f"- Frozen history relations: {summary['history_checks_met']}/{summary['history_checks_total']}",
        f"- Candidate-derived driver cases exact: {summary['driver_cases_exact']}/5",
        f"- Corroboration cases exact: {summary['corroboration_cases_exact']}/4",
        f"- Missing-history controls exact: {summary['missing_history_controls_exact']}/{summary['missing_history_controls_total']}",
        f"- Direction distinguished: {summary['direction_distinguished']}",
        f"- Load-bearing tail won: {summary['tail_load_bearing_chunk_won']}",
        f"- Python 10K clone applied: {summary['tree']['application']['applied']}",
        f"- Compiled T/S/P reached pinned plan: {summary['tree']['plan_matches_compiled_drivers']}",
        f"- Untouched seed runtime bytes exact: {summary['tree']['seed_bytes_unchanged']}",
        "",
        "No provider generation, Feeling Wheel, production activation, Rust mechanics path, "
        "golden change or G-gate verdict was used.",
    ]
    report_path = output / "REPORT.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {
        "label": "LOCAL-SHADOW-CORRECTION-NOT-A-GATE",
        "inputs": {
            "cases_sha256": _sha256_file(CASES_PATH),
            "preregistration_sha256": _sha256_file(PREREG_PATH),
        },
        "files": {},
    }
    for path in (observation_path, summary_path, report_path):
        manifest["files"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
    (output / "manifest.json").write_bytes(_canonical_json(manifest) + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    encoder = Encoder(args.model)
    observations: list[dict[str, Any]] = []

    history_results = []
    for experiment in cases["history_experiments"]:
        outputs = {}
        for variant_name in ("left", "right", "control"):
            if variant_name not in experiment:
                continue
            dense, row = _history_variant(encoder, experiment, variant_name)
            outputs[variant_name] = dense
            observations.append(row)
        checks = _evaluate_history(experiment, outputs)
        history_results.append({"experiment_id": experiment["id"], "checks": checks})

    driver_exact = 0
    missing_history_checks: list[bool] = []
    driver_dense: dict[str, dict[str, Any]] = {}
    for case in cases["driver_cases"]:
        profile = encoder.profile(case["text"])
        analysis = _source_analysis(case["text"], profile, signals=case["signals"])
        dense, row = _observe(case["id"], case["text"], profile, analysis, "driver")
        direct = {name: _driver_record(dense, name)["direct_evidence"] for name in dense["driver_loads"]}
        counts = {name: len(_driver_record(dense, name)["direct_support"]) for name in dense["driver_loads"]}
        exact = direct == case["expected_direct"] and counts == case["expected_support_counts"]
        driver_exact += int(exact)
        row.update({"expected": case["expected"], "direct_evidence": direct,
                    "direct_support_counts": counts, "expected_exact": exact,
                    "missing_history_exact": _missing_history_exact(dense)})
        missing_history_checks.append(row["missing_history_exact"])
        observations.append(row)
        driver_dense[case["id"]] = dense

    corroboration_exact = 0
    for case in cases["corroboration_cases"]:
        profile = encoder.profile(case["text"])
        analysis = _source_analysis(case["text"], profile, signals=case["signals"])
        dense, row = _observe(case["id"], case["text"], profile, analysis, "corroboration")
        actual = dense["structural_corroboration"][case["channel"]]["present"]
        exact = actual is case["expected"]
        corroboration_exact += int(exact)
        row.update({"channel": case["channel"], "expected": case["expected"],
                    "actual": actual, "expected_exact": exact,
                    "missing_history_exact": _missing_history_exact(dense)})
        missing_history_checks.append(row["missing_history_exact"])
        observations.append(row)

    direction = cases["direction_case"]
    direction_dense = []
    for side in ("forward", "reverse"):
        text = direction[side]
        profile = encoder.profile(text)
        analysis = _source_analysis(
            text, profile, relation=direction[f"{side}_relation"]
        )
        dense, row = _observe(f"{direction['id']}:{side}", text, profile, analysis, "direction")
        row.update({"side": side, "graph_digest": dense["directed_graph_digest"]})
        row["missing_history_exact"] = _missing_history_exact(dense)
        missing_history_checks.append(row["missing_history_exact"])
        observations.append(row)
        direction_dense.append(dense)
    direction_distinguished = (
        direction_dense[0]["directed_graph_digest"] != direction_dense[1]["directed_graph_digest"]
        and direction_dense[0]["analysis_digest"] != direction_dense[1]["analysis_digest"]
    )

    tail = cases["long_tail_case"]
    tail_text = tail["neutral_sentence"] * tail["neutral_repetitions"] + tail["load_bearing"]
    tail_profile = encoder.profile(tail_text)
    tail_analysis = _source_analysis(tail_text, tail_profile, signals=tail["signals"])
    tail_dense, tail_row = _observe(tail["id"], tail_text, tail_profile, tail_analysis, "long_tail")
    tail_record = _channel_record(tail_dense, tail["expected"])
    span = tail_record["semantic"]
    load_start = tail_text.index(tail["load_bearing"])
    tail_won = span["start"] <= load_start < span["end"]
    tail_row.update({"expected": tail["expected"], "winning_chunk_index": span["chunk_index"],
                     "winning_span": [span["start"], span["end"]],
                     "corroborated": tail_dense["structural_corroboration"][tail["expected"]]["present"],
                     "missing_history_exact": _missing_history_exact(tail_dense)})
    missing_history_checks.append(tail_row["missing_history_exact"])
    observations.append(tail_row)

    tree = _tree_observation(driver_dense["DRV-MIX"])
    from agency.mechanics.sicd_msr_load import LoadSignature
    from agency.mechanics.sicd_msr_load_application import project_msr_load_to_sicd_step
    tree_dense = driver_dense["DRV-MIX"]
    expected_plan = project_msr_load_to_sicd_step(
        LoadSignature.from_mapping(tree_dense["load_signature"], strict=True),
        threat_load=tree_dense["driver_loads"]["threat_load"],
        sustenance_potential=tree_dense["driver_loads"]["sustenance_potential"],
        procreation_potential=tree_dense["driver_loads"]["procreation_potential"],
    ).as_dict()
    tree["compiled_driver_loads"] = tree_dense["driver_loads"]
    tree["plan_matches_compiled_drivers"] = tree["application"]["plan"] == expected_plan

    all_positive = all(
        all(0.0 < value <= 1.0 for value in row["load_signature"].values())
        and all(0.0 < value <= 1.0 for value in row["driver_loads"].values())
        for row in observations
    )
    history_checks = [check for result in history_results for check in result["checks"]]
    summary = {
        "label": cases["label"],
        "provider_generations": 0,
        "total_observations": len(observations),
        "all_values_strictly_positive": all_positive,
        "history_results": history_results,
        "history_checks_total": len(history_checks),
        "history_checks_met": sum(int(check["met"]) for check in history_checks),
        "driver_cases_exact": driver_exact,
        "corroboration_cases_exact": corroboration_exact,
        "missing_history_controls_total": len(missing_history_checks),
        "missing_history_controls_exact": sum(int(value) for value in missing_history_checks),
        "direction_distinguished": direction_distinguished,
        "tail_load_bearing_chunk_won": tail_won,
        "tree": tree,
    }
    _write_output(args.output, observations, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
