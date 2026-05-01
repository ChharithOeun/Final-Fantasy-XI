"""Spell-family amplification — 3x base, 5x on Light chain.

Per INTERVENTION_MB.md the amplification table is:
    base 3.0x in window
    5.0x  if chain element matches Light

Direct-damage spells (Fire, Blizzard, etc) are NOT eligible — those
go through the offensive Magic Burst pipeline. The intervention
path covers heal/support/debuff/song/helix/geomancy/enmity-spike.
"""
from __future__ import annotations

import dataclasses
import enum


BASE_AMPLIFICATION: float = 3.0
LIGHT_AMPLIFICATION: float = 5.0


class SpellFamily(str, enum.Enum):
    """Eligibility families for the intervention path."""
    CURE = "cure"
    CURAGA = "curaga"
    NA_SPELL = "na_spell"            # Paralyna / Poisona / Silena / etc.
    ERASE = "erase"
    RDM_ENHANCING = "rdm_enhancing"
    BLM_DEBUFF = "blm_debuff"
    BRD_SONG = "brd_song"
    SCH_HELIX = "sch_helix"
    GEO_LUOPAN = "geo_luopan"        # special: radius doubling, not amp
    TANK_FLASH = "tank_flash"
    DIRECT_DAMAGE = "direct_damage"  # NOT eligible


def is_eligible(family: SpellFamily) -> bool:
    """Direct-damage spells use the offensive MB pipeline; reject."""
    return family != SpellFamily.DIRECT_DAMAGE


def amplification_for(family: SpellFamily, *, light_bonus: bool) -> float:
    """Return the multiplier to apply.

    GEO is special — its 'amplification' is luopan radius doubling
    (or tripling on Light), not effect amplification. Caller handles
    that branch separately; we still return a number so the call
    site can use it for radius scaling if it likes.
    """
    if not is_eligible(family):
        return 1.0
    if family == SpellFamily.GEO_LUOPAN:
        return 3.0 if light_bonus else 2.0     # radius doubling/tripling
    return LIGHT_AMPLIFICATION if light_bonus else BASE_AMPLIFICATION


def apply_amplification(*,
                            family: SpellFamily,
                            base_effect: float,
                            light_bonus: bool) -> float:
    """Apply the amplifier to a base effect value.

    For heal/buff potency: the result is the new applied effect.
    For GEO: the caller treats the result as a radius scalar.
    """
    if base_effect < 0:
        raise ValueError("base_effect must be non-negative")
    return base_effect * amplification_for(family, light_bonus=light_bonus)
