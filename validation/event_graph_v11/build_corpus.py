"""Authored framing variants; no development rows used as training labels."""
from copy import deepcopy
import json
from pathlib import Path
from validation.event_graph_v10.build_corpus import example
from validation.event_graph_v10 import session as old
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import prompt
from gateway.typed_event_graph import validate_graph,semantic_graph
HERE=Path(__file__).parent
HEADERS=('Construction note — ','For the supervisor log: ','Current work requirements: ','Applicable instructions: ','Daily operations record: ','Local operating rules: ')


def framed(family,i,v):
    # Both equivalent variants keep nominalized action wording, but change framing.
    row=deepcopy(example(family,i,2 if v==2 else 0))
    header=HEADERS[(i+v)%len(HEADERS)]
    if i%3==0:header+='Operational guidance: '
    def shift(x):
        if isinstance(x,dict):
            if set(x)=={'start','end','quote'}:x['start']+=len(header);x['end']+=len(header)
            else:
                for y in x.values():shift(y)
        elif isinstance(x,list):
            for y in x:shift(y)
    shift(row['graph']);row['source']=header+row['source']
    row.update(id=f'v11-train-{family}-{i}-{v}',group=f'v11-train-{family}-{i}',variant=('canonical','paraphrase','contrast')[v])
    validate_graph(row['graph'],row['source']);return row


def build():
    extra=[framed(f,i,v) for f in ('paragraph','approval') for i in range(20,40) for v in range(3)]
    for i in range(0,len(extra),3):
        a,b,c=[semantic_graph(r['graph']) for r in extra[i:i+3]];assert a==b and a!=c
    rows=old.read_rows('train')+extra;assert len(rows)==1320
    assert len({r['source'] for r in rows})==1320
    assert not {r['source'] for r in rows}&{r['source'] for r in old.read_rows('dev')}
    (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
    with (HERE/'data/train.jsonl').open('x') as f:
        for r in rows:f.write(json.dumps(r)+'\n')
    with (HERE/'training/train.jsonl').open('x') as f:
        for r in rows:f.write(json.dumps({'messages':[{'role':'user','content':prompt(r['source'])},{'role':'assistant','content':json.dumps(to_wire(r['graph'],r['source']),separators=(',',':'))}]})+'\n')
    with (HERE/'training/valid.jsonl').open('x') as f:f.write((old.HERE/'training/valid.jsonl').read_text())


if __name__=='__main__':build()
