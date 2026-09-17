"""Continue V23 evaluation from verified saved outputs, without retraining.

Each explicitly launched attempt has its own Passport receipts and output part.
Completed parts are immutable. The original generation and scoring settings,
checkpoint and resource guard remain unchanged; there is no automatic retry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from validation.event_graph_v23 import recovery as base

experiment = base.experiment
ARM = base.RUN / experiment.ARM
POLICY = {"seed": 7, "temperature": 0.0, "max_tokens": 4096,
          "enable_thinking": False, "resource_policy": base.RESOURCE_POLICY,
          "selection": "retain V14; complete evaluation and require review"}


def directory(attempt):
    if attempt < 1:
        raise ValueError("attempt must be positive")
    return base.RUN / f"evaluation-resume-{attempt:03d}"


def prediction_parts(attempt):
    return [ARM / "predictions.jsonl"] + [
        directory(i) / "predictions.jsonl" for i in range(1, attempt)
        if (directory(i) / "predictions.jsonl").exists()]


def read_prefix(paths, rows):
    predictions = []
    for path in paths:
        data = path.read_bytes()
        if data and not data.endswith(b"\n"):
            raise ValueError(f"incomplete saved record: {path}")
        predictions.extend(json.loads(line) for line in data.splitlines())
    if [p["id"] for p in predictions] != [r["id"] for r in rows[:len(predictions)]]:
        raise ValueError("saved outputs are not a unique, ordered evaluation prefix")
    for prediction, row in zip(predictions, rows):
        try:
            graph = experiment.control.old.parse_output(prediction["raw"], row["source"])
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            if "graph" in prediction or prediction.get("error") != str(exc):
                raise ValueError("saved parse error changed") from exc
        else:
            if prediction.get("graph") != graph or "error" in prediction:
                raise ValueError("saved graph disagrees with raw output")
        tokens = prediction["token_ids"]
        if not tokens or len(tokens) > POLICY["max_tokens"]:
            raise ValueError("invalid saved generation length")
        reason = prediction["finish_reason"]
        if reason == "stop":
            if tokens[-1] not in prediction["eos_token_ids"]:
                raise ValueError("saved stop lacks an end token")
        elif reason != "length" or len(tokens) != POLICY["max_tokens"]:
            raise ValueError("invalid saved finish reason")
    return predictions


def verify_training():
    frozen = base.verify()
    receipt = json.loads((ARM / "training_complete.json").read_text())
    if receipt["iterations"] != 96 or not receipt["sampled_all_once"]:
        raise ValueError("training is not complete")
    for name, key in (("adapters.safetensors", "adapter_sha256"),
                      ("adapter_config.json", "config_sha256")):
        if experiment.sha(ARM / "adapter" / name) != receipt[key]:
            raise ValueError("saved checkpoint changed")
    if receipt["training_sha256"] != frozen["training_sha256"]:
        raise ValueError("training data changed")
    return frozen, receipt


def verify_manifest(attempt):
    frozen = json.loads((directory(attempt) / "freeze.json").read_text())
    if frozen["policy"] != POLICY or frozen["attempt"] != attempt:
        raise ValueError("continuation policy changed")
    for name, expected in frozen["files"].items():
        if experiment.sha(Path(name)) != expected:
            raise ValueError(f"continuation input changed: {name}")
    rows = experiment.control.evaluation_rows()
    if experiment.rows_digest(rows) != frozen["evaluation_sha256"]:
        raise ValueError("evaluation inventory changed")
    prefix = read_prefix([Path(p) for p in frozen["prediction_parts"]], rows)
    if len(prefix) != frozen["completed_before"]:
        raise ValueError("saved prefix changed")
    return frozen, prefix


def freeze(attempt):
    target = directory(attempt)
    if target.exists() or not base.RUN.parent.parent.is_mount():
        raise ValueError("attempt exists or Passport unavailable")
    original, receipt = verify_training()
    stopped = json.loads((base.RUN / "status.json").read_text())
    if stopped["status"] != "STOPPED_RESOURCE_CONFLICT" or stopped["phase"] != "evaluate":
        raise ValueError("unexpected original recovery status")
    files = [Path(__file__).resolve(), ROOT / "gateway/tests/test_event_graph_v23_evaluation_resume.py",
             base.RUN / "freeze.json", base.RUN / "status.json", ARM / "training_complete.json",
             ARM / "sampled_ids.jsonl", ARM / "training_started.json",
             ARM / "adapter/adapters.safetensors", ARM / "adapter/adapter_config.json"]
    for prior in range(1, attempt):
        verify_manifest(prior)
        prior_status = json.loads((directory(prior) / "status.json").read_text())
        if prior_status["status"] not in ("BLOCKED_RESOURCES", "STOPPED_RESOURCE_CONFLICT", "FAILED"):
            raise ValueError("previous evaluation attempt is not stopped")
        files.extend(directory(prior) / name for name in ("freeze.json", "status.json"))
    parts = prediction_parts(attempt)
    rows = experiment.control.evaluation_rows()
    prefix = read_prefix(parts, rows)
    if not 0 < len(prefix) < len(rows) or (ARM / "report.json").exists():
        raise ValueError("evaluation is not the expected incomplete run")
    files.extend(parts)
    frozen = {"attempt": attempt, "time": time.time(), "policy": POLICY,
              "files": {str(p): experiment.sha(p) for p in files},
              "prediction_parts": [str(p) for p in parts], "completed_before": len(prefix),
              "evaluation_sha256": original["evaluation_sha256"],
              "adapter_sha256": receipt["adapter_sha256"],
              "scope": "generate only remaining cases; saved outputs retained unchanged; no training or promotion"}
    target.mkdir()
    experiment.write_new(target / "freeze.json", frozen)
    status(target, "FROZEN", completed=len(prefix), remaining=len(rows)-len(prefix))
    print(json.dumps({"status": "FROZEN", "directory": str(target), "completed": len(prefix), "remaining": len(rows)-len(prefix)}), flush=True)


def status(target, value, **extra):
    (target / "status.json").write_text(json.dumps({"status": value, "time": time.time(), **extra}))


def observe(target, before_load):
    observation = base.snapshot()
    observation["blockers"] = base.blockers(observation, before_load)
    with (target / "resource_observations.jsonl").open("a") as stream:
        stream.write(json.dumps(observation) + "\n")
    return observation


def run(attempt):
    target = directory(attempt)
    experiment.write_new(target / "started.json", {"time": time.time(), "pid": os.getpid()})
    child = None
    try:
        verify_training()
        verify_manifest(attempt)
        deadline = time.monotonic() + base.RESOURCE_POLICY["maximum_wait_seconds"]
        while True:
            observed = observe(target, True)
            if not observed["blockers"]:
                break
            remaining = max(0, int(deadline-time.monotonic()))
            status(target, "WAITING_FOR_RESOURCES", blockers=observed["blockers"], remaining_wait_seconds=remaining)
            if time.monotonic() >= deadline:
                status(target, "BLOCKED_RESOURCES", blockers=observed["blockers"])
                return
            time.sleep(base.RESOURCE_POLICY["poll_seconds"])
        with (target / "evaluate.log").open("x") as log:
            child = subprocess.Popen([base.GPU_PYTHON, "-u", str(Path(__file__).resolve()),
                                      "evaluate", "--attempt", str(attempt)],
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            status(target, "RUNNING", phase="evaluate", child_pid=child.pid)
            while child.poll() is None:
                observed = observe(target, False)
                if observed["blockers"]:
                    base.stop_owned_child(child)
                    status(target, "STOPPED_RESOURCE_CONFLICT", blockers=observed["blockers"])
                    return
                time.sleep(base.RESOURCE_POLICY["poll_seconds"])
            if child.returncode:
                raise RuntimeError(f"evaluation child exited {child.returncode}")
        verify_training()
        verify_manifest(attempt)
        if not (target / "report.json").exists():
            raise ValueError("evaluation report missing")
        status(target, "COMPLETE_UNREVIEWED", completed=248)
    except BaseException as exc:
        if child is not None:
            base.stop_owned_child(child)
        status(target, "FAILED", error=str(exc))
        raise


def evaluate(attempt):
    original, receipt = verify_training()
    frozen, prefix = verify_manifest(attempt)
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(POLICY["seed"])
    model, tokenizer = load(str(experiment.control.old.prior.MODEL), adapter_path=str(ARM / "adapter"))
    sampler = make_sampler(temp=POLICY["temperature"])
    rows = experiment.control.evaluation_rows()
    target = directory(attempt)
    path = target / "predictions.jsonl"
    with path.open("x") as out:
        for row in rows[len(prefix):]:
            prompt = tokenizer.apply_chat_template([experiment.control.messages(row)[0]], tokenize=False,
                        add_generation_prompt=True, enable_thinking=POLICY["enable_thinking"])
            chunks = list(stream_generate(model, tokenizer, prompt=prompt, max_tokens=POLICY["max_tokens"], sampler=sampler))
            prediction = {"id": row["id"], "raw": "".join(c.text for c in chunks),
                          "token_ids": [int(c.token) for c in chunks],
                          "finish_reason": chunks[-1].finish_reason,
                          "eos_token_ids": sorted(tokenizer.eos_token_ids)}
            try:
                prediction["graph"] = experiment.control.old.parse_output(prediction["raw"], row["source"])
            except (ValueError, TypeError, KeyError, RecursionError) as exc:
                prediction["error"] = str(exc)
            out.write(json.dumps(prediction) + "\n")
            out.flush()
            print(json.dumps({"completed_id": row["id"]}), flush=True)
    parts = [Path(p) for p in frozen["prediction_parts"]] + [path]
    predictions = read_prefix(parts, rows)
    result = experiment.control.score(rows, predictions, original["thresholds"])
    result.update(adapter_sha256=receipt["adapter_sha256"],
                  prediction_parts={str(p): experiment.sha(p) for p in parts})
    experiment.write_new(target / "report.json", result)


def main():
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "evaluate"))
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    {"freeze": freeze, "run": run, "evaluate": evaluate}[args.command](args.attempt)


if __name__ == "__main__":
    main()
