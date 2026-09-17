"""V23: one matched 96-update family/curriculum replay-coverage diagnostic.

Only selection of existing training records changes relative to V22. One
unaltered canonical/paraphrase/contrast group per family/curriculum stratum.
This tests a sampling policy, not a causal attribution to any individual row.
No held-out exposure, label repair, matrix/Tree run or automatic promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
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
from validation.event_graph_v22 import session as previous
control = previous.control

HERE = Path(__file__).parent
RUN = Path("/Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v23-pilot-001")
ARM = "broader_replay"
SAMPLING_VERSION = "v23-broader-replay/1"
VARIANTS = ("canonical", "paraphrase", "contrast")
START_SHA = "c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994"
PLAN = {
    "updates": 96,
    "baseline_steps": 4380,
    "seed": 151,
    "learning_rate": 1e-06,
    "variable": "selection of existing training records only versus V22; same sample-slot permutation, changed row identities",
    "initialization": "retained V14 epoch-1 adapter; optimizer reset",
    "dataset": "one complete three-variant group per each of 32 family/curriculum strata; all 20 families; unchanged labels",
    "sampling": "SHA-256 rank with fixed seed151 selects one group per stratum; family/numeric-curriculum/variant order defines slots; no evaluation score or prediction used for selection",
    "reason": "V22 introduced three empty revision evidence spans; old sample had 48 causal and only two revision records from one old group",
    "hypothesis": "broader replay may retain revision validity without losing causal performance",
    "limits": "one seed and one selection policy; 32 of 528 training groups, not all training language; curriculum is provenance, not a semantic family; changing sampling changes content mix, not just one linguistic feature; exposed synthetic evaluation is not fresh confirmation",
    "retention": "original132 exact=132; earlier156 exact>=155; all192 exact>=191 and valid=192; no invented authority",
    "diagnostic": "unique causal exact>=50/56; all four original anchors correct; also report matched V22 comparison at48/56",
    "selection": "retain V14 regardless; stop after one train/evaluation and require review",
    "evaluation": "same 192 development plus 56 unique exposed diagnostics; no held-out, matrix or Tree execution"
}
sha = control.old.prior.sha
write_new = control.old.prior.write_new


def group_id(row):
    value = row.get("group_id", row.get("group"))
    if not isinstance(value, str) or not value:
        raise ValueError("training row lacks a group identity")
    return value


def selection(rows):
    strata = defaultdict(lambda: defaultdict(list))
    ids = set()
    for row in rows:
        if row["id"] in ids:
            raise ValueError("duplicate training record")
        ids.add(row["id"])
        curriculum = row["id"].split("-")[0]
        strata[(row["family"], curriculum)][group_id(row)].append(row)
    if len(strata) != 32 or len({key[0] for key in strata}) != 20:
        raise ValueError("family/curriculum inventory changed")
    chosen = []
    for (family, curriculum), groups in sorted(strata.items(), key=lambda x: (x[0][0], int(x[0][1][1:]))):
        def rank(group):
            key = f"{SAMPLING_VERSION}\0seed=151\0{family}\0{curriculum}\0{group}"
            return hashlib.sha256(key.encode()).hexdigest(), group
        group = min(groups, key=rank)
        candidates = groups[group]
        if len(candidates) != 3 or {row["variant"] for row in candidates} != set(VARIANTS):
            raise ValueError("selected group is not a complete three-variant group")
        chosen.extend(sorted(candidates, key=lambda row: VARIANTS.index(row["variant"])))
    if len(chosen) != 96 or len({row["id"] for row in chosen}) != 96:
        raise ValueError("selected training inventory changed")
    return copy.deepcopy(chosen)


def training_rows():
    return selection(control.old.read_rows("train"))


def coverage(rows):
    return {
        "records": len(rows), "groups": len({group_id(row) for row in rows}),
        "family_counts": dict(sorted(Counter(row["family"] for row in rows).items())),
        "groups_selected": [
            {"family": rows[i]["family"], "curriculum": rows[i]["id"].split("-")[0],
             "group": group_id(rows[i]), "ids": [row["id"] for row in rows[i:i + 3]]}
            for i in range(0, len(rows), 3)
        ],
    }


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
    original = json.loads((previous.RUN / previous.ARM / "training_started.json").read_text())["config"]
    changes = {key for key in set(original) | set(config) if original.get(key) != config.get(key)}
    if changes != {"adapter_path"}:
        raise ValueError(f"unexpected training configuration changes: {sorted(changes)}")
    if original["learning_rate"] != PLAN["learning_rate"]:
        raise ValueError("comparison rate changed")


def verify(run):
    if run != RUN:
        raise ValueError("unexpected run directory")
    previous.verify(previous.RUN)
    frozen = control.verify(run)
    if frozen["plan"] != PLAN or frozen["training_sha256"] != rows_digest(training_rows()):
        raise ValueError("frozen plan or training inputs changed")
    if frozen["coverage"] != coverage(training_rows()) or frozen["sampling_version"] != SAMPLING_VERSION:
        raise ValueError("frozen sampling coverage changed")
    if frozen["evaluation_sha256"] != rows_digest(control.evaluation_rows()):
        raise ValueError("frozen evaluation inventory changed")
    adapter = control.old.adapter(control.V16, 0) / "adapters.safetensors"
    if sha(adapter) != START_SHA:
        raise ValueError("retained V14 adapter changed")
    return frozen


def freeze():
    previous.verify(previous.RUN)
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
        Path(__file__).resolve(), ROOT / "gateway/tests/test_event_graph_v23.py",
        Path(control.__file__).resolve(), Path(previous.__file__).resolve(),
        previous.RUN / "freeze.json", previous.RUN / "baseline.json", previous.RUN / "review_receipt.json", source / "adapters.safetensors",
        source / "adapter_config.json",
    ]
    files += [previous.RUN / previous.ARM / name for name in (
        "training_started.json", "training_complete.json", "sampled_ids.jsonl",
        "predictions.jsonl", "report.json", "adapter/adapter_config.json",
        "adapter/adapters.safetensors",
    )]
    frozen = {
        "created_unix": time.time(), "plan": PLAN,
        "files": {str(p): sha(p) for p in files},
        "thresholds": control.old.verify(control.V16)["thresholds"],
        "training_sha256": rows_digest(training_rows()),
        "evaluation_sha256": rows_digest(control.evaluation_rows()),
        "training_ids": [r["id"] for r in training_rows()],
        "coverage": coverage(training_rows()),
        "sampling_version": SAMPLING_VERSION,
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
    slot_by_id = {row["id"]: i for i, row in enumerate(rows)}

    class RecordedChat(ChatDataset):
        def process(self, item):
            processed.append(item["id"])
            with (directory / "sampled_ids.jsonl").open("a") as stream:
                stream.write(json.dumps({"step": len(processed), "id": item["id"], "slot": slot_by_id[item["id"]]}) + "\n")
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
    original = json.loads((previous.RUN / previous.ARM / "training_complete.json").read_text())
    old_slots = {row["id"]: i for i, row in enumerate(previous.training_rows())}
    actual_slots = [slot_by_id[item] for item in processed]
    comparison_slots = [old_slots[item] for item in original["sampled_ids"]]
    if processed != expected or actual_slots != comparison_slots or len(set(processed)) != 96:
        raise ValueError("sample-slot order or one-pass coverage differs from V22")
    adapter = directory / "adapter"
    write_new(directory / "training_complete.json", {
        "time": time.time(), "iterations": 96, "cumulative_steps": 4476,
        "sampled_all_once": True, "sampled_ids": processed, "sampled_slots": actual_slots,
        "training_sha256": rows_digest(rows), "coverage": coverage(rows),
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
