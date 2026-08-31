"""DRAFT-PENDING-OWNER-FREEZE: read-only authoring checks, never a battery run."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from validation.arms import Arm, render_arm
from validation.draft_cases import FAMILIES, MODES, ROOT, STATUS
from validation.harness import canonical, load_histories


def load_answers(path: Path) -> dict[str, dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = {row["test_id"]: row for row in rows}
    if len(result) != len(rows): raise ValueError("duplicate answer ID")
    return result


def request_for_answer(case: dict, expected: dict, arm: str, answer: object, packet_injected: bool | None = None) -> dict:
    """Assemble an isolated oracle request AFTER capture, never provider context."""
    if arm not in {a.value for a in Arm} or case["test_id"] != expected["test_id"]:
        raise ValueError("oracle case/arm mismatch")
    request = {"oracle_version": "typed-action-oracle/1", "case_id":case["test_id"],
               "arm":arm,"expected_answer":copy.deepcopy(expected["expected_answer"]),"answer":copy.deepcopy(answer)}
    if arm in expected["mismatch_allowed_arms"]:
        request["acceptable_mismatch_answer"] = copy.deepcopy(expected["acceptable_mismatch_answer"])
    if case["mode"] == "no_rot" and arm == "SUB-D":
        request["expected_packet_injected"] = False
        if packet_injected is not None: request["packet_injected"] = packet_injected
    return request


def inspect() -> dict:
    counts, case_hashes = {}, {}
    modes = {mode: 0 for mode in MODES}
    all_ids = set()
    for family in FAMILIES:
        path = ROOT / "cases" / f"{family.lower()}.jsonl"
        cases = load_histories(path)
        answers = load_answers(ROOT / "answers" / path.name)
        assert len(cases) == len(answers) == 12, family
        assert {c["test_id"] for c in cases} == set(answers)
        assert {c["mode"] for c in cases} == set(MODES)
        counts[family] = len(cases)
        for case in cases:
            cid, expected = case["test_id"], answers[case["test_id"]]
            assert cid not in all_ids
            all_ids.add(cid)
            assert case["focus_family"] == family
            assert case["status"] == expected["status"] == STATUS
            assert expected["oracle_version"] == "typed-action-oracle/1"
            assert expected["mismatch_allowed_arms"] == ["SUB-E"]
            modes[case["mode"]] += 1
            assert len(case["history"]) == case["history_turns"]
            assert len({t["turn_id"] for t in case["history"]}) == len(case["history"])
            assert {o["type"] for o in case["objects"]} == set(FAMILIES)
            objects = {o["id"]:o for o in case["objects"]}
            answer = expected["expected_answer"]
            option_ids = {o["id"] for o in case["options"]}
            assert len(option_ids) == 4 and answer["action_id"] in option_ids
            assert set(answer["rejected_action_ids"]) == option_ids - {answer["action_id"]}
            assert answer["authority"] == "ledger_only" and answer["proposed_mutations"] == []
            for field in ["cited_state_ids", "historical_state_ids"]:
                assert answer[field] == sorted(set(answer[field]))
                assert set(answer[field]) <= objects.keys()
            assert all(objects[i]["status"] == "superseded" for i in answer["historical_state_ids"])
            assert all(r in case["relationships"] for r in answer["relationships"])
            assert answer["relationships"] == sorted(answer["relationships"],key=lambda r:(r["from_id"],r["relation"],r["to_id"]))
            assert objects[f"{cid}:assumption"]["authority"] == "provider_candidate"
            assert objects[f"{cid}:constraint"]["binding_strength"] == "hard"
            if case["mode"] == "no_rot":
                assert case["visible_turns"] == len(case["history"]) <= 20
                assert case["packet_policy"] == "no_gratuitous_injection"
            else:
                assert 100 <= len(case["history"]) <= 300
                if case["mode"] == "cross_session":
                    assert len({t["session_id"] for t in case["history"]}) == 2
                    assert case["visible_turns"] == 4
                if case["mode"] == "supersession":
                    assert case["history"][-3]["role"] == "user" and case["current_state"] in case["history"][-3]["text"]
                if case["mode"] == "paraphrase_revival":
                    assert case["history"][-2]["role"] == "assistant" and "not owner authority" in case["history"][-2]["text"]
            for arm in Arm:
                rendered = render_arm(arm, case)
                assert rendered.probe == case["probe"]  # Same task across conditions.
                assert canonical(answer) not in rendered.context + rendered.probe
                if arm in {Arm.SUB_B, Arm.SUB_C, Arm.SUB_D} or (arm == Arm.SUB_A and case["mode"] == "no_rot"):
                    assert all(i in rendered.context for i in answer["cited_state_ids"] + answer["historical_state_ids"])
            case_hashes[cid] = "sha256:" + hashlib.sha256(canonical(case).encode()).hexdigest()
    return {"status":STATUS,"check_kind":"authoring-contract-only","families":counts,
            "cases":len(all_ids),"modes":modes,"provider_calls":0,"gate_verdicts":[],
            "materialized_case_sha256":case_hashes}


def inventory() -> dict:
    files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p.name != "manifest.json")
    code = [Path(__file__), Path(__file__).with_name("draft_cases.py"),
            Path(__file__).with_name("oracle_worker.py"), Path(__file__).with_name("arms.py"),
            Path(__file__).with_name("harness.py"), Path(__file__).parent / "tests" / "test_draft_contract.py"]
    repo = ROOT.parents[2]
    return {str(p.relative_to(repo)):"sha256:"+hashlib.sha256(p.read_bytes()).hexdigest() for p in files+code}


def main() -> int:
    parser = argparse.ArgumentParser(description="DRAFT-PENDING-OWNER-FREEZE: static checks only; no live or battery replay")
    parser.add_argument("--emit-manifest", action="store_true", help="print a draft checksum inventory; does not freeze or run anything")
    args = parser.parse_args()
    result = inspect()
    if args.emit_manifest:
        result.update({"format":"tom-assist-draft-inventory/1","owner_frozen":False,
                       "files_sha256":inventory(),"hypothesis_status":"unexecuted draft","runs":[]})
        print(json.dumps(result,indent=2,sort_keys=True))
    else:
        manifest_path = ROOT / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["owner_frozen"] is True:
                assert manifest["status"] == "FROZEN-WP25-V1"
                assert manifest["freeze"]["version"] == "wp25-prereg-frozen/1"
                # The authoring inventory is retained as the immutable source
                # snapshot. Freeze/runner code is separately pinned by WP-25.
                for relative, expected in manifest["files_sha256"].items():
                    if ("/cases/" in relative or "/answers/" in relative
                            or relative.endswith("/domains.json")
                            or relative.endswith("/PREREGISTRATION.md")):
                        repository = ROOT.parents[2]
                        actual = "sha256:" + hashlib.sha256((repository / relative).read_bytes()).hexdigest()
                        assert actual == expected, f"frozen authored file changed: {relative}"
                result["freeze_status"] = manifest["status"]
                result["freeze_version"] = manifest["freeze"]["version"]
            else:
                assert manifest["status"] == STATUS
                assert manifest["files_sha256"] == inventory(), "draft file checksum mismatch; intentional draft revision requires new inventory"
            assert manifest["materialized_case_sha256"] == result["materialized_case_sha256"]
        result.pop("materialized_case_sha256")
        print(json.dumps(result,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
