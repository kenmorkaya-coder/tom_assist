import json
from gateway.typed_event_graph import semantic_graph
from gateway.event_graph_span_extractor import parse_output
from gateway.event_graph_span_wire import to_wire
from validation.event_graph_v18 import diagnostic as d


def test_original_failures_are_exact_anchors():
    rows = d.rows()
    actual = [r['source'] for r in rows if r['family'] == 'anchor' and r['variant'] == 'canonical']
    old = json.loads((d.ROOT / 'validation/runs/event-graph-lora-v16-session-001/TRANSITIONS.json').read_text())
    shared = json.loads((d.ROOT / 'validation/runs/event-graph-lora-v17-diagnostic-001/RESULT.json').read_text())
    assert actual == [r['source'] for r in old if r['transition'] == 'regressed'] + [shared['details'][0]['source']]


def test_labels_roundtrip_and_role_reversal():
    rows = d.rows()
    assert len(rows) == 60 and len({r['id'] for r in rows}) == 60
    for row in rows:
        parsed = parse_output(json.dumps(to_wire(row['graph'], row['source'])), row['source'])
        assert semantic_graph(parsed) == semantic_graph(row['graph'])
        assert all(m['quote'] == ent['name'] for ent in parsed['entities'] for m in ent['mentions'])
    for i in range(0, len(rows), 3):
        a, b, c = [semantic_graph(r['graph']) for r in rows[i:i+3]]
        assert a == b and a != c
        assert a['events'][0]['roles']['source'] == c['events'][0]['roles']['target']
        assert a['events'][0]['roles']['target'] == c['events'][0]['roles']['source']


def test_interventions_preserve_declared_names():
    rows = d.rows()
    for i in range(4):
        group = {r['family']: r for r in rows if r['anchor_index'] == i and r['variant'] == 'canonical'}
        roles = {k: semantic_graph(r['graph'])['events'][0]['roles'] for k, r in group.items()}
        assert roles['anchor'] == roles['wording']
        assert roles['anchor']['source'] == roles['distinct_prefixes']['source']
        assert roles['anchor']['target'] != roles['distinct_prefixes']['target']
        assert roles['anchor']['source'] != roles['rename_site']['source']
        assert roles['anchor']['target'] != roles['rename_site']['target']
    report = d.score(rows, [{'id': r['id'], 'graph': r['graph']} for r in rows])
    assert report['exact'] == 60 and report['contrast_distinct'] == 20
