from copy import deepcopy
import json
from pathlib import Path
import pytest
from gateway.event_graph_span_wire import to_wire,bind,source_tokens,source_table
from gateway.typed_event_graph import semantic_graph

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('path',[
    'validation/event_graph_v3/data/train.jsonl',
    'validation/event_graph_v3/data/dev.jsonl',
    'validation/event_graph_v6/heldout.jsonl',
])
def test_authored_meaning_roundtrip_without_quote_or_name_generation(path):
    for line in (ROOT/path).read_text().splitlines():
        row=json.loads(line);wire=to_wire(row['graph'],row['source'])
        assert 'entities' not in wire
        assert semantic_graph(bind(wire,row['source']))==semantic_graph(row['graph'])


def sample():
    return next(json.loads(x) for x in (ROOT/'validation/event_graph_v6/heldout.jsonl').read_text().splitlines()
                if json.loads(x)['family']=='notification_roles')


@pytest.mark.parametrize('bad',[{'token_start':True,'token_end':2},
    {'token_start':0,'token_end':99999},{'token_start':2,'token_end':2},
    {'token_start':-1,'token_end':2},'n5'])
def test_invalid_role_span_is_not_repaired(bad):
    row=sample();wire=to_wire(row['graph'],row['source'])
    wire['events'][1]['roles']['recipient']=bad
    with pytest.raises(ValueError):bind(wire,row['source'])


def test_no_unreferenced_entity_declarations_or_dangling_condition_repair():
    row=sample();wire=to_wire(row['graph'],row['source'])
    extra=deepcopy(wire);extra['entities']=[]
    with pytest.raises(ValueError):bind(extra,row['source'])
    wire['events'][0]['condition']='absent_condition'
    with pytest.raises(ValueError,match='dangling'):bind(wire,row['source'])


def test_wrong_role_choice_stays_wrong_instead_of_being_inferred_from_prose():
    row=sample();wire=to_wire(row['graph'],row['source'])
    wire['events'][1]['roles']['recipient']=wire['events'][1]['roles']['authority']
    assert semantic_graph(bind(wire,row['source']))!=semantic_graph(row['graph'])


def test_source_indices_preserve_exact_punctuation_and_whitespace():
    text='Mica  12-1 crew\nnotifies deputy.'
    tokens=source_tokens(text)
    assert all(text[t['start']:t['end']]==t['text'] for t in tokens)
    assert source_table(text)==[{'index':t['index'],'text':t['text']} for t in tokens]
