from validation.event_graph_v14 import session as s


def test_unchanged_inventory_and_bounded_plan():
    assert s.read_rows('train')==s.parent.read_rows('train')
    assert s.read_rows('dev')==s.parent.read_rows('dev')
    assert len(s.read_rows('train'))==1440 and len(s.read_rows('dev'))==156
    assert s.PLAN['steps_per_epoch']==360 and s.PLAN['baseline_steps']==4020
    assert s.PLAN['learning_rate']==0.000005 and s.PLAN['epochs']==1


def test_selection_protects_original_and_validity_breaks_exact_tie():
    b=dict(epoch=0,exact=154,valid=155,invented_authority=0,paraphrase_equal=50,contrast_distinct=52,original_132={'exact':132})
    n={**b,'epoch':1,'valid':156}
    assert s.selection_key(n)>s.selection_key(b)
    n['original_132']={'exact':131}
    assert s.selection_key(b)>s.selection_key(n)
