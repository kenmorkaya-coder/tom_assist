from validation.event_graph_v7 import session
from gateway.tests.test_event_graph_continuation import report


def test_lower_rate_starts_from_best_not_final_previous_weights():
    assert session.PARENT.name == 'epoch-1'
    assert session.SESSION.name == 'event-graph-lora-v5-session-001'
    assert session.PLAN['baseline_steps'] == 992
    assert session.PLAN['learning_rate'] == 0.00002
    assert session.PLAN['steps_per_epoch'] == 480
    assert session.PLAN['epochs'] == 2


def test_best_baseline_survives_two_regressions():
    records=[report(0,127,130),report(1,125,129),report(2,124,128)]
    for r in records:r['cumulative_steps']=992+480*r['epoch']
    selected=session.comparison(records)
    assert selected['selected_cumulative_steps']==992
    assert selected['exact_gain_records']==0
    assert selected['fresh_heldout']=='NOT_RUN'


def test_mid_session_peak_beats_last_weights():
    records=[report(0,127,130),report(1,130,132),report(2,128,131)]
    for r in records:r['cumulative_steps']=992+480*r['epoch']
    selected=session.comparison(records)
    assert selected['selected_epoch']==1
    assert selected['selected_cumulative_steps']==1472
    assert selected['exact_gain_records']==3
