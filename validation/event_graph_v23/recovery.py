"""Resource-isolated retry of the frozen V23 experiment; no training changes.

The original failed attempt and controller remain untouched. This wrapper binds
only a new output directory, waits at most 30 minutes for resources, and stops
its own child if competition appears. It cannot prevent other apps starting
between observations. It never kills, suspends or modifies another task.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from validation.event_graph_v23 import session as experiment

ORIGINAL = experiment.RUN
RUN = ORIGINAL.with_name("event-graph-lora-v23-pilot-002")
GPU_PYTHON = "/Users/kenmorkaya/PycharmProjects/tom_sicd_gemma/.venv/bin/python"
GIB = 1024 ** 3
RESOURCE_POLICY = {
    "version": "v23-resource-isolation/1",
    "maximum_wait_seconds": 1800,
    "poll_seconds": 5,
    "before_load_reclaimable_min_bytes": 28 * GIB,
    "during_run_reclaimable_min_bytes": 2 * GIB,
    "other_python_rss_limit_bytes": 2 * GIB,
    "rationale": "48 GiB host; observed MLX peak 20.91 decimal GB; reserve headroom before loading and exclude other large Python or MLX jobs",
    "limitation": "free+inactive+speculative pages are an estimate, not guaranteed allocatable GPU memory; monitoring is not a system-wide GPU lock",
}


def parse_processes(text):
    records = []
    for line in text.splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) == 4:
            records.append({"pid": int(parts[0]), "parent_pid": int(parts[1]),
                            "rss_bytes": int(parts[2]) * 1024, "executable": parts[3]})
    return records


def owned_pids(records, root_pid):
    owned = {root_pid}
    while True:
        expanded = owned | {r["pid"] for r in records if r["parent_pid"] in owned}
        if expanded == owned:
            return owned
        owned = expanded


def reclaimable_bytes(text):
    size = re.search(r"page size of (\d+) bytes", text)
    if size is None:
        raise ValueError("vm_stat page size missing")
    pages = []
    for field in ("Pages free", "Pages inactive", "Pages speculative"):
        found = re.search(r"^" + field + r":\s+(\d+)", text, re.M)
        if found is None:
            raise ValueError(f"vm_stat omitted {field}")
        pages.append(int(found[1]))
    return sum(pages) * int(size[1])


def snapshot():
    raw = subprocess.check_output(["ps", "-axo", "pid=,ppid=,rss=,comm="], text=True, timeout=10)
    records = parse_processes(raw)
    own = owned_pids(records, os.getpid())
    others = []
    for row in records:
        if row["pid"] in own:
            continue
        name = Path(row["executable"]).name.lower()
        python = name.startswith("python")
        model_name = any(x in name for x in ("ollama", "llama-server", "mlx"))
        if not python and not model_name:
            continue
        probe = subprocess.run(["lsof", "-a", "-p", str(row["pid"]), "-d", "txt", "-Fn"],
                               capture_output=True, text=True, timeout=10)
        if probe.returncode not in (0, 1):
            raise RuntimeError("process library inspection failed")
        if probe.returncode == 1 and not probe.stdout.strip():
            # A disappearing process is harmless; an existing uninspectable one is not.
            alive = subprocess.run(["ps", "-p", str(row["pid"]), "-o", "pid="], capture_output=True, text=True)
            if alive.stdout.strip():
                raise RuntimeError(f"cannot inspect live process {row['pid']}")
            continue
        libraries = [line[1:] for line in probe.stdout.splitlines() if line.startswith("n")]
        mlx = any("libmlx" in path.lower() for path in libraries)
        others.append({"pid": row["pid"], "rss_bytes": row["rss_bytes"],
                       "python": python, "mlx_loaded": mlx, "model_process_name": model_name})
    vm = subprocess.check_output(["vm_stat"], text=True, timeout=10)
    return {"time": time.time(), "reclaimable_estimate_bytes": reclaimable_bytes(vm), "other_processes": others}


def blockers(observation, before_load):
    blocked = []
    for row in observation["other_processes"]:
        if row["mlx_loaded"] or row["model_process_name"]:
            blocked.append({"pid": row["pid"], "reason": "other_model_process"})
        elif row["python"] and row["rss_bytes"] >= RESOURCE_POLICY["other_python_rss_limit_bytes"]:
            blocked.append({"pid": row["pid"], "reason": "other_large_python_job"})
    required = RESOURCE_POLICY["before_load_reclaimable_min_bytes" if before_load else "during_run_reclaimable_min_bytes"]
    if observation["reclaimable_estimate_bytes"] < required:
        blocked.append({"reason": "insufficient_memory_headroom", "required_bytes": required})
    return blocked


def observe(before_load):
    observed = snapshot()
    observed["blockers"] = blockers(observed, before_load)
    with (RUN / "resource_observations.jsonl").open("a") as stream:
        stream.write(json.dumps(observed) + "\n")
    return observed


def status(value, **extra):
    (RUN / "status.json").write_text(json.dumps({"status": value, "time": time.time(), **extra}))


def bind_output():
    # Explicit output relocation only. The original module's math/data/PLAN remain frozen.
    experiment.RUN = RUN


def verify():
    bind_output()
    frozen = experiment.verify(RUN)
    if frozen["recovery"]["resource_policy"] != RESOURCE_POLICY:
        raise ValueError("resource policy drift")
    return frozen


def freeze():
    if RUN.exists() or not RUN.parent.is_dir() or not RUN.parent.parent.is_mount():
        raise ValueError("Passport unavailable or recovery attempt already exists")
    if shutil.disk_usage(RUN.parent).free < GIB:
        raise ValueError("less than 1 GiB free on Passport")
    inherited = copy.deepcopy(experiment.verify(ORIGINAL))
    failed = json.loads((ORIGINAL / "status.json").read_text())
    if failed["status"] != "FAILED" or (ORIGINAL / experiment.ARM / "training_complete.json").exists():
        raise ValueError("original attempt is not the expected failed training")
    if list((ORIGINAL / experiment.ARM).rglob("*.safetensors")):
        raise ValueError("original attempt has an unexpected checkpoint; inspect first")
    files = [Path(__file__).resolve(), ROOT / "gateway/tests/test_event_graph_v23_recovery.py",
             ORIGINAL / "freeze.json", ORIGINAL / "status.json", ORIGINAL / "session.log"]
    files += [ORIGINAL / experiment.ARM / name for name in
              ("train.log", "sampled_ids.jsonl", "alignment.json", "training_started.json")]
    inherited["files"].update({str(p): experiment.sha(p) for p in files})
    inherited["created_unix"] = time.time()
    inherited["recovery"] = {
        "original_attempt": str(ORIGINAL), "resource_policy": RESOURCE_POLICY,
        "change": "resource isolation and observation only; output path relocated explicitly",
        "restart": "restart all 96 updates from V14; there is no checkpoint to resume",
        "diagnosis": "another MLX process 61628 crashed 0.117 seconds after trainer 61391; input at sample86 was2098 tokens, below earlier2231; competition is supported but not exclusively proven",
    }
    RUN.mkdir()
    experiment.write_new(RUN / "freeze.json", inherited)
    experiment.write_new(RUN / "baseline.json", json.loads((ORIGINAL / "baseline.json").read_text()))
    status("FROZEN")
    print(json.dumps({"status": "FROZEN", "run": str(RUN), "resource_policy": RESOURCE_POLICY}), flush=True)


def stop_owned_child(child):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


def wait_for_resources(phase):
    deadline = time.monotonic() + RESOURCE_POLICY["maximum_wait_seconds"]
    while True:
        observed = observe(before_load=True)
        if not observed["blockers"]:
            return True
        status("WAITING_FOR_RESOURCES", phase=phase, blockers=observed["blockers"],
               remaining_wait_seconds=max(0, int(deadline - time.monotonic())))
        if time.monotonic() >= deadline:
            status("BLOCKED_RESOURCES", phase=phase, blockers=observed["blockers"])
            return False
        time.sleep(RESOURCE_POLICY["poll_seconds"])


def run():
    verify()
    experiment.write_new(RUN / "started.json", {"time": time.time(), "pid": os.getpid()})
    try:
        (RUN / experiment.ARM).mkdir(exist_ok=True)
        for phase in ("train", "evaluate"):
            if not wait_for_resources(phase):
                return
            status("RUNNING", phase=phase)
            with (RUN / experiment.ARM / f"{phase}.log").open("x") as log:
                child = subprocess.Popen([GPU_PYTHON, "-u", str(Path(__file__).resolve()), phase],
                                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                try:
                    while child.poll() is None:
                        observed = observe(before_load=False)
                        if observed["blockers"]:
                            stop_owned_child(child)
                            status("STOPPED_RESOURCE_CONFLICT", phase=phase, blockers=observed["blockers"])
                            return
                        time.sleep(RESOURCE_POLICY["poll_seconds"])
                    if child.returncode:
                        raise RuntimeError(f"{phase} child exited {child.returncode}")
                except BaseException:
                    stop_owned_child(child)
                    raise
        verify()
        experiment.write_new(RUN / "complete.json", {"status": "COMPLETE_UNREVIEWED", "time": time.time()})
        status("COMPLETE_UNREVIEWED")
    except BaseException as exc:
        status("FAILED", error=str(exc))
        raise


def main():
    os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "freeze", "run", "train", "evaluate"))
    command = parser.parse_args().command
    if command == "inspect":
        observed = snapshot()
        print(json.dumps({**observed, "blockers": blockers(observed, True)}))
    elif command == "freeze":
        freeze()
    elif command == "run":
        run()
    else:
        verify()
        if command == "train":
            experiment.train()
        else:
            experiment.control.evaluate(RUN, experiment.ARM)


if __name__ == "__main__":
    main()
