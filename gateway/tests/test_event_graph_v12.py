import json
from collections import Counter
from gateway.typed_event_graph import semantic_graph
from gateway.event_graph_span_wire import to_wire
from gateway.event_graph_span_extractor import parse_output
from validation.event_graph_v12 import experiment as e


def test_inventory_group_contrasts_and_no_previous_source_overlap():
    rows=e.read_rows('heldout');sources={r['source'] for r in rows}
    assert len(rows)==len(sources)==132
    assert len({r['group'] for r in rows})==44
    assert len(Counter(r['family'] for r in rows))==20
    for directory in e.ROOT.glob('validation/event_graph_v*'):
        if directory==e.HERE:continue
        for p in list(directory.glob('data/*.jsonl'))+list(directory.glob('heldout.jsonl')):
            assert not sources & {json.loads(x)['source'] for x in p.read_text().splitlines()}
    for i in range(0,len(rows),3):
        a,b,c=[semantic_graph(r['graph']) for r in rows[i:i+3]];assert a==b and a!=c


def test_all_gold_roundtrips_and_roles_stay_separate():
    for r in e.read_rows('heldout'):
        graph=parse_output(json.dumps(to_wire(r['graph'],r['source'])),r['source'])
        assert semantic_graph(graph)==semantic_graph(r['graph'])
        if r['family']=='recipient':
            assert all(x['roles']['authority'] is None for x in graph['events'])
        if r['family']=='notification_roles':
            roles=graph['events'][1]['roles']
            assert len({roles['actor'],roles['authority'],roles['recipient']})==3
        if r['family']=='paragraph':
            es=graph['events'];assert len(es)==4 and es[1]['condition']==es[2]['condition']
