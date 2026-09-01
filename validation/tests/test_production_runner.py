"""WP-25 frozen selection/UUID/telemetry checks; no provider calls."""
import json
import unittest
import uuid
from argparse import Namespace

from validation.production_runner import (
    AUTHORIZED_GENERATIONS,
    MANIFEST,
    all_cases,
    native_case,
    observation_order,
    packet_telemetry,
    pilot_selection,
    verify_freeze,
    cluster_bootstrap,
    oracle_result,
    run,
    substrate_engagement,
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

    def test_v3_live_path_is_blocked_until_owner_freezes_v2(self):
        with self.assertRaisesRegex(ValueError, "DRAFT-PENDING-OWNER-FREEZE"):
            run(Namespace())

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
