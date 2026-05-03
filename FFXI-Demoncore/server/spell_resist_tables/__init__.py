"""Spell resist tables — half/quarter/full resist resolution.

Sits between spell_casting and magic_damage_formula. The caster's
magic accuracy is rolled against the target's magic evasion + the
spell's element-vs-affinity modifier; the outcome is a tier:

    NONE      — full damage
    HALF      — 50% damage
    QUARTER   — 25% damage
    EIGHTH    — 12.5% damage
    FULL_RESIST — 0 damage (rare)

The caller multiplies their base spell damage by the returned
multiplier; the resolution also exposes the underlying roll so
status-effect duration mods can scale.

Inputs
------
* caster_magic_accuracy
* target_magic_evasion
* spell_element (FIRE / ICE / WIND / EARTH / LIGHTNING / WATER /
                  LIGHT / DARK)
* target_element_affinity (per element: -100..+100; positive =
  resists that element)
* target_silenced (silenced targets cast nothing AND resist
  worse — magic accuracy still rolls)
* target_dispelled_buffs (some buffs grant resist; gone if
  dispelled)
* spell_is_enfeeble (status spells use a separate threshold)

Resolution
----------
1) Compute effective_magic_accuracy = caster_acc - target_eva
   - element_affinity (positive affinity helps the target)
   + dispelled_buff_bonus
2) Roll d100 vs effective_magic_accuracy:
   - >= 95 always lands NONE (no resist) — spell pierces
   - <= 5 always FULL_RESIST — natural fizzle
   - else resist tier picked by margin

Public surface
--------------
    Element enum
    ResistTier enum
    ResistContext dataclass
    ResistResolution dataclass
    resolve_resist(context, rng) -> ResistResolution
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# Cast outcome multipliers
_TIER_MULT: dict["ResistTier", float] = {}

# Default magic accuracy bonus for unbuffed casters (so even
# "no buff" casters don't sit at 0 acc).
DEFAULT_MAGIC_ACCURACY = 100
DEFAULT_MAGIC_EVASION = 100

# Element-vs-affinity coefficient — the "weight" affinity has on
# the resist roll. 1.0 = each affinity point shifts roll by 1.
AFFINITY_TO_ROLL = 1.0


class Element(str, enum.Enum):
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


class ResistTier(str, enum.Enum):
    NONE = "none"             # no resist; full damage
    HALF = "half"
    QUARTER = "quarter"
    EIGHTH = "eighth"
    FULL_RESIST = "full_resist"


_TIER_MULT = {
    ResistTier.NONE: 1.0,
    ResistTier.HALF: 0.5,
    ResistTier.QUARTER: 0.25,
    ResistTier.EIGHTH: 0.125,
    ResistTier.FULL_RESIST: 0.0,
}


def multiplier_for_tier(tier: ResistTier) -> float:
    return _TIER_MULT[tier]


@dataclasses.dataclass(frozen=True)
class ResistContext:
    caster_magic_accuracy: int = DEFAULT_MAGIC_ACCURACY
    target_magic_evasion: int = DEFAULT_MAGIC_EVASION
    spell_element: Element = Element.FIRE
    target_element_affinity: int = 0     # -100..100; +ve resists
    target_silenced: bool = False
    target_dispelled_buffs: int = 0      # buffs lost (each +5 acc)
    spell_is_enfeeble: bool = False


@dataclasses.dataclass(frozen=True)
class ResistResolution:
    tier: ResistTier
    multiplier: float
    effective_magic_accuracy: int
    roll: int
    notes: str = ""


def _effective_acc(ctx: ResistContext) -> int:
    base = ctx.caster_magic_accuracy - ctx.target_magic_evasion
    base -= int(ctx.target_element_affinity * AFFINITY_TO_ROLL)
    base += ctx.target_dispelled_buffs * 5
    if ctx.target_silenced and not ctx.spell_is_enfeeble:
        # Silenced targets are mostly free real estate
        base += 20
    return base


def _tier_from_margin(
    *, roll: int, effective_acc: int,
    is_enfeeble: bool,
) -> ResistTier:
    """Convert (roll, effective_acc) into a tier.

    Damage spells: margin >= 0 -> NONE; -10..0 -> HALF;
    -25..-11 -> QUARTER; -50..-26 -> EIGHTHS; <-50 -> FULL.

    Enfeebles (status spells) are stricter — same margins map one
    tier worse. (FFXI canonically: enfeebles have a separate
    fail/half-effect curve; we approximate.)
    """
    margin = effective_acc - roll
    if not is_enfeeble:
        if margin >= 0:
            return ResistTier.NONE
        if margin >= -10:
            return ResistTier.HALF
        if margin >= -25:
            return ResistTier.QUARTER
        if margin >= -50:
            return ResistTier.EIGHTH
        return ResistTier.FULL_RESIST
    # Enfeeble curve — one tier worse for same margin
    if margin >= 10:
        return ResistTier.NONE
    if margin >= 0:
        return ResistTier.HALF
    if margin >= -15:
        return ResistTier.QUARTER
    if margin >= -40:
        return ResistTier.EIGHTH
    return ResistTier.FULL_RESIST


def resolve_resist(
    *, context: ResistContext,
    rng: t.Optional[random.Random] = None,
) -> ResistResolution:
    rng = rng or random.Random()
    eff_acc = _effective_acc(context)
    roll = rng.randint(1, 100)
    # Always-pierce / always-fizzle bands
    if roll >= 95:
        return ResistResolution(
            tier=ResistTier.NONE,
            multiplier=1.0,
            effective_magic_accuracy=eff_acc,
            roll=roll,
            notes="natural pierce",
        )
    if roll <= 5:
        return ResistResolution(
            tier=ResistTier.FULL_RESIST,
            multiplier=0.0,
            effective_magic_accuracy=eff_acc,
            roll=roll,
            notes="natural fizzle",
        )
    tier = _tier_from_margin(
        roll=roll, effective_acc=eff_acc,
        is_enfeeble=context.spell_is_enfeeble,
    )
    return ResistResolution(
        tier=tier,
        multiplier=multiplier_for_tier(tier),
        effective_magic_accuracy=eff_acc,
        roll=roll,
    )


__all__ = [
    "DEFAULT_MAGIC_ACCURACY", "DEFAULT_MAGIC_EVASION",
    "AFFINITY_TO_ROLL",
    "Element", "ResistTier",
    "multiplier_for_tier",
    "ResistContext", "ResistResolution",
    "resolve_resist",
]
