import copy
from validation.event_graph_v21 import session as s
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v9.audit import differences


def test_only_four_event_evidence_fields_change():
    before=s.previous.training_rows('revision_replay');after=s.training_rows('event_evidence')
    changed=[]
    for a,b in zip(before,after):
        assert semantic_graph(a['graph'])==semantic_graph(b['graph'])
        if a==b:continue
        changed.append(b['source_row_id'])
        restored=copy.deepcopy(b)
        for i in range(2):
            assert b['graph']['events'][i]['evidence']!=a['graph']['events'][i]['evidence']
            restored['graph']['events'][i]['evidence']=a['graph']['events'][i]['evidence']
        assert restored==a
        diffs=differences(s.to_wire(a['graph'],a['source']),s.to_wire(b['graph'],b['source']))
        assert all(d['path'].startswith(('.events[0].evidence[0].','.events[1].evidence[0].')) for d in diffs)
    assert len(before)==len(after)==96 and changed==list(s.EVIDENCE)


def test_evidence_text_and_cross_sentence_antecedent():
    rows={r['source_row_id']:r for r in s.training_rows('event_evidence') if 'source_row_id' in r}
    a=rows['v13-train-revision-0-0'];b=rows['v13-train-revision-0-1']
    assert a['graph']['events'][0]['evidence'][0]['quote']=='Revision PLAN-t-00-R2 says Slate Pier T00 foundation works must stop.'
    assert a['graph']['events'][1]['evidence'][0]['quote']=='Revision PLAN-t-00-R4 replaces PLAN-t-00-R2 and says Slate Pier T00 foundation works may continue.'
    assert b['graph']['events'][0]['evidence'][0]['quote']=='PLAN-t-00-R2 requires stopping Slate Pier T00 foundation works.'
    assert b['graph']['events'][1]['evidence'][0]['quote']=='Slate Pier T00 foundation works. The replacement PLAN-t-00-R4 permits its continuation and supersedes PLAN-t-00-R2.'
    for r in s.training_rows('event_evidence'):
        assert semantic_graph(s.old.parse_output(s.messages(r)[-1]['content'],r['source']))==semantic_graph(r['graph'])
    assert s.evaluation_rows()==s.previous.evaluation_rows()
