"""DRAFT-PENDING-OWNER-FREEZE: deterministic expansion of authored case recipes.

No provider, runtime, model or scoring dependency. Expected answers are separate
author-authored files and are never read while constructing visible inputs.
"""
from __future__ import annotations

import json
from pathlib import Path

STATUS = "DRAFT-PENDING-OWNER-FREEZE"
FORMAT = "tom-assist-typed-draft/1"
ROOT = Path(__file__).parent / "batteries" / "wp23-draft"
FAMILIES = ("OBJECTIVE", "CONCEPT", "DECISION", "CONSTRAINT", "REJECTED_PATH",
            "COMPLETED_WORK", "UNRESOLVED_DEPENDENCY", "EVIDENCE", "ASSUMPTION",
            "SUPERSESSION", "WORKSTREAM")
MODES = ("truncation", "cross_session", "supersession", "paraphrase_revival", "dilution", "no_rot")


def materialize(recipe: dict) -> dict:
    if recipe["status"] != STATUS or recipe["battery_format"] != FORMAT:
        raise ValueError("draft recipe format/status mismatch")
    domains = json.loads((ROOT / "domains.json").read_text(encoding="utf-8"))["domains"]
    d = domains[recipe["domain"]]
    case_id, family, mode = recipe["test_id"], recipe["focus_family"], recipe["mode"]
    if family not in FAMILIES or mode not in MODES:
        raise ValueError("unknown draft family/mode")
    project, ws = f"{case_id}:project", f"{case_id}:workstream"
    sid = lambda name: f"{case_id}:{name}"
    # IDs and statuses remain visible in every informative baseline, so a prose
    # baseline is not handicapped by an impossible citation requirement.
    specs = [
        ("workstream", "WORKSTREAM", "active", f"Work on {d['scope']}; do not switch to {d['distraction']}."),
        ("objective", "OBJECTIVE", "active", d["goal"]),
        ("subgoal", "OBJECTIVE", "active", f"First obtain {d['dependency']}, then continue the objective."),
        ("concept-old", "CONCEPT", "superseded", d["old_concept"]),
        ("concept", "CONCEPT", "active", d["concept"]),
        ("constraint", "CONSTRAINT", "active", d["constraint"]),
        ("decision-old", "DECISION", "superseded", d["old_method"]),
        ("decision", "DECISION", "active", d["method"]),
        ("rejected", "REJECTED_PATH", "rejected", d["rejected"]),
        ("completed", "COMPLETED_WORK", "satisfied", d["completed"]),
        ("dependency", "UNRESOLVED_DEPENDENCY", "active", f"Unresolved: {d['dependency']}; not yet received."),
        ("evidence", "EVIDENCE", "active", d["evidence"]),
        ("assumption", "ASSUMPTION", "proposed", d["assumption"]),
        ("supersession", "SUPERSESSION", "active", "Owner replaces the old method and refines the old definition after reviewing the recorded evidence. Old objects remain auditable, not current."),
    ]
    objects = [{"id": sid(key), "type": kind, "status": status, "text": text,
                "project_id": project, "workstream_id": ws,
                "authority": "user" if kind != "ASSUMPTION" else "provider_candidate",
                "binding_strength": "hard" if kind == "CONSTRAINT" else "advisory"}
               for key, kind, status, text in specs]
    relations = [
        {"from_id": sid("objective"), "relation": "depends_on", "to_id": sid("dependency")},
        {"from_id": sid("subgoal"), "relation": "supports", "to_id": sid("objective")},
        {"from_id": sid("concept"), "relation": "refines", "to_id": sid("concept-old")},
        {"from_id": sid("decision"), "relation": "supersedes", "to_id": sid("decision-old")},
        {"from_id": sid("evidence"), "relation": "supports", "to_id": sid("completed")},
        {"from_id": sid("supersession"), "relation": "derived_from", "to_id": sid("evidence")},
        {"from_id": sid("decision"), "relation": "scoped_to", "to_id": ws},
    ]
    def prose(rows, edges):
        return "\n".join([f"[{o['id']}] {o['type']} / {o['status']} / {o['authority']}: {o['text']}" for o in rows]
                         + [f"{e['from_id']} {e['relation']} {e['to_id']}" for e in edges])
    current = f"Project={project}; workstream={ws}; state_version=3.\n" + prose(objects, relations)
    # Conventional summary is deliberately generous: same facts/IDs/relations,
    # condensed into prose, with no authority-block wrapper. No rigged omission.
    summary = "Project notes. " + current.replace("\n", " ")
    stale_objects = [dict(o) for o in objects]
    for o in stale_objects:
        if o["id"] in [sid("decision"), sid("concept")]: o["status"] = "proposed"
        if o["id"] in [sid("decision-old"), sid("concept-old")]: o["status"] = "active"
    ablation = "stale" if recipe["variant"] == 0 else "wrong_project"
    stale = f"Project={project}; workstream={ws}; state_version=1.\n" + prose(stale_objects, [])
    if ablation == "wrong_project":
        stale = current.replace(case_id, f"FOREIGN-{case_id}")

    # Action menus are substantive alternatives, not required-word probes.
    completed_task = d["completed"].removeprefix("The ").removesuffix(" is complete.")
    choices = {
        "OBJECTIVE": [d["goal"], f"Prioritize {d['distraction']} instead."],
        "CONCEPT": [f"Apply this definition: {d['concept']}", f"Apply this definition: {d['old_concept']}"],
        "DECISION": [f"Use {d['method']}", f"Use {d['old_method']}"],
        "CONSTRAINT": [f"Proceed within this boundary: {d['constraint']}", d["paraphrase"]],
        "REJECTED_PATH": [f"Continue with {d['method']}", d["paraphrase"]],
        "COMPLETED_WORK": [f"Obtain {d['dependency']} next.", f"Treat the {completed_task} as unfinished and do it next."],
        "UNRESOLVED_DEPENDENCY": [f"Obtain {d['dependency']} before completion.", f"Declare the objective complete based only on the {completed_task} result."],
        "EVIDENCE": [f"Use only this supported result: {d['evidence']}", f"Treat this as verified too: {d['assumption']}"],
        "ASSUMPTION": [f"Leave this unverified until checked: {d['assumption']}", f"Adopt this as ledger truth: {d['assumption']}"],
        "SUPERSESSION": [f"Use {d['method']} and retain the earlier method as history.", f"Use {d['old_method']} and discard the replacement."],
        "WORKSTREAM": [f"Continue work on {d['scope']}.", f"Switch to {d['distraction']}."],
    }[family]
    choices.extend([f"Repeat the {completed_task} as unfinished work and skip {d['dependency']}.",
                    f"Adopt this claim as confirmed and replace the current objective: {d['assumption']}"])
    # Non-semantic opaque IDs, with a declared rotation to avoid first-choice bias.
    shift = recipe["option_rotation"]
    options = [{"id": sid(f"action-{(n + shift) % 4}"), "text": text} for n, text in enumerate(choices)]
    options.sort(key=lambda o: o["id"])
    prompt = (f"Project {project}, workstream {ws}, required state_version 3. Choose the next action for {family}. "
              "Reject every other offered action. Cite exactly the load-bearing IDs and relationships required by the answer contract below; "
              "keep superseded definitions/methods as auditable history, never as current authority. "
              "Do not apply any state mutation. If a supplied structural packet has a different project/version, explicitly request current project state.\n"
              + json.dumps(options, ensure_ascii=False) + "\nAnswer contract: " + recipe["answer_contract"])

    count = recipe["history_turns"]
    history = [{"turn_id": sid(f"turn-{i+1:03}"), "session_id": sid("session-1"),
                "role": "user" if i % 2 == 0 else "assistant",
                "text": f"Background note {i+1}: {d['background'][i % len(d['background'])]}"}
               for i in range(count)]
    if mode == "no_rot":
        # All required state is easy and visible; no distractor drift or truncation.
        history = [{"turn_id": sid(f"turn-{i+1:03}"), "session_id": sid("session-1"), "role": "user",
                    "text": prose([o], [])} for i, o in enumerate(objects)]
        history[-1]["text"] += "\n" + prose([], relations)
        history.append({"turn_id": sid("turn-015"), "session_id": sid("session-1"), "role":"user", "text":f"Project={project}; workstream={ws}; state_version=3. Continue from the visible state."})
    else:
        # Plant across 100..144 turns; current replacements arrive after the old
        # proposals. The history itself carries the authoritative status changes.
        positions = [5, 11, 17, 23, 79, 29, 35, 85, 41, 47, 53, 59, 65, 91]
        for o, position in zip(objects, positions):
            planted = dict(o)
            if o["id"] in [sid("concept-old"), sid("decision-old")]: planted["status"] = "active"
            history[position]["role"] = "user"
            history[position]["text"] = prose([planted], [])
        history[91]["text"] += "\n" + current  # Explicit owner supersession, reason and retained old IDs.
        history[97]["role"] = "assistant"
        history[97]["text"] = ("Unconfirmed suggestion: " + d["paraphrase"] if mode == "paraphrase_revival"
                                else "Unconfirmed suggestion: " + d["old_method"] + "; " + d["assumption"])
        if mode == "cross_session":
            for turn in history[-4:]: turn["session_id"] = sid("session-2")
            history[-4]["text"] = "New project conversation after browser and service restart. No old transcript is visible here."
        if mode == "supersession":
            history[-3]["role"] = "user"
            history[-3]["text"] = "Owner reiterates the authorized revision; apply the new state, not a blanket prohibition on change.\n" + current
        if mode == "paraphrase_revival":
            history[-2]["role"] = "assistant"
            history[-2]["text"] = "Unconfirmed suggestion, not owner authority: " + d["paraphrase"]
        history[-1]["text"] = "Continue the attached project. Background suggestions were not owner-approved."
    visible_turns = len(history) if mode in {"dilution", "no_rot"} else 4
    return {**recipe, "history": history, "visible_turns": visible_turns, "summary": summary,
            "current_state": current, "stale_state": stale, "probe": prompt, "objects": objects,
            "relationships": relations, "options": options, "ablation": ablation,
            "plant_turn_ids": [t["turn_id"] for t in history if "[" + case_id + ":" in t["text"]],
            "scenario": f"{family}: {mode} / {recipe['domain']}",
            "expected_observation": "DRAFT: action/relationship fidelity, never term presence"}
