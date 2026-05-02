"""Parry / Block / Shield-block defensive rolls.

Canonical FFXI defense reactions, in order:
  1. Shadow image absorbs the hit (if any utsusemi up — handled
     elsewhere in nin_hand_signs)
  2. PARRY — weapon deflects the attack. Skill-based roll.
  3. BLOCK — shield catches it. Shield-skill + shield-rate roll.
  4. ABSORB — armor takes a fraction.

Order matters because each successful prior step short-circuits
the rest. We model parry, block, and shield-block here as a
single gate; absorb is handled by spell_shield + armor stats.

Public surface
--------------
    DefenseAttempt result
    parry_chance(skill, attacker_lvl) -> float
    block_chance(shield_size, shield_skill, attacker_lvl) -> float
    roll_defense(...) -> DefenseAttempt
    ShieldKind enum
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import STREAM_BOSS_CRITIC, RngPool


# Canonical caps
PARRY_BASE_CAP = 0.25         # 25% baseline cap
PARRY_HIGH_SKILL_CAP = 0.40   # 40% with capped parry skill
DUAL_WIELD_PARRY_PENALTY = 0.5  # halved when DW (no shield to compensate)


class ShieldKind(str, enum.Enum):
    NONE = "none"
    BUCKLER = "buckler"       # smallest, fastest
    ROUND = "round"           # standard medium
    KITE = "kite"             # larger
    TOWER = "tower"           # heaviest, PLD-only
    AEGIS = "aegis"           # relic, PLD-only
    OCHAIN = "ochain"         # relic, lockable PDT


# Block rate per shield kind (base, before skill mods)
_BASE_BLOCK_RATE: dict[ShieldKind, float] = {
    ShieldKind.NONE: 0.0,
    ShieldKind.BUCKLER: 0.30,
    ShieldKind.ROUND: 0.45,
    ShieldKind.KITE: 0.55,
    ShieldKind.TOWER: 0.65,
    ShieldKind.AEGIS: 0.55,
    ShieldKind.OCHAIN: 1.00,  # locked block
}


# Damage reduction on a successful block, percent
_BASE_BLOCK_DR: dict[ShieldKind, int] = {
    ShieldKind.NONE: 0,
    ShieldKind.BUCKLER: 30,
    ShieldKind.ROUND: 45,
    ShieldKind.KITE: 55,
    ShieldKind.TOWER: 65,
    ShieldKind.AEGIS: 70,
    ShieldKind.OCHAIN: 100,   # full mitigation when triggered
}


@dataclasses.dataclass(frozen=True)
class DefenseAttempt:
    parried: bool = False
    blocked: bool = False
    damage_reduction_pct: int = 0     # of incoming damage
    reason: t.Optional[str] = None    # debug helper for tests


def parry_chance(*, parry_skill: int, attacker_lvl: int,
                  dual_wielding: bool = False) -> float:
    """Probability the defender parries. Caps at PARRY_HIGH_SKILL_CAP
    once parry skill matches or exceeds attacker level * 4 + 100."""
    if parry_skill <= 0:
        return 0.0
    skill_threshold = attacker_lvl * 4 + 100
    if parry_skill >= skill_threshold:
        chance = PARRY_HIGH_SKILL_CAP
    else:
        chance = (parry_skill / max(skill_threshold, 1)) * PARRY_HIGH_SKILL_CAP
    chance = min(chance, PARRY_BASE_CAP if parry_skill < skill_threshold * 0.8
                  else PARRY_HIGH_SKILL_CAP)
    if dual_wielding:
        chance *= DUAL_WIELD_PARRY_PENALTY
    return chance


def block_chance(*, shield: ShieldKind, shield_skill: int,
                  attacker_lvl: int) -> float:
    """Probability the defender blocks with their shield."""
    base = _BASE_BLOCK_RATE.get(shield, 0.0)
    if base == 0.0:
        return 0.0
    if shield == ShieldKind.OCHAIN:
        return 1.0   # canonical Ochain is always-block
    skill_threshold = attacker_lvl * 4 + 100
    skill_factor = min(1.0, shield_skill / max(skill_threshold, 1))
    # Aegis gets a smooth scaling boost rather than the cliff
    return base * (0.5 + 0.5 * skill_factor)


def block_damage_reduction(*, shield: ShieldKind) -> int:
    return _BASE_BLOCK_DR.get(shield, 0)


def roll_defense(
    *, attacker_lvl: int,
    parry_skill: int, dual_wielding: bool,
    shield: ShieldKind, shield_skill: int,
    rng_pool: RngPool,
) -> DefenseAttempt:
    """One full defensive roll. Parry first, then block."""
    rng = rng_pool.stream(STREAM_BOSS_CRITIC)

    # PARRY ----------------------------------------------------------
    p_chance = parry_chance(
        parry_skill=parry_skill, attacker_lvl=attacker_lvl,
        dual_wielding=dual_wielding,
    )
    if rng.random() < p_chance:
        return DefenseAttempt(
            parried=True, damage_reduction_pct=100,
            reason="parry",
        )

    # BLOCK ----------------------------------------------------------
    b_chance = block_chance(
        shield=shield, shield_skill=shield_skill,
        attacker_lvl=attacker_lvl,
    )
    if rng.random() < b_chance:
        return DefenseAttempt(
            blocked=True,
            damage_reduction_pct=block_damage_reduction(shield=shield),
            reason="block",
        )

    return DefenseAttempt(reason="none")


__all__ = [
    "PARRY_BASE_CAP", "PARRY_HIGH_SKILL_CAP",
    "DUAL_WIELD_PARRY_PENALTY",
    "ShieldKind", "DefenseAttempt",
    "parry_chance", "block_chance", "block_damage_reduction",
    "roll_defense",
]
