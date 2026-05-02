"""Spell catalog — WHM/BLM/RDM/etc spell list with cost + level.

Each spell has element, MP cost, target type (single/aoe/self),
caster level requirements per job, base cast time, base recast.

Public surface
--------------
    Element enum
    TargetType enum
    SpellSchool enum (Healing/Elemental/Enfeebling/etc)
    Spell catalog with ~30 sample spells
    spells_for_job_at_level(job, level) -> tuple[Spell, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Element(str, enum.Enum):
    NONE = "none"
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


class TargetType(str, enum.Enum):
    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    AOE_ALLY = "aoe_ally"
    AOE_ENEMY = "aoe_enemy"


class SpellSchool(str, enum.Enum):
    HEALING = "healing"
    ENHANCING = "enhancing"
    ENFEEBLING = "enfeebling"
    ELEMENTAL = "elemental"
    DARK = "dark"
    DIVINE = "divine"
    SUMMONING = "summoning"
    NINJUTSU = "ninjutsu"
    SONG = "song"
    BLUE = "blue"
    GEOMANCY = "geomancy"


@dataclasses.dataclass(frozen=True)
class JobLevelGate:
    job: str
    min_level: int


@dataclasses.dataclass(frozen=True)
class Spell:
    spell_id: str
    label: str
    element: Element
    school: SpellSchool
    target: TargetType
    mp_cost: int
    base_cast_seconds: float
    base_recast_seconds: float
    job_gates: tuple[JobLevelGate, ...]


# Sample catalog (representative ~30 spells)
SPELL_CATALOG: tuple[Spell, ...] = (
    # WHM Healing
    Spell("cure", "Cure", Element.LIGHT, SpellSchool.HEALING,
          TargetType.SINGLE_ALLY, mp_cost=8,
          base_cast_seconds=2.0, base_recast_seconds=5.0,
          job_gates=(JobLevelGate("white_mage", 1),
                     JobLevelGate("red_mage", 1))),
    Spell("cure_ii", "Cure II", Element.LIGHT, SpellSchool.HEALING,
          TargetType.SINGLE_ALLY, mp_cost=24,
          base_cast_seconds=2.5, base_recast_seconds=5.0,
          job_gates=(JobLevelGate("white_mage", 11),
                     JobLevelGate("red_mage", 14))),
    Spell("cure_iii", "Cure III", Element.LIGHT, SpellSchool.HEALING,
          TargetType.SINGLE_ALLY, mp_cost=46,
          base_cast_seconds=3.0, base_recast_seconds=5.0,
          job_gates=(JobLevelGate("white_mage", 21),
                     JobLevelGate("red_mage", 26))),
    Spell("cure_iv", "Cure IV", Element.LIGHT, SpellSchool.HEALING,
          TargetType.SINGLE_ALLY, mp_cost=88,
          base_cast_seconds=3.0, base_recast_seconds=5.0,
          job_gates=(JobLevelGate("white_mage", 41),
                     JobLevelGate("red_mage", 47))),
    Spell("cure_v", "Cure V", Element.LIGHT, SpellSchool.HEALING,
          TargetType.SINGLE_ALLY, mp_cost=135,
          base_cast_seconds=3.5, base_recast_seconds=5.0,
          job_gates=(JobLevelGate("white_mage", 61),)),
    Spell("curaga", "Curaga", Element.LIGHT, SpellSchool.HEALING,
          TargetType.AOE_ALLY, mp_cost=20,
          base_cast_seconds=2.5, base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 16),)),
    # BLM Elemental
    Spell("fire", "Fire", Element.FIRE, SpellSchool.ELEMENTAL,
          TargetType.SINGLE_ENEMY, mp_cost=15,
          base_cast_seconds=4.0, base_recast_seconds=15.0,
          job_gates=(JobLevelGate("black_mage", 4),
                     JobLevelGate("red_mage", 5))),
    Spell("fire_ii", "Fire II", Element.FIRE,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=37, base_cast_seconds=5.5,
          base_recast_seconds=20.0,
          job_gates=(JobLevelGate("black_mage", 19),)),
    Spell("fire_iii", "Fire III", Element.FIRE,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=89, base_cast_seconds=7.0,
          base_recast_seconds=30.0,
          job_gates=(JobLevelGate("black_mage", 39),)),
    Spell("fire_iv", "Fire IV", Element.FIRE,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=148, base_cast_seconds=8.0,
          base_recast_seconds=45.0,
          job_gates=(JobLevelGate("black_mage", 60),)),
    Spell("blizzard", "Blizzard", Element.ICE,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=18, base_cast_seconds=4.0,
          base_recast_seconds=15.0,
          job_gates=(JobLevelGate("black_mage", 7),)),
    Spell("thunder", "Thunder", Element.LIGHTNING,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=23, base_cast_seconds=4.0,
          base_recast_seconds=15.0,
          job_gates=(JobLevelGate("black_mage", 13),)),
    Spell("stone", "Stone", Element.EARTH,
          SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
          mp_cost=6, base_cast_seconds=4.0,
          base_recast_seconds=15.0,
          job_gates=(JobLevelGate("black_mage", 1),
                     JobLevelGate("red_mage", 3))),
    # Enhancing
    Spell("protect", "Protect", Element.LIGHT,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=12, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 7),
                     JobLevelGate("red_mage", 8),
                     JobLevelGate("paladin", 17))),
    Spell("shell", "Shell", Element.WIND,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=18, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 17),
                     JobLevelGate("red_mage", 19))),
    Spell("haste", "Haste", Element.WIND,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=30, base_cast_seconds=4.0,
          base_recast_seconds=20.0,
          job_gates=(JobLevelGate("white_mage", 40),
                     JobLevelGate("red_mage", 38))),
    Spell("regen", "Regen", Element.LIGHT,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=15, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 21),
                     JobLevelGate("red_mage", 23))),
    Spell("refresh", "Refresh", Element.WIND,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=29, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("red_mage", 41),)),
    # Enfeebling
    Spell("dia", "Dia", Element.LIGHT,
          SpellSchool.ENFEEBLING, TargetType.SINGLE_ENEMY,
          mp_cost=4, base_cast_seconds=1.5,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 1),
                     JobLevelGate("red_mage", 2),
                     JobLevelGate("paladin", 7))),
    Spell("paralyze", "Paralyze", Element.ICE,
          SpellSchool.ENFEEBLING, TargetType.SINGLE_ENEMY,
          mp_cost=10, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("red_mage", 11),
                     JobLevelGate("white_mage", 14))),
    Spell("slow", "Slow", Element.EARTH,
          SpellSchool.ENFEEBLING, TargetType.SINGLE_ENEMY,
          mp_cost=15, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("red_mage", 17),)),
    # Divine
    Spell("banish", "Banish", Element.LIGHT,
          SpellSchool.DIVINE, TargetType.SINGLE_ENEMY,
          mp_cost=8, base_cast_seconds=2.5,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 7),
                     JobLevelGate("paladin", 17))),
    Spell("holy", "Holy", Element.LIGHT,
          SpellSchool.DIVINE, TargetType.SINGLE_ENEMY,
          mp_cost=80, base_cast_seconds=4.0,
          base_recast_seconds=20.0,
          job_gates=(JobLevelGate("white_mage", 50),
                     JobLevelGate("paladin", 75))),
    # Dark
    Spell("bio", "Bio", Element.DARK,
          SpellSchool.DARK, TargetType.SINGLE_ENEMY,
          mp_cost=6, base_cast_seconds=2.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("dark_knight", 1),
                     JobLevelGate("red_mage", 14))),
    Spell("drain", "Drain", Element.DARK,
          SpellSchool.DARK, TargetType.SINGLE_ENEMY,
          mp_cost=18, base_cast_seconds=3.5,
          base_recast_seconds=60.0,
          job_gates=(JobLevelGate("dark_knight", 12),
                     JobLevelGate("red_mage", 33))),
    Spell("aspir", "Aspir", Element.DARK,
          SpellSchool.DARK, TargetType.SINGLE_ENEMY,
          mp_cost=8, base_cast_seconds=3.5,
          base_recast_seconds=60.0,
          job_gates=(JobLevelGate("dark_knight", 22),
                     JobLevelGate("red_mage", 36))),
    # Utility
    Spell("warp", "Warp", Element.NONE,
          SpellSchool.ENHANCING, TargetType.SELF,
          mp_cost=22, base_cast_seconds=10.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("black_mage", 17),
                     JobLevelGate("red_mage", 24))),
    Spell("sneak", "Sneak", Element.WIND,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=8, base_cast_seconds=2.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 25),
                     JobLevelGate("red_mage", 27))),
    Spell("invisible", "Invisible", Element.WIND,
          SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
          mp_cost=10, base_cast_seconds=3.0,
          base_recast_seconds=10.0,
          job_gates=(JobLevelGate("white_mage", 30),
                     JobLevelGate("red_mage", 32))),
)


SPELL_BY_ID: dict[str, Spell] = {s.spell_id: s for s in SPELL_CATALOG}


def spells_for_job_at_level(
    *, job: str, level: int,
) -> tuple[Spell, ...]:
    out = []
    for s in SPELL_CATALOG:
        for gate in s.job_gates:
            if gate.job == job and gate.min_level <= level:
                out.append(s)
                break
    return tuple(out)


def can_cast(*, spell_id: str, job: str, level: int) -> bool:
    spell = SPELL_BY_ID.get(spell_id)
    if spell is None:
        return False
    for gate in spell.job_gates:
        if gate.job == job and gate.min_level <= level:
            return True
    return False


__all__ = [
    "Element", "TargetType", "SpellSchool",
    "JobLevelGate", "Spell",
    "SPELL_CATALOG", "SPELL_BY_ID",
    "spells_for_job_at_level", "can_cast",
]
