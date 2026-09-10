"""Source-span protocol: two development-scored epochs from the pinned base."""
from __future__ import annotations
import argparse
from collections import Counter
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from validation.event_graph_v4 import experiment as prior
from gateway.event_graph_span_extractor import prompt, parse_output
from gateway.gemma_training_alignment import AlignedChatTokenizer, check_alignment

HERE = Path(__file__).parent
PARENT = ROOT / ".tmp/event-graph-lora-v4-run-001"
PLAN = {"epochs": 2, "steps_per_epoch": 960, "seeds": [61, 73],
        "learning_rate": 0.0001, "baseline_steps": 0,
        "initialization": "pinned base, fresh LoRA; optimizer reset each epoch",
        "selection": "exact, valid, fewer invented authorities, paraphrase, contrast, earliest"}


def read_rows(split):
    return [json.loads(x) for x in (HERE/'data'/f'{split}.jsonl').read_text().splitlines()]


def stage(run, epoch):
    if epoch not in (0, 1, 2):
        raise ValueError("epoch must be 0, 1 or 2")
    return run / f"epoch-{epoch}"


def verify(run):
    frozen=json.loads((run/'freeze.json').read_text())
    if prior.sha(PARENT/'freeze.json') != frozen['parent_freeze']:
        raise ValueError('parent freeze changed')
    prior.verify_freeze(PARENT)
    for name,expected in frozen['files'].items():
        if prior.sha(ROOT/name)!=expected:raise ValueError(f'frozen source changed: {name}')
    return frozen


def freeze(run):
    parent=prior.verify_freeze(PARENT)
    paths=[p for p in HERE.rglob('*') if p.is_file() and p.suffix in ('.py','.md','.json','.jsonl')]
    paths += [ROOT/p for p in ('gateway/event_graph_span_wire.py','gateway/event_graph_span_extractor.py',
        'gateway/tests/test_event_graph_span_wire.py','gateway/tests/test_event_graph_span_extractor.py')]
    preflight=json.loads((HERE/'PREFLIGHT.json').read_text())
    assert preflight['train']['count']==960 and preflight['valid']['count']==132
    assert max(v['max_tokens'] for v in preflight.values()) <= prior.CONFIG['max_seq_length']
    prior.write_new(run/'freeze.json',{'created_unix':time.time(),'plan':PLAN,
        'files':{str(p.relative_to(ROOT)):prior.sha(p) for p in paths},
        'parent_freeze':prior.sha(PARENT/'freeze.json'),'thresholds':parent['thresholds'],
        'development_records':132,'preflight':preflight})


def adapter(run, epoch):
    if epoch == 0:
        return None
    directory = stage(run, epoch)
    complete = json.loads((directory / "training_complete.json").read_text())
    path = directory / "adapter"
    if prior.sha(path / "adapters.safetensors") != complete["adapter"]:
        raise ValueError("completed adapter changed")
    if prior.sha(path / "adapter_config.json") != complete["config_sha256"]:
        raise ValueError("completed adapter configuration changed")
    return path


def train(run, epoch):
    frozen = verify(run)
    if epoch not in (1, 2):
        raise ValueError("only epochs 1 and 2 can train")
    directory = stage(run, epoch)
    previous = adapter(run, epoch - 1)
    versions = {n: importlib.metadata.version(n) for n in ("mlx", "mlx-lm")}
    if versions != {"mlx": "0.31.1", "mlx-lm": "0.31.2"}:
        raise ValueError("runtime version mismatch")
    from types import SimpleNamespace
    import mlx.core as mx
    import numpy as np
    from mlx_lm import load
    from mlx_lm.lora import CONFIG_DEFAULTS, train_model
    from mlx_lm.tuner.datasets import load_dataset
    plan = frozen["plan"]
    seed = plan["seeds"][epoch - 1]
    config = {**CONFIG_DEFAULTS, **prior.CONFIG, "seed": seed,
        "iters": plan["steps_per_epoch"], "learning_rate": plan["learning_rate"],
        "steps_per_report": 16, "steps_per_eval": 480, "save_every": 960,
        "model": str(prior.MODEL), "data": str(HERE / "training"),
        "adapter_path": str(directory / "adapter"),
        "resume_adapter_file": str(previous / "adapters.safetensors") if previous else None}
    prior.write_new(directory / "training_started.json", {"time": time.time(),
        "config": config, "versions": versions, "optimizer_state": "reset",
        "input_adapter_sha256": prior.sha(previous / "adapters.safetensors") if previous else None})
    mx.random.seed(seed); np.random.seed(seed)
    model, tokenizer = load(str(prior.MODEL))
    for split in ("train", "valid"):
        for line in (HERE / "training" / f"{split}.jsonl").read_text().splitlines():
            result = check_alignment(tokenizer, json.loads(line)["messages"])
            if result["total_tokens"] > config["max_seq_length"]:
                raise ValueError("training label would be truncated")
    args = SimpleNamespace(**config)
    training, development, _ = load_dataset(args, AlignedChatTokenizer(tokenizer))
    if len(training) != plan["steps_per_epoch"]:
        raise ValueError("epoch inventory changed")
    train_model(args, model, training, development, training_callback=None)
    path = directory / "adapter"
    prior.write_new(directory / "training_complete.json", {"time": time.time(),
        "iterations": config["iters"], "cumulative_steps": 960 * epoch,
        "adapter": prior.sha(path / "adapters.safetensors"),
        "config_sha256": prior.sha(path / "adapter_config.json")})


def development_score(rows, predictions, thresholds):
    result = prior.score_extraction(rows, predictions, thresholds)
    result["development_thresholds_met"] = result.pop("verdict") == "GREEN"
    result["status"] = "DEVELOPMENT_ONLY_NOT_HELDOUT_GATE"
    result["parser_errors"] = dict(Counter(p["error"] for p in predictions if "graph" not in p))
    return result


def evaluate(run, epoch):
    frozen = verify(run)
    directory = stage(run, epoch)
    selected = adapter(run, epoch)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / "dev_predictions.jsonl"
    if output.exists():
        raise ValueError("development pass already started; preserve its record")
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7)
    model, tokenizer = load(str(prior.MODEL), adapter_path=str(selected))
    rows = read_rows("dev")
    sampler = make_sampler(temp=0.0)
    with output.open("x") as stream:
        for row in rows:
            start = time.time()
            text = tokenizer.apply_chat_template([{"role": "user", "content": prompt(row["source"])}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False)
            pieces = []; token_ids = []
            for chunk in stream_generate(model, tokenizer, prompt=text, max_tokens=4096, sampler=sampler):
                pieces.append(chunk.text); token_ids.append(int(chunk.token))
            raw = ''.join(pieces)
            p = {"id": row["id"], "raw": raw, "token_ids": token_ids, "finish_reason": chunk.finish_reason,
                 "eos_token_ids": sorted(tokenizer.eos_token_ids), "seconds": time.time() - start}
            try:
                p["graph"] = parse_output(raw, row["source"])
            except (ValueError, TypeError, KeyError, RecursionError) as exc:
                p["error"] = str(exc)
            stream.write(json.dumps(p) + "\n"); stream.flush()
            print(json.dumps({"completed_id": row["id"], "seconds": p["seconds"]}), flush=True)
    predictions = [json.loads(x) for x in output.read_text().splitlines()]
    report = development_score(rows, predictions, frozen["thresholds"])
    report.update(epoch=epoch, cumulative_steps=960 * epoch,
        adapter_sha256=prior.sha(selected / "adapters.safetensors"),
        prediction_sha256=prior.sha(output), local_generations=len(predictions), cloud_generations=0)
    prior.write_new(directory / "dev_report.json", report)


def selection_key(report):
    return (report["exact"], report["valid"], -report["invented_authority"],
            report["paraphrase_equal"], report["contrast_distinct"], -report["epoch"])


def comparison(reports):
    baseline = reports[0]
    best = max(reports, key=selection_key)
    return {"status": "DEVELOPMENT_COMPARISON_ONLY", "selected_epoch": best["epoch"],
        "selected_cumulative_steps": best["cumulative_steps"],
        "exact_gain_records": best["exact"] - baseline["exact"],
        "reference": "first trained v8 checkpoint; old wire scores are not directly comparable",
        "checkpoints": [{k: r[k] for k in ("epoch", "cumulative_steps", "total", "valid", "exact",
            "invented_authority", "paraphrase_equal", "contrast_distinct", "parser_errors")}
            for r in reports], "fresh_heldout": "NOT_RUN", "matrix_and_tree": "NOT_RUN"}


def run_session(run):
    verify(run)
    prior.write_new(run / "session_started.json", {"time": time.time()})
    reports = []
    def child(command, epoch):
        directory = stage(run, epoch)
        directory.mkdir(parents=True, exist_ok=True)
        status = {"status": "RUNNING", "phase": command, "epoch": epoch, "updated_unix": time.time()}
        (run / "status.json").write_text(json.dumps(status, indent=2))
        with (directory / f"{command}.log").open("x") as log:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), command,
                "--run", str(run), "--epoch", str(epoch)], check=True, stdout=log, stderr=subprocess.STDOUT)
    try:
        for epoch in (1, 2):
            child("train", epoch)
            child("evaluate", epoch)
            report = json.loads((stage(run, epoch) / "dev_report.json").read_text())
            reports.append(report)
            prior.write_new(run / f"comparison-{epoch}.json", comparison(reports))
        result = comparison(reports)
        result["completed_unix"] = time.time()
        prior.write_new(run / "session_complete.json", result)
        (run / "status.json").write_text(json.dumps({**result, "status": "COMPLETE"}, indent=2))
    except BaseException as exc:
        (run / "status.json").write_text(json.dumps({"status": "FAILED", "error": str(exc), "time": time.time()}))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "train", "evaluate"))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--epoch", type=int, choices=(0, 1, 2), default=0)
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    run = args.run.resolve()
    if args.command == "freeze": freeze(run)
    elif args.command == "run": run_session(run)
    elif args.command == "train": train(run, args.epoch)
    else: evaluate(run, args.epoch)


if __name__ == "__main__":
    main()
