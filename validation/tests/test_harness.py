from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validation.arms import Arm
from validation.harness import ROOT, load_histories, replay, run


class HarnessTests(unittest.TestCase):
    fixture = ROOT / "validation/fixtures/toy_cases.jsonl"

    def test_three_case_replay_runs_all_subscription_arms_out_of_process(self):
        observations, traces = replay(self.fixture)
        self.assertEqual(len(load_histories(self.fixture)), 3)
        self.assertEqual(len(observations), 3 * len(Arm))
        self.assertEqual(len(traces), len(observations))
        self.assertEqual({row.arm for row in observations}, {arm.value for arm in Arm})
        self.assertTrue(all(trace["response"]["oracle_version"] == "deterministic-term-oracle/1.0" for trace in traces))

    def test_report_is_complete_reproducible_instrumentation_not_a_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path, manifest_path = run(self.fixture, Path(directory), "2026-08-10T00:00:00+00:00")
            report = report_path.read_text(encoding="utf-8")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("NOT-A-GATE", report)
            self.assertIn("Appendix-C-format observations", report)
            self.assertEqual(manifest["result_summary"], {"cases": 3, "observations": 15, "gate_verdicts": 0})
            for field in ("code_sha", "provider_version", "adapter_version", "state_policy", "packet_renderer_version", "exact_arms", "event_trace", "packet_trace", "result_summary"):
                self.assertIn(field, manifest)
                self.assertTrue(manifest[field] or manifest[field] == 0)


if __name__ == "__main__":
    unittest.main()
