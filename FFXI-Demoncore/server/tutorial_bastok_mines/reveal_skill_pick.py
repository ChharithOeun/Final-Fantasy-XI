"""Reveal-skill pick — minute 25-40 of the tutorial.

Per TUTORIAL_BASTOK_MINES.md the reveal skill is job-determined:
    WHM      -> Scan         (free Cure first; Scan unlocks lvl 20)
    BLM      -> Drain
    THF      -> Mug          (introduced at lvl 25, used early here)
    WAR/PLD  -> /check command

Every other job at character creation gets /check as the universal
fallback so no one is left out of the gate. The reveal-skill the
player gets here is what's used on the sleeping fomor in the mine
shafts and is the same skill the unlock_cadence assigns at lvl 20
(generic; per-job rules layered on top).
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class RevealSkill:
    """The skill granted to the player for the reveal-skill gate."""
    skill_id: str
    label: str
    job_unlock_level: int
    is_command: bool = False    # True for /check (no spell, just command)


REVEAL_SKILL_BY_JOB: dict[str, RevealSkill] = {
    "WHM": RevealSkill(skill_id="scan", label="Scan",
                          job_unlock_level=20),
    "BLM": RevealSkill(skill_id="drain", label="Drain",
                          job_unlock_level=20),
    "THF": RevealSkill(skill_id="mug", label="Mug",
                          job_unlock_level=25),
    "WAR": RevealSkill(skill_id="check", label="/check",
                          job_unlock_level=5, is_command=True),
    "PLD": RevealSkill(skill_id="check", label="/check",
                          job_unlock_level=5, is_command=True),
}


# Default for any job not in the table — universal /check.
DEFAULT_REVEAL_SKILL = RevealSkill(
    skill_id="check", label="/check",
    job_unlock_level=5, is_command=True,
)


def pick_reveal_skill(job: str) -> RevealSkill:
    """Return the reveal skill granted to a character of the given job.

    Unknown jobs fall through to /check so every newcomer can clear
    the gate. Doc: '/check command' is the universal fallback.
    """
    return REVEAL_SKILL_BY_JOB.get(job.upper(), DEFAULT_REVEAL_SKILL)
