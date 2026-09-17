"""Fresh authored post-selection test; no model-generated labels or training data."""
from decimal import Decimal
from validation.event_graph_v12.wording import render
import json
from pathlib import Path
from gateway.event_graph_extractor_v3 import to_wire, bind, normalize_graph
from gateway.typed_event_graph import validate_graph, semantic_graph
from validation.event_graph_v1.build_corpus import Builder
from validation.event_graph_v3.build_corpus import FAMILIES

HERE = Path(__file__).parent


def make_row(family, index, variant):
    para, changed = variant == 1, variant == 2
    number = FAMILIES.index(family) + 1
    site = f'{("Obsidian Reach", "Willow Crossing")[index % 2]} {number:02d}-{index+1}'
    a, b = f'{site} excavation', f'{site} vibration'
    c, d = f'{site} superintendent', f'{site} discharge'
    value = ('2.17', '9.61')[index % 2]
    higher = str(Decimal(value) + Decimal('1.43'))
    g = None
    if family in ('quantity', 'comparator', 'polarity'):
        amount = higher if changed and family == 'quantity' else value
        op = 'LE' if changed and family == 'comparator' else 'GT'
        condition = f'{b} is {"at or below" if op == "LE" else "strictly above"} {amount} mm/s'
        neg = changed and family == 'polarity'
        modal = 'forbidden' if neg else 'compulsory'
        text = (f'Whenever {condition}, it is {modal} for {a} to stop.' if para else
                f'Stopping {a} is {modal} in the case where {condition}.')
        g=Builder(text); w=g.entity(a); m=g.entity(b)
        p=g.predicate(m,amount,'mm/s',op,condition)
        g.event('stop',roles={'object':w},condition=p,negated=neg)
    elif family in ('recipient','authority'):
        person = c + (' acting deputy' if changed else '')
        trigger = f'{b} is above {value} mm/s'
        if family == 'recipient':
            text = (f'{a} must stop when {trigger}. That same reading makes notification to {person} obligatory.' if para else
                    f'When {trigger}, a stop is required for {a}; the same trigger also requires that {person} receive notification.')
        else:
            text = (f'The issuer of this requirement is {person}: {a} must stop when {trigger}.' if para else
                    f'{person} issues the following requirement: a stop for {a} is mandatory when {trigger}.')
        g=Builder(text); w=g.entity(a); m=g.entity(b); person_id=g.entity(person)
        p=g.predicate(m,value,'mm/s','GT',trigger)
        g.event('stop',roles={'object':w,**({'authority':person_id} if family=='authority' else {})},condition=p)
        if family=='recipient':g.event('notify',roles={'recipient':person_id},condition=p)
    elif family=='unless':
        amount=higher if changed else value
        trigger=f'{b} is above {amount} mm/s'
        text=(f'{a} has permission to continue, except if {trigger}.' if para else
              f'Continuing {a} is permitted unless {trigger}.')
        g=Builder(text); w=g.entity(a); m=g.entity(b)
        p=g.predicate(m,amount,'mm/s','GT',trigger)
        g.event('continue',roles={'object':w},modality='permission',exception=p)
    elif family in ('nested','nested_boolean','negation_scope'):
        c,d=f'{site} water level',f'{site} settlement'
        ptext=f'{b} is {"not " if changed and family=="negation_scope" else ""}above {value} mm/s'
        qtext=f'{c} is below 1.63 m'; rtext=f'{d} is above 5.27 m'
        operator='any' if changed and family in ('nested','nested_boolean') else 'all'
        join='OR' if operator=='any' else 'AND'
        condition=f'({ptext}) {join} ({qtext})' if family=='nested' else f'({ptext}) {join} (({qtext}) OR ({rtext}))'
        text=(f'A stop for {a} is required if the following condition holds: {condition}.' if para else
              f'{a} must stop under this logical condition: {condition}.')
        g=Builder(text); w=g.entity(a); m=g.entity(b); low=g.entity(c)
        p=g.predicate(m,value,'mm/s','GT',ptext,negated=changed and family=='negation_scope')
        q=g.predicate(low,'1.63','m','LT',qtext)
        if family=='nested':cond=g.condition(operator,[p,q])
        else:
            high=g.entity(d); r=g.predicate(high,'5.27','m','GT',rtext)
            inner=g.condition('any',[q,r]);cond=g.condition(operator,[p,inner])
        g.event('stop',roles={'object':w},condition=cond)
    elif family=='direction':
        a,b=f'{site} dewatering',f'{site} settlement'
        source,target=(b,a) if changed else (a,b)
        text=(f'{source} is what causes {target}.' if para else f'{target} occurs because of {source}.')
        g=Builder(text); s=g.entity(source); t=g.entity(target)
        g.event('cause',roles={'source':s,'target':t},modality='assertion')
    elif family=='temporal':
        a,b,c=f'{site} inspection crew',f'{site} pump',f'{site} dewatering'
        order='after' if changed else 'before'
        text=(f'{a} is required to inspect {b}. This inspection must occur {order} {c} may continue.' if para else
              f'{a} must inspect {b}; the inspection is to take place {order} the permitted continuation of {c}.')
        g=Builder(text); actor=g.entity(a); obj=g.entity(b); works=g.entity(c)
        first=g.event('inspect',roles={'actor':actor,'object':obj})
        second=g.event('continue',roles={'object':works},modality='permission')
        g.link(order,first,second)
    elif family=='revision':
        old=f'SPEC-{number}-{index}-V7';new=f'SPEC-{number}-{index}-V'+('9' if changed else '8')
        text=(f'{old} requires {a} to stop. Its successor, {new}, supersedes that requirement and allows {a} to continue.' if para else
              f'Document revision {old} makes stopping {a} mandatory. This is superseded by revision {new}, which permits continuation of {a}.')
        g=Builder(text); w=g.entity(a)
        first=g.event('stop',roles={'object':w},revision=old)
        second=g.event('continue',roles={'object':w},modality='permission',revision=new)
        g.link('supersedes',second,first)
    elif family=='time':
        a,b=f'{site} inspection crew',f'{site} pump'
        date=f'2034-08-{11+index+(1 if changed else 0):02d}'
        text=(f'{a} must inspect {b} on the date {date}.' if para else
              f'The date assigned to the mandatory inspection of {b} by {a} is {date}.')
        g=Builder(text);actor=g.entity(a);obj=g.entity(b)
        g.event('inspect',roles={'actor':actor,'object':obj},time=date)
    elif family=='approval':
        person=c+(' acting deputy' if changed else '')
        text=(f'{a} may continue unless {person} approves a stop to it.' if para else
              f'Continuation of {a} is permitted. An exception applies if {person} approves stopping that excavation.')
        g=Builder(text);w=g.entity(a);who=g.entity(person)
        g.event('continue',roles={'object':w},modality='permission',exception='e2')
        g.event('approve',roles={'actor':who},modality='hypothetical',complement='e3')
        g.event('stop',roles={'object':w},modality='hypothetical')
    elif family=='conflict':
        last='allows it to continue' if changed else 'forbids it from stopping'
        text=(f'{a} must stop according to one instruction. Another instruction conflicts with this and {last}.' if para else
              f'The first rule makes stopping {a} compulsory; a second, conflicting rule {last}.')
        g=Builder(text);w=g.entity(a)
        first=g.event('stop',roles={'object':w})
        second=g.event('continue' if changed else 'stop',roles={'object':w},modality='permission' if changed else 'obligation',negated=not changed)
        g.link('conflicts',first,second)
    elif family=='multi_quantity':
        v1,v2=(higher,value) if changed else (value,higher)
        text=(f'{a} must stop when {b} exceeds {v1} mm/s. Notification to {c} is required if that reading exceeds {v2} mm/s.' if para else
              f'Two requirements apply: stop {a} if {b} rises above {v1} mm/s; notify {c} if that same measurement rises above {v2} mm/s.')
        g=Builder(text);w=g.entity(a);m=g.entity(b);who=g.entity(c)
        p=g.predicate(m,v1,'mm/s','GT',text);q=g.predicate(m,v2,'mm/s','GT',text)
        g.event('stop',roles={'object':w},condition=p);g.event('notify',roles={'recipient':who},condition=q)
    elif family=='unit_equivalence':
        b=f'{site} water level'
        amount,unit=(str(Decimal(value)*1000),'mm') if para else (higher if changed else value,'m')
        text=(f'{a} must stop if {b} is greater than {amount} {unit}.' if para else
              f'A reading of {b} strictly over {amount} {unit} makes stopping {a} obligatory.')
        g=Builder(text);w=g.entity(a);m=g.entity(b)
        p=g.predicate(m,amount,unit,'GT',text);g.event('stop',roles={'object':w},condition=p)
    elif family=='paragraph':
        cap=('37.9','62.8')[index]
        if changed:cap=str(Decimal(cap)+Decimal('8.6'))
        text=(f'{a} may continue if {b} is below {value} mm/s. If this reading is above {value} mm/s, {a} must stop and {c} must receive notification. {d} is permitted at a rate of at most {cap} L/min.' if para else
              f'With {b} below {value} mm/s, continued operation of {a} is allowed. A rise in that same reading above {value} mm/s requires {a} to stop; it also requires notification to {c}. The permitted upper rate for {d} is {cap} L/min.')
        g=Builder(text);w=g.entity(a);m=g.entity(b);who=g.entity(c);flow=g.entity(d)
        low=g.predicate(m,value,'mm/s','LT',text);high=g.predicate(m,value,'mm/s','GT',text);limit=g.predicate(flow,cap,'L/min','LE',text)
        g.event('continue',roles={'object':w},modality='permission',condition=low)
        g.event('stop',roles={'object':w},condition=high)
        g.event('notify',roles={'recipient':who},condition=high)
        g.event('discharge',roles={'object':flow},modality='permission',condition=limit)
    elif family=='comparison_bounds':
        value=('-2.19','0','3.79','6.23','10.51','14.87')[index]
        op=('GT','LT','EQ','GE','LE','NE')[(index+(1 if changed else 0))%6]
        phrase={'GT':'strictly greater than','LT':'strictly less than','EQ':'equal to','GE':'greater than or equal to','LE':'less than or equal to','NE':'not equal to'}[op]
        text=(f'If {b} is {phrase} {value} mm/s, {a} is required to stop.' if para else
              f'The condition making a stop compulsory for {a} is that {b} is {phrase} {value} mm/s.')
        g=Builder(text);w=g.entity(a);m=g.entity(b)
        p=g.predicate(m,value,'mm/s',op,text);g.event('stop',roles={'object':w},condition=p)
    elif family=='notification_roles':
        actor=f'{site} crew';issuer=f'{site} engineer';recipient=c
        if changed:issuer,recipient=recipient,issuer
        text=(f'The requirement issued by {issuer} says that {actor} must stop {a} and notify {recipient} if {b} exceeds {value} mm/s.' if para else
              f'{issuer} gives this instruction to {actor}: when {b} exceeds {value} mm/s, stop {a} and send notification to {recipient}.')
        g=Builder(text);w=g.entity(a);m=g.entity(b);who=g.entity(actor);auth=g.entity(issuer);dest=g.entity(recipient)
        p=g.predicate(m,value,'mm/s','GT',text)
        g.event('stop',roles={'actor':who,'object':w,'authority':auth},condition=p)
        g.event('notify',roles={'actor':who,'recipient':dest,'authority':auth},condition=p)
    else:raise ValueError(family)
    text=render(family,locals())
    for table in ('predicates','conditions','events','links'):
        for item in g.graph[table]:
            item['evidence']=[{'start':0,'end':len(text),'quote':text}]
            if table=='events':
                for key in ('time','revision'):
                    if item[key] is not None:
                        q=item[key]['value'];start=text.index(q)
                        item[key]['evidence']=[{'start':start,'end':start+len(q),'quote':q}]
    # Authored entity spans identify the first exact occurrence explicitly.
    for entity in g.graph['entities']:
        quote=entity['name'];start=text.index(quote)
        entity['mentions']=[{'quote':quote,'start':start,'end':start+len(quote)}]
    graph=normalize_graph(g.graph);validate_graph(graph,text)
    assert bind(to_wire(graph,text),text)==graph
    return {'id':f'v12-{family}-{index}-{variant}','group':f'v12-{family}-{index}',
            'family':family,'variant':('canonical','paraphrase','contrast')[variant],
            'source':text,'graph':graph}


def build():
    rows=[make_row(f,i,v) for f in FAMILIES for i in range(6 if f=='comparison_bounds' else 2) for v in range(3)]
    for start in range(0,len(rows),3):
        a,p,c=rows[start:start+3]
        assert semantic_graph(a['graph'])==semantic_graph(p['graph'])
        assert semantic_graph(a['graph'])!=semantic_graph(c['graph'])
    with (HERE/'heldout.jsonl').open('x') as stream:
        for r in rows:stream.write(json.dumps(r)+'\n')


if __name__=='__main__':build()
