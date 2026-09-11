import json
from gateway.event_graph_span_extractor import parse_output
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v16 import session as s


def test_preserved_inventory_and_new_source_separation():
    train=s.read_rows('train');dev=s.read_rows('dev')
    assert len(train)==1584 and len(dev)==192
    assert train[:1440]==s.parent.read_rows('train') and dev[:156]==s.parent.read_rows('dev')
    assert not {r['source'] for r in train}&{r['source'] for r in dev}
    prior=set()
    for directory in s.ROOT.glob('validation/event_graph_v*'):
        if directory==s.HERE:continue
        for p in list(directory.glob('data/*.jsonl'))+list(directory.glob('heldout.jsonl')):
            prior.update(json.loads(x)['source'] for x in p.read_text().splitlines())
    assert not prior & {r['source'] for r in train[1440:]+dev[156:]}


def test_semantic_roundtrips_and_negation_scope():
    for split,name,offset in [('train','train',1440),('dev','valid',156)]:
        rows=s.read_rows(split);answers=[json.loads(x)['messages'][-1]['content'] for x in (s.HERE/'training'/f'{name}.jsonl').read_text().splitlines()]
        assert len(rows)==len(answers)
        for r,a in zip(rows,answers):assert semantic_graph(parse_output(a,r['source']))==semantic_graph(r['graph'])
        for i in range(offset,len(rows),3):
            a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]];assert a==b and a!=c
        for r in rows[offset:]:
            g=r['graph'];es=g['events']
            if r['family']=='polarity':
                assert es[0]['negated']==(r['variant']=='contrast')
                assert es[0]['condition'] and es[0]['exception'] is None
            for ent in g['entities']:
                assert all(m['quote']==ent['name'] for m in ent['mentions'])
                assert not ent['name'].endswith(('measuring','measures','reports','records'))
            if r['family']=='paragraph':assert len(es)==4 and es[1]['condition']==es[2]['condition']


def test_selection_retains_prior_development_performance():
    b=dict(epoch=0,exact=175,valid=192,invented_authority=0,paraphrase_equal=60,contrast_distinct=64,original_132={'exact':132},extension_24={'exact':23})
    n={**b,'epoch':1,'exact':188,'extension_24':{'exact':22}}
    assert s.selection_key(b)>s.selection_key(n)
    n['extension_24']={'exact':23}
    assert s.selection_key(n)>s.selection_key(b)
