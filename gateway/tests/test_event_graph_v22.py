"""The rate experiment must not alter labels, order, evaluation or other training settings."""
import json
import math
import numpy as np
from gateway.typed_event_graph import semantic_graph
from validation.event_graph_v22 import session as s


def test_rate_is_the_only_training_config_change():
    original = json.loads((s.control.RUN / "control/training_started.json").read_text())["config"]
    config = s.training_config(original)
    s.compare_config(config)
    assert math.isclose(config["learning_rate"], original["learning_rate"] / 5, rel_tol=1e-15)
    assert config["iters"] == 96 and config["seed"] == 151
    assert config["resume_adapter_file"] == original["resume_adapter_file"]


def test_exact_control_inputs_and_saved_order_are_retained():
    rows = s.training_rows()
    control = s.control.training_rows("control")
    assert rows == control and len(rows) == len({r["id"] for r in rows}) == 96
    expected = [r["id"] for r in rows]
    frozen = json.loads((s.control.RUN / "freeze.json").read_text())
    assert expected == frozen["training_ids"]
    sources = {r["source"] for r in s.control.evaluation_rows()}
    for row in rows:
        assert row["source"] not in sources
        graph = s.control.old.parse_output(s.control.messages(row)[-1]["content"], row["source"])
        assert semantic_graph(graph) == semantic_graph(row["graph"])
    sampled = json.loads((s.control.RUN / "control/training_complete.json").read_text())["sampled_ids"]
    assert sampled == [rows[int(i)]["id"] for i in np.random.RandomState(151).permutation(96)]
    assert s.PLAN["selection"].startswith("retain V14")
