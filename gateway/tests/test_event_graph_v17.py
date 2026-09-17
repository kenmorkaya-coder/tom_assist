from gateway.typed_event_graph import semantic_graph
from gateway.event_graph_span_extractor import parse_output
from gateway.event_graph_span_wire import to_wire
from validation.event_graph_v17.diagnostic import rows, score
import json


def test_diagnostic_roles_roundtrip_and_contrasts():
    corpus = rows()
    assert len(corpus) == 72 and len({r['source'] for r in corpus}) == 72
    for row in corpus:
        graph = parse_output(json.dumps(to_wire(row['graph'], row['source'])), row['source'])
        assert semantic_graph(graph) == semantic_graph(row['graph'])
        for entity in graph['entities']:
            assert all(m['quote'] == entity['name'] for m in entity['mentions'])
    for i in range(0, 72, 3):
        a, b, c = [semantic_graph(r['graph']) for r in corpus[i:i+3]]
        assert a == b and a != c
        assert a['events'][0]['roles']['source'] == c['events'][0]['roles']['target']
        assert a['events'][0]['roles']['target'] == c['events'][0]['roles']['source']


def test_diagnostic_scores_reversal_and_invalid_output():
    corpus = rows(); predictions = [{'id': r['id'], 'graph': r['graph']} for r in corpus]
    good = score(corpus, predictions)
    assert good['exact'] == good['valid'] == 72
    assert good['paraphrase_equal'] == good['contrast_distinct'] == 24
    predictions[2] = {'id': corpus[2]['id'], 'graph': corpus[0]['graph']}
    predictions[3] = {'id': corpus[3]['id'], 'error': 'invalid'}
    bad = score(corpus, predictions)
    assert bad['exact'] == 70 and bad['valid'] == 71
    assert bad['contrast_distinct'] == 22
