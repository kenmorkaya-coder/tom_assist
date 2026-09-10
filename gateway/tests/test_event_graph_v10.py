import json
from collections import Counter
from gateway.event_graph_span_extractor import parse_output
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v10 import session as s
from validation.event_graph_v8 import session as original


def test_augmentation_keeps_old_examples_and_dev_unchanged():
    rows=s.read_rows('train');assert len(rows)==1200
    assert rows[:960]==original.read_rows('train')
    assert (s.HERE/'training/valid.jsonl').read_bytes()==(original.HERE/'training/valid.jsonl').read_bytes()
    assert len({r['source'] for r in rows})==1200
    extra=rows[960:]
    assert Counter(r['family'] for r in extra)==dict.fromkeys(('unless','direction','paragraph','approval','multi_quantity'),48)
    forbidden={r['source'] for r in s.read_rows('dev')}
    for split in ('train','dev','heldout'):forbidden.update(r['source'] for r in s.prior.read_rows(split))
    assert not forbidden & {r['source'] for r in extra}


def test_all_training_answers_roundtrip_and_new_groups_preserve_contrasts():
    rows=s.read_rows('train');answers=[json.loads(x)['messages'][-1]['content'] for x in (s.HERE/'training/train.jsonl').read_text().splitlines()]
    assert len(rows)==len(answers)
    for r,a in zip(rows,answers):assert semantic_graph(parse_output(a,r['source']))==semantic_graph(r['graph'])
    for i in range(960,1200,3):
        a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]];assert a==b and a!=c


def test_explicit_roles_and_reference_binding_in_new_labels():
    for r in s.read_rows('train')[960:]:
        g=semantic_graph(r['graph']);events=g['events']
        assert all(e['roles']['authority'] is None for e in events)
        assert all(not n['name'].startswith(('Continuation','Above','Stopping')) for n in r['graph']['entities'])
        if r['family']=='paragraph':
            assert events[1]['condition']==events[2]['condition']
            assert events[0]['condition']['subject']==events[1]['condition']['subject']
            assert events[3]['condition']['subject']==events[3]['roles']['object']
            assert events[0]['roles']['object']==events[1]['roles']['object']
        if r['family']=='multi_quantity':assert events[0]['condition']['subject']==events[1]['condition']['subject']
        if r['family']=='unless':
            contrast=r['variant']=='contrast'
            assert (events[0]['condition'] is not None)==contrast
            assert (events[0]['exception'] is not None)!=contrast


def test_full_pass_and_baseline_selection():
    assert s.PLAN['steps_per_epoch']==1200 and s.PLAN['baseline_steps']==1440
    assert s.PLAN['learning_rate']==0.00001
    b=dict(epoch=0,cumulative_steps=1440,total=132,exact=123,valid=132,invented_authority=0,paraphrase_equal=43,contrast_distinct=44,parser_errors={})
    n={**b,'epoch':1,'cumulative_steps':2640,'exact':122}
    assert s.comparison([b,n])['selected_epoch']==0
