"""One fresh held-out pass for the development-selected 992-step adapter."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from validation.event_graph_v4 import experiment as previous
from validation.event_graph_v5.session import verify as verify_session, adapter
from gateway.event_graph_extractor_v3 import prompt,parse_output
from gateway.typed_event_graph import semantic_graph,validate_graph
from gateway.event_graph_compiler import compile_graph
HERE=Path(__file__).parent
SESSION=ROOT/'.tmp/event-graph-lora-v5-session-001'
ADAPTER=SESSION/'epoch-1/adapter'
MODEL=previous.MODEL
sha=previous.sha
write_new=previous.write_new
score_extraction=previous.score_extraction


def read_rows(split):
    if split!='heldout':raise ValueError('this experiment has only fresh held-out data')
    return [json.loads(x) for x in (HERE/'heldout.jsonl').read_text().splitlines()]


def verify_freeze(run):
    frozen=json.loads((run/'freeze.json').read_text())
    if sha(SESSION/'freeze.json')!=frozen['session_freeze_sha256']:
        raise ValueError('parent session manifest changed')
    verify_session(SESSION)
    for name,expected in frozen['files'].items():
        if sha(ROOT/name)!=expected:raise ValueError(f'frozen file changed: {name}')
    if adapter(SESSION,1)!=ADAPTER:raise ValueError('wrong selected adapter path')
    if sha(ADAPTER/'adapters.safetensors')!=frozen['adapter_sha256']:
        raise ValueError('selected adapter changed')
    return frozen


def freeze(run):
    parent=verify_session(SESSION)
    result_path=ROOT/'validation/runs/event-graph-lora-v5-session-001/RESULT.json'
    result=json.loads(result_path.read_text())
    assert result['comparison']['selected_epoch']==1
    assert result['comparison']['selected_cumulative_steps']==992
    selected=adapter(SESSION,1)
    rows=read_rows('heldout')
    sources={r['source'] for r in rows}
    if len(rows)!=132 or len(sources)!=132:raise ValueError('fresh source inventory mismatch')
    prior_sources=set()
    for version in ('v1','v3'):
        for split in ('train','dev','heldout'):
            p=ROOT/f'validation/event_graph_{version}/data/{split}.jsonl'
            prior_sources.update(json.loads(x)['source'] for x in p.read_text().splitlines())
    if sources & prior_sources:raise ValueError('source overlap with previous inventories')
    groups=defaultdict(dict)
    for row in rows:
        validate_graph(row['graph'],row['source'])
        groups[row['group']][row['variant']]=semantic_graph(row['graph'])
    assert len(groups)==44
    for g in groups.values():
        assert g['canonical']==g['paraphrase'] and g['canonical']!=g['contrast']
    files=[p for p in HERE.iterdir() if p.suffix in ('.py','.md','.jsonl')]
    files += [ROOT/'gateway/tests/test_event_graph_fresh_holdout.py',result_path]
    write_new(run/'freeze.json',{'created_unix':time.time(),'selected_cumulative_steps':992,
        'files':{str(p.relative_to(ROOT)):sha(p) for p in files},
        'session_freeze_sha256':sha(SESSION/'freeze.json'),
        'adapter_sha256':sha(selected/'adapters.safetensors'),
        'thresholds':parent['thresholds'],'counts':{'records':132,'unique_sources':132,'groups':44},
        'prior_source_overlap':0,'training':'NOT_RUN'})


def infer(run, split):
    frozen = verify_freeze(run)
    complete = {"adapter": frozen["adapter_sha256"]}
    if sha(ADAPTER / "adapters.safetensors") != complete["adapter"]:
        raise ValueError("adapter changed")
    output = run / f"{split}_predictions.jsonl"
    if output.exists():
        raise ValueError("predictions already exist; refusing repeated held-out use")
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7)
    model, tokenizer = load(str(MODEL), adapter_path=str(ADAPTER))
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
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','verify','infer','matrix'))
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    if args.command=='freeze':freeze(args.run)
    elif args.command=='verify':verify_freeze(args.run)
    elif args.command=='infer':infer(args.run,'heldout')
    else:matrix_gate(args.run)

if __name__=='__main__':main()
