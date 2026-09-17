"""Recompute v8 regression transitions from immutable saved generations."""
import json
from collections import Counter
from pathlib import Path
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v8 import session as s


def differences(a,b,path=''):
    if type(a)!=type(b):return [{'path':path,'expected':a,'actual':b}]
    if isinstance(a,dict):
        if set(a)!=set(b):return [{'path':path,'expected':a,'actual':b}]
        return [d for k in a for d in differences(a[k],b[k],path+'.'+k)]
    if isinstance(a,list):
        if len(a)!=len(b):return [{'path':path+'.length','expected':len(a),'actual':len(b)}]
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+f'[{i}]')]
    return [] if a==b else [{'path':path,'expected':a,'actual':b}]


def audit(run):
    frozen=s.verify(run);rows=s.read_rows('dev');sources={r['id']:r['source'] for r in rows};predictions=[];reports=[]
    for epoch in (1,2):
        directory=run/f'epoch-{epoch}';adapter=s.adapter(run,epoch)
        ps=[json.loads(x) for x in (directory/'dev_predictions.jsonl').read_text().splitlines()]
        assert len(ps)==132
        for p in ps:
            try:g=s.parse_output(p['raw'],sources[p['id']])
            except (ValueError,TypeError,KeyError,RecursionError) as exc:assert 'graph' not in p and str(exc)==p['error']
            else:assert g==p['graph']
        r=json.loads((directory/'dev_report.json').read_text());actual=s.development_score(rows,ps,frozen['thresholds'])
        assert all(r[k]==v for k,v in actual.items())
        assert r['adapter_sha256']==s.prior.sha(adapter/'adapters.safetensors')
        assert r['prediction_sha256']==s.prior.sha(directory/'dev_predictions.jsonl')
        predictions.append({p['id']:p for p in ps});reports.append(r)
    transitions=Counter();details=[]
    for row in rows:
        gold=semantic_graph(row['graph']);ps=[d[row['id']] for d in predictions]
        gs=[semantic_graph(p['graph']) if 'graph' in p else None for p in ps];ok=[g==gold for g in gs]
        category='unchanged_correct' if all(ok) else 'regressed' if ok[0] else 'recovered' if ok[1] else 'persistent'
        transitions[category]+=1
        if category=='unchanged_correct':continue
        details.append({'id':row['id'],'family':row['family'],'transition':category,'source':row['source'],
            'epochs':[{'error':p['error']} if g is None else {'differences':differences(gold,g)} for p,g in zip(ps,gs)]})
    return {'transitions':dict(transitions),'comparison':s.comparison(reports),'details':details,
            'prediction_hashes':[r['prediction_sha256'] for r in reports],
            'limitation':'Observed error transitions do not establish the causal contribution of learning rate, optimizer reset or template coverage.'}


if __name__=='__main__':
    out=Path('validation/runs/event-graph-v8-regression-audit');out.mkdir(parents=True,exist_ok=True)
    result=audit(Path('.tmp/event-graph-lora-v8-session-001').resolve())
    result['token_replay']=json.loads(Path('.tmp/event-graph-v8-regression-audit/token_replay.json').read_text())
    s.prior.write_new(out/'RESULT.json',result)
    print(json.dumps(result['transitions']))
