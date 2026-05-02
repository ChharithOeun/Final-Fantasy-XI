"""Tier-VI spell scrolls — post-Master-Level magic.

The existing spell_catalog covers spells through Cure V / Fire IV /
Stone V — the canonical 99-cap meta. At ML 100-150 a caster needs
spells that scale with the new HP/MP pools and the +51 hard-stat
ceiling Master Levels grant. This module adds the next tier on
top of that catalog without disturbing the existing data.

Drop sources
------------
Each tier-VI spell is a single-use scroll learned by trade. Drops
are R/EX from:
* Shadow Genkai bosses (the 11 Fomor Lords, see shadow_genkai)
* Elite Fomor mobs in the unreleased shadow zones (high-tier
  Fomor Warlords, Mages, etc.)

Drop catalog is a separate concern (lives in loot_table); this
module owns the spell definitions and the gate logic.

Public surface
--------------
    TIER_VI_SPELLS — tuple of Spell entries
    TIER_VI_BY_ID
    is_tier_vi(spell_id) -> bool
    spell_for_replacement(canonical_spell_id) -> Optional[Spell]
        (e.g. cure_v -> cure_vi)
    skill_cap_required(spell_id) -> int
"""
from __future__ import annotations

import typing as t

from server.spell_catalog import (
    Element,
    JobLevelGate,
    Spell,
    SpellSchool,
    TargetType,
)


# Tier-VI spells require a job level above 99 (i.e. ML > 0). The
# minimum main-job level encodes the Master Level milestone the
# spell unlocks at: 100, 105, 110, etc.
#
# Each tier-VI spell also requires post-99 skill points. The
# skill cap formula in master_levels gives +5 cap per ML, so
# even at lvl 100 a player can have skill 354 — well above the
# "needs 360" threshold these spells use.

# MP costs are tuned for the new MP pools: a lvl 150 RDM has
# +765 MP from MLs alone (15 per ML * 51 levels). Tier-VI MP
# costs sit at roughly 1.5x the corresponding tier-V cost.

TIER_VI_SPELLS: tuple[Spell, ...] = (
    # ---- Healing ----------------------------------------------------
    Spell(
        "cure_vi", "Cure VI", Element.LIGHT, SpellSchool.HEALING,
        TargetType.SINGLE_ALLY, mp_cost=130,
        base_cast_seconds=4.0, base_recast_seconds=12.0,
        job_gates=(
            JobLevelGate("white_mage", 100),
            JobLevelGate("red_mage", 110),
        ),
    ),
    Spell(
        "curaga_v", "Curaga V", Element.LIGHT, SpellSchool.HEALING,
        TargetType.AOE_ALLY, mp_cost=180,
        base_cast_seconds=5.0, base_recast_seconds=15.0,
        job_gates=(JobLevelGate("white_mage", 110),),
    ),
    # ---- Elemental nukes (existing meta tops at IV/V; bump to V/VI) -
    Spell(
        "fire_v", "Fire V", Element.FIRE, SpellSchool.ELEMENTAL,
        TargetType.SINGLE_ENEMY, mp_cost=240,
        base_cast_seconds=8.0, base_recast_seconds=30.0,
        job_gates=(
            JobLevelGate("black_mage", 105),
            JobLevelGate("red_mage", 130),
        ),
    ),
    Spell(
        "blizzard_v", "Blizzard V", Element.ICE,
        SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
        mp_cost=240, base_cast_seconds=8.0, base_recast_seconds=30.0,
        job_gates=(JobLevelGate("black_mage", 105),),
    ),
    Spell(
        "thunder_v", "Thunder V", Element.LIGHTNING,
        SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
        mp_cost=260, base_cast_seconds=8.0, base_recast_seconds=30.0,
        job_gates=(JobLevelGate("black_mage", 110),),
    ),
    Spell(
        "stone_vi", "Stone VI", Element.EARTH,
        SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
        mp_cost=220, base_cast_seconds=7.0, base_recast_seconds=28.0,
        job_gates=(JobLevelGate("black_mage", 115),),
    ),
    Spell(
        "aero_v", "Aero V", Element.WIND,
        SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
        mp_cost=220, base_cast_seconds=7.0, base_recast_seconds=28.0,
        job_gates=(JobLevelGate("black_mage", 115),),
    ),
    Spell(
        "water_v", "Water V", Element.WATER,
        SpellSchool.ELEMENTAL, TargetType.SINGLE_ENEMY,
        mp_cost=240, base_cast_seconds=8.0, base_recast_seconds=30.0,
        job_gates=(JobLevelGate("black_mage", 120),),
    ),
    # ---- Divine -----------------------------------------------------
    Spell(
        "holy_ii", "Holy II", Element.LIGHT, SpellSchool.DIVINE,
        TargetType.SINGLE_ENEMY, mp_cost=200,
        base_cast_seconds=8.0, base_recast_seconds=60.0,
        job_gates=(
            JobLevelGate("white_mage", 110),
            JobLevelGate("paladin", 130),
        ),
    ),
    Spell(
        "banishga_iii", "Banishga III", Element.LIGHT,
        SpellSchool.DIVINE, TargetType.AOE_ENEMY,
        mp_cost=160, base_cast_seconds=5.0, base_recast_seconds=30.0,
        job_gates=(JobLevelGate("white_mage", 120),),
    ),
    # ---- Dark / debuffs ---------------------------------------------
    Spell(
        "bio_iv", "Bio IV", Element.DARK, SpellSchool.DARK,
        TargetType.SINGLE_ENEMY, mp_cost=80,
        base_cast_seconds=3.0, base_recast_seconds=20.0,
        job_gates=(
            JobLevelGate("black_mage", 110),
            JobLevelGate("dark_knight", 115),
            JobLevelGate("scholar", 120),
        ),
    ),
    Spell(
        "dia_iv", "Dia IV", Element.LIGHT, SpellSchool.ENFEEBLING,
        TargetType.SINGLE_ENEMY, mp_cost=80,
        base_cast_seconds=3.0, base_recast_seconds=20.0,
        job_gates=(
            JobLevelGate("white_mage", 110),
            JobLevelGate("paladin", 125),
        ),
    ),
    Spell(
        "drain_iii", "Drain III", Element.DARK, SpellSchool.DARK,
        TargetType.SINGLE_ENEMY, mp_cost=120,
        base_cast_seconds=5.0, base_recast_seconds=60.0,
        job_gates=(JobLevelGate("dark_knight", 120),),
    ),
    Spell(
        "aspir_iii", "Aspir III", Element.DARK, SpellSchool.DARK,
        TargetType.SINGLE_ENEMY, mp_cost=80,
        base_cast_seconds=4.0, base_recast_seconds=45.0,
        job_gates=(JobLevelGate("dark_knight", 125),),
    ),
    # ---- Enhancing --------------------------------------------------
    Spell(
        "haste_ii", "Haste II", Element.WIND,
        SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
        mp_cost=80, base_cast_seconds=4.0, base_recast_seconds=15.0,
        job_gates=(
            JobLevelGate("white_mage", 110),
            JobLevelGate("red_mage", 115),
        ),
    ),
    Spell(
        "refresh_iii", "Refresh III", Element.WIND,
        SpellSchool.ENHANCING, TargetType.SINGLE_ALLY,
        mp_cost=46, base_cast_seconds=4.0, base_recast_seconds=10.0,
        job_gates=(JobLevelGate("red_mage", 120),),
    ),
)


TIER_VI_BY_ID: dict[str, Spell] = {s.spell_id: s for s in TIER_VI_SPELLS}


# Mapping from canonical-cap spell -> tier-VI replacement, so callers
# upgrading a UI macro can easily resolve "what's my best tier."
_REPLACEMENT_MAP: dict[str, str] = {
    "cure_v": "cure_vi",
    "curaga_iv": "curaga_v",
    "fire_iv": "fire_v",
    "blizzard_iv": "blizzard_v",
    "thunder_iv": "thunder_v",
    "stone_v": "stone_vi",
    "aero_iv": "aero_v",
    "water_iv": "water_v",
    "holy": "holy_ii",
    "banishga_ii": "banishga_iii",
    "bio_iii": "bio_iv",
    "dia_iii": "dia_iv",
    "drain_ii": "drain_iii",
    "aspir_ii": "aspir_iii",
    "haste": "haste_ii",
    "refresh_ii": "refresh_iii",
}


# Each tier-VI spell additionally requires this much skill in its
# school (combat/magic skills get a +5 cap per ML; players will
# meet these caps at the same ML the spell becomes available).
_SKILL_REQUIREMENTS: dict[str, int] = {
    "cure_vi": 360,
    "curaga_v": 365,
    "fire_v": 360,
    "blizzard_v": 360,
    "thunder_v": 365,
    "stone_vi": 370,
    "aero_v": 370,
    "water_v": 375,
    "holy_ii": 365,
    "banishga_iii": 375,
    "bio_iv": 365,
    "dia_iv": 365,
    "drain_iii": 375,
    "aspir_iii": 380,
    "haste_ii": 365,
    "refresh_iii": 370,
}


def is_tier_vi(spell_id: str) -> bool:
    return spell_id in TIER_VI_BY_ID


def spell_for_replacement(canonical_spell_id: str) -> t.Optional[Spell]:
    """Given a canonical spell, return the tier-VI replacement (or None)."""
    new_id = _REPLACEMENT_MAP.get(canonical_spell_id)
    if new_id is None:
        return None
    return TIER_VI_BY_ID.get(new_id)


def skill_cap_required(spell_id: str) -> int:
    """Magic skill required to land tier-VI without resists. Returns
    0 for non-tier-VI spells (no special requirement)."""
    return _SKILL_REQUIREMENTS.get(spell_id, 0)


__all__ = [
    "TIER_VI_SPELLS", "TIER_VI_BY_ID",
    "is_tier_vi", "spell_for_replacement",
    "skill_cap_required",
]
