"""WP-25 frozen selection/UUID/telemetry checks; no provider calls."""
import json
import unittest
import uuid
from argparse import Namespace
from unittest.mock import patch

from validation.production_runner import (
    AUTHORIZED_GENERATIONS,
    MANIFEST,
    V2_DRAFT_MANIFEST,
    all_cases,
    native_case,
    observation_order,
    packet_telemetry,
    pilot_selection,
    verify_freeze,
    cluster_bootstrap,
    oracle_result,
    substrate_engagement,
    sha256_file_at_commit,
    verify_v2_freeze,
)
from validation.production_runner_v4 import (
    MAX_UNKNOWN_OUTCOMES,
    MIN_COMPLETE_CASES,
    OBSERVATION_TIMEOUT_SECONDS,
    V3_APPROVED_CHANGES,
    V3_DRAFT_MANIFEST,
    run,
    v3_analysis,
    verify_v3_delta,
)


class ProductionRunnerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.answers = all_cases()
        cls.selected = pilot_selection(cls.cases)

    def test_owner_freeze_selection_and_rotated_matrix_are_exact(self):
        manifest = json.loads(MANIFEST.read_text())
        verify_freeze(manifest, self.cases)
        self.assertEqual(len(self.selected), 33)
        self.assertEqual(len(observation_order(self.selected)), AUTHORIZED_GENERATIONS)
        by_family = {}
        for case in self.selected:
            by_family.setdefault(case["focus_family"], []).append(case)
        self.assertEqual(set(map(len, by_family.values())), {3})
        for rows in by_family.values():
            self.assertEqual(sum(row["mode"] == "no_rot" for row in rows), 1)

    def test_native_mapping_is_uuid_project_bound_and_key_preserving(self):
        case = self.selected[0]
        source = self.answers[case["test_id"]]
        first, expected, mapping, floor = native_case(case, source, "SUB-A")
        second, _, second_mapping, _ = native_case(case, source, "SUB-B")
        for value in mapping.values():
            uuid.UUID(value)
        self.assertNotEqual(first["project_id"], second["project_id"])
        self.assertNotEqual(mapping, second_mapping)
        self.assertEqual(expected["expected_answer"]["action_id"], source["expected_answer"]["action_id"])
        self.assertTrue(floor)
        self.assertEqual({row["project_id"] for row in first["objects"]}, {first["project_id"]})
        self.assertEqual({row["workstream_id"] for row in first["objects"]}, {first["workstream_id"]})
        self.assertEqual(len(first["history"]), len(case["history"]))
        self.assertEqual(
            {turn["turn_id"] for turn in first["history"]},
            {mapping[turn["turn_id"]] for turn in case["history"]},
        )

    def test_no_rot_floor_is_allowed_but_optional_content_is_gratuitous(self):
        result = {"arm": "SUB-D", "packet_text": "packet", "packet": {
            "sections": [{"items": [{"state_id": "floor"}, {"state_id": "optional"}]}],
            "retrieved_anchor_ids": [], "estimated_tokens": 2,
        }}
        measured = packet_telemetry(result, {"floor"}, "no_rot")
        self.assertEqual(measured["floor_ids"], ["floor"])
        self.assertEqual(measured["optional_ids"], ["optional"])
        self.assertTrue(measured["gratuitous_packet_injected"])
        result["packet"]["sections"][0]["items"].pop()
        self.assertFalse(packet_telemetry(result, {"floor"}, "no_rot")["gratuitous_packet_injected"])

    def test_cluster_bootstrap_retains_the_sub_d_side_of_every_pair(self):
        rows = []
        for family in sorted({case["focus_family"] for case in self.selected}):
            for domain in ("domain-a", "domain-b"):
                test_id = f"{family}:{domain}"
                for arm, exact in (("SUB-D", True), ("SUB-A", False)):
                    rows.append({
                        "test_id": test_id,
                        "family": family,
                        "domain": domain,
                        "mode": "truncation",
                        "arm": arm,
                        "oracle": {"action_consistent": exact},
                    })
        result = cluster_bootstrap(rows, "SUB-A")
        self.assertEqual(result["valid_replicates"], 10_000)
        self.assertEqual(result["invalid_replicates"], 0)
        self.assertEqual(result["ci95"], [1.0, 1.0])

    def test_future_runner_uses_v2_multiset_citation_comparison(self):
        expected = self.answers[self.selected[0]["test_id"]]
        answer = json.loads(json.dumps(expected["expected_answer"]))
        answer["cited_state_ids"].reverse()
        answer["historical_state_ids"].reverse()
        scored = oracle_result(expected, "SUB-D", json.dumps(answer), {}, "truncation")
        self.assertEqual(scored["oracle_version"], "typed-action-oracle/2")
        self.assertTrue(scored["action_consistent"])

    def test_v4_frozen_path_requires_fresh_explicit_authorization(self):
        registration = json.loads(V3_DRAFT_MANIFEST.read_text())
        verify_v3_delta(registration, require_frozen=True)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "explicit WP-29 pilot-v4 authorization"):
                run(Namespace(authorized_generations=165))

    def test_historical_freeze_reads_recorded_commit_not_current_worktree(self):
        registration = json.loads(V2_DRAFT_MANIFEST.read_text())
        verify_v2_freeze(registration)
        self.assertEqual(
            sha256_file_at_commit(registration["code_sha"], "gateway/tom_gateway.py"),
            registration["files_sha256"]["gateway/tom_gateway.py"],
        )
        with self.assertRaisesRegex(ValueError, "unavailable"):
            sha256_file_at_commit("0" * 40, "gateway/tom_gateway.py")

    def test_v3_delta_is_exactly_the_five_owner_approved_changes(self):
        registration = json.loads(V3_DRAFT_MANIFEST.read_text())
        self.assertEqual(registration["changes"], V3_APPROVED_CHANGES)
        self.assertEqual(OBSERVATION_TIMEOUT_SECONDS, 600)
        self.assertEqual(MAX_UNKNOWN_OUTCOMES, 8)
        self.assertEqual(MIN_COMPLETE_CASES, 30)
        changed = json.loads(json.dumps(registration))
        changed["changes"].append({"id": 6})
        with self.assertRaisesRegex(ValueError, "exactly the five"):
            verify_v3_delta(changed, require_frozen=False)

    def test_v3_excludes_an_entire_case_after_one_unknown_arm(self):
        captured = []
        dispositions = []
        for case_number in range(31):
            test_id = f"case-{case_number:02}"
            for arm in ("SUB-A", "SUB-B", "SUB-C", "SUB-D", "SUB-E"):
                disposition = {"test_id": test_id, "arm": arm, "disposition": "captured"}
                dispositions.append(disposition)
                if not (test_id == "case-30" and arm == "SUB-C"):
                    captured.append(disposition)
                else:
                    disposition["disposition"] = "unknown_outcome"
        analysis_rows, metadata = v3_analysis(captured, dispositions)
        self.assertEqual(metadata["complete_cases"], 30)
        self.assertEqual(metadata["excluded_case_ids"], ["case-30"])
        self.assertEqual(len(analysis_rows), 150)

    def test_substrate_engagement_requires_every_native_tripwire(self):
        telemetry = {
            "history_turns": 4,
            "five_dynamics_receipts": 4,
            "canonical_17_channel_applications": 4,
            "routing_basis_8d_applications": 4,
            "assistant_turns": 2,
            "assistant_teaches": 2,
            "tick_delta": 4,
            "checkpoint_changed": True,
            "provider_calls_during_import": 0,
        }
        result = substrate_engagement([{"substrate_engagement": telemetry}])
        self.assertTrue(result["all_rows_fully_engaged"])
        self.assertEqual(result["rows_fully_engaged"], 1)
        telemetry = dict(telemetry, assistant_teaches=1)
        self.assertFalse(substrate_engagement([{"substrate_engagement": telemetry}])["all_rows_fully_engaged"])


if __name__ == "__main__":
    unittest.main()
