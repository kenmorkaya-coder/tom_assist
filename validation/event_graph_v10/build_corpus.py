"""Development-informed general-pattern augmentation; no evaluation rows copied."""
import json
from decimal import Decimal
from pathlib import Path
from validation.event_graph_v1.build_corpus import Builder
from validation.event_graph_v8 import session as old
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import prompt
from gateway.typed_event_graph import validate_graph,semantic_graph
HERE=Path(__file__).parent
FAMILIES=('unless','direction','paragraph','approval','multi_quantity')


def example(family,i,v):
    site=('Granite Yard','Cedar Tunnel','Delta Basin','Foundry Site')[i%4]+f' X{i:02d}'
    a=f'{site} '+('east trench works','piling operation','south excavation','drilling works')[i%4]
    b=f'{site} vibration sensor';c=f'{site} '+('shift supervisor','deputy inspector','site superintendent','night supervisor')[i%4]
    d=f'{site} discharge';n=str(Decimal('0.8')+Decimal(i)*Decimal('0.6'));m=str(Decimal(n)+Decimal('3.7'))
    cap=str(180+i*25+(75 if v==2 else 0));para=v==1;contrast=v==2
    if family=='unless':
        join='if' if contrast else 'unless'
        text=(f'{a} may continue {join} {b} exceeds {n} mm/s.' if para else
              f'{join.capitalize()} {b} exceeds {n} mm/s, continuation of {a} is permitted.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b);p=g.predicate(sensor,n,'mm/s','GT',text)
        g.event('continue',roles={'object':w},modality='permission',**{('condition' if contrast else 'exception'):p})
    elif family=='direction':
        a=f'{site} groundwater removal';b=f'{site} ground movement'
        src,dst=(b,a) if contrast else (a,b)
        text=f'{src} causes {dst}.' if para else (f'The cause of {dst} is {src}.' if i%2 else f'The process responsible for {dst} is {src}.')
        g=Builder(text);s=g.entity(src);t=g.entity(dst);g.event('cause',roles={'source':s,'target':t},modality='assertion')
    elif family=='paragraph':
        text=(f'{a} may continue while {b} is below {n} mm/s. If that sensor exceeds {n} mm/s, {a} must stop and {c} must be notified. {d} may operate at no more than {cap} L/min.' if para else
              f'Continuation of {a} is permitted when {b} stays below {n} mm/s. A reading above {n} mm/s on the same sensor requires stopping {a} and notifying {c}. The permitted rate for {d} is at most {cap} L/min.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b);person=g.entity(c);dis=g.entity(d)
        low=g.predicate(sensor,n,'mm/s','LT',text);high=g.predicate(sensor,n,'mm/s','GT',text);limit=g.predicate(dis,cap,'L/min','LE',text)
        g.event('continue',roles={'object':w},condition=low,modality='permission')
        g.event('stop',roles={'object':w},condition=high);g.event('notify',roles={'recipient':person},condition=high)
        g.event('discharge',roles={'object':dis},condition=limit,modality='permission')
    elif family=='approval':
        if contrast:c+=' alternate'
        text=(f'{a} may continue unless {c} approves stopping {a}.' if para else
              f'Continuation of {a} is permitted except if {c} approves stopping it.')
        g=Builder(text);w=g.entity(a);person=g.entity(c)
        g.event('continue',roles={'object':w},modality='permission',exception='e2')
        g.event('approve',roles={'actor':person},modality='hypothetical',complement='e3')
        g.event('stop',roles={'object':w},modality='hypothetical')
    else:
        first,second=(m,n) if contrast else (n,m)
        text=(f'{a} must stop if {b} exceeds {first} mm/s. Notification to {c} is required if that sensor exceeds {second} mm/s.' if para else
              f'Above {first} mm/s measured by {b}, stopping {a} is mandatory; above {second} mm/s on the same sensor, notifying {c} is mandatory.')
        g=Builder(text);w=g.entity(a);sensor=g.entity(b);person=g.entity(c)
        p=g.predicate(sensor,first,'mm/s','GT',text);q=g.predicate(sensor,second,'mm/s','GT',text)
        g.event('stop',roles={'object':w},condition=p);g.event('notify',roles={'recipient':person},condition=q)
    # Full named entity spans, even when a name appears repeatedly.
    for e in g.graph['entities']:
        start=text.index(e['name']);e['mentions']=[{'start':start,'end':start+len(e['name']),'quote':e['name']}]
    validate_graph(g.graph,text)
    return {'id':f'v10-train-{family}-{i}-{v}','group':f'v10-train-{family}-{i}',
            'family':family,'variant':('canonical','paraphrase','contrast')[v],'source':text,'graph':g.graph}


def build():
    extra=[example(f,i,v) for f in FAMILIES for i in range(16) for v in range(3)]
    for k in range(0,len(extra),3):
        a,b,c=[semantic_graph(r['graph']) for r in extra[k:k+3]];assert a==b and a!=c
    rows=old.read_rows('train')+extra;assert len(rows)==1200
    assert len({r['source'] for r in rows})==1200
    assert not {r['source'] for r in rows}&{r['source'] for r in old.read_rows('dev')}
    (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
    with (HERE/'data/train.jsonl').open('x') as f:
        for r in rows:f.write(json.dumps(r)+'\n')
    with (HERE/'training/train.jsonl').open('x') as f:
        for r in rows:f.write(json.dumps({'messages':[{'role':'user','content':prompt(r['source'])},{'role':'assistant','content':json.dumps(to_wire(r['graph'],r['source']),separators=(',',':'))}]})+'\n')
    with (HERE/'training/valid.jsonl').open('x') as f:f.write((old.HERE/'training/valid.jsonl').read_text())


if __name__=='__main__':build()
