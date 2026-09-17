from validation.event_graph_v19 import session as s
from gateway.typed_event_graph import semantic_graph


def test_only_eight_effect_first_examples_change():
    a=s.training_rows('control');b=s.training_rows('coverage');changed=0
    for x,y in zip(a,b):
        assert x['id']==y['id']
        if x==y:continue
        changed+=1
        assert x['variant']=='paraphrase' and x['family']=='direction'
        before=semantic_graph(x['graph'])['events'][0]['roles'];after=semantic_graph(y['graph'])['events'][0]['roles']
        assert before['source']==after['target'] and before['target']==after['source']
        for row,roles in ((x,before),(y,after)):
            assert row['source']==f"The cause of {roles['target']} is {roles['source']}."
    assert changed==8 and len(a)==len(b)==96


def test_labels_roundtrip_and_evaluation_separation():
    seen={r['source'] for r in s.evaluation_rows()}
    for arm in ('control','coverage'):
        for r in s.training_rows(arm):
            assert r['source'] not in seen
            assert semantic_graph(s.old.parse_output(s.messages(r)[-1]['content'],r['source']))==semantic_graph(r['graph'])
    rows=s.evaluation_rows();assert len(rows)==248
    assert len({r['source'] for r in rows[192:]})==56
    result=s.score(rows,s.baseline_predictions(),s.old.verify(s.V16)['thresholds'])
    assert result['development']['exact']==191 and result['diagnostic']['exact']==47
