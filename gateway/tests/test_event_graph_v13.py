import json
from gateway.event_graph_span_extractor import parse_output
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v13 import session as s


def test_separate_inventories_and_preserved_old_rows():
    train=s.read_rows('train');dev=s.read_rows('dev')
    assert len(train)==1440 and len(dev)==156
    assert train[:1320]==s.parent.read_rows('train')
    assert dev[:132]==s.parent.read_rows('dev')
    assert not {r['source'] for r in train}&{r['source'] for r in dev}
    old=set()
    for directory in s.ROOT.glob('validation/event_graph_v*'):
        if directory==s.HERE:continue
        for p in list(directory.glob('data/*.jsonl'))+list(directory.glob('heldout.jsonl')):
            old.update(json.loads(x)['source'] for x in p.read_text().splitlines())
    assert not old & {r['source'] for r in train[1320:]+dev[132:]}


def test_roundtrip_and_completeness_in_new_labels():
    for split,name,offset in [('train','train',1320),('dev','valid',132)]:
        rows=s.read_rows(split);answers=[json.loads(x)['messages'][-1]['content'] for x in (s.HERE/'training'/f'{name}.jsonl').read_text().splitlines()]
        assert len(rows)==len(answers)
        for r,a in zip(rows,answers):assert semantic_graph(parse_output(a,r['source']))==semantic_graph(r['graph'])
        for i in range(offset,len(rows),3):
            a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]];assert a==b and a!=c
        for r in rows[offset:]:
            g=r['graph'];es=g['events']
            if r['family']=='revision':
                assert [e['action'] for e in es]==['stop','continue']
                assert g['links'][0]['source']==es[1]['id'] and g['links'][0]['target']==es[0]['id']
            else:
                assert [e['action'] for e in es]==['continue','stop','notify','discharge']
                assert es[1]['condition']==es[2]['condition']
                assert es[2]['roles']['recipient'] and es[2]['roles']['authority'] is None


def test_selection_protects_original_inventory():
    b=dict(epoch=0,exact=140,valid=156,invented_authority=0,paraphrase_equal=48,contrast_distinct=52,original_132={'exact':132})
    n={**b,'epoch':1,'exact':150,'original_132':{'exact':131}}
    assert s.selection_key(b)>s.selection_key(n)
