"""Authored training/development extensions after the exposed v12 result."""
import json
from pathlib import Path
from decimal import Decimal
from validation.event_graph_v1.build_corpus import Builder
from validation.event_graph_v11 import session as old
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import prompt
from gateway.typed_event_graph import validate_graph,semantic_graph
HERE=Path(__file__).parent


def example(split,family,i,v):
    para=v==1;contrast=v==2
    site=(('Slate Pier','Pine Shaft','Copper Yard','Elm Cut')[i%4] if split=='train' else ('Basalt Lock','Maple Portal')[i%2])+f' {split[0].upper()}{i:02d}'
    a=f'{site} foundation works';b=f'{site} velocity monitor';c=f'{site} duty inspector';d=f'{site} outlet flow'
    n=str(Decimal('1.13' if split=='train' else '2.87')+Decimal(i)*Decimal('0.41'))
    cap=str(210+i*13+(29 if contrast else 0))
    if family=='revision':
        oldrev=f'PLAN-{split[0]}-{i:02d}-R2';newrev=f'PLAN-{split[0]}-{i:02d}-R'+('5' if contrast else '4')
        if split=='train':
            text=(f'{oldrev} requires stopping {a}. The replacement {newrev} permits its continuation and supersedes {oldrev}.' if para else
                  f'Revision {oldrev} says {a} must stop. Revision {newrev} replaces {oldrev} and says {a} may continue.')
        else:
            text=(f'Under {oldrev}, stopping {a} is obligatory. The later {newrev} supersedes it, permitting those works to continue.' if para else
                  f'The rule in {oldrev} requires {a} to stop; the permission in {newrev} lets {a} continue. {newrev} supersedes {oldrev}.')
        g=Builder(text);w=g.entity(a)
        first=g.event('stop',roles={'object':w},revision=oldrev)
        second=g.event('continue',roles={'object':w},modality='permission',revision=newrev)
        g.link('supersedes',second,first)
    else:
        if split=='train':
            text=(f'{a} may continue with {b} below {n} mm/s. Above {n} mm/s on the same monitor, two duties apply: stop those works and notify {c}. {d} may run at up to {cap} L/min.' if para else
                  f'{a} is allowed to continue if {b} stays below {n} mm/s. If that monitor exceeds {n} mm/s, stopping {a} and informing {c} are both required. Separately, {d} is permitted subject to a maximum of {cap} L/min.')
        else:
            text=(f'Continuation of {a} is permitted for {b} under {n} mm/s. When that measurement is over {n} mm/s, {a} must stop; notification to {c} is required by the same trigger. {d} may operate at no more than {cap} L/min.' if para else
                  f'{a} may continue while {b} is below {n} mm/s. Exceeding {n} mm/s on that measurement imposes both a stop on those works and a notification to {c}. A separate permission limits {d} to {cap} L/min.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b);who=g.entity(c);flow=g.entity(d)
        low=g.predicate(sensor,n,'mm/s','LT',text);high=g.predicate(sensor,n,'mm/s','GT',text);limit=g.predicate(flow,cap,'L/min','LE',text)
        g.event('continue',roles={'object':w},condition=low,modality='permission')
        g.event('stop',roles={'object':w},condition=high)
        g.event('notify',roles={'recipient':who},condition=high)
        g.event('discharge',roles={'object':flow},condition=limit,modality='permission')
    for entity in g.graph['entities']:
        q=entity['name'];start=text.index(q);entity['mentions']=[{'start':start,'end':start+len(q),'quote':q}]
    validate_graph(g.graph,text)
    return {'id':f'v13-{split}-{family}-{i}-{v}','group':f'v13-{split}-{family}-{i}','family':family,
            'variant':('canonical','paraphrase','contrast')[v],'source':text,'graph':g.graph}


def build():
    for split,count in (('train',20),('dev',4)):
        extra=[example(split,f,i,v) for f in ('revision','paragraph') for i in range(count) for v in range(3)]
        for i in range(0,len(extra),3):
            a,b,c=[semantic_graph(r['graph']) for r in extra[i:i+3]];assert a==b and a!=c
        rows=old.read_rows(split)+extra
        assert len(rows)==(1440 if split=='train' else 156)
        assert len({r['source'] for r in rows})==len(rows)
        (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
        with (HERE/'data'/f'{split}.jsonl').open('x') as f:
            for r in rows:f.write(json.dumps(r)+'\n')
        with (HERE/'training'/('train.jsonl' if split=='train' else 'valid.jsonl')).open('x') as f:
            for r in rows:f.write(json.dumps({'messages':[{'role':'user','content':prompt(r['source'])},{'role':'assistant','content':json.dumps(to_wire(r['graph'],r['source']),separators=(',',':'))}]})+'\n')


if __name__=='__main__':build()
