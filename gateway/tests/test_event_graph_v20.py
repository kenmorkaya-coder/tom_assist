from validation.event_graph_v20 import session as s
from gateway.typed_event_graph import semantic_graph


def test_only_two_revision_slots_change():
    before=s.previous.training_rows('control');after=s.training_rows('revision_replay')
    changed=[]
    for a,b in zip(before,after):
        assert a['id']==b['id']
        if a==b:continue
        changed.append(b)
        assert a['family']==b['family']=='revision'
    assert len(before)==len(after)==96 and len(changed)==2
    assert [r['source_row_id'] for r in changed]==['v13-train-revision-0-0','v13-train-revision-0-1']
    originals={r['id']:r for r in s.old.read_rows('train')}
    for r in changed:
        original=originals[r['source_row_id']]
        assert r['source']==original['source'] and r['graph']==original['graph']


def test_labels_and_evaluation_unchanged():
    assert s.evaluation_rows()==s.previous.evaluation_rows()
    sources={r['source'] for r in s.evaluation_rows()}
    for row in s.training_rows('revision_replay'):
        assert row['source'] not in sources
        assert semantic_graph(s.old.parse_output(s.messages(row)[-1]['content'],row['source']))==semantic_graph(row['graph'])
    assert (s.PLAN['updates_per_arm'],s.PLAN['seed'],s.PLAN['learning_rate'],s.PLAN['baseline_steps'])==(96,151,0.000005,4380)
