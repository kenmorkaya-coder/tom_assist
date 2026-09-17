"""Reject corrupt continuation inputs and preserve original evaluation settings."""
import json
from types import SimpleNamespace

import pytest

from validation.event_graph_v23 import evaluation_resume as resume


def test_saved_prefix_rejects_duplicates_truncation_and_changed_graph(tmp_path):
    rows = resume.experiment.control.evaluation_rows()[:2]
    predictions = []
    for row in rows:
        raw = resume.experiment.control.messages(row)[-1]["content"]
        predictions.append({"id": row["id"], "raw": raw,
                            "graph": resume.experiment.control.old.parse_output(raw, row["source"]),
                            "token_ids": [106], "eos_token_ids": [106], "finish_reason": "stop"})
    first, second = tmp_path / "first.jsonl", tmp_path / "second.jsonl"
    first.write_text(json.dumps(predictions[0]) + "\n")
    second.write_text(json.dumps(predictions[1]) + "\n")
    assert resume.read_prefix([first, second], rows) == predictions
    with pytest.raises(ValueError, match="unique, ordered"):
        resume.read_prefix([first, first], rows)
    second.write_text(json.dumps(predictions[1]))
    with pytest.raises(ValueError, match="incomplete"):
        resume.read_prefix([first, second], rows)
    predictions[1]["graph"] = {}
    second.write_text(json.dumps(predictions[1]) + "\n")
    with pytest.raises(ValueError, match="disagrees"):
        resume.read_prefix([first, second], rows)


def test_resource_timeout_does_not_launch_model(tmp_path, monkeypatch):
    monkeypatch.setattr(resume, "directory", lambda attempt: tmp_path)
    monkeypatch.setattr(resume, "verify_training", lambda: None)
    monkeypatch.setattr(resume, "verify_manifest", lambda attempt: None)
    monkeypatch.setattr(resume, "observe", lambda *args: {"blockers": [{"reason": "other_large_python_job"}]})
    ticks = iter([0, 1801, 1801])
    monkeypatch.setattr(resume, "time", SimpleNamespace(time=lambda: 1, monotonic=lambda: next(ticks)))
    monkeypatch.setattr(resume.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("model must not launch"))
    resume.run(1)
    assert json.loads((tmp_path / "status.json").read_text())["status"] == "BLOCKED_RESOURCES"
    assert {k: resume.POLICY[k] for k in ("seed", "temperature", "max_tokens", "enable_thinking")} == {
        "seed": 7, "temperature": 0.0, "max_tokens": 4096, "enable_thinking": False}
    assert resume.POLICY["resource_policy"] == resume.base.RESOURCE_POLICY
