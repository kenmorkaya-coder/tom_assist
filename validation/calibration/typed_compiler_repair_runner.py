#!/usr/bin/env python3
"""Freeze and execute the offline typed compiler repair; never loads a Tree."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
BASELINE = Path("/Volumes/My Passport for Mac/TomAssist/compiler-discrimination-20260909-run-001")
EXPECTED_BASELINE_FREEZE = "803560b22f846d6f313f5417c3c75798dcd6238f2b5aa2616e73e7ab7ced2704"
ARMS = ("typed", "symbol_ablation")
CODE_FILES = (
    "gateway/typed_matrix_compiler.py", "gateway/matrix_events.py",
    "gateway/document_ingestion.py", "gateway/document_embedding_worker.py",
    "gateway/tests/test_typed_matrix_compiler.py",
    "validation/calibration/matrix_event_scaw_runner.py",
    "validation/calibration/matrix_tree_32sq_runner.py",
    "validation/calibration/typed_compiler_repair_runner.py",
    "validation/calibration/typed_compiler_repair_holdout.py",
    "validation/calibration/TYPED_COMPILER_REPAIR_V1_DESIGN.md",
)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    with path.open("xb") as handle:
        handle.write(canonical(value) + b"\n")


def baseline():
    manifest = json.loads((BASELINE / "MANIFEST.json").read_text())
    assert manifest["complete_freeze_sha256"] == EXPECTED_BASELINE_FREEZE
    for name, row in manifest["files"].items():
        assert (BASELINE / name).stat().st_size == row["bytes"]
        assert digest(BASELINE / name) == row["sha256"], name
    spec = importlib.util.spec_from_file_location("frozen_compiler_discrimination", BASELINE / "runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def freeze(output):
    from validation.calibration.typed_compiler_repair_holdout import cases
    b = baseline()
    original = json.loads((BASELINE / "BLIND_INPUT.json").read_text())
    original_key = json.loads((BASELINE / "SCORER_KEY.json").read_text())
    b.CASES = cases(b)
    holdout, holdout_key = b.build_inputs()
    assert len(holdout["items"]) == 96 and len(holdout_key["sets"]) == 24
    assert len({r["source_text"] for r in holdout["items"]}) == 96
    assert not ({r["source_text"] for r in holdout["items"]} & {r["source_text"] for r in original["items"]})
    assert Counter(s["category"] for s in holdout_key["sets"]) == Counter(s["category"] for s in original_key["sets"])
    output.mkdir(parents=True, exist_ok=False)
    for name in CODE_FILES:
        target = output / "SOURCE_SNAPSHOT" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    write_json(output / "ORIGINAL_BLIND.json", original)
    write_json(output / "ORIGINAL_KEY.json", original_key)
    write_json(output / "HOLDOUT_BLIND.json", holdout)
    write_json(output / "HOLDOUT_KEY.json", holdout_key)
    record = {"version": "typed-compiler-repair-freeze/1", "baseline_freeze": EXPECTED_BASELINE_FREEZE,
              "code": {name: digest(ROOT / name) for name in CODE_FILES},
              "inputs": {name: digest(output / name) for name in ("ORIGINAL_BLIND.json", "ORIGINAL_KEY.json", "HOLDOUT_BLIND.json", "HOLDOUT_KEY.json")},
              "gate": {"basis_rank": 3, "condition_max": 10, "paraphrase_ratio": 1.25, "margin_total_min": 22, "margin_category_min": 2, "orientation_max": 1e-12},
              "symbol_mix": "normalize(unit_semantic32 + unit_symbol32)", "matrix_weights": [1, 0.5, 0.25], "projection_seed": 539362568,
              "claim_boundary": "compiler-only manually supplied events; no Tree, generation, retrieval or product verdict"}
    record["freeze_sha256"] = hashlib.sha256(canonical(record)).hexdigest()
    write_json(output / "FREEZE.json", record)
    print(json.dumps({"frozen": str(output), "freeze_sha256": record["freeze_sha256"]}), flush=True)


def protected_identity():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    return {name: digest(ROOT / name) if (ROOT / name).is_file() else None for name in names if name}


def score_dataset(b, key, ids, values, errors, arm):
    sets, categories, orientation = [], {}, []
    for row in key["sets"]:
        category = row["category"]
        count = categories.setdefault(category, {"sets": 0, "basis_pass": 0, "nearest_pass": 0, "margin_pass": 0, "substitution_pass": 0, "unsupported": 0})
        count["sets"] += 1
        unsupported = {item: errors[item] for item in row["item_by_role"].values() if item in errors}
        if unsupported:
            count["unsupported"] += 1
            sets.append({"case_id": row["case_id"], "category": category, "supported": False, "errors": unsupported})
            continue
        mapping = {item: values[ids.index(item)] for item in row["item_by_role"].values()}
        metrics = b.score_set(row["item_by_role"], mapping)
        count["basis_pass"] += int(metrics["canonical_basis"]["passes"])
        count["nearest_pass"] += int(metrics["p2_nearest"] == "V2")
        count["margin_pass"] += int(metrics["p2_changed_over_same_distance_ratio"] >= 1.25)
        count["substitution_pass"] += int(metrics["paraphrase_substitution_basis"]["passes"])
        sets.append({"case_id": row["case_id"], "category": category, "supported": True, "metrics": metrics})
        if row["directional"]:
            left = mapping[row["item_by_role"]["V1"]].reshape(32, 32)
            right = mapping[row["item_by_role"]["V2"]].reshape(32, 32)
            error = float(np.linalg.norm(left.T - right) / np.linalg.norm(left))
            orientation.append({"case_id": row["case_id"], "transpose_error": error, "identical": np.array_equal(left, right)})
    totals = {name: sum(c[name] for c in categories.values()) for name in ("sets", "basis_pass", "nearest_pass", "margin_pass", "substitution_pass", "unsupported")}
    checks = {
        "all_items_supported": not errors,
        "all_bases_pass": totals["basis_pass"] == 24,
        "all_nearest_pass": totals["nearest_pass"] == 24,
        "margin_gate": totals["margin_pass"] >= 22 and all(c["margin_pass"] >= 2 for c in categories.values()),
        "all_substitutions_pass": totals["substitution_pass"] == 24,
        "all_orientations_pass": len(orientation) == 9 and all(v["transpose_error"] <= 1e-12 and not v["identical"] for v in orientation),
    }
    return {"arm": arm, "decision": "GREEN" if all(checks.values()) else "RED", "checks": checks, "totals": totals,
            "categories": categories, "sets": sets, "orientation": orientation}


def execute(output):
    from gateway.typed_matrix_compiler import UnsupportedTypedEvent, prepare_candidate, semantic_texts, compile_prepared, symbol_vector
    from validation.calibration.matrix_event_scaw_runner import embed_texts
    b = baseline()
    frozen = json.loads((output / "FREEZE.json").read_text())
    freeze_id = frozen.pop("freeze_sha256")
    assert hashlib.sha256(canonical(frozen)).hexdigest() == freeze_id
    for name, expected in frozen["code"].items():
        assert digest(ROOT / name) == expected, name
        assert digest(output / "SOURCE_SNAPSHOT" / name) == expected, name
    for name, expected in frozen["inputs"].items():
        assert digest(output / name) == expected, name
    if (output / "STARTED.json").exists():
        raise SystemExit("frozen run already started; no overwrite/retry into this run")
    write_json(output / "STARTED.json", {"freeze_sha256": freeze_id, "started_unix": time.time()})
    started = time.monotonic()
    protected = protected_identity()
    write_json(output / "PROTECTED_BEFORE.json", protected)
    prepared, errors, ids, texts = {}, {}, {}, set()
    # Compilation sees only blind event inputs. Scorer keys are not loaded yet.
    for dataset in ("ORIGINAL", "HOLDOUT"):
        rows = json.loads((output / f"{dataset}_BLIND.json").read_text())["items"]
        prepared[dataset], errors[dataset] = {}, {}
        ids[dataset] = [row["item_id"] for row in rows]
        for row in rows:
            assert hashlib.sha256(row["source_text"].encode()).hexdigest() == row["source_sha256"]
            try:
                p = prepare_candidate(row["candidates"]["shipping_fallback"], row["source_text"])
                prepared[dataset][row["item_id"]] = p
                texts.update(semantic_texts(p))
            except UnsupportedTypedEvent as error:
                errors[dataset][row["item_id"]] = str(error)
    write_json(output / "PREPARED.json", prepared)
    write_json(output / "UNSUPPORTED.json", errors)
    print(json.dumps({"stage": "prepared", "items": {k: len(v) for k, v in prepared.items()}, "unsupported": {k: len(v) for k, v in errors.items()}, "embedding_texts": len(texts)}), flush=True)
    embeddings = embed_texts(sorted(texts))
    arrays, integrity = {}, {"deterministic": True, "finite_norm_one_nonzero": True, "symbol_collisions": []}
    symbol_codes = {}
    for dataset in prepared:
        arrays[dataset + "__ids"] = np.asarray(ids[dataset])
        for p in prepared[dataset].values():
            for event in p["events"]:
                for field in event["fields"].values():
                    if field["symbols"]:
                        code = np.asarray(symbol_vector(field["symbols"])).tobytes().hex()
                        signature = canonical(field["symbols"]).decode()
                        if code in symbol_codes and symbol_codes[code] != signature:
                            integrity["symbol_collisions"].append([signature, symbol_codes[code]])
                        symbol_codes[code] = signature
        for arm in ARMS:
            matrices, fields = [], []
            for item in ids[dataset]:
                if item in errors[dataset]:
                    matrices.append(np.zeros(1024)); fields.append(np.zeros(128)); continue
                p = prepared[dataset][item]
                result = compile_prepared(p, embeddings, ablate_symbols=arm == "symbol_ablation")
                repeated = compile_prepared(p, embeddings, ablate_symbols=arm == "symbol_ablation")
                integrity["deterministic"] &= result == repeated
                value = np.asarray(result["matrix"], dtype=np.float64)
                integrity["finite_norm_one_nonzero"] &= bool(np.isfinite(value).all() and abs(np.linalg.norm(value) - 1) <= 1e-12 and not np.any(value == 0))
                matrices.append(value)
                fields.append(np.concatenate([result["events"][0]["fields32"][name] for name in ("source", "target", "relation", "context")]))
            arrays[dataset + "__" + arm + "__final_matrix"] = np.stack(matrices)
            arrays[dataset + "__" + arm + "__fields32"] = np.stack(fields)
        print(json.dumps({"stage": "compiled", "dataset": dataset}), flush=True)
    with (output / "STAGE_VECTORS.npz").open("xb") as handle:
        np.savez_compressed(handle, **arrays)
    write_json(output / "STAGE_ARCHIVE_FROZEN.json", {"sha256": digest(output / "STAGE_VECTORS.npz"), "scorer_keys_read": False})
    results = {}
    for dataset in prepared:
        key = json.loads((output / f"{dataset}_KEY.json").read_text())
        results[dataset] = {arm: score_dataset(b, key, ids[dataset], arrays[dataset + "__" + arm + "__final_matrix"], errors[dataset], arm) for arm in ARMS}
    integrity["protected_tracked_files_unchanged"] = protected == protected_identity()
    integrity["frozen_code_unchanged"] = all(digest(ROOT / name) == expected for name, expected in frozen["code"].items())
    integrity["baseline_manifest_unchanged"] = True
    baseline()
    all_green = all(results[k]["typed"]["decision"] == "GREEN" for k in results) and all(v for k,v in integrity.items() if k != "symbol_collisions") and not integrity["symbol_collisions"]
    report = {"version": "typed-compiler-repair-result/1", "freeze_sha256": freeze_id, "decision": "GREEN" if all_green else "RED",
              "datasets": results, "integrity": integrity, "elapsed_seconds": time.monotonic() - started,
              "calls": {"local_embedding_texts": len(texts), "model_generations": 0, "provider": 0, "tree": 0, "memory": 0},
              "claim_boundary": frozen["claim_boundary"], "unsupported": errors}
    write_json(output / "RESULT.json", report)
    lines = ["# Typed compiler repair v1", "", f"**{report['decision']} — compiler-only, not an app or Tree verdict.**", "", f"Freeze: `{freeze_id}`", "", "| Dataset / arm | Basis | Nearest | Margin | Substitution | Unsupported sets |", "|---|---:|---:|---:|---:|---:|"]
    for dataset, arms in results.items():
        for arm, outcome in arms.items():
            t = outcome["totals"]
            lines.append(f"| {dataset} / {arm} | {t['basis_pass']}/24 | {t['nearest_pass']}/24 | {t['margin_pass']}/24 | {t['substitution_pass']}/24 | {t['unsupported']} |")
    lines.extend(["", "Unsupported items are failures, not removed from denominators. Original inputs and gates were preserved. No post-score tuning.", "", "Exact symbols use deterministic identity codes, not arithmetic ordering in cosine space. English extraction, dates, IDs, arbitrary ranges and compound condition scopes are not validated by this bounded experiment.", "", "See RESULT.json for all per-set metrics, integrity and call counts; PREPARED.json for exact spans/canonical symbols; STAGE_VECTORS.npz for field and matrix arrays."])
    with (output / "REPORT.md").open("x") as handle:
        handle.write("\n".join(lines) + "\n")
    files = {str(p.relative_to(output)): {"sha256": digest(p), "bytes": p.stat().st_size} for p in output.rglob("*") if p.is_file()}
    write_json(output / "MANIFEST.json", {"freeze_sha256": freeze_id, "files": files})
    print(json.dumps({"decision": report["decision"], "report": str(output / "REPORT.md"), "results": {d: {a: r["totals"] for a,r in arms.items()} for d,arms in results.items()}}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "run"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "validation" / "runs"):
        raise SystemExit("experiment output must be a new workspace validation/runs directory")
    freeze(output) if args.phase == "freeze" else execute(output)


if __name__ == "__main__":
    main()
