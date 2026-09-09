"""New typed-role vocabulary, compact evidence and independently written test wording.

Uses v1's authored semantic contrast definitions, never model predictions as labels.
V1 held-out source sentences are not used in training. Fresh test prose below is
written before v3 generation; shared semantic templates remain a stated limitation.
"""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import re
from gateway.event_graph_extractor_v3 import prompt, to_wire, bind, normalize_graph
from gateway.typed_event_graph import validate_graph, semantic_graph
from validation.event_graph_v1.build_corpus import case, FAMILIES as BASE_FAMILIES, Builder
FAMILIES = (*BASE_FAMILIES, "comparison_bounds", "notification_roles")

HERE = Path(__file__).parent


def span(text, quote, occurrence=0):
    matches = list(re.finditer(re.escape(quote), text))
    m = matches[occurrence]
    return [{"start": m.start(), "end": m.end(), "quote": quote}]


def fresh_text(family, a, b, c, d, value, contrast, para, revision_old, revision_new, date):
    amount = str(Decimal(value) + Decimal('2.3')) if contrast and family in ('quantity','unless','paragraph') else value
    wording = 'exceeds' if not para else 'is greater than'
    if family in ('quantity','comparator','polarity'):
        bound = f'is no higher than {amount}' if contrast and family=='comparator' else f'{wording} {amount}'
        modal = 'shall not halt' if contrast and family=='polarity' else ('is obliged to halt' if para else 'shall halt')
        return f'{a} {modal} whenever {b} {bound} mm/s.'
    if family=='recipient':
        return f'A measurement of {b} above {value} mm/s requires {a} to halt. Under that very trigger, notification must reach {c}. '
    if family=='authority':
        return f'{c} directs that {a} shall halt upon {b} rising above {value} mm/s.'
    if family=='unless':
        return f'{a} is allowed to carry on, except where {b} registers above {amount} mm/s.'
    if family=='nested':
        join='or' if contrast else 'and'
        return f'Halt {a} as a mandatory measure when {b} exceeds {value} mm/s {join} {c} measures under 2 m.'
    if family=='direction':
        source, target=(b,a) if contrast else (a,b)
        return f'{target} is a consequence of {source}.' if para else f'{source} is responsible for causing {target}.'
    if family=='temporal':
        order='after' if contrast else 'before'
        return f'{a} is required to inspect {b}, with that inspection taking place {order} {c} is permitted to proceed.'
    if family=='revision':
        return f'The instruction in {revision_old} obliges {a} to halt. That instruction is replaced by {revision_new}, under which {a} is allowed to carry on.'
    if family=='time':
        return f'{a} shall carry out an inspection of {b}; the specified date is {date}.'
    if family=='approval':
        return f'Permission for {a} to carry on has one exception: should {c} approve halting it, the permission does not apply.'
    if family in ('nested_boolean','negation_scope'):
        first=f'{b} is {"not " if contrast and family=="negation_scope" else ""}greater than {value} mm/s'
        join='or' if contrast and family=='nested_boolean' else 'and'
        return f'{a} is obliged to halt if {first} {join} either {c} measures less than 2 m or {d} measures more than 3 m.'
    if family=='conflict':
        second='is permitted to carry on' if contrast else 'is prohibited from halting'
        return f'One instruction obliges {a} to halt. A conflicting instruction says {a} {second}.'
    if family=='multi_quantity':
        first, second=(str(Decimal(value)+Decimal('2.3')),value) if contrast else (value,str(Decimal(value)+Decimal('2.3')))
        return f'{a} shall halt once {b} rises above {first} mm/s. A separate notification to {c} is mandatory once the same measurement rises above {second} mm/s.'
    if family=='unit_equivalence':
        unit='mm' if para else 'm'
        number=str(Decimal(value)*1000) if para else str(Decimal(value)+Decimal('2.3')) if contrast else value
        return f'{a} shall halt whenever {b} registers more than {number} {unit}.'
    return f'{a} is permitted to carry on so long as {b} stays below {value} mm/s. Should that measurement rise above {value} mm/s, {a} shall halt and a notification must be delivered to {c}. The permitted rate for {d} is no greater than {amount} L/min.'


def extra_row(split, family, index, variant):
    prefix={'train':['North','South','East','West','Upper','Lower','Central','Outer'],
            'dev':['Harbour','Ridge'], 'heldout':['Estuary','Plateau']}[split][index % (8 if split=='train' else 2)]
    value=(('-1','0','0.5','1','2','3','4','5') if split=='train' else
           ('-0.3','0','1.7','4.1','5.9','7.1') if split=='dev' else
           ('-0.7','0','2.9','6.7','8.1','9.3'))[index]
    works=f'{prefix} excavation'; monitor=f'{prefix} monitor'; crew=f'{prefix} crew'
    issuer=f'{prefix} engineer'; recipient=f'{prefix} superintendent'
    if family=='comparison_bounds':
        operators=('GT','LT','EQ','GE','LE','NE')
        op=operators[(index+(1 if variant==2 else 0))%6]
        words={'GT':('exceeds','is greater than'),'LT':('is below','is less than'),
               'EQ':('equals','is exactly'),'GE':('is at least','is no less than'),
               'LE':('is at most','is no more than'),'NE':('does not equal','is different from')}[op][variant==1]
        text=(f'{works} must stop if {monitor} {words} {value} mm/s.' if split=='train' else
              f'When {monitor} {words} {value} mm/s, stopping {works} is required.' if split=='dev' else
              f'The mandatory halt rule for {works} applies whenever {monitor} {words} {value} mm/s.')
        g=Builder(text); w=g.entity(works); m=g.entity(monitor)
        condition=g.predicate(m,value,'mm/s',op,text)
        g.event('stop',roles={'object':w},condition=condition)
    else:
        if variant==2:issuer,recipient=recipient,issuer
        if split=='train':
            text=f'{issuer} directs {crew} to stop {works} and notify {recipient} if {monitor} exceeds {value} mm/s.'
        elif split=='dev':
            text=f'By order of {issuer}, {crew} must stop {works} and notify {recipient} whenever {monitor} is above {value} mm/s.'
        else:
            text=f'Under an instruction issued by {issuer}, a reading of {monitor} greater than {value} mm/s requires {crew} to halt {works} and deliver notification to {recipient}.'
        if variant==1:text=text.replace('directs','instructs').replace('must stop','is required to stop').replace('deliver notification to','inform')
        g=Builder(text); w=g.entity(works); m=g.entity(monitor); a=g.entity(crew); auth=g.entity(issuer); dest=g.entity(recipient)
        condition=g.predicate(m,value,'mm/s','GT',text)
        g.event('stop',roles={'actor':a,'object':w,'authority':auth},condition=condition)
        g.event('notify',roles={'actor':a,'recipient':dest,'authority':auth},condition=condition)
    for entity in g.graph['entities']:entity['mentions']=span(text,entity['name'])
    validate_graph(g.graph,text)
    assert bind(to_wire(g.graph,text),text)==g.graph
    return {'id':f'v3-{split}-{family}-{index}-{variant}','group':f'v3-{split}-{family}-{index}',
            'family':family,'variant':('canonical','paraphrase','contrast')[variant], 'source':text,'graph':g.graph}


def make_row(split, family, index, variant):
    if family in ("comparison_bounds", "notification_roles"):
        return extra_row(split,family,index,variant)
    old=case(split,family,index,variant)
    old_prefix={'train':'Aster','dev':'Birch','heldout':'Cobalt'}[split]
    prefix={'train':['North','South','East','West','Upper','Lower','Central','Outer'][index%8],
            'dev':['Harbour','Ridge'][index%2], 'heldout':['Estuary','Plateau'][index%2]}[split]
    a,b,c,d=f'{prefix} excavation',f'{prefix} vibration',f'{prefix} superintendent',f'{prefix} discharge'
    if family in ('nested','nested_boolean','negation_scope'):
        c=f'{prefix} water level'; d=f'{prefix} settlement'
    if family in ('time','temporal'):
        a=f'{prefix} inspection crew'; b=f'{prefix} pump'; c=f'{prefix} dewatering'
    if family=='direction':
        a=f'{prefix} dewatering'; b=f'{prefix} settlement'
    old_value=((100,300,500,700,900,1100,1300,1500) if split=='train' else (127,347) if split=='dev' else (193,419))[index]
    value=(('0.5','1','2','3','4','5','6','7') if split=='train' else ('1.7','4.1') if split=='dev' else ('2.9','6.7'))[index]
    extra=str(Decimal(value)+Decimal('2.3'))
    changes=[(f'{old_prefix} works {index}',a),(f'{old_prefix} monitor {index}',b),
             (f'{old_prefix} officer {index}',c),(f'{old_prefix} gauge {index}',d),
             (f'{old_prefix} discharge {index}',d),(old_prefix,prefix),
             (str(old_value*1000),str(Decimal(value)*1000)),(str(old_value+17),extra),(str(old_value),value)]
    def replace(s):
        for source,target in changes: s=s.replace(source,target)
        return s
    def transform(v):
        if isinstance(v,str):return replace(v)
        if isinstance(v,list):return [transform(x) for x in v]
        if isinstance(v,dict):return {k:transform(x) for k,x in v.items()}
        return v
    graph=transform(deepcopy(old['graph']))
    text=replace(old['source'])
    if split=='train':
        # Diversify wording within training, without taking v1 held-out sentences.
        alternatives=[('must stop','shall halt'),('is required to stop','is obliged to halt'),
                      ('must be notified','must receive notification'),('may continue','is allowed to continue')]
        if index%2:
            for source,target in alternatives:text=text.replace(source,target)
    if split=='heldout':
        person=c+(' alternate' if variant==2 and family in ('recipient','authority','approval') else '')
        old_revision=graph['events'][0]['revision']['value'] if family=='revision' else ''
        new_revision=graph['events'][1]['revision']['value'] if family=='revision' else ''
        date=graph['events'][0]['time']['value'] if family=='time' else ''
        text=fresh_text(family,a,b,person,d,value,variant==2,variant==1,old_revision,new_revision,date).strip()
        if variant==1 and family not in ('direction','quantity','comparator','polarity','unit_equivalence'):
            text='Work instruction: '+text
    # Rebind authored meanings to this authored source; this is dataset construction,
    # never runtime interpretation or model-generated supervision.
    for row in graph['entities']:
        row['mentions']=span(text,row['name'])
    sentences=re.split(r'(?<=\.)\s+',text)
    for table in ('predicates','conditions','events','links'):
        for n,row in enumerate(graph[table]):
            quote=text
            if table=='events' and len(sentences)>1:
                if family=='paragraph':quote=sentences[[0,1,1,2][n]]
                elif family in ('recipient','revision','conflict','multi_quantity'):quote=sentences[min(n,len(sentences)-1)]
            if table=='predicates' and family=='paragraph' and len(sentences)>2:
                quote=sentences[n]
            row['evidence']=span(text,quote)
            if table=='events':
                for key in ('time','revision'):
                    if row[key] is not None:row[key]['evidence']=span(text,row[key]['value'])
    graph=normalize_graph(graph)
    validate_graph(graph,text)
    assert bind(to_wire(graph,text),text)==graph
    return {**old,'id':f'v3-{old["id"]}','group':f'v3-{old["group"]}','source':text,'graph':graph}


def build():
    (HERE/'data').mkdir(exist_ok=True);(HERE/'training').mkdir(exist_ok=True)
    for split,size in (('train',8),('dev',2),('heldout',2)):
        rows=[make_row(split,f,i,v) for f in FAMILIES for i in range(6 if f=="comparison_bounds" and split!="train" else size) for v in range(3)]
        (HERE/'data'/f'{split}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        if split!='heldout':
            name='train' if split=='train' else 'valid'
            chats=[{'messages':[{'role':'user','content':prompt(r['source'])},{'role':'assistant','content':json.dumps(to_wire(r['graph'],r['source']),separators=(',',':'))}]} for r in rows]
            (HERE/'training'/f'{name}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in chats))

if __name__=='__main__':build()
