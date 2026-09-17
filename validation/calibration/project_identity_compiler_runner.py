#!/usr/bin/env python3
"""Fresh registry-identity diagnostic; both fixed arms use the unchanged compiler."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gateway.typed_matrix_compiler import (
    FIELD_NAMES, compile_prepared, normalize, prepare_candidate, project,
    semantic_texts, symbol_vector,
)
from gateway.project_identity_matrix_compiler import prepare_identity_candidate
from validation.calibration.typed_compiler_repair_runner import (
    CODE_FILES as OLD_CODE_FILES, baseline, canonical, digest, protected_identity,
    write_json,
)
from validation.calibration.matrix_event_scaw_runner import embed_texts

PREVIOUS = ROOT / "validation/runs/typed-compiler-repair-20260909-v1"
FILES = (*OLD_CODE_FILES,
         "gateway/project_identity_matrix_compiler.py",
         "gateway/tests/test_project_identity_matrix_compiler.py",
         "validation/calibration/project_identity_compiler_runner.py",
         "validation/calibration/PROJECT_IDENTITY_COMPILER_V1_DESIGN.md")
ARMS = ("current", "project_identity")
STAGES = ("raw_fields384", "projected_fields32", "target_mixed32", "combined_mixed32",
          "weighted_components", "view_full", "view_source_context", "view_context_target", "view_sum", "final_matrix")
SPECS = (
    ("locker", "locker", ("Locker Maple", "Locker Oak", "Locker Pine"), "Archive Indigo"),
    ("valve", "valve", ("Valve Inlet", "Valve Outlet", "Valve Bypass"), "Flow Sentinel"),
    ("gate", "gate", ("Gate Upper", "Gate Lower", "Gate Central"), "Access Juncture"),
    ("sensor", "sensor", ("Sensor East", "Sensor West", "Sensor North"), "Weather Watch"),
    ("store", "store", ("Store Dry", "Store Wet", "Store Cool"), "Supply Haven"),
    ("panel", "panel", ("Panel Main", "Panel Auxiliary", "Panel Reserve"), "Power Console"),
    ("same_cabinet", "cabinet", ("Cabinet Control",) * 3, "Archive Violet"),
    ("same_valve", "valve", ("Valve Main",) * 3, "Flow Steward"),
    ("same_gate", "gate", ("Gate Access",) * 3, "Access Portal"),
    ("same_sensor", "sensor", ("Sensor Ambient",) * 3, "Climate Watch"),
    ("same_store", "store", ("Store Central",) * 3, "Supply Refuge"),
    ("same_panel", "panel", ("Panel Distribution",) * 3, "Power Junction"),
)


def registry_text(rows):
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("project_id", "entity_id", "kind", "label"))
    writer.writerows(rows)
    return stream.getvalue()


def item(text, source, target, relation, context, project_id, register):
    identifier = hashlib.sha256(canonical([text, project_id, register])).hexdigest()[:24]
    return {"item_id": "identity_" + identifier, "source_text": text,
            "project_id": project_id, "registry_csv": register,
            "candidate": {"events": [{"source_evidence": {"quote": source}, "target_evidence": {"quote": target},
                "relation_kind": relation, "relation_evidence": {"quote": text}, "context_evidence": {"quote": context},
                "modality": "asserted", "negated": False, "confidence": 1.0}], "unknown_relations": []}}


def build_inputs():
    rows, keys, directions = [], [], []
    for case_id, kind, labels, alias in SPECS:
        cross_project = case_id.startswith("same_")
        projects = [f"project-{case_id}-{i}" if cross_project else f"project-{case_id}" for i in range(3)]
        entities = ["asset-primary" if cross_project else f"asset-{i}" for i in range(3)]
        records = [(projects[i], entities[i], kind, labels[i]) for i in range(3)]
        records.append((projects[1], entities[1], kind, alias))
        register = registry_text(records)
        by_role = {}
        for role, index in (("V1", 0), ("V2", 1), ("V3", 2), ("P2", 1), ("A2", 1)):
            label = alias if role == "A2" else labels[index]
            action = ("record an inspection of " if role == "P2" else "log inspection of ") + label
            actor, context = "the maintenance coordinator", "the planned inspection"
            text = f"During {context}, {actor} must {action}."
            r = item(text, actor, action, "obligation", context, projects[index], register)
            rows.append(r); by_role[role] = r["item_id"]
        keys.append({"case_id": case_id, "category": "identical_labels_different_projects" if cross_project else "similar_labels_same_project", "item_by_role": by_role})
        # Separate registry-backed direction controls. These do not enter the
        # identity-family discrimination denominator.
        control_project = "direction-" + case_id
        register = registry_text([(control_project, "input", kind, "Control Input"), (control_project, "output", kind, "Control Output")])
        pair = []
        for left, right in (("Control Input", "Control Output"), ("Control Output", "Control Input")):
            context = "the interlock check"
            r = item(f"During {context}, {left} enables {right}.", left, right, "enables", context, control_project, register)
            rows.append(r); pair.append(r["item_id"])
        directions.append({"case_id": case_id, "forward": pair[0], "reverse": pair[1]})
    assert len(rows) == 84 and len({r["item_id"] for r in rows}) == 84
    rows.sort(key=lambda r: hashlib.sha256(("identity-blind-v1:" + r["item_id"]).encode()).hexdigest())
    return {"schema": "identity-compiler-blind/1", "items": rows}, {"schema": "identity-compiler-key/1", "sets": keys, "directions": directions}


def verify_previous():
    manifest = json.loads((PREVIOUS / "MANIFEST.json").read_text())
    for name, record in manifest["files"].items():
        assert digest(PREVIOUS / name) == record["sha256"]
    return digest(PREVIOUS / "MANIFEST.json")


def freeze(output):
    previous = verify_previous()
    blind, key = build_inputs()
    old_texts = set()
    for dataset in ("ORIGINAL", "HOLDOUT"):
        old_texts.update(r["source_text"] for r in json.loads((PREVIOUS / f"{dataset}_BLIND.json").read_text())["items"])
    assert not old_texts.intersection(r["source_text"] for r in blind["items"])
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "BLIND.json", blind)
    write_json(output / "SCORER_KEY.json", key)
    for name in FILES:
        target = output / "SOURCE_SNAPSHOT" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    frozen = {"version": "project-identity-freeze/1", "previous_manifest_sha256": previous,
              "code": {name: digest(ROOT / name) for name in FILES},
              "inputs": {name: digest(output / name) for name in ("BLIND.json", "SCORER_KEY.json")},
              "arms": list(ARMS), "families": 12, "direction_controls": 12,
              "condition_limit": 10, "paraphrase_ratio_min": 1.25, "tolerance": 1e-12,
              "source_of_identity": "manually authored synthetic project register; not inferred from labels"}
    frozen["freeze_sha256"] = hashlib.sha256(canonical(frozen)).hexdigest()
    write_json(output / "FREEZE.json", frozen)
    print(json.dumps({"frozen": str(output), "freeze_sha256": frozen["freeze_sha256"]}), flush=True)


def trace(prepared, embeddings):
    result = compile_prepared(prepared, embeddings)
    fields = prepared["events"][0]["fields"]
    raw = np.asarray([embeddings[fields[name]["semantic_text"]] for name in FIELD_NAMES])
    projected = np.asarray([project(row) for row in raw])
    symbols = np.asarray([symbol_vector(fields[name]["symbols"]) if fields[name]["symbols"] else [0.0] * 32 for name in FIELD_NAMES])
    mixed = np.asarray([result["events"][0]["fields32"][name] for name in FIELD_NAMES])
    views = np.asarray(result["events"][0]["views"])
    components = []
    for left, right in ((0, 1), (0, 3), (3, 1)):
        components.append(np.stack((np.outer(mixed[left], mixed[right]), 0.5 * np.outer(mixed[2], mixed[2]), 0.25 * np.outer(mixed[3], mixed[3]))))
    return result, {"raw_fields384": raw.reshape(-1), "projected_fields32": projected.reshape(-1),
                    "target_mixed32": mixed[1], "combined_mixed32": mixed.reshape(-1),
                    "weighted_components": np.asarray(components).reshape(-1),
                    "view_full": views[0], "view_source_context": views[1], "view_context_target": views[2],
                    "view_sum": np.sum(views, axis=0), "final_matrix": np.asarray(result["matrix"]),
                    "symbol_fields32": symbols.reshape(-1)}


def assembly_error(stages):
    components = stages["weighted_components"].reshape(3, 3, 32, 32)
    instrument_views = [normalize(np.sum(component, axis=0).reshape(-1).tolist()) for component in components]
    instrument = np.asarray(normalize(np.sum(instrument_views, axis=0).tolist()))
    return float(np.max(np.abs(instrument - stages["final_matrix"])))


def run(output):
    b = baseline()
    frozen = json.loads((output / "FREEZE.json").read_text())
    freeze_id = frozen.pop("freeze_sha256")
    assert hashlib.sha256(canonical(frozen)).hexdigest() == freeze_id
    assert verify_previous() == frozen["previous_manifest_sha256"]
    for name, expected in frozen["code"].items():
        assert digest(ROOT / name) == expected and digest(output / "SOURCE_SNAPSHOT" / name) == expected, name
    for name, expected in frozen["inputs"].items():
        assert digest(output / name) == expected
    write_json(output / "STARTED.json", {"time": time.time(), "freeze_sha256": freeze_id})
    started = time.monotonic()
    protected = protected_identity()
    rows = json.loads((output / "BLIND.json").read_text())["items"]
    ids = [r["item_id"] for r in rows]
    prepared = {arm: {} for arm in ARMS}
    texts = set()
    for row in rows:
        prepared["current"][row["item_id"]] = prepare_candidate(row["candidate"], row["source_text"])
        prepared["project_identity"][row["item_id"]] = prepare_identity_candidate(row["candidate"], row["source_text"], project_id=row["project_id"], registry_csv=row["registry_csv"])
        for arm in ARMS:
            texts.update(semantic_texts(prepared[arm][row["item_id"]]))
    regression = {}
    for dataset in ("ORIGINAL", "HOLDOUT"):
        regression[dataset] = json.loads((PREVIOUS / f"{dataset}_BLIND.json").read_text())["items"]
        for row in regression[dataset]:
            p = prepare_candidate(row["candidates"]["shipping_fallback"], row["source_text"])
            assert p == prepare_identity_candidate(row["candidates"]["shipping_fallback"], row["source_text"])
            texts.update(semantic_texts(p))
    write_json(output / "PREPARED.json", prepared)
    print(json.dumps({"stage": "prepared", "identity_items": len(rows), "regression_items": 192, "embedding_texts": len(texts)}), flush=True)
    embeddings = embed_texts(sorted(texts))
    arrays = {"ids": np.asarray(ids), "embedding_texts": np.asarray(sorted(texts)), "embeddings384": np.asarray([embeddings[t] for t in sorted(texts)])}
    integrity = {"deterministic": True, "finite_norm_one_nonzero": True, "assembly_parity": True}
    for arm in ARMS:
        stage_rows = {}
        for identifier in ids:
            result, stages = trace(prepared[arm][identifier], embeddings)
            integrity["deterministic"] &= result == compile_prepared(prepared[arm][identifier], embeddings)
            value = stages["final_matrix"]
            integrity["finite_norm_one_nonzero"] &= bool(np.isfinite(value).all() and abs(np.linalg.norm(value) - 1) <= 1e-12 and not np.any(value == 0))
            integrity["assembly_parity"] &= assembly_error(stages) <= 1e-12
            for name, stage in stages.items():
                stage_rows.setdefault(name, []).append(stage)
        for name, values in stage_rows.items():
            arrays[arm + "__" + name] = np.stack(values)
        print(json.dumps({"stage": "compiled", "arm": arm}), flush=True)
    old_arrays = np.load(PREVIOUS / "STAGE_VECTORS.npz", allow_pickle=False)
    regression_report = {}
    for dataset, records in regression.items():
        matrices = []
        old_ids = [str(x) for x in old_arrays[dataset + "__ids"]]
        maximum_error = 0.0
        for row in records:
            p = prepare_identity_candidate(row["candidates"]["shipping_fallback"], row["source_text"])
            value = np.asarray(compile_prepared(p, embeddings)["matrix"])
            reference_index = old_ids.index(row["item_id"])
            reference = old_arrays[dataset + "__typed__final_matrix"][reference_index]
            maximum_error = max(maximum_error, float(np.max(np.abs(value - reference))))
            matrices.append(value)
        arrays[dataset + "__regression_ids"] = np.asarray([r["item_id"] for r in records])
        arrays[dataset + "__regression_matrices"] = np.stack(matrices)
        regression_report[dataset] = {"items": len(records), "maximum_reference_error": maximum_error, "unchanged": maximum_error <= 1e-12, "unannotated_prepared_inputs_byte_equal": True}
    with (output / "STAGE_VECTORS.npz").open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    write_json(output / "STAGE_ARCHIVE_FROZEN.json", {"sha256": digest(output / "STAGE_VECTORS.npz"), "scorer_key_read": False})
    # Only now read the expected identity/paraphrase/alias relationships.
    key = json.loads((output / "SCORER_KEY.json").read_text())
    outcomes = {}
    for arm in ARMS:
        cases = []
        totals = {"basis_pass": 0, "nearest_pass": 0, "margin_pass": 0, "substitution_pass": 0, "alias_exact": 0, "distinct": 0}
        for family in key["sets"]:
            stage_scores = {}
            role_ids = {role: family["item_by_role"][role] for role in ("V1", "V2", "V3", "P2")}
            for stage in STAGES:
                vectors = {identifier: arrays[arm + "__" + stage][ids.index(identifier)] for identifier in role_ids.values()}
                stage_scores[stage] = b.score_set(role_ids, vectors)
            final = stage_scores["final_matrix"]
            v2 = arrays[arm + "__final_matrix"][ids.index(family["item_by_role"]["V2"])]
            alias = arrays[arm + "__final_matrix"][ids.index(family["item_by_role"]["A2"])]
            canonical_values = [arrays[arm + "__final_matrix"][ids.index(family["item_by_role"][r])] for r in ("V1", "V2", "V3")]
            distinct = all(not np.array_equal(canonical_values[i], canonical_values[j]) for i in range(3) for j in range(i))
            totals["basis_pass"] += int(final["canonical_basis"]["passes"])
            totals["nearest_pass"] += int(final["p2_nearest"] == "V2")
            totals["margin_pass"] += int(final["p2_changed_over_same_distance_ratio"] >= 1.25)
            totals["substitution_pass"] += int(final["paraphrase_substitution_basis"]["passes"])
            totals["alias_exact"] += int(np.array_equal(v2, alias))
            totals["distinct"] += int(distinct)
            cases.append({"case_id": family["case_id"], "category": family["category"], "stages": stage_scores, "alias_exact": np.array_equal(v2, alias), "alias_max_error": float(np.max(np.abs(v2 - alias))), "distinct": distinct})
        directions = []
        for pair in key["directions"]:
            forward = arrays[arm + "__final_matrix"][ids.index(pair["forward"])].reshape(32, 32)
            reverse = arrays[arm + "__final_matrix"][ids.index(pair["reverse"])].reshape(32, 32)
            directions.append({"case_id": pair["case_id"], "transpose_error": float(np.linalg.norm(forward.T - reverse)), "identical": np.array_equal(forward, reverse)})
        direction_pass = all(d["transpose_error"] <= 1e-12 and not d["identical"] for d in directions)
        outcomes[arm] = {"decision": "GREEN" if all(x == 12 for x in totals.values()) and direction_pass else "RED", "totals": totals, "cases": cases, "directions": directions, "directions_pass": direction_pass}
    integrity["tracked_worktree_unchanged"] = protected == protected_identity()
    integrity["frozen_code_unchanged"] = all(digest(ROOT / name) == value for name,value in frozen["code"].items())
    integrity["old_experiment_unchanged"] = verify_previous() == frozen["previous_manifest_sha256"]
    code_owners = {}; collisions = []
    for p in prepared["project_identity"].values():
        for event in p["events"]:
            for field in event["fields"].values():
                if field["symbols"]:
                    bits = np.asarray(symbol_vector(field["symbols"])).tobytes().hex()
                    signature = canonical(field["symbols"]).decode()
                    if bits in code_owners and code_owners[bits] != signature:
                        collisions.append([signature, code_owners[bits]])
                    code_owners[bits] = signature
    integrity["no_observed_code_collisions"] = not collisions
    decision = "GREEN" if outcomes["project_identity"]["decision"] == "GREEN" and all(integrity.values()) and all(r["unchanged"] for r in regression_report.values()) else "RED"
    report = {"version": "project-identity-compiler-result/1", "freeze_sha256": freeze_id, "decision": decision,
              "arms": outcomes, "regression": regression_report, "integrity": integrity, "elapsed_seconds": time.monotonic() - started,
              "calls": {"local_embedding_texts": len(texts), "model_generations": 0, "provider": 0, "tree": 0, "memory": 0},
              "claim_boundary": "synthetic supplied project-register compiler diagnostic; no extraction, Tree, product or arithmetic claim"}
    write_json(output / "RESULT.json", report)
    lines = ["# Project identity compiler diagnostic", "", f"**{decision}: local identity experiment only. The earlier typed-compiler RED is unchanged.**", "", f"Freeze: `{freeze_id}`", "", "| Arm | Basis | Paraphrase nearest | Margin | Substitution | Exact alias equality | Distinct identities |", "|---|---:|---:|---:|---:|---:|---:|"]
    for arm,outcome in outcomes.items():
        t = outcome["totals"]
        lines.append(f"| {arm} | {t['basis_pass']}/12 | {t['nearest_pass']}/12 | {t['margin_pass']}/12 | {t['substitution_pass']}/12 | {t['alias_exact']}/12 | {t['distinct']}/12 |")
    lines += ["", "All 192 unannotated regression events are checked against the retained v1 matrices. See RESULT.json for exact errors and each stage's metrics.", "", "Inputs are manually supplied events and synthetic project registers. Same-label cross-project separation uses additional project-record information; it is not recovered from the labels. Ambiguous labels within one project are rejected. No automatic entity resolution or paragraph extraction was tested.", "", "Embedding, symbol, projection, component, view and aggregate arrays are saved in STAGE_VECTORS.npz before scoring. No weights, seeds or pass thresholds were tuned after scoring."]
    with (output / "REPORT.md").open("x") as handle:
        handle.write("\n".join(lines) + "\n")
    manifest = {str(p.relative_to(output)): {"sha256": digest(p), "bytes": p.stat().st_size} for p in output.rglob("*") if p.is_file()}
    write_json(output / "MANIFEST.json", {"freeze_sha256": freeze_id, "files": manifest})
    print(json.dumps({"decision": decision, "totals": {arm: r["totals"] for arm,r in outcomes.items()}, "report": str(output / "REPORT.md")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "run"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "validation/runs"):
        raise SystemExit("output must be a new workspace validation/runs directory")
    freeze(output) if args.phase == "freeze" else run(output)


if __name__ == "__main__":
    main()
