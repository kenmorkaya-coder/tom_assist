"""DRAFT-PENDING-OWNER-FREEZE: static fixture/oracle plumbing, not experiments."""
import copy
import unittest
from unittest.mock import patch

from validation.draft_cases import ROOT, STATUS
from validation.draft_contract import inspect, load_answers, request_for_answer
from validation.harness import load_histories, oracle, replay
from validation.oracle_worker import score


class DraftContractTests(unittest.TestCase):
    def test_all_draft_families_histories_provenance_and_expected_answers_are_consistent(self):
        result = inspect()
        self.assertEqual(result["status"], STATUS)
        self.assertEqual(result["cases"],132)
        self.assertEqual(len(result["families"]),11)
        self.assertEqual(set(result["families"].values()),{12})
        self.assertEqual(set(result["modes"].values()),{22})
        self.assertEqual(result["provider_calls"],0)

    def test_expected_answers_are_oracle_inputs_not_context_matches(self):
        for path in sorted((ROOT / "cases").glob("*.jsonl")):
            answers = load_answers(ROOT / "answers" / path.name)
            for case in load_histories(path):
                expected = answers[case["test_id"]]
                request = request_for_answer(case, expected, "SUB-D", expected["expected_answer"])
                self.assertTrue(score(request)["action_consistent"])
                request["answer"] = {**expected["expected_answer"], "action_id":expected["expected_answer"]["rejected_action_ids"][0]}
                # Even an entire correct key in the context/probe cannot rescue a bad answer.
                request["context"] = expected["expected_answer"]
                request["probe"] = expected["expected_answer"]
                self.assertFalse(score(request)["observed_match"])

    def test_stdin_stdout_oracle_rejects_mutation_wrong_edges_and_misused_mismatch(self):
        path = ROOT / "cases" / "supersession.jsonl"
        case = load_histories(path)[0]
        expected = load_answers(ROOT / "answers" / path.name)[case["test_id"]]
        base = request_for_answer(case, expected, "SUB-D", expected["expected_answer"])
        self.assertTrue(oracle(base)["observed_match"])
        for field, bad in [("proposed_mutations",[{"operation":"UPDATE"}]),("relationships",[]),
                           ("historical_state_ids",[]),("authority","provider_candidate")]:
            request = copy.deepcopy(base)
            request["answer"][field] = bad
            self.assertFalse(oracle(request)["observed_match"],field)
        request = request_for_answer(case, expected, "SUB-E", expected["acceptable_mismatch_answer"])
        result = oracle(request)
        self.assertTrue(result["explicit_mismatch"])
        self.assertFalse(result["action_consistent"])
        self.assertIsNone(result["gate_verdict"])
        request["arm"] = "SUB-D"
        self.assertFalse(oracle(request)["observed_match"])
        request["answer"] = "```json\n{}\n```"
        self.assertFalse(oracle(request)["answer_shape_valid"])

    def test_draft_replay_is_disabled_before_any_oracle_or_provider_operation(self):
        with patch("validation.harness.oracle") as call:
            with self.assertRaisesRegex(ValueError,STATUS):
                replay(ROOT / "cases" / "objective.jsonl")
            call.assert_not_called()

    def test_no_rot_requires_measured_packet_policy_not_an_inferred_success(self):
        path = ROOT / "cases" / "constraint.jsonl"
        case = load_histories(path)[-1]
        expected = load_answers(ROOT / "answers" / path.name)[case["test_id"]]
        request = request_for_answer(case, expected, "SUB-D", expected["expected_answer"])
        self.assertIsNone(score(request)["packet_policy_match"])
        request["packet_injected"] = True
        self.assertFalse(score(request)["packet_policy_match"])
        request["packet_injected"] = False
        self.assertTrue(score(request)["packet_policy_match"])

    def test_v2_draft_compares_citation_lists_as_multisets_only(self):
        expected = {
            "action_id": "act",
            "rejected_action_ids": ["reject-1", "reject-2"],
            "cited_state_ids": ["state-a", "state-b", "state-b"],
            "historical_state_ids": ["old-a", "old-b"],
            "relationships": [{"from": "a", "relation": "depends_on", "to": "b"}],
            "proposed_mutations": [],
            "authority": "ledger_only",
        }
        answer = copy.deepcopy(expected)
        answer["cited_state_ids"] = ["state-b", "state-a", "state-b"]
        answer["historical_state_ids"] = ["old-b", "old-a"]
        request = {"oracle_version": "typed-action-oracle/2", "arm": "SUB-D", "expected_answer": expected, "answer": answer}
        self.assertTrue(score(request)["action_consistent"])
        answer["cited_state_ids"] = ["state-a", "state-b"]
        self.assertFalse(score(request)["field_matches"]["cited_state_ids"])
        answer = copy.deepcopy(expected)
        answer["rejected_action_ids"].reverse()
        request["answer"] = answer
        self.assertFalse(score(request)["field_matches"]["rejected_action_ids"])


if __name__ == "__main__": unittest.main()
