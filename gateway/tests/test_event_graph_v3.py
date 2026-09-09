from copy import deepcopy
import json
import pytest
from gateway.event_graph_extractor_v3 import bind, parse_output, to_wire
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v3.build_corpus import make_row, FAMILIES

@pytest.mark.parametrize('family',FAMILIES)
def test_fresh_contrast_meanings_and_binding(family):
    rows=[make_row('heldout',family,0,v) for v in range(3)]
    for row in rows:
        assert bind(to_wire(row['graph'],row['source']),row['source'])==row['graph']
    assert semantic_graph(rows[0]['graph'])==semantic_graph(rows[1]['graph'])
    assert semantic_graph(rows[0]['graph'])!=semantic_graph(rows[2]['graph'])


def test_explicit_occurrence_selects_repeated_mention():
    row=make_row('train','paragraph',0,0)
    candidate=to_wire(row['graph'],row['source'])
    mention=candidate['entities'][0]['mentions'][0]
    assert row['source'].count(mention['quote'])>1
    mention['occurrence']=1
    selected=bind(candidate,row['source'])['entities'][0]['mentions'][0]
    assert selected['start']>row['graph']['entities'][0]['mentions'][0]['start']
    mention['occurrence']=999
    with pytest.raises(ValueError,match='absent'):bind(candidate,row['source'])


@pytest.mark.parametrize('bad',(-1,True,'0',0.5,None))
def test_occurrence_is_not_guessed_or_coerced(bad):
    row=make_row('train','quantity',0,0);wire=to_wire(row['graph'],row['source'])
    wire['entities'][0]['mentions'][0]['occurrence']=bad
    with pytest.raises(ValueError):bind(wire,row['source'])


def test_single_boolean_wrapper_normalizes_without_role_repair():
    row=make_row('train','recipient',0,0);g=deepcopy(row['graph'])
    p=g['events'][0]['condition']
    g['conditions']=[{'id':'wrapper','operator':'all','args':[p],'evidence':g['events'][0]['evidence']}]
    for e in g['events']:e['condition']='wrapper'
    result=bind(to_wire(g,row['source']),row['source'])
    assert semantic_graph(result)==semantic_graph(row['graph'])
    result['events'][1]['roles']['target']=result['events'][1]['roles']['recipient']
    assert semantic_graph(result)!=semantic_graph(row['graph'])


def test_fences_allowed_but_incomplete_json_not_repaired():
    row=make_row('train','time',0,0);raw=json.dumps(to_wire(row['graph'],row['source']))
    assert parse_output('```json\n'+raw+'\n```',row['source'])==row['graph']
    with pytest.raises(ValueError):parse_output(raw[:-1],row['source'])


def test_role_triple_and_all_comparator_operators_are_supervised():
    operators=set()
    for i in range(6):
        row=make_row('heldout','comparison_bounds',i,0)
        operators.add(row['graph']['predicates'][0]['comparator'])
    assert operators=={'GT','LT','EQ','GE','LE','NE'}
    row=make_row('train','notification_roles',0,0)
    roles=row['graph']['events'][1]['roles']
    assert len({roles[k] for k in ('actor','authority','recipient')})==3
    assert roles['target'] is None and roles['object'] is None


def test_numeric_negation_normalizes_but_action_negation_does_not_move():
    row=make_row('train','negation_scope',0,2)
    wire=to_wire(row['graph'],row['source'])
    assert wire['predicates'][0]['comparator']=='LE'
    wire['predicates'][0]['comparator']='GT';wire['predicates'][0]['negated']=True
    wire['events'][0]['negated']=True
    normalized=bind(wire,row['source'])
    assert normalized['predicates'][0]['comparator']=='LE'
    assert normalized['predicates'][0]['negated'] is False
    assert normalized['events'][0]['negated'] is True
    assert normalized['events'][0]['condition']==row['graph']['events'][0]['condition']
