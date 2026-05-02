"""Magic damage formula — INT-based with resistances + day/weather.

Canonical FFXI magic damage:

    base = spell_damage + (dINT * spell_int_factor)
    magic_attack_bonus_mult = 1 + MAB / 100
    target_resist = 1 / (2 ** resist_tier)
    day_modifier = 1.10 if matching element day, 0.90 if opposing
    weather_modifier = same idea
    magic_burst_mult = 1.30 if MB

    final = base * MAB * resist * day_mod * weather_mod * MB

Public surface
--------------
    MagicDamageInputs
    compute_dint(attacker_int, target_int) -> int
    resist_tier_to_multiplier(tier) -> float
    compute_magic_damage(...) -> MagicDamageResult
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class MagicDamageInputs:
    spell_base_damage: int           # before scaling
    spell_int_factor: float          # 1.0 = 1pt damage per dINT
    attacker_int: int
    target_int: int
    magic_attack_bonus_pct: int = 0  # MAB %
    magic_defense_bonus_pct: int = 0  # MDB on target
    resist_tier: int = 0             # 0 = no resist, 1 = 1/2,
                                      # 2 = 1/4, 3 = 1/8, 4 = full
    is_matching_day: bool = False
    is_opposing_day: bool = False
    is_matching_weather: bool = False
    is_opposing_weather: bool = False
    is_magic_burst: bool = False
    magic_burst_bonus_pct: int = 0


def compute_dint(*, attacker_int: int, target_int: int) -> int:
    """dINT = attacker INT - target INT, can be negative."""
    return attacker_int - target_int


def resist_tier_to_multiplier(*, tier: int) -> float:
    """0 = 1.0x, 1 = 0.5x, 2 = 0.25x, 3 = 0.125x, 4+ = 0.0x."""
    if tier <= 0:
        return 1.0
    if tier >= 4:
        return 0.0
    return 0.5 ** tier


@dataclasses.dataclass(frozen=True)
class MagicDamageResult:
    base_damage: int
    dint: int
    mab_multiplier: float
    resist_multiplier: float
    day_multiplier: float
    weather_multiplier: float
    burst_multiplier: float
    final_damage: int


def compute_magic_damage(
    *, inputs: MagicDamageInputs,
) -> MagicDamageResult:
    dint = compute_dint(
        attacker_int=inputs.attacker_int,
        target_int=inputs.target_int,
    )
    base_pre_int = inputs.spell_base_damage
    int_bonus = int(dint * inputs.spell_int_factor)
    base = max(0, base_pre_int + int_bonus)

    # MAB - MDB net
    net_mab = inputs.magic_attack_bonus_pct - \
        inputs.magic_defense_bonus_pct
    mab_mult = max(0.5, 1.0 + net_mab / 100.0)

    resist = resist_tier_to_multiplier(tier=inputs.resist_tier)

    day_mult = 1.0
    if inputs.is_matching_day:
        day_mult = 1.10
    elif inputs.is_opposing_day:
        day_mult = 0.90

    weather_mult = 1.0
    if inputs.is_matching_weather:
        weather_mult = 1.10
    elif inputs.is_opposing_weather:
        weather_mult = 0.90

    burst_mult = 1.0
    if inputs.is_magic_burst:
        burst_mult = 1.30 + inputs.magic_burst_bonus_pct / 100.0

    final = int(
        base * mab_mult * resist * day_mult * weather_mult * burst_mult,
    )
    return MagicDamageResult(
        base_damage=base,
        dint=dint,
        mab_multiplier=mab_mult,
        resist_multiplier=resist,
        day_multiplier=day_mult,
        weather_multiplier=weather_mult,
        burst_multiplier=burst_mult,
        final_damage=max(0, final),
    )


__all__ = [
    "MagicDamageInputs", "MagicDamageResult",
    "compute_dint", "resist_tier_to_multiplier",
    "compute_magic_damage",
]
