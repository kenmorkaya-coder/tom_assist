"""Frozen local-only extraction experiment. No Tree integration or network calls."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gateway.typed_event_graph import canonical, digest, semantic_graph, validate_graph
from gateway.event_graph_extractor import prompt, parse_output, quote_only
from gateway.event_graph_compiler import compile_graph

HERE = Path(__file__).parent
MODEL = Path.home() / ".cache/huggingface/hub/models--mlx-community--gemma-4-26b-a4b-it-4bit/snapshots/0d77464eeb233a2da68ebf9d7dc4edaac7db956d"
CONFIG = {"seed": 7, "train": True, "test": False, "fine_tune_type": "lora", "num_layers": 8,
          "batch_size": 1, "iters": 128, "val_batches": 4, "learning_rate": 0.0001,
          "steps_per_report": 1, "steps_per_eval": 32, "save_every": 32,
          "max_seq_length": 4096, "grad_checkpoint": True, "mask_prompt": True,
          "lora_parameters": {"rank": 8, "dropout": 0.0, "scale": 16.0, "keys": ["self_attn.q_proj", "self_attn.v_proj"]}}


def read_rows(split):
    return [json.loads(line) for line in (HERE / "data" / f"{split}.jsonl").read_text().splitlines()]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2) + "\n")


def verify_freeze(run):
    freeze = json.loads((run / "freeze.json").read_text())
    for name, expected in freeze["files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError(f"frozen file changed: {name}")
    for name, expected in freeze["model"].items():
        if sha(MODEL / name) != expected:
            raise ValueError(f"model file changed: {name}")
    return freeze


def freeze(run):
    files = [ROOT / "gateway" / name for name in ("typed_event_graph.py", "event_graph_compiler.py", "event_graph_extractor.py")]
    files.append(ROOT / "gateway/tests/test_event_graph_v1.py")
    files += sorted(p for p in HERE.rglob("*") if p.is_file() and (p.suffix in (".py", ".json", ".jsonl", ".md")) and "__pycache__" not in p.parts)
    corpora = {s: read_rows(s) for s in ("train", "dev", "heldout")}
    sources = {s: {r["source"] for r in rows} for s, rows in corpora.items()}
    if any(sources[a] & sources[b] for a, b in (("train", "dev"), ("train", "heldout"), ("dev", "heldout"))):
        raise ValueError("split leakage")
    for rows in corpora.values():
        groups = defaultdict(dict)
        for r in rows:
            validate_graph(r["graph"], r["source"])
            groups[r["group"]][r["variant"]] = semantic_graph(r["graph"])
        for variants in groups.values():
            if variants["canonical"] != variants["paraphrase"] or variants["canonical"] == variants["contrast"]:
                raise ValueError("invalid contrast label")
    write_new(run / "freeze.json", {"version": 1, "created_unix": time.time(), "training": CONFIG,
        "files": {str(p.relative_to(ROOT)): sha(p) for p in files},
        "model": {p.name: sha(p) for p in sorted(MODEL.iterdir()) if p.suffix in (".safetensors", ".json", ".jinja")},
        "counts": {s: len(rows) for s, rows in corpora.items()},
        "thresholds": {"valid": 1.0, "exact": .95, "family_exact": .90, "invented_authority": 0, "contrast_distinct": 1.0,
                       "paraphrase_equal": .95, "matrix_margin": .05, "condition_number_max": 10.0}})


def score_extraction(rows, predictions, thresholds):
    expected_ids = {r["id"] for r in rows}
    if len({p["id"] for p in predictions}) != len(predictions) or any(p["id"] not in expected_ids for p in predictions):
        raise ValueError("duplicate or unexpected prediction id")
    by_id = {p["id"]: p for p in predictions}
    families = defaultdict(Counter)
    fields = Counter()
    valid = exact = invented = 0
    comparisons = defaultdict(dict)
    details = []
    for row in rows:
        family = families[row["family"]]; family["total"] += 1
        prediction = by_id.get(row["id"], {})
        correct = False
        error = prediction.get("error", "missing prediction")
        try:
            graph = validate_graph(prediction["graph"], row["source"])
            if graph["unresolved"]:
                raise ValueError("unresolved extraction")
            actual, expected = semantic_graph(graph), semantic_graph(row["graph"])
            valid += 1; family["valid"] += 1
            correct = actual == expected
            comparisons[row["group"]][row["variant"]] = actual
            # Fail any unsupported authority assignment; source order is required.
            for index, event in enumerate(actual["events"]):
                auth = event["roles"]["authority"]
                expected_auth = expected["events"][index]["roles"]["authority"] if index < len(expected["events"]) else None
                invented += bool(auth is not None and auth != expected_auth)
            for key in ("action", "roles", "modality", "negated", "condition", "exception", "complement", "revision", "time"):
                fields[key] += [e[key] for e in actual["events"]] == [e[key] for e in expected["events"]]
            fields["links"] += actual["links"] == expected["links"]
            error = None if correct else "semantic mismatch"
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            error = str(exc)
        exact += correct; family["exact"] += correct
        details.append({"id": row["id"], "exact": correct, "error": error})
    groups = {r["group"] for r in rows}
    para = contrast = 0
    for key in groups:
        group = comparisons[key]
        para += "canonical" in group and "paraphrase" in group and group["canonical"] == group["paraphrase"]
        contrast += "canonical" in group and "contrast" in group and group["canonical"] != group["contrast"]
    total = len(rows)
    green = (valid / total >= thresholds["valid"] and exact / total >= thresholds["exact"] and
             all(c["exact"] / c["total"] >= thresholds["family_exact"] for c in families.values()) and
             invented <= thresholds["invented_authority"] and para / len(groups) >= thresholds["paraphrase_equal"] and
             contrast / len(groups) >= thresholds["contrast_distinct"])
    return {"verdict": "GREEN" if green else "RED", "total": total, "valid": valid, "exact": exact,
            "invented_authority": invented, "paraphrase_equal": para, "contrast_distinct": contrast,
            "groups": len(groups), "families": dict(families), "field_exact": dict(fields), "details": details}


def train(run):
    frozen = verify_freeze(run)
    from types import SimpleNamespace
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    lengths = []
    for name in ("train", "valid"):
        for line in (HERE / "training" / f"{name}.jsonl").read_text().splitlines():
            lengths.append(len(tokenizer.apply_chat_template(json.loads(line)["messages"], return_dict=False)))
    if max(lengths) > frozen["training"]["max_seq_length"]:
        raise ValueError("training context would truncate labels")
    if {n: importlib.metadata.version(n) for n in ("mlx", "mlx-lm")} != {"mlx": "0.31.1", "mlx-lm": "0.31.2"}:
        raise ValueError("training runtime version mismatch")
    import mlx.core as mx
    from mlx_lm.lora import CONFIG_DEFAULTS, run as train_run
    import numpy as np
    mx.random.seed(CONFIG["seed"]); np.random.seed(CONFIG["seed"])
    config = {**CONFIG_DEFAULTS, **frozen["training"], "model": str(MODEL), "data": str(HERE / "training"), "adapter_path": str(run / "adapter")}
    if (run / "training_started.json").exists():
        raise ValueError("training already started; preserve run and use a new preregistered run")
    write_new(run / "training_started.json", {"config": config, "versions": {n: importlib.metadata.version(n) for n in ("mlx", "mlx-lm")}, "time": time.time()})
    train_run(SimpleNamespace(**config))
    write_new(run / "training_complete.json", {"time": time.time(), "adapter": sha(run / "adapter" / "adapters.safetensors"), "iterations": config["iters"]})


def infer(run, split):
    frozen = verify_freeze(run)
    complete = json.loads((run / "training_complete.json").read_text())
    if sha(run / "adapter" / "adapters.safetensors") != complete["adapter"]:
        raise ValueError("adapter changed")
    output = run / f"{split}_predictions.jsonl"
    if output.exists():
        raise ValueError("predictions already exist; refusing repeated held-out use")
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7)
    model, tokenizer = load(str(MODEL), adapter_path=str(run / "adapter"))
    sampler = make_sampler(temp=0.0)
    with output.open("x") as stream:
        for row in read_rows(split):
            start = time.time()
            formatted = tokenizer.apply_chat_template([{"role": "user", "content": prompt(row["source"])}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            raw = generate(model, tokenizer, prompt=formatted, max_tokens=4096, sampler=sampler, verbose=False)
            prediction = {"id": row["id"], "raw": raw, "seconds": time.time() - start}
            try:
                prediction["graph"] = parse_output(raw, row["source"])
            except (ValueError, TypeError, KeyError, RecursionError) as exc:
                prediction["error"] = str(exc)
            stream.write(json.dumps(prediction) + "\n"); stream.flush()
            print(json.dumps({"id": row["id"], "seconds": prediction["seconds"], "valid": "graph" in prediction}), flush=True)
    predictions = [json.loads(line) for line in output.read_text().splitlines()]
    report = score_extraction(read_rows(split), predictions, frozen["thresholds"])
    report.update(adapter_sha256=complete["adapter"], prediction_sha256=sha(output), local_generations=len(predictions), cloud_generations=0)
    write_new(run / f"{split}_extraction_report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("details", "families")}))


def matrix_gate(run):
    frozen = verify_freeze(run)
    report = json.loads((run / "heldout_extraction_report.json").read_text())
    predictions_path = run / "heldout_predictions.jsonl"
    predictions = [json.loads(line) for line in predictions_path.read_text().splitlines()]
    # Recompute rather than trusting a manually edited verdict file.
    extraction = score_extraction(read_rows("heldout"), predictions, frozen["thresholds"])
    if report["prediction_sha256"] != sha(predictions_path) or extraction["verdict"] != "GREEN":
        raise ValueError("held-out extraction is not GREEN; matrix and Tree gates blocked")
    import numpy as np
    by_id = {p["id"]: p["graph"] for p in predictions}
    groups = defaultdict(dict)
    artifacts = []
    conditioning = True
    for row in read_rows("heldout"):
        compiled = compile_graph(by_id[row["id"]], row["source"])
        if compiled != compile_graph(by_id[row["id"]], row["source"]):
            raise ValueError("nondeterministic compiler")
        mats = np.array([load["matrix"] for load in compiled["loads"]])
        svs = [np.linalg.svd(m, compute_uv=False) for m in mats]
        stats = [{"rank": int(np.sum(s > 1e-10)), "condition": float(s[0] / s[2])} for s in svs]
        conditioning &= all(s["rank"] == 3 and s["condition"] <= 10 for s in stats)
        groups[row["group"]][row["variant"]] = mats
        artifacts.append({"id": row["id"], "compiled": compiled, "conditioning": stats,
                          "ablation": compile_graph(by_id[row["id"]], row["source"], ablate_symbols=True)})
    passes = 0
    details = []
    for group, variants in groups.items():
        a, p, c = (variants[k] for k in ("canonical", "paraphrase", "contrast"))
        if a.shape != p.shape or a.shape != c.shape:
            good, equivalent, changed = False, None, None
        else:
            equivalent = float(np.linalg.norm(a-p)); changed = float(np.linalg.norm(a-c))
            good = equivalent <= 1e-8 and changed - equivalent >= frozen["thresholds"]["matrix_margin"]
        passes += good
        details.append({"group": group, "pass": good, "paraphrase_distance": equivalent, "contrast_distance": changed})
    write_new(run / "matrix_artifacts.json", artifacts)
    write_new(run / "matrix_report.json", {"verdict": "GREEN" if passes == len(groups) and conditioning else "RED", "groups": len(groups), "passes": passes,
        "conditioning": conditioning, "details": details, "tree_test": "NOT_RUN: original regression and independent review remain required"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "verify", "train", "infer", "matrix"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--split", choices=("dev", "heldout"), default="heldout")
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    if args.command == "freeze": freeze(args.run)
    elif args.command == "verify": verify_freeze(args.run)
    elif args.command == "train": train(args.run)
    elif args.command == "infer": infer(args.run, args.split)
    else: matrix_gate(args.run)

if __name__ == "__main__":
    main()
