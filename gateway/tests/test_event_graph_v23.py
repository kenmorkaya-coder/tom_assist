"""Keep V23 a controlled sampling experiment over untouched training labels."""
import copy
import json
from collections import Counter
import numpy as np
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v23 import session as s


def test_coverage_is_input_order_independent_and_complete_by_stratum():
    all_rows = s.control.old.read_rows("train")
    before = copy.deepcopy(all_rows)
    selected = s.selection(all_rows)
    assert all_rows == before
    assert selected == s.selection(list(reversed(all_rows)))
    by_id = {row["id"]: row for row in all_rows}
    assert len(selected) == len({row["id"] for row in selected}) == 96
    assert len({s.group_id(row) for row in selected}) == 32
    expected_strata = {(row["family"], row["id"].split("-")[0]) for row in all_rows}
    observed = Counter((row["family"], row["id"].split("-")[0]) for row in selected)
    assert set(observed) == expected_strata and set(observed.values()) == {3}
    for i in range(0,96,3):
        group = selected[i:i+3]
        assert len({s.group_id(row) for row in group}) == 1
        assert tuple(row["variant"] for row in group) == s.VARIANTS
    assert all(row == by_id[row["id"]] for row in selected)
    revisions = [row for row in selected if row["family"] == "revision"]
    assert len(revisions) == 6 and len({s.group_id(row) for row in revisions}) == 2
    assert {row["id"].split("-")[0] for row in revisions} == {"v8","v13"}


def test_unchanged_settings_shuffle_positions_grounding_and_evaluation_separation():
    prior = json.loads((s.previous.RUN/s.previous.ARM/"training_started.json").read_text())["config"]
    config = s.training_config(prior)
    s.compare_config(config)
    assert {k for k in prior if prior[k] != config[k]} == {"adapter_path"}
    evaluation = s.control.evaluation_rows()
    assert len(evaluation) == 248
    frozen = json.loads((s.previous.RUN/"freeze.json").read_text())
    assert s.rows_digest(evaluation) == frozen["evaluation_sha256"]
    texts = {r["source"] for r in evaluation}; groups = {s.group_id(r) for r in evaluation}
    for row in s.training_rows():
        assert row["source"] not in texts and s.group_id(row) not in groups
        graph = s.control.old.parse_output(s.control.messages(row)[-1]["content"],row["source"])
        assert semantic_graph(graph) == semantic_graph(row["graph"])
    prior_rows = s.previous.training_rows()
    prior_slots = {row["id"]: i for i,row in enumerate(prior_rows)}
    receipt = json.loads((s.previous.RUN/s.previous.ARM/"training_complete.json").read_text())
    assert [prior_slots[i] for i in receipt["sampled_ids"]] == list(np.random.RandomState(151).permutation(96))
