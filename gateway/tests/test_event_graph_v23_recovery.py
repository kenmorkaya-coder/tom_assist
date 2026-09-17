"""Regression checks for missed generic model processes and unchanged V23 inputs."""
import json
from validation.event_graph_v23 import recovery as r


def test_generic_python_competition_and_own_descendants():
    records = r.parse_processes("10 1 100 /usr/bin/Python\n11 10 100 /usr/bin/Python\n12 11 100 /usr/bin/Python\n20 1 3000000 /usr/bin/Python\n")
    assert r.owned_pids(records, 10) == {10, 11, 12}
    observation = {"reclaimable_estimate_bytes": 40*r.GIB, "other_processes": [
        {"pid":20,"rss_bytes":3*r.GIB,"python":True,"mlx_loaded":False,"model_process_name":False},
        {"pid":21,"rss_bytes":10,"python":True,"mlx_loaded":True,"model_process_name":False},
    ]}
    assert r.blockers(observation, True) == [
        {"pid":20,"reason":"other_large_python_job"}, {"pid":21,"reason":"other_model_process"}]
    observation["other_processes"] = []
    assert r.blockers(observation, True) == []
    observation["reclaimable_estimate_bytes"] = 27*r.GIB
    assert r.blockers(observation, True) and not r.blockers(observation, False)


def test_vm_estimate_and_unchanged_experiment_with_new_output(monkeypatch):
    assert r.reclaimable_bytes("Mach statistics (page size of 16384 bytes)\nPages free: 1.\nPages inactive: 2.\nPages speculative: 3.\n") == 6*16384
    before = r.experiment.rows_digest(r.experiment.training_rows())
    frozen = json.loads((r.ORIGINAL/"freeze.json").read_text())
    actual = json.loads((r.ORIGINAL/r.experiment.ARM/"training_started.json").read_text())["config"]
    monkeypatch.setattr(r.experiment,"RUN",r.RUN)
    after = r.experiment.training_config(actual)
    assert {k for k in actual if actual[k] != after[k]} == {"adapter_path"}
    assert before == r.experiment.rows_digest(r.experiment.training_rows()) == frozen["training_sha256"]
    assert r.experiment.PLAN == frozen["plan"]
    assert r.experiment.rows_digest(r.experiment.control.evaluation_rows()) == frozen["evaluation_sha256"]
