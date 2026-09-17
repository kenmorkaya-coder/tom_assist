"""Authored augmentation of train-only semantics; separate development names."""
import json
from pathlib import Path
from gateway.event_graph_extractor_v3 import to_wire as quote_wire,bind as bind_quotes
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import prompt
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v3.build_corpus import make_row,FAMILIES
HERE=Path(__file__).parent


def augment(base,split,group_index):
    site=(('Basin Facility','Quarry Sector','Intake Zone','Switchyard Annex')[group_index%4] if split=='train' else
          ('Canal Reach','Ravine Station')[group_index%2])
    site+=f' {"T" if split=="train" else "D"}{group_index:03d}'
    old=base['graph']['entities'][0]['name'].split()[0]
    words={'excavation':'west excavation area','superintendent':'deputy superintendent','engineer':'senior engineer','crew':'night crew','pump':'transfer pump'} if group_index%2 else {}
    def replace(s):
        for a,b in words.items():s=s.replace(a,b)
        return s.replace(old,site)
    def walk(v):
        if isinstance(v,str):return replace(v)
        if isinstance(v,list):return [walk(x) for x in v]
        if isinstance(v,dict):return {k:walk(x) for k,x in v.items()}
        return v
    wire=walk(quote_wire(base['graph'],base['source']))
    headers=('Project instructions — ','For the day shift: ','Method statement note: ','Operational guidance: ','') if split=='train' else ('Site briefing: ','In the execution notes: ','')
    variant=('canonical','paraphrase','contrast').index(base['variant'])
    text=headers[(group_index+variant)%len(headers)]+replace(base['source'])
    graph=bind_quotes(wire,text)
    return {'id':f'v8-{split}-{group_index}-{variant}','group':f'v8-{split}-{group_index}',
        'family':base['family'],'variant':base['variant'],'source':text,'graph':graph}


def build():
    train=[];dev=[];group=0
    for family in FAMILIES:
        for index in range(8):
            train.extend(augment(make_row('train',family,index,v),'train',group) for v in range(3));group+=1
    # 160 more groups: half explicitly bind actor, issuer and notification recipient.
    for i in range(160):
        family='notification_roles' if i%2==0 else FAMILIES[(i//2)%len(FAMILIES)]
        train.extend(augment(make_row('train',family,i%8,v),'train',group) for v in range(3));group+=1
    group=0
    for family in FAMILIES:
        for index in range(6 if family=='comparison_bounds' else 2):
            dev.extend(augment(make_row('dev',family,index,v),'dev',group) for v in range(3));group+=1
    assert len(train)==960 and len(dev)==132
    for split,rows in (('train',train),('dev',dev)):
        assert len({r['source'] for r in rows})==len(rows)
        for i in range(0,len(rows),3):
            a,p,c=[semantic_graph(r['graph']) for r in rows[i:i+3]]
            assert a==p and a!=c
        (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
        with (HERE/'data'/f'{split}.jsonl').open('x') as f:
            for row in rows:f.write(json.dumps(row)+'\n')
        with (HERE/'training'/('train.jsonl' if split=='train' else 'valid.jsonl')).open('x') as f:
            for row in rows:
                messages=[{'role':'user','content':prompt(row['source'])},{'role':'assistant','content':json.dumps(to_wire(row['graph'],row['source']),separators=(',',':'))}]
                f.write(json.dumps({'messages':messages})+'\n')


if __name__=='__main__':build()
