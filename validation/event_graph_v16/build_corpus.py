"""Authored boundary and scoped-negation curriculum with separate dev extension."""
import json
from decimal import Decimal
from pathlib import Path
from validation.event_graph_v1.build_corpus import Builder
from validation.event_graph_v14 import session as old
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import prompt
from gateway.typed_event_graph import validate_graph,semantic_graph
HERE=Path(__file__).parent
FAMILIES=('polarity','direction','paragraph')


def example(split,family,i,v):
    para=v==1;changed=v==2
    site=(('Alder Hall','Quartz Depot','Birch Dock','Amber Shaft')[i%4] if split=='train' else ('Marsh Gallery','Flint Tunnel')[i%2])+f' {split[0].upper()}{i:02d}-K'
    a=f'{site} '+('east foundation works','south cutting works')[i%2]
    b=f'{site} vibration monitor';c=f'{site} deputy superintendent';d=f'{site} outlet discharge'
    n=str(Decimal('1.37' if split=='train' else '2.53')+Decimal(i)*Decimal('0.73'))
    cap=str(170+i*19+(41 if changed else 0))
    verb=('registers','records','reports','measures')[i%4]
    if family=='polarity':
        modal='must not' if changed else 'must'
        if split=='train':
            text=(f'When {b} {verb} above {n} mm/s, {a} {modal} stop.' if para else
                  f'{a} {modal} stop if {b} {verb} above {n} mm/s.')
        else:
            text=(f'For readings of {b} above {n} mm/s, {a} {modal} stop.' if para else
                  f'The following conditional rule applies: {a} {modal} stop when {b} {verb} more than {n} mm/s.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b)
        p=g.predicate(sensor,n,'mm/s','GT',text)
        g.event('stop',roles={'object':w},condition=p,negated=changed)
    elif family=='direction':
        a=f'{site} groundwater pumping';b=f'{site} ground settlement'
        source,target=(b,a) if changed else (a,b)
        if split=='train':
            text=(f'The cause of {target} is {source}.' if para else
                  f'{source} causes {target}.')
        else:
            text=(f'{target} is caused by {source}.' if para else
                  f'The process bringing about {target} is {source}.')
        g=Builder(text);src=g.entity(source);dst=g.entity(target)
        g.event('cause',roles={'source':src,'target':dst},modality='assertion')
    else:
        if split=='train':
            text=(f'Continuation of {a} is permitted while {b} {verb} below {n} mm/s. Above {n} mm/s on that monitor, {a} must stop and {c} must be notified. {d} may run at no more than {cap} L/min.' if para else
                  f'{a} may continue when {b} {verb} less than {n} mm/s. If that monitor {verb} more than {n} mm/s, stopping those works and notifying {c} are required. {d} is allowed at up to {cap} L/min.')
        else:
            text=(f'{a} has permission to continue with {b} measuring below {n} mm/s. A value above {n} mm/s on that device requires stopping {a} and notification to {c}. Operation of {d} is permitted with a cap of {cap} L/min.' if para else
                  f'{a} may continue provided {b} records under {n} mm/s. A reading over {n} mm/s from that monitor requires a stop to those works, together with notification to {c}. {d} may operate at a maximum of {cap} L/min.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b);who=g.entity(c);flow=g.entity(d)
        low=g.predicate(sensor,n,'mm/s','LT',text);high=g.predicate(sensor,n,'mm/s','GT',text);limit=g.predicate(flow,cap,'L/min','LE',text)
        g.event('continue',roles={'object':w},condition=low,modality='permission')
        g.event('stop',roles={'object':w},condition=high)
        g.event('notify',roles={'recipient':who},condition=high)
        g.event('discharge',roles={'object':flow},condition=limit,modality='permission')
    for entity in g.graph['entities']:
        q=entity['name'];start=text.index(q);entity['mentions']=[{'start':start,'end':start+len(q),'quote':q}]
    validate_graph(g.graph,text)
    return {'id':f'v16-{split}-{family}-{i}-{v}','group':f'v16-{split}-{family}-{i}',
            'family':family,'variant':('canonical','paraphrase','contrast')[v],'source':text,'graph':g.graph}


def build():
    for split,count in (('train',16),('dev',4)):
        extra=[example(split,f,i,v) for f in FAMILIES for i in range(count) for v in range(3)]
        for i in range(0,len(extra),3):
            a,b,c=[semantic_graph(r['graph']) for r in extra[i:i+3]];assert a==b and a!=c
        rows=old.read_rows(split)+extra
        assert len(rows)==(1584 if split=='train' else 192)
        assert len({r['source'] for r in rows})==len(rows)
        (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
        with (HERE/'data'/f'{split}.jsonl').open('x') as f:
            for r in rows:f.write(json.dumps(r)+'\n')
        with (HERE/'training'/('train.jsonl' if split=='train' else 'valid.jsonl')).open('x') as f:
            for r in rows:f.write(json.dumps({'messages':[{'role':'user','content':prompt(r['source'])},{'role':'assistant','content':json.dumps(to_wire(r['graph'],r['source']),separators=(',',':'))}]})+'\n')


if __name__=='__main__':build()
