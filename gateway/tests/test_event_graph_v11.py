import json
from gateway.event_graph_span_extractor import parse_output
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v11 import session as s


def test_preserve_training_and_development_and_check_new_meanings():
    rows=s.read_rows('train');assert len(rows)==1320
    assert rows[:1200]==s.parent.read_rows('train')
    assert (s.HERE/'training/valid.jsonl').read_bytes()==(s.parent.HERE/'training/valid.jsonl').read_bytes()
    assert len({r['source'] for r in rows})==1320
    assert not {r['source'] for r in rows}&{r['source'] for r in s.read_rows('dev')}
    for i in range(1200,1320,3):
        a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]];assert a==b and a!=c
    for r in rows[1200:]:
        for e in r['graph']['entities']:
            assert not e['name'].startswith(('Continuation','Construction','Operational'))
            assert all(m['quote']==e['name'] for m in e['mentions'])


def test_all_answers_roundtrip_with_shifted_framing():
    rows=s.read_rows('train');answers=[json.loads(x)['messages'][-1]['content'] for x in (s.HERE/'training/train.jsonl').read_text().splitlines()]
    assert len(rows)==len(answers)
    for r,a in zip(rows,answers):assert semantic_graph(parse_output(a,r['source']))==semantic_graph(r['graph'])


def test_bounded_steps_and_baseline_retention():
    assert s.PLAN['baseline_steps']==2640 and s.PLAN['steps_per_epoch']==660
    b=dict(epoch=0,cumulative_steps=2640,total=132,exact=130,valid=132,invented_authority=0,paraphrase_equal=42,contrast_distinct=44,parser_errors={})
    n={**b,'epoch':1,'cumulative_steps':3300,'exact':129}
    assert s.comparison([b,n])['selected_epoch']==0
