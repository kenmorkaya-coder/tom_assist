"""One fresh held-out pass for the development-selected 4380-step adapter."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
import importlib.metadata
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from validation.event_graph_v4 import experiment as previous
from validation.event_graph_v14.session import verify as verify_session, adapter
from gateway.event_graph_span_extractor import prompt,parse_output
from gateway.typed_event_graph import semantic_graph,validate_graph
from gateway.event_graph_compiler import compile_graph
HERE=Path(__file__).parent
SESSION=ROOT/'.tmp/event-graph-lora-v14-session-001'
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
    result_path=ROOT/'validation/runs/event-graph-lora-v14-session-001/RESULT.json'
    result=json.loads(result_path.read_text())
    assert result['comparison']['selected_epoch']==1
    assert result['comparison']['selected_cumulative_steps']==4380
    assert result['reports'][1]['development_thresholds_met']
    selected=adapter(SESSION,1)
    assert sha(selected/'adapters.safetensors')=='c6a4708d9ceca6dab5d275ea0bff5ac172e392d085a4fda6b0d875e51d95a994'
    preflight=json.loads((HERE/'PREFLIGHT.json').read_text())
    assert preflight['records']==132 and preflight['max_gold_sequence_tokens']<=4096
    rows=read_rows('heldout')
    sources={r['source'] for r in rows}
    if len(rows)!=132 or len(sources)!=132:raise ValueError('fresh source inventory mismatch')
    prior_sources=set()
    for directory in ROOT.glob('validation/event_graph_v*'):
        if directory==HERE:continue
        for p in list(directory.glob('data/*.jsonl'))+list(directory.glob('heldout.jsonl')):
            prior_sources.update(json.loads(x)['source'] for x in p.read_text().splitlines())
    if sources & prior_sources:raise ValueError('source overlap with previous inventories')
    groups=defaultdict(dict)
    for row in rows:
        validate_graph(row['graph'],row['source'])
        groups[row['group']][row['variant']]=semantic_graph(row['graph'])
    assert len(groups)==44
    for g in groups.values():
        assert g['canonical']==g['paraphrase'] and g['canonical']!=g['contrast']
    files=[p for p in HERE.iterdir() if p.suffix in ('.py','.md','.jsonl','.json')]
    files += [ROOT/'gateway/tests/test_event_graph_v15.py',result_path]
    write_new(run/'freeze.json',{'created_unix':time.time(),'selected_cumulative_steps':4380,
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
    assert {n:importlib.metadata.version(n) for n in ('mlx','mlx-lm')}=={'mlx':'0.31.1','mlx-lm':'0.31.2'}
    from mlx_lm import load, stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7)
    model, tokenizer = load(str(MODEL), adapter_path=str(ADAPTER))
    sampler = make_sampler(temp=0.0)
    with output.open("x") as stream:
        for row in read_rows(split):
            start = time.time()
            formatted = tokenizer.apply_chat_template([{"role": "user", "content": prompt(row["source"])}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
            pieces=[];token_ids=[]
            for chunk in stream_generate(model,tokenizer,prompt=formatted,max_tokens=4096,sampler=sampler):
                pieces.append(chunk.text);token_ids.append(int(chunk.token))
            raw=''.join(pieces)
            prediction = {"id": row["id"], "raw": raw, "token_ids":token_ids,
                "finish_reason":chunk.finish_reason,"eos_token_ids":sorted(tokenizer.eos_token_ids),"seconds": time.time() - start}
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

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('freeze','verify','infer'))
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    if args.command=='freeze':freeze(args.run)
    elif args.command=='verify':verify_freeze(args.run)
    else:
        write_new(args.run/'status.json',{'status':'RUNNING','phase':'heldout_extraction','started_unix':time.time()})
        try:
            infer(args.run,'heldout')
            (args.run/'status.json').write_text(json.dumps({'status':'COMPLETE','completed_unix':time.time()}))
        except BaseException as exc:
            (args.run/'status.json').write_text(json.dumps({'status':'FAILED','error':str(exc),'time':time.time()}))
            raise

if __name__=='__main__':main()
