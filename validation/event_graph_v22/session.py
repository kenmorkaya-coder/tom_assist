"""V22: one 96-update learning-rate diagnostic, retaining the V19 control data.

Only the learning rate changes from 5e-6 to 1e-6. The biased 96-row mix is
deliberately held fixed to isolate update size, not called representative.
No new labels, held-out exposure, matrix/Tree run or automatic promotion.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from validation.event_graph_v19 import session as control

HERE = Path(__file__).parent
RUN = Path("/Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v22-pilot-001")
ARM = "lower_rate"
START_SHA = "c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994"
PLAN = {
    "updates": 96, "baseline_steps": 4380, "seed": 151,
    "learning_rate": 0.000001, "comparison_learning_rate": 0.000005,
    "variable": "learning rate only; fivefold reduction versus V19 control",
    "initialization": "retained V14 epoch-1 adapter; optimizer reset",
    "dataset": "identical V19 control 96 records, prompts, labels, order",
    "reason": "control and label pilots shared regression despite low rounded training loss; label edits did not resolve the tradeoff",
    "hypothesis": "smaller updates may retain revision validity while preserving control causal gains",
    "limits": "single seed, biased small replay set, exposed synthetic development; update size is a hypothesis, not established cause",
    "retention": "original132 exact=132; earlier156 exact>=155; all192 exact>=191 and valid=192; no invented authority",
    "diagnostic": "unique causal exact>=50/56; all four original anchors correct",
    "selection": "retain V14 regardless; stop after one train/evaluation and require review",
    "evaluation": "same 192 development plus 56 unique exposed diagnostics; no held-out, matrix or Tree execution",
}
sha = control.old.prior.sha
write_new = control.old.prior.write_new


def training_rows():
    return control.training_rows("control")


def training_config(defaults):
    return {
        **defaults, **control.old.prior.CONFIG,
        "seed": PLAN["seed"], "iters": PLAN["updates"],
        "learning_rate": PLAN["learning_rate"],
        "steps_per_report": 16, "steps_per_eval": 96, "save_every": 96,
        "model": str(control.old.prior.MODEL),
        "adapter_path": str(RUN / ARM / "adapter"),
        "resume_adapter_file": str(control.old.adapter(control.V16, 0) / "adapters.safetensors"),
    }


def rows_digest(rows):
    import hashlib
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compare_config(config):
    original = json.loads((control.RUN / "control/training_started.json").read_text())["config"]
    changes = {key for key in set(original) | set(config) if original.get(key) != config.get(key)}
    if changes != {"learning_rate", "adapter_path"}:
        raise ValueError(f"unexpected training configuration changes: {sorted(changes)}")
    if original["learning_rate"] != PLAN["comparison_learning_rate"]:
        raise ValueError("comparison rate changed")


def verify(run):
    if run != RUN:
        raise ValueError("unexpected run directory")
    control.verify(control.RUN)
    frozen = control.verify(run)
    if frozen["plan"] != PLAN or frozen["training_sha256"] != rows_digest(training_rows()):
        raise ValueError("frozen plan or training inputs changed")
    if frozen["evaluation_sha256"] != rows_digest(control.evaluation_rows()):
        raise ValueError("frozen evaluation inventory changed")
    adapter = control.old.adapter(control.V16, 0) / "adapters.safetensors"
    if sha(adapter) != START_SHA:
        raise ValueError("retained V14 adapter changed")
    return frozen


def freeze():
    control.verify(control.RUN)
    if not Path("/Volumes/My Passport for Mac").is_mount():
        raise ValueError("Passport is not mounted")
    if not RUN.parent.is_dir() or RUN.exists():
        raise ValueError("run parent unavailable or run already exists")
    if shutil.disk_usage(RUN.parent).free < 1024**3:
        raise ValueError("less than 1 GiB free on Passport")
    source = control.old.adapter(control.V16, 0)
    if sha(source / "adapters.safetensors") != START_SHA:
        raise ValueError("starting adapter mismatch")
    files = [
        Path(__file__).resolve(), ROOT / "gateway/tests/test_event_graph_v22.py",
        Path(control.__file__).resolve(), control.RUN / "freeze.json",
        control.RUN / "baseline.json", source / "adapters.safetensors",
        source / "adapter_config.json",
    ]
    files += [control.RUN / "control" / name for name in (
        "training_started.json", "training_complete.json", "sampled_ids.jsonl",
        "predictions.jsonl", "report.json", "adapter/adapter_config.json",
        "adapter/adapters.safetensors",
    )]
    files += [ROOT / f"validation/runs/event-graph-lora-v{v}-pilot-001/REPORT.md" for v in (19, 20, 21)]
    frozen = {
        "created_unix": time.time(), "plan": PLAN,
        "files": {str(p): sha(p) for p in files},
        "thresholds": control.old.verify(control.V16)["thresholds"],
        "training_sha256": rows_digest(training_rows()),
        "evaluation_sha256": rows_digest(control.evaluation_rows()),
        "training_ids": [r["id"] for r in training_rows()],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_state": "shared dirty checkout; exact experiment files frozen; unrelated edits excluded",
    }
    baseline = control.score(control.evaluation_rows(), control.baseline_predictions(), frozen["thresholds"])
    if baseline["development"]["exact"] != 191 or baseline["diagnostic"]["exact"] != 47:
        raise ValueError("retained baseline changed")
    RUN.mkdir()
    write_new(RUN / "freeze.json", frozen)
    write_new(RUN / "baseline.json", baseline)
    print(json.dumps({"status": "FROZEN", "run": str(RUN), "plan": PLAN}), flush=True)


def train():
    verify(RUN)
    versions = {name: importlib.metadata.version(name) for name in ("mlx", "mlx-lm", "transformers")}
    if versions != {"mlx": "0.31.1", "mlx-lm": "0.31.2", "transformers": "5.5.3"}:
        raise ValueError(f"runtime version mismatch: {versions}")
    import mlx.core as mx
    import numpy as np
    from types import SimpleNamespace
    from mlx_lm import load
    from mlx_lm.lora import CONFIG_DEFAULTS, train_model
    from mlx_lm.tuner.datasets import ChatDataset
    from mlx_lm.tuner.callbacks import TrainingCallback
    from gateway.gemma_training_alignment import AlignedChatTokenizer, check_alignment

    if not mx.metal.is_available():
        raise ValueError("Metal GPU unavailable")
    directory = RUN / ARM
    directory.mkdir(exist_ok=True)
    config = training_config(CONFIG_DEFAULTS)
    compare_config(config)
    write_new(directory / "training_started.json", {
        "time": time.time(), "config": config, "versions": versions,
        "input_adapter_sha256": START_SHA, "optimizer_state": "reset",
    })
    model, tokenizer = load(str(control.old.prior.MODEL))
    rows = training_rows()
    alignment = [check_alignment(tokenizer, control.messages(r)) for r in rows]
    if max(x["total_tokens"] for x in alignment) > 4096:
        raise ValueError("supervised example would be truncated")
    write_new(directory / "alignment.json", {"count": len(rows), "max_tokens": max(x["total_tokens"] for x in alignment)})
    processed = []

    class RecordedChat(ChatDataset):
        def process(self, item):
            processed.append(item["id"])
            with (directory / "sampled_ids.jsonl").open("a") as stream:
                stream.write(json.dumps({"step": len(processed), "id": item["id"]}) + "\n")
            return super().process(item)

    class PreciseLoss(TrainingCallback):
        def on_train_loss_report(self, info):
            if not math.isfinite(info["train_loss"]):
                raise ValueError("nonfinite training loss")
            print("TRAIN_TELEMETRY " + json.dumps(info, allow_nan=False), flush=True)

    data = [{"id": r["id"], "messages": control.messages(r)} for r in rows]
    dataset = RecordedChat(data, AlignedChatTokenizer(tokenizer), mask_prompt=True)
    expected = [rows[int(i)]["id"] for i in np.random.RandomState(151).permutation(96)]
    np.random.seed(151)
    mx.random.seed(151)
    train_model(SimpleNamespace(**config), model, dataset, [], training_callback=PreciseLoss())
    original = json.loads((control.RUN / "control/training_complete.json").read_text())
    if processed != expected or processed != original["sampled_ids"] or len(set(processed)) != 96:
        raise ValueError("sample order or coverage differs from control")
    adapter = directory / "adapter"
    write_new(directory / "training_complete.json", {
        "time": time.time(), "iterations": 96, "cumulative_steps": 4476,
        "sampled_all_once": True, "sampled_ids": processed,
        "adapter_sha256": sha(adapter / "adapters.safetensors"),
        "config_sha256": sha(adapter / "adapter_config.json"),
    })


def run():
    verify(RUN)
    write_new(RUN / "started.json", {"time": time.time(), "pid": os.getpid()})
    try:
        (RUN / ARM).mkdir(exist_ok=True)
        for phase in ("train", "evaluate"):
            (RUN / "status.json").write_text(json.dumps({"status": "RUNNING", "phase": phase, "arm": ARM}))
            with (RUN / ARM / f"{phase}.log").open("x") as log:
                subprocess.run([sys.executable, "-u", str(Path(__file__).resolve()), phase],
                               check=True, stdout=log, stderr=subprocess.STDOUT)
        verify(RUN)
        write_new(RUN / "complete.json", {"status": "COMPLETE_UNREVIEWED", "time": time.time()})
        (RUN / "status.json").write_text(json.dumps({"status": "COMPLETE_UNREVIEWED"}))
    except BaseException as exc:
        (RUN / "status.json").write_text(json.dumps({"status": "FAILED", "error": str(exc), "time": time.time()}))
        raise


def main():
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "train", "evaluate"))
    command = parser.parse_args().command
    if command == "freeze":
        freeze()
    elif command == "train":
        train()
    elif command == "evaluate":
        verify(RUN)
        control.evaluate(RUN, ARM)
    else:
        run()


if __name__ == "__main__":
    main()
