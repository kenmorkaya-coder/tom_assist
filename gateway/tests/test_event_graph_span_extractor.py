import json
from collections import Counter
import pytest
from gateway.event_graph_span_extractor import parse_output, prompt
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v8 import session


@pytest.mark.parametrize('split,training,count',[('train','train',960),('dev','valid',132)])
def test_new_corpus_roundtrip_and_group_meaning(split,training,count):
    rows=session.read_rows(split)
    messages=[json.loads(x)['messages'] for x in (session.HERE/'training'/f'{training}.jsonl').read_text().splitlines()]
    assert len(rows)==len(messages)==count
    assert len({r['source'] for r in rows})==count
    for row,pair in zip(rows,messages):
        assert pair[0]['content']==prompt(row['source'])
        parsed=parse_output(pair[1]['content'],row['source'])
        assert semantic_graph(parsed)==semantic_graph(row['graph'])
    for i in range(0,len(rows),3):
        a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]]
        assert a==b and a!=c


def test_split_separation_and_explicit_participant_coverage():
    train=session.read_rows('train');dev=session.read_rows('dev')
    sources={r['source'] for r in train}
    assert not sources & {r['source'] for r in dev}
    assert sum(len(r['graph']['entities'])>=5 for r in train)>=240
    for split in ('train','dev','heldout'):
        assert not sources & {r['source'] for r in session.prior.read_rows(split)}
    assert len(Counter(r['family'] for r in train))==20


def test_selection_retains_earlier_checkpoint_on_tie_and_rejects_regression():
    first=dict(epoch=1,cumulative_steps=960,total=132,exact=100,valid=120,invented_authority=0,
               paraphrase_equal=30,contrast_distinct=40,parser_errors={})
    second={**first,'epoch':2,'cumulative_steps':1920}
    assert session.comparison([first,second])['selected_epoch']==1
    second['exact']=99
    assert session.comparison([first,second])['selected_epoch']==1
    second['exact']=101
    result=session.comparison([first,second])
    assert result['selected_epoch']==2 and result['exact_gain_records']==1
    assert result['fresh_heldout']=='NOT_RUN'
