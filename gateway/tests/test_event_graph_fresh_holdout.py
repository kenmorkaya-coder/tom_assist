from collections import defaultdict
from copy import deepcopy
import json
from pathlib import Path
import pytest
from validation.event_graph_v6.build_corpus import make_row,FAMILIES
from validation.event_graph_v6.experiment import read_rows,score_extraction
from gateway.event_graph_extractor_v3 import bind,to_wire
from gateway.typed_event_graph import semantic_graph,validate_graph
from gateway.tests.test_event_graph_v1 import THRESHOLDS


@pytest.mark.parametrize('family',FAMILIES)
def test_authored_contrasts_and_wire_roundtrip(family):
    for i in range(6 if family=='comparison_bounds' else 2):
        rows=[make_row(family,i,v) for v in range(3)]
        meanings=[]
        for row in rows:
            validate_graph(row['graph'],row['source'])
            assert bind(to_wire(row['graph'],row['source']),row['source'])==row['graph']
            meanings.append(semantic_graph(row['graph']))
        assert meanings[0]==meanings[1] and meanings[0]!=meanings[2]


def test_inventory_is_unique_and_disjoint_from_all_prior_sources():
    rows=read_rows('heldout');sources={r['source'] for r in rows}
    assert len(rows)==len(sources)==132
    assert len({r['group'] for r in rows})==44
    root=Path(__file__).resolve().parents[2]
    for v in ('v1','v3'):
        for split in ('train','dev','heldout'):
            old={json.loads(x)['source'] for x in (root/f'validation/event_graph_{v}/data/{split}.jsonl').read_text().splitlines()}
            assert not sources & old


def test_notification_roles_and_source_event_order_are_distinct():
    row=make_row('notification_roles',0,0)
    stop,notify=row['graph']['events']
    assert len({notify['roles'][k] for k in ('actor','authority','recipient')})==3
    assert stop['roles']['authority']==notify['roles']['authority']
    assert stop['condition']==notify['condition']
    assert stop['roles']['recipient'] is None
    row=make_row('paragraph',0,0)
    assert [e['action'] for e in row['graph']['events']]==['continue','stop','notify','discharge']


def test_order_error_cannot_pass_the_frozen_scorer():
    rows=[make_row('paragraph',0,v) for v in range(3)]
    ps=[{'id':r['id'],'graph':deepcopy(r['graph'])} for r in rows]
    ps[0]['graph']['events'][2:4]=ps[0]['graph']['events'][2:4][::-1]
    result=score_extraction(rows,ps,THRESHOLDS)
    assert result['valid']==3 and result['exact']==2 and result['verdict']=='RED'


def test_dataset_has_no_training_or_development_entrypoint():
    with pytest.raises(ValueError):read_rows('train')
    with pytest.raises(ValueError):read_rows('dev')
