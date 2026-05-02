"""Skill levels — combat + magic skill XP, separate from job level.

Every weapon class and magic school has its own skill stat that
increases by use. Cap is gated by the current job level: a level-30
WAR can't push Sword skill above the WAR's level-30 cap, even if
they accumulate xp.

Public surface
--------------
    Skill enum (~25 skills covering weapons + magic schools)
    SkillTracker per (player, skill)
        .gain_xp(amount)
        .level
        .effective_level(job_level_cap)
    skill_cap_for_job_level(skill, job, job_level)
    XP_PER_LEVEL formula
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Skill(str, enum.Enum):
    # Weapons
    HAND_TO_HAND = "hand_to_hand"
    DAGGER = "dagger"
    SWORD = "sword"
    GREAT_SWORD = "great_sword"
    AXE = "axe"
    GREAT_AXE = "great_axe"
    SCYTHE = "scythe"
    POLEARM = "polearm"
    KATANA = "katana"
    GREAT_KATANA = "great_katana"
    CLUB = "club"
    STAFF = "staff"
    ARCHERY = "archery"
    MARKSMANSHIP = "marksmanship"
    THROWING = "throwing"
    GUARDING = "guarding"
    EVASION = "evasion"
    SHIELD = "shield"
    PARRY = "parry"
    # Magic
    DIVINE_MAGIC = "divine_magic"
    HEALING_MAGIC = "healing_magic"
    ENHANCING_MAGIC = "enhancing_magic"
    ENFEEBLING_MAGIC = "enfeebling_magic"
    ELEMENTAL_MAGIC = "elemental_magic"
    DARK_MAGIC = "dark_magic"
    SUMMONING_MAGIC = "summoning_magic"
    NINJUTSU = "ninjutsu"
    SINGING = "singing"
    STRING_INSTRUMENT = "string_instrument"
    WIND_INSTRUMENT = "wind_instrument"
    BLUE_MAGIC = "blue_magic"


# Approximate XP needed per skill level. Skills up to 600 retail.
# Linear-ish baseline: 1 xp per use, ~12-15 uses per level.
XP_PER_LEVEL = 12


# Skill cap per job-level approximation. Real FFXI uses A+/A/B+/B/...
# letter grades; we model as a simple per-skill multiplier.
@dataclasses.dataclass(frozen=True)
class SkillGradeRule:
    """Cap = job_level * multiplier + plateau."""
    multiplier: float
    plateau: int = 0


# Sample grade rules (tuneable by designers).
SKILL_GRADES: dict[Skill, SkillGradeRule] = {
    Skill.SWORD: SkillGradeRule(multiplier=3.0),    # high A
    Skill.DAGGER: SkillGradeRule(multiplier=2.8),
    Skill.HAND_TO_HAND: SkillGradeRule(multiplier=3.0),
    Skill.GREAT_SWORD: SkillGradeRule(multiplier=2.5),
    Skill.AXE: SkillGradeRule(multiplier=3.0),
    Skill.GREAT_AXE: SkillGradeRule(multiplier=3.0),
    Skill.SCYTHE: SkillGradeRule(multiplier=3.0),
    Skill.POLEARM: SkillGradeRule(multiplier=3.0),
    Skill.KATANA: SkillGradeRule(multiplier=3.0),
    Skill.GREAT_KATANA: SkillGradeRule(multiplier=2.7),
    Skill.CLUB: SkillGradeRule(multiplier=2.7),
    Skill.STAFF: SkillGradeRule(multiplier=2.5),
    Skill.ARCHERY: SkillGradeRule(multiplier=2.7),
    Skill.MARKSMANSHIP: SkillGradeRule(multiplier=2.7),
    Skill.THROWING: SkillGradeRule(multiplier=2.0),
    Skill.GUARDING: SkillGradeRule(multiplier=2.5),
    Skill.EVASION: SkillGradeRule(multiplier=2.7),
    Skill.SHIELD: SkillGradeRule(multiplier=2.5),
    Skill.PARRY: SkillGradeRule(multiplier=2.0),
    Skill.DIVINE_MAGIC: SkillGradeRule(multiplier=2.7),
    Skill.HEALING_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.ENHANCING_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.ENFEEBLING_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.ELEMENTAL_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.DARK_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.SUMMONING_MAGIC: SkillGradeRule(multiplier=3.0),
    Skill.NINJUTSU: SkillGradeRule(multiplier=3.0),
    Skill.SINGING: SkillGradeRule(multiplier=3.0),
    Skill.STRING_INSTRUMENT: SkillGradeRule(multiplier=3.0),
    Skill.WIND_INSTRUMENT: SkillGradeRule(multiplier=3.0),
    Skill.BLUE_MAGIC: SkillGradeRule(multiplier=3.0),
}


def skill_cap_for_job_level(
    skill: Skill, job_level: int,
) -> int:
    """Maximum skill level allowed for this skill at job_level."""
    if job_level < 0:
        raise ValueError("job_level must be >= 0")
    rule = SKILL_GRADES.get(
        skill, SkillGradeRule(multiplier=2.0),
    )
    return int(job_level * rule.multiplier) + rule.plateau


@dataclasses.dataclass
class SkillTracker:
    player_id: str
    skill: Skill
    accumulated_xp: int = 0

    @property
    def level(self) -> int:
        """Skill level from raw XP, ignoring the job-level cap."""
        return self.accumulated_xp // XP_PER_LEVEL

    def gain_xp(
        self, *, amount: int, job_level_cap: int,
    ) -> bool:
        """Add xp; returns True if the skill went up at least 1 level."""
        if amount < 0:
            raise ValueError("amount must be >= 0")
        cap = skill_cap_for_job_level(self.skill, job_level_cap)
        if self.level >= cap:
            return False
        before = self.level
        # Don't accumulate past the level just over the cap.
        self.accumulated_xp += amount
        # Clamp accumulated_xp so .level never reports above cap.
        max_xp = (cap + 1) * XP_PER_LEVEL - 1
        if self.accumulated_xp > max_xp:
            self.accumulated_xp = max_xp
        return self.level > before

    def effective_level(self, job_level_cap: int) -> int:
        """Skill level after job-level cap clamp."""
        cap = skill_cap_for_job_level(self.skill, job_level_cap)
        return min(self.level, cap)


__all__ = [
    "Skill", "XP_PER_LEVEL",
    "SkillGradeRule", "SKILL_GRADES",
    "skill_cap_for_job_level",
    "SkillTracker",
]
