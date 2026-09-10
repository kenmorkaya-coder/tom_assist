from validation.event_graph_v9 import session as s
from validation.event_graph_v9.audit import differences


def test_bounded_plan_keeps_data_and_scores_comparable():
    assert s.PLAN['learning_rate']==0.00001
    assert s.PLAN['steps_per_epoch']==480 and s.PLAN['epochs']==1
    assert s.PLAN['baseline_steps']==960 and s.PLAN['seeds']==[73]
    assert s.read_rows('train')==s.parent.read_rows('train')
    assert s.read_rows('dev')==s.parent.read_rows('dev')


def test_selection_retains_baseline_on_regression():
    base=dict(epoch=0,cumulative_steps=960,total=132,valid=130,exact=121,invented_authority=0,
              paraphrase_equal=41,contrast_distinct=43,parser_errors={})
    new={**base,'epoch':1,'cumulative_steps':1440,'valid':131,'exact':111}
    assert s.comparison([base,new])['selected_epoch']==0
    new['exact']=122
    assert s.comparison([base,new])['selected_epoch']==1


def test_recursive_diff_reports_meaning_leaf_and_missing_events():
    assert differences({'events':[{'negated':True}]},{'events':[{'negated':False}]})==[
        {'path':'.events[0].negated','expected':True,'actual':False}]
    assert differences({'events':[1]},{'events':[]})[0]['path']=='.events.length'
