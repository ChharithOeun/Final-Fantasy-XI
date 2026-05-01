"""Skill mastery 0-5 per skill — character-bound, not gear-bound.

Per PLAYER_PROGRESSION.md: 'Mastery is tied to YOU, not your gear. A
WHM can transfer to RDM and bring their Cure-mastery with them — they
just can't cast WHM-only spells until they level RDM.'

XP sources from the doc:
    MB-window cast            : +1 mastery exp
    Perfect skillchain close  : +2 mastery exp (within 0.3s of optimal)
    Low-HP survival no CD     : +1 on tank skills
    Successful intervention   : +3 on cure/buff/debuff family

Mastery 5 unlocks:
    -10% cast time on that specific spell
    Refined animation (less wobble, more decisive form)
    Veteran voice variant for callouts (more confident delivery)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkillFamily(str, enum.Enum):
    """Skill family classification — determines which XP awards apply."""
    HEALING = "healing"                    # cure, regen, raise
    OFFENSE_PHYSICAL = "offense_physical"  # weapon skills + physical attacks
    OFFENSE_MAGIC = "offense_magic"        # nukes (BLM/SCH/etc.)
    TANK = "tank"                          # provoke, flash, defensive
    SUPPORT = "support"                    # haste, march, ballad
    DEBUFF = "debuff"                      # slow, paralyze, bio
    UTILITY = "utility"                    # scan, mug, drain, sneak


# Cumulative XP required to enter each mastery level (1..5).
# Matches the doc's flavor of mastery 5 being a serious investment.
MASTERY_XP_THRESHOLDS: dict[int, int] = {
    1: 50,
    2: 150,
    3: 350,
    4: 700,
    5: 1500,
}
MAX_MASTERY_LEVEL = 5


# Per-event-kind XP grant. The orchestrator emits these events from
# combat / cast / intervention pipelines.
MASTERY_XP_AWARDS: dict[str, int] = {
    "mb_window_cast":            1,    # cast landed in MB window
    "perfect_skillchain_close":  2,    # SC closed within 0.3s of optimal
    "low_hp_survival_no_cd":     1,    # survived a round at low HP w/o CD
    "successful_intervention":   3,    # intervention-MB landed
    "weapon_skill_clean_hit":    1,    # WS lands without resist
    "spell_cast_resisted":       0,    # neutral; no XP
}


# Mastery-5 perks bundle. Caller layers these into the combat
# pipeline (cast_time multiplier, voice variant, animation flag).
MASTERY_5_PERKS = {
    "cast_time_reduction": 0.10,    # 10% off cast time
    "voice_variant": "veteran",
    "animation_flag": "refined",
}


@dataclasses.dataclass
class SkillMastery:
    """Per-skill mastery state."""
    skill_id: str
    family: SkillFamily
    mastery_level: int = 0
    mastery_xp: int = 0


def _level_for_xp(xp: int) -> int:
    """Resolve the mastery level from cumulative XP."""
    level = 0
    for tier, threshold in sorted(MASTERY_XP_THRESHOLDS.items()):
        if xp >= threshold:
            level = tier
        else:
            break
    return level


class SkillMasteryTracker:
    """Owns the per-character skill-mastery roster. Mutates in place;
    persisted by the caller."""

    def __init__(self) -> None:
        self.skills: dict[str, SkillMastery] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def grant_xp(self,
                  skill_id: str,
                  *,
                  family: SkillFamily,
                  event_kind: str,
                  multiplier: float = 1.0) -> int:
        """Grant mastery XP from an in-game event. Returns the new
        mastery level (caller compares with previous to detect a
        level-up)."""
        award = MASTERY_XP_AWARDS.get(event_kind, 0)
        if award <= 0:
            return self.skills.get(skill_id, SkillMastery(
                skill_id=skill_id, family=family,
            )).mastery_level

        gain = int(round(award * multiplier))

        skill = self.skills.get(skill_id)
        if skill is None:
            skill = SkillMastery(skill_id=skill_id, family=family)
            self.skills[skill_id] = skill

        skill.mastery_xp += gain
        new_level = _level_for_xp(skill.mastery_xp)
        if new_level > skill.mastery_level:
            skill.mastery_level = new_level
        return skill.mastery_level

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def mastery_level(self, skill_id: str) -> int:
        skill = self.skills.get(skill_id)
        return skill.mastery_level if skill is not None else 0

    def has_mastery_5(self, skill_id: str) -> bool:
        return self.mastery_level(skill_id) >= MAX_MASTERY_LEVEL

    def cast_time_multiplier(self, skill_id: str) -> float:
        """Mastery 5 grants -10% cast time on that specific skill."""
        if self.has_mastery_5(skill_id):
            return 1.0 - MASTERY_5_PERKS["cast_time_reduction"]
        return 1.0

    def voice_variant_for(self, skill_id: str) -> str:
        return ("veteran" if self.has_mastery_5(skill_id)
                  else "untrained")

    def transfer_eligible(self, skill_id: str) -> bool:
        """Is this skill character-bound and would transfer to a new job?
        All mastered skills are; the doc says 'mastery is tied to YOU,
        not your gear' — and not tied to job either."""
        return skill_id in self.skills

    def all_mastery_5_skills(self) -> list[str]:
        return [skill_id for skill_id, m in self.skills.items()
                  if m.mastery_level >= MAX_MASTERY_LEVEL]
