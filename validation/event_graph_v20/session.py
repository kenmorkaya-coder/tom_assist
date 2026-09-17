"""Matched 96-update revision-replay pilot; outputs belong on Passport."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import argparse
import copy
import json
import time
from collections import defaultdict
from validation.event_graph_v16 import session as old
from validation.event_graph_v19 import session as previous
from validation.event_graph_v18 import diagnostic as diag
from validation.event_graph_v1.build_corpus import Builder
from gateway.typed_event_graph import semantic_graph, validate_graph
from gateway.event_graph_span_wire import to_wire
from gateway.gemma_training_alignment import AlignedChatTokenizer, check_alignment

HERE = Path(__file__).parent
V16 = ROOT / '.tmp/event-graph-lora-v16-session-001'
V18 = ROOT / '.tmp/event-graph-lora-v18-diagnostic-001'
RUN = Path('/Volumes/My Passport for Mac/gemmatraining/event-graph-lora-v20-pilot-001')
PLAN = dict(updates_per_arm=96, seed=151, learning_rate=0.000005, baseline_steps=4380,
    arms=['revision_replay'], changed_records=2, optimizer='reset as in V19 control',
    variable='replace only the two V8 revision examples with first two existing V13 revision examples',
    comparison='completed V19 control, same starting weights, 94 identical examples and identical sample slots/order',
    retention='original132 all exact; prior156 at least155; dev192 at least191 exact and all192 valid',
    evidence='all eight shared invalid-span revision cases must become valid and exact; unique diagnostic exact at least50; preserve all four original diagnostic anchor roles achieved by control',
    selection='retain4380 regardless; review before any further training or promotion',
    limitation='one small pilot at one seed; replacements differ in wording and evidence style together; tests revision replay as a bundle, not which subfeature caused an effect; exposed diagnostic is not held-out')


def training_rows(arm):
    assert arm == 'revision_replay'
    rows = previous.training_rows('control')
    replacements = [r for r in old.read_rows('train') if r['id'] in ('v13-train-revision-0-0','v13-train-revision-0-1')]
    assert len(replacements) == 2
    positions = [i for i,r in enumerate(rows) if r['family'] == 'revision']
    assert len(positions) == 2
    for i, replacement in zip(positions, replacements):
        slot_id = rows[i]['id']
        rows[i] = copy.deepcopy(replacement)
        rows[i]['source_row_id'] = replacement['id']
        rows[i]['id'] = slot_id
    return rows


def evaluation_rows():
    dev = old.read_rows('dev'); seen = set(); diagnostics = []
    for row in diag.rows():
        if row['source'] not in seen:
            seen.add(row['source']); diagnostics.append(row)
    assert len(dev) == 192 and len(diagnostics) == 56
    return dev + diagnostics


def messages(row):
    return [{'role': 'user', 'content': old.prompt(row['source'])},
        {'role': 'assistant', 'content': json.dumps(to_wire(row['graph'], row['source']), separators=(',', ':'))}]


def baseline_predictions():
    base = [json.loads(x) for x in (V16 / 'epoch-0/dev_predictions.jsonl').read_text().splitlines()]
    prior = {p['id']: p for p in map(json.loads, (V18 / 'epoch-0.jsonl').read_text().splitlines())}
    return base + [prior[r['id']] for r in evaluation_rows()[192:]]


def score(rows, predictions, thresholds):
    by_id = {p['id']: p for p in predictions}
    assert len(predictions) == len(by_id) == 248 and set(by_id) == {r['id'] for r in rows}
    development = old.development_score(rows[:192], [by_id[r['id']] for r in rows[:192]], thresholds)
    diagnostic_rows = rows[192:]; exact = valid = 0; cases = []
    for row in diagnostic_rows:
        p = by_id[row['id']]; g = semantic_graph(p['graph']) if 'graph' in p else None
        gold = semantic_graph(row['graph']); ok = g == gold
        exact += ok; valid += g is not None
        cases.append({'id': row['id'], 'exact': ok, 'roles': {role: g is not None and len(g['events']) == 1 and g['events'][0]['roles'][role] == gold['events'][0]['roles'][role] for role in ('source','target')}})
    return {'development': development, 'diagnostic': {'total':56,'exact':exact,'valid':valid,'details':cases}}


def verify(run):
    frozen = json.loads((run / 'freeze.json').read_text())
    old.verify(V16); diag.verify(V18); previous.verify(previous.RUN)
    for name, expected in frozen['files'].items(): assert old.prior.sha(Path(name)) == expected, name
    return frozen


def freeze(run):
    old.verify(V16); diag.verify(V18); previous.verify(previous.RUN)
    assert run == RUN and run.parent.is_dir() and not run.exists()
    source = old.adapter(V16, 0)
    files = [Path(__file__).resolve(), ROOT/'gateway/tests/test_event_graph_v20.py',
        ROOT/'validation/event_graph_v19/session.py', previous.RUN/'freeze.json',
        previous.RUN/'control/report.json', previous.RUN/'control/predictions.jsonl',
        previous.RUN/'control/training_complete.json', previous.RUN/'control/training_started.json',
        previous.RUN/'control/sampled_ids.jsonl',
        V16/'freeze.json', V16/'epoch-0/dev_predictions.jsonl', V18/'freeze.json', V18/'epoch-0.jsonl',
        ROOT/'validation/event_graph_v18/diagnostic.py', source/'adapters.safetensors', source/'adapter_config.json']
    run.mkdir()
    frozen = {'created_unix':time.time(),'plan':PLAN,'files':{str(p):old.prior.sha(p) for p in files},
        'thresholds':old.verify(V16)['thresholds'],'training_ids':[r['id'] for r in training_rows('revision_replay')],
        'changed_ids':[a['id'] for a,b in zip(previous.training_rows('control'),training_rows('revision_replay')) if a!=b],
        'replacement_mapping':{r['id']:r['source_row_id'] for r in training_rows('revision_replay') if 'source_row_id' in r}}
    old.prior.write_new(run/'freeze.json',frozen)
    predictions=baseline_predictions()
    for row,p in zip(evaluation_rows(),predictions):
        assert row['id']==p['id']
        assert old.parse_output(p['raw'],row['source'])==p['graph']
    old.prior.write_new(run/'baseline.json',score(evaluation_rows(),predictions,frozen['thresholds']))


def train(run, arm):
    frozen=verify(run)
    import importlib.metadata
    assert {n:importlib.metadata.version(n) for n in ('mlx','mlx-lm')} == {'mlx':'0.31.1','mlx-lm':'0.31.2'}
    import mlx.core as mx
    import numpy as np
    from types import SimpleNamespace
    from mlx_lm import load
    from mlx_lm.lora import train_model, CONFIG_DEFAULTS
    from mlx_lm.tuner.datasets import ChatDataset
    directory=run/arm; directory.mkdir(exist_ok=True)
    source=old.adapter(V16,0)
    config={**CONFIG_DEFAULTS,**old.prior.CONFIG,'seed':151,'iters':96,'learning_rate':0.000005,
        'steps_per_report':16,'steps_per_eval':96,'save_every':96,'model':str(old.prior.MODEL),
        'adapter_path':str(directory/'adapter'),'resume_adapter_file':str(source/'adapters.safetensors')}
    old.prior.write_new(directory/'training_started.json',{'time':time.time(),'config':config,'input_adapter_sha256':old.prior.sha(source/'adapters.safetensors')})
    model,tokenizer=load(str(old.prior.MODEL)); rows=training_rows(arm)
    alignment=[check_alignment(tokenizer,messages(r)) for r in rows]
    assert max(x['total_tokens'] for x in alignment)<=4096
    old.prior.write_new(directory/'alignment.json',{'count':96,'max_tokens':max(x['total_tokens'] for x in alignment)})
    processed=[]
    class RecordedChat(ChatDataset):
        def process(self, item):
            processed.append(item['id'])
            with (directory/'sampled_ids.jsonl').open('a') as f:f.write(json.dumps({'step':len(processed),'id':item['id']})+'\n')
            return super().process(item)
    data=[{'id':r['id'],'messages':messages(r)} for r in rows]
    # CacheDataset sorts these uniform two-key records stably; log actual processing too.
    expected=[rows[int(i)]['id'] for i in np.random.RandomState(151).permutation(96)]
    dataset=RecordedChat(data,AlignedChatTokenizer(tokenizer),mask_prompt=True)
    np.random.seed(151);mx.random.seed(151)
    train_model(SimpleNamespace(**config),model,dataset,[],training_callback=None)
    assert processed==expected and len(set(processed))==96
    control_receipt=json.loads((previous.RUN/'control/training_complete.json').read_text())
    assert processed==control_receipt['sampled_ids']
    adapter=directory/'adapter'
    old.prior.write_new(directory/'training_complete.json',{'iterations':96,'cumulative_steps':4476,'sampled_all_once':True,
        'sampled_ids':processed,'adapter_sha256':old.prior.sha(adapter/'adapters.safetensors'),'config_sha256':old.prior.sha(adapter/'adapter_config.json')})


def evaluate(run, arm):
    frozen=verify(run); directory=run/arm
    receipt=json.loads((directory/'training_complete.json').read_text()); adapter=directory/'adapter'
    assert old.prior.sha(adapter/'adapters.safetensors')==receipt['adapter_sha256']
    assert old.prior.sha(adapter/'adapter_config.json')==receipt['config_sha256']
    from mlx_lm import load,stream_generate
    from mlx_lm.sample_utils import make_sampler
    import mlx.core as mx
    mx.random.seed(7);model,tokenizer=load(str(old.prior.MODEL),adapter_path=str(adapter));sampler=make_sampler(temp=0.0)
    rows=evaluation_rows();path=directory/'predictions.jsonl'
    with path.open('x') as out:
        for row in rows:
            prompt=tokenizer.apply_chat_template([messages(row)[0]],tokenize=False,add_generation_prompt=True,enable_thinking=False)
            chunks=list(stream_generate(model,tokenizer,prompt=prompt,max_tokens=4096,sampler=sampler))
            p={'id':row['id'],'raw':''.join(c.text for c in chunks),'token_ids':[int(c.token) for c in chunks],
                'finish_reason':chunks[-1].finish_reason,'eos_token_ids':sorted(tokenizer.eos_token_ids)}
            try:p['graph']=old.parse_output(p['raw'],row['source'])
            except (ValueError,TypeError,KeyError,RecursionError) as exc:p['error']=str(exc)
            out.write(json.dumps(p)+'\n');out.flush();print(json.dumps({'arm':arm,'completed_id':row['id']}),flush=True)
    result=score(rows,[json.loads(x) for x in path.read_text().splitlines()],frozen['thresholds'])
    result.update(prediction_sha256=old.prior.sha(path),adapter_sha256=receipt['adapter_sha256'])
    old.prior.write_new(directory/'report.json',result)


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=('freeze','run','train','evaluate'));p.add_argument('--arm',choices=PLAN['arms']);args=p.parse_args();run=RUN
    if args.command=='freeze':freeze(run);return
    if args.command=='train':train(run,args.arm);return
    if args.command=='evaluate':evaluate(run,args.arm);return
    import subprocess
    verify(run);old.prior.write_new(run/'started.json',{'time':time.time()})
    try:
        for arm in PLAN['arms']:
            (run/arm).mkdir(exist_ok=True)
            for phase in ('train','evaluate'):
                (run/'status.json').write_text(json.dumps({'status':'RUNNING','arm':arm,'phase':phase}))
                with (run/arm/f'{phase}.log').open('x') as log:subprocess.run([sys.executable,'-u',str(Path(__file__).resolve()),phase,'--arm',arm],stdout=log,stderr=subprocess.STDOUT,check=True)
        old.prior.write_new(run/'complete.json',{'status':'COMPLETE_UNREVIEWED','time':time.time()})
        (run/'status.json').write_text(json.dumps({'status':'COMPLETE_UNREVIEWED'}))
    except BaseException as exc:
        (run/'status.json').write_text(json.dumps({'status':'FAILED','error':str(exc)}));raise


if __name__=='__main__':main()
