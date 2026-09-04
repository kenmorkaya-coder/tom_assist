#!/usr/bin/env python3
"""Run the frozen WP-36b local dense-load shadow calibration."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import tempfile
import time
from pathlib import Path
from typing import Any

from gateway.dense_load17 import (
    ANCHOR_BANK_PATH,
    compile_dense_shadow_load,
    validate_dense_shadow_load,
)
from gateway.semantic_chunks import build_semantic_profile, build_token_chunks
from gateway.structural_analysis import CHANNELS


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "validation" / "calibration" / "wp36b_cases.json"
PREREG_PATH = ROOT / "validation" / "calibration" / "WP36B_PREREGISTRATION.md"
DEFAULT_OUTPUT = ROOT / "validation" / "runs" / "wp36b-dense-load-shadow-v1"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_PATH = Path(
    "/Users/kenmorkaya/.cache/huggingface/hub/"
    "models--sentence-transformers--all-MiniLM-L6-v2/snapshots/"
    + MODEL_REVISION
)


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


class Encoder:
    def __init__(self, model_path: Path) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), local_files_only=True
        )
        self.model = AutoModel.from_pretrained(str(model_path), local_files_only=True)
        self.model.eval()

    def profile(self, text: str) -> dict[str, Any]:
        offsets = self.tokenizer(
            text, add_special_tokens=False, return_offsets_mapping=True,
            verbose=False,
        )["offset_mapping"]
        plan = build_token_chunks(text, offsets)
        chunk_texts = [text[row["start"]:row["end"]] for row in plan]
        encoded = self.tokenizer(
            chunk_texts, padding=True, truncation=False, return_tensors="pt",
        )
        with self.torch.no_grad():
            hidden = self.model(**encoded).last_hidden_state
        mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
        pooled = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
        return build_semantic_profile(
            text,
            [
                {"start": row["start"], "end": row["end"],
                 "values": [float(value) for value in vector.tolist()]}
                for row, vector in zip(plan, pooled)
            ],
            model=MODEL_NAME,
            revision=MODEL_REVISION,
        )


def _analysis(case: dict[str, Any], graph: list[Any] | None = None) -> dict[str, Any]:
    history = case.get("history", {})
    return {
        "load_signature": {
            name: float(case.get("structural", {}).get(name, 0.0))
            for name in CHANNELS
        },
        "history_metrics": {
            "combined_similarities": list(history.get("similarities", [])),
            "static_distance_from_previous": float(
                history.get("static_distance_from_previous", 0.0)
            ),
            "change_evidence": float(history.get("change_evidence", 0.0)),
        },
        "current_classification_confidence": history.get("current_confidence"),
        "previous_classification_confidence": history.get("previous_confidence"),
        "driver_evidence": {
            name: float(case.get("driver_evidence", {}).get(name, 0.0))
            for name in ("threat_load", "sustenance_potential", "procreation_potential")
        },
        "directed_graph": list(graph or []),
    }


def _rank(values: dict[str, float]) -> list[str]:
    return [name for name, _ in sorted(values.items(), key=lambda row: (-row[1], row[0]))]


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    names = list(CHANNELS)
    dot = sum(left[name] * right[name] for name in names)
    ln = math.sqrt(sum(left[name] ** 2 for name in names))
    rn = math.sqrt(sum(right[name] ** 2 for name in names))
    return dot / (ln * rn)


def _observe(
    encoder: Encoder,
    case_id: str,
    text: str,
    analysis: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    start = time.monotonic()
    profile = encoder.profile(text)
    dense = compile_dense_shadow_load(text, profile, analysis)
    validate_dense_shadow_load(dense, text, profile, analysis)
    elapsed = time.monotonic() - start
    load = dense["load_signature"]
    drivers = dense["driver_loads"]
    if len(load) != 17 or not all(0.0 < value <= 1.0 for value in load.values()):
        raise RuntimeError(f"{case_id} did not produce a strictly positive q17")
    if len(drivers) != 3 or not all(0.0 < value <= 1.0 for value in drivers.values()):
        raise RuntimeError(f"{case_id} did not produce strictly positive T/S/P")
    return dense, {
        "case_id": case_id,
        "source_text_sha256": dense["source_text_sha256"],
        "analysis_digest": dense["analysis_digest"],
        "chunk_count": len(profile["chunks"]),
        "load_signature": load,
        "driver_loads": drivers,
        "channel_rank": _rank(load),
        "driver_rank": _rank(drivers),
        "elapsed_seconds": elapsed,
    }


def _semantic_row(dense: dict[str, Any], channel: str) -> dict[str, Any]:
    record = next(row for row in dense["channel_records"] if row["channel"] == channel)
    semantic = record["semantic"]
    return {
        "semantic_rank": _rank({
            row["channel"]: row["semantic"]["value"]
            for row in dense["channel_records"]
        }).index(channel) + 1,
        "combined_rank": _rank(dense["load_signature"]).index(channel) + 1,
        "positive_cosine": semantic["positive_cosine"],
        "contrast_cosine": semantic["contrast_cosine"],
        "semantic_value": semantic["value"],
        "combined_evidence": record["combined_evidence"],
        "final_value": record["value"],
        "winning_chunk_index": semantic["chunk_index"],
        "winning_span": [semantic["start"], semantic["end"]],
    }


def _tree_observation(dense: dict[str, Any]) -> dict[str, Any]:
    from gateway.tom_gateway import SEED_PROFILE, TomGateway

    def state_digest(state: tuple[bytes, bytes]) -> str:
        framed = b"".join(len(item).to_bytes(8, "big") + item for item in state)
        return _sha256_bytes(framed)

    with tempfile.TemporaryDirectory(prefix="tom-assist-wp36b-tree-") as directory:
        runtime = TomGateway(Path(directory)).project("shadow-calibration")
        before = runtime.serialized_state_bytes()
        clone = copy.deepcopy(runtime.engine)
        from agency.mechanics.sicd_msr_load import LoadSignature
        from agency.mechanics.sicd_msr_load_application import (
            apply_msr_load_to_sicd_engine,
        )

        signature = LoadSignature.from_mapping(dense["load_signature"], strict=True)
        drivers = dense["driver_loads"]
        result = apply_msr_load_to_sicd_engine(
            clone,
            signature,
            threat_load=drivers["threat_load"],
            sustenance_potential=drivers["sustenance_potential"],
            procreation_potential=drivers["procreation_potential"],
            source="wp36b_disposable_shadow_clone",
        )
        after = runtime.serialized_state_bytes()
        payload = result.as_dict()
        stored_basis = list(clone.state.last_semantic_routing_basis_8d)
        planned_basis = payload["plan"]["routing_basis_8d"]
        basis_deltas = [stored - planned for planned, stored in zip(planned_basis, stored_basis)]
        return {
            "runtime_type": f"{type(runtime.engine).__module__}.{type(runtime.engine).__name__}",
            "seed_profile": runtime.creation_metadata["seed_profile"],
            "seed_branch_count": runtime.creation_metadata["seed_branch_count"],
            "seed_bytes_before_sha256": state_digest(before),
            "seed_bytes_after_sha256": state_digest(after),
            "seed_bytes_unchanged": before == after,
            "application": payload,
            "shape_q17": len(payload["plan"]["load_signature_17"]),
            "shape_routing_basis": len(payload["plan"]["routing_basis_8d"]),
            "shape_driver": len(payload["plan"]["driver_vec"]),
            "routing_basis_stored": stored_basis,
            "routing_basis_deltas": basis_deltas,
            "routing_basis_max_abs_delta": max(abs(value) for value in basis_deltas),
            "routing_basis_applied_exactly": stored_basis == planned_basis,
            "expected_seed_profile": SEED_PROFILE,
        }


def _write_artifacts(output: Path, observations: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    if output.exists():
        raise SystemExit(f"output directory already exists: {output}")
    output.mkdir(parents=True)
    observations_path = output / "observations.jsonl"
    observations_path.write_bytes(b"".join(_canonical_json(row) + b"\n" for row in observations))
    summary_path = output / "summary.json"
    summary_path.write_bytes(_canonical_json(summary) + b"\n")
    report = [
        "# WP-36b dense load shadow calibration",
        "",
        "**LOCAL SHADOW CALIBRATION — NOT A GATE**",
        "",
        f"- Channel observations: {summary['channel_observations']}",
        f"- All q17/T/S/P values strictly positive: {summary['all_values_strictly_positive']}",
        f"- Combined intended channel top-ranked: {summary['combined_primary_top_count']}/17",
        f"- Semantic-only intended channel top-3: {summary['semantic_primary_top3_count']}/17",
        f"- Independent driver winner correct: {summary['driver_winner_count']}/3",
        f"- Paraphrase pair family winners retained: {summary['paraphrase_pair_winner_count']}/2",
        f"- Direction graph/digests distinguish reversal: {summary['direction_distinguished']}",
        f"- Load-bearing tail won its channel: {summary['tail_load_bearing_chunk_won']}",
        f"- Python 10K clone step complete: {summary['tree']['application']['applied']}",
        f"- Original seed runtime unchanged: {summary['tree']['seed_bytes_unchanged']}",
        "",
        "No provider generation, Feeling Wheel path, production preview, production commit, "
        "Rust mechanics path or G-gate verdict was used.",
    ]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {
        "label": "LOCAL-SHADOW-CALIBRATION-NOT-A-GATE",
        "files": {},
        "inputs": {
            "cases_sha256": _sha256_file(CASES_PATH),
            "preregistration_sha256": _sha256_file(PREREG_PATH),
            "anchor_bank_sha256": _sha256_file(ANCHOR_BANK_PATH),
            "model_revision": MODEL_REVISION,
        },
    }
    for path in (observations_path, summary_path, output / "REPORT.md"):
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
    if args.model.resolve().name != MODEL_REVISION:
        raise SystemExit("MiniLM revision differs from frozen pre-registration")
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    encoder = Encoder(args.model)
    observations: list[dict[str, Any]] = []
    dense_by_id: dict[str, dict[str, Any]] = {}

    combined_top = 0
    semantic_top3 = 0
    for case in cases["channel_cases"]:
        dense, row = _observe(encoder, case["id"], case["text"], _analysis(case))
        expected = case["expected"]
        details = _semantic_row(dense, expected)
        row.update({"family": "channel", "expected": expected, **details})
        combined_top += int(details["combined_rank"] == 1)
        semantic_top3 += int(details["semantic_rank"] <= 3)
        observations.append(row)
        dense_by_id[case["id"]] = dense

    driver_winners = 0
    for case in cases["driver_cases"]:
        dense, row = _observe(encoder, case["id"], case["text"], _analysis(case))
        expected = case["expected"]
        row.update({"family": "driver", "expected": expected})
        driver_winners += int(row["driver_rank"][0] == expected)
        observations.append(row)
        dense_by_id[case["id"]] = dense

    paraphrase_winners = 0
    pair_rows = []
    for pair in cases["paraphrase_pairs"]:
        members = []
        outputs = []
        for side in ("left", "right"):
            case = {"structural": pair["structural"]}
            dense, row = _observe(
                encoder, f"{pair['id']}:{side}", pair[side], _analysis(case)
            )
            row.update({"family": "paraphrase", "pair_id": pair["id"], "side": side,
                        "expected": pair["expected"]})
            observations.append(row)
            members.append(row)
            outputs.append(dense)
        retained = all(member["channel_rank"][0] == pair["expected"] for member in members)
        paraphrase_winners += int(retained)
        pair_rows.append({
            "pair_id": pair["id"],
            "winner_retained": retained,
            "q17_cosine": _cosine(outputs[0]["load_signature"], outputs[1]["load_signature"]),
            "q17_l1": sum(abs(outputs[0]["load_signature"][name] - outputs[1]["load_signature"][name])
                           for name in CHANNELS),
        })

    direction = cases["direction_case"]
    direction_outputs = []
    for side in ("forward", "reverse"):
        graph = direction[f"{side}_graph"]
        case = {"structural": direction["structural"]}
        dense, row = _observe(
            encoder, f"{direction['id']}:{side}", direction[side], _analysis(case, graph)
        )
        row.update({"family": "direction", "side": side,
                    "directed_graph_digest": dense["directed_graph_digest"]})
        observations.append(row)
        direction_outputs.append(dense)
    direction_summary = {
        "graph_digests_differ": (
            direction_outputs[0]["directed_graph_digest"]
            != direction_outputs[1]["directed_graph_digest"]
        ),
        "analysis_digests_differ": (
            direction_outputs[0]["analysis_digest"] != direction_outputs[1]["analysis_digest"]
        ),
        "q17_cosine": _cosine(
            direction_outputs[0]["load_signature"],
            direction_outputs[1]["load_signature"],
        ),
        "q17_l1": sum(
            abs(direction_outputs[0]["load_signature"][name]
                - direction_outputs[1]["load_signature"][name])
            for name in CHANNELS
        ),
    }

    tail = cases["long_tail_case"]
    tail_text = tail["neutral_sentence"] * tail["neutral_repetitions"] + tail["load_bearing"]
    tail_dense, tail_row = _observe(encoder, tail["id"], tail_text, _analysis(tail))
    tail_detail = _semantic_row(tail_dense, tail["expected"])
    tail_row.update({"family": "long_tail", "expected": tail["expected"], **tail_detail})
    observations.append(tail_row)
    winning_start, winning_end = tail_detail["winning_span"]
    load_start = tail_text.index(tail["load_bearing"])
    tail_won = winning_start <= load_start < winning_end

    tree = _tree_observation(dense_by_id["DR-02"])
    all_positive = all(
        all(0.0 < value <= 1.0 for value in row["load_signature"].values())
        and all(0.0 < value <= 1.0 for value in row["driver_loads"].values())
        for row in observations
    )
    summary = {
        "label": cases["label"],
        "provider_generations": 0,
        "channel_observations": len(cases["channel_cases"]),
        "total_observations": len(observations),
        "all_values_strictly_positive": all_positive,
        "combined_primary_top_count": combined_top,
        "semantic_primary_top3_count": semantic_top3,
        "driver_winner_count": driver_winners,
        "paraphrase_pair_winner_count": paraphrase_winners,
        "paraphrases": pair_rows,
        "direction": direction_summary,
        "direction_distinguished": (
            direction_summary["graph_digests_differ"]
            and direction_summary["analysis_digests_differ"]
        ),
        "tail_load_bearing_chunk_won": tail_won,
        "tree": tree,
    }
    _write_artifacts(args.output, observations, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
