"""Damage formula — canonical FFXI pDIF / cRatio.

The classic FFXI physical damage formula:

    base_damage = weapon_damage + fSTR
    cRatio = attacker_attack / target_defense
    pDIF = derived from cRatio with caps + variance
    final_damage = base_damage * pDIF * crit_multiplier

fSTR is computed from STR delta and weapon rank. cRatio determines
the pDIF range; cap depends on whether the attacker is a player or
mob (mobs cap higher).

Public surface
--------------
    DamageInputs dataclass
    compute_fstr(attacker_str, target_vit, weapon_rank) -> int
    compute_cratio(attack, defense) -> float
    pdif_range(cratio) -> tuple[low, high]
    compute_physical_damage(...) -> DamageResult
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.rng_pool import RngPool, STREAM_BOSS_CRITIC


@dataclasses.dataclass(frozen=True)
class DamageInputs:
    weapon_damage: int
    weapon_rank: int                  # 1-12, higher = more fSTR cap
    attacker_str: int
    attacker_attack: int
    attacker_dex: int
    target_vit: int
    target_defense: int
    target_agi: int
    is_critical: bool = False


def compute_fstr(
    *, attacker_str: int, target_vit: int, weapon_rank: int,
) -> int:
    """fSTR = floor((STR - VIT + 4) / 4), capped by weapon rank.
    Returns the bonus damage component."""
    delta = attacker_str - target_vit
    fstr = (delta + 4) // 4
    # Weapon rank caps the upside
    cap = max(weapon_rank, 1)
    return max(-cap, min(cap, fstr))


def compute_cratio(
    *, attack: int, defense: int,
) -> float:
    """cRatio = attack / defense. Capped at 4.0 for players,
    higher for mobs (we use 4.0 for our purposes)."""
    if defense <= 0:
        return 4.0
    return min(4.0, attack / defense)


def pdif_range(*, cratio: float) -> tuple[float, float]:
    """Min and max pDIF for the given cRatio. Linear approximation
    of the FFXI pDIF curve."""
    if cratio <= 0:
        return (0.0, 0.0)
    # Below 0.5: hugely penalized
    if cratio < 0.5:
        return (0.0, cratio * 1.5)
    if cratio < 1.0:
        return (cratio * 0.7, cratio * 1.2)
    if cratio < 2.0:
        return (cratio * 0.85, cratio * 1.3)
    # cap at 4.0
    cratio = min(4.0, cratio)
    return (cratio * 0.9, cratio * 1.35)


@dataclasses.dataclass(frozen=True)
class DamageResult:
    base_damage: int
    fstr: int
    cratio: float
    pdif: float
    final_damage: int
    was_critical: bool


def compute_physical_damage(
    *, inputs: DamageInputs, rng_pool: RngPool,
    stream_name: str = STREAM_BOSS_CRITIC,
) -> DamageResult:
    fstr = compute_fstr(
        attacker_str=inputs.attacker_str,
        target_vit=inputs.target_vit,
        weapon_rank=inputs.weapon_rank,
    )
    base = max(1, inputs.weapon_damage + fstr)
    cratio = compute_cratio(
        attack=inputs.attacker_attack,
        defense=inputs.target_defense,
    )
    low, high = pdif_range(cratio=cratio)
    rng = rng_pool.stream(stream_name)
    pdif = rng.uniform(low, high)
    if pdif < 0:
        pdif = 0.0
    final = int(base * pdif)
    if inputs.is_critical:
        # Crit doubles base then multiplies pdif
        final = int(base * 2 * pdif)
    return DamageResult(
        base_damage=base,
        fstr=fstr,
        cratio=cratio,
        pdif=pdif,
        final_damage=max(0, final),
        was_critical=inputs.is_critical,
    )


__all__ = [
    "DamageInputs", "DamageResult",
    "compute_fstr", "compute_cratio", "pdif_range",
    "compute_physical_damage",
]
