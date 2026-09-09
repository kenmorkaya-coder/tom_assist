from copy import deepcopy
import pytest
from validation.event_graph_v5.session import comparison, development_score, stage
from validation.event_graph_v1.build_corpus import case
from gateway.tests.test_event_graph_v1 import THRESHOLDS


def report(epoch, exact, valid=132):
    return dict(epoch=epoch, cumulative_steps=512+480*epoch, total=132,
                exact=exact, valid=valid, invented_authority=0,
                paraphrase_equal=40, contrast_distinct=40, parser_errors={})


def test_regression_does_not_replace_better_baseline():
    r = comparison([report(0, 120), report(1, 119), report(2, 118)])
    assert r['selected_epoch'] == 0 and r['exact_gain_records'] == 0
    assert r['fresh_heldout'] == 'NOT_RUN'


def test_peak_is_retained_even_when_last_epoch_regresses():
    r = comparison([report(0, 120), report(1, 125), report(2, 123)])
    assert r['selected_epoch'] == 1 and r['exact_gain_records'] == 5


def test_equal_scores_prefer_earliest_not_longest_training():
    assert comparison([report(0, 120), report(1, 120)])['selected_epoch'] == 0
    assert comparison([report(0, 120, 130), report(1, 120, 132)])['selected_epoch'] == 1


def test_development_success_cannot_be_mistaken_for_heldout_verdict():
    rows = [case('train', 'quantity', 0, v) for v in range(3)]
    ps = [{'id': r['id'], 'graph': deepcopy(r['graph'])} for r in rows]
    result = development_score(rows, ps, THRESHOLDS)
    assert 'verdict' not in result
    assert result['development_thresholds_met']
    ps[0] = {'id': rows[0]['id'], 'error': 'quote occurrence absent'}
    result = development_score(rows, ps, THRESHOLDS)
    assert result['total'] == 3 and result['valid'] == 2
    assert result['parser_errors'] == {'quote occurrence absent': 1}
    assert not result['development_thresholds_met']


def test_stage_inventory_is_bounded(tmp_path):
    with pytest.raises(ValueError): stage(tmp_path, 3)
