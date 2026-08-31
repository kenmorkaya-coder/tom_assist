"""WP-25 frozen selection/UUID/telemetry checks; no provider calls."""
import json
import unittest
import uuid

from validation.production_runner import (
    AUTHORIZED_GENERATIONS,
    MANIFEST,
    all_cases,
    native_case,
    observation_order,
    packet_telemetry,
    pilot_selection,
    verify_freeze,
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


if __name__ == "__main__":
    unittest.main()
