"""Post-hoc diagnosis and representation measurements; never changes old scores."""
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gateway.typed_event_graph import semantic_graph
from gateway.event_graph_extractor_v3 import to_wire as quote_wire
from gateway.event_graph_span_wire import to_wire as span_wire,bind,source_table


def rows(path):return [json.loads(x) for x in path.read_text().splitlines()]


def quotes(value):
    if isinstance(value,dict):
        if 'quote' in value:yield value['quote']
        for child in value.values():yield from quotes(child)
    elif isinstance(value,list):
        for child in value:yield from quotes(child)


def main():
    corpora={}
    for split in ('train','dev'):
        inventory=rows(ROOT/f'validation/event_graph_v3/data/{split}.jsonl')
        meanings=defaultdict(set);entity_sizes=Counter();old_bytes=new_bytes=quote_chars=table_bytes=0
        for row in inventory:
            meanings[row['source']].add(json.dumps(semantic_graph(row['graph']),sort_keys=True))
            entity_sizes[len(row['graph']['entities'])]+=1
            old=quote_wire(row['graph'],row['source']);new=span_wire(row['graph'],row['source'])
            assert semantic_graph(bind(new,row['source']))==semantic_graph(row['graph'])
            old_bytes+=len(json.dumps(old,separators=(',',':')).encode())
            new_bytes+=len(json.dumps(new,separators=(',',':')).encode())
            quote_chars+=sum(len(q) for q in quotes(old))
            table_bytes+=len(json.dumps(source_table(row['source']),separators=(',',':')).encode())
        corpora[split]={'records':len(inventory),'unique_source_strings':len(meanings),
            'conflicting_semantic_labels':sum(len(v)>1 for v in meanings.values()),
            'entity_count_distribution':dict(entity_sizes),'old_wire_bytes':old_bytes,
            'prototype_wire_bytes':new_bytes,'old_repeated_quote_characters':quote_chars,
            'prototype_added_source_table_bytes':table_bytes,
            'wire_size_reduction_percent':round(100*(old_bytes-new_bytes)/old_bytes,2)}
    predicted=rows(ROOT/'.tmp/event-graph-lora-v7-session-001/epoch-1/dev_predictions.jsonl')
    details=[]
    for p in predicted:
        if p.get('error') not in ('unreferenced graph content','dangling or mistyped reference'):continue
        g=json.loads(p['raw']);refs=set()
        for e in g['events']:
            refs.update(v for v in e['roles'].values() if v is not None)
            refs.update(e[k] for k in ('condition','exception','complement') if e[k] is not None)
        for c in g['conditions']:refs.update(c['args'])
        for q in g['predicates']:refs.add(q['subject'])
        known={r['id'] for t in ('entities','predicates','conditions','events','links') for r in g[t]}
        unused=[r['name'] for r in g['entities'] if r['id'] not in refs]
        details.append({'id':p['id'],'error':p['error'],'unused_entity_names':unused,'absent_referenced_ids':sorted(refs-known)})
    result={'status':'POST_HOC_AUDIT_NO_SCORE_REPAIR','corpora':corpora,
        'v7_epoch1_reference_failures':details,
        'orphan_entity_name_counts':dict(Counter(n for d in details for n in d['unused_entity_names'])),
        'missing_id_counts':dict(Counter(n for d in details for n in d['absent_referenced_ids'])),
        'new_generations':0,'training_updates':0,
        'prototype_limit':'Deterministic roundtrips demonstrate representability only. Index selection and role accuracy require new supervised training and evaluation; wrong valid spans remain possible.'}
    out=ROOT/'.tmp/event-graph-binding-audit-001';out.mkdir(parents=True,exist_ok=True)
    with (out/'structure.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='v7_epoch1_reference_failures'},indent=2))


if __name__=='__main__':main()
