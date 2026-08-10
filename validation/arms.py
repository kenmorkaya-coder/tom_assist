from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Arm(str, Enum):
    SUB_A = "SUB-A"
    SUB_B = "SUB-B"
    SUB_C = "SUB-C"
    SUB_D = "SUB-D"
    SUB_E = "SUB-E"


@dataclass(frozen=True)
class ArmInput:
    arm: Arm
    history: list[dict[str, str]]
    probe: str
    context: str


def render_arm(arm: Arm, case: dict) -> ArmInput:
    history = list(case["history"])
    visible = history[-int(case.get("visible_turns", 2)) :]
    current = str(case["current_state"])
    stale = str(case["stale_state"])
    if arm is Arm.SUB_A:
        context = "\n".join(turn["text"] for turn in visible)
    elif arm is Arm.SUB_B:
        context = f"Conversation summary: {case['summary']}"
    elif arm is Arm.SUB_C:
        context = f"Prior project state in prose: {current}"
    elif arm is Arm.SUB_D:
        context = "\n".join(("[TOM_ASSIST_STATE v1]", current, "[/TOM_ASSIST_STATE]"))
    else:
        context = "\n".join(("[TOM_ASSIST_STATE v1 | STALE_ABLATION]", stale, "[/TOM_ASSIST_STATE]"))
    return ArmInput(arm=arm, history=history, probe=str(case["probe"]), context=context)
