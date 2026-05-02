"""Healing magic — Cure I-V + Curaga + MND scaling.

Cure formula approximation:
    base = cure_base + (MND - 10) * mnd_factor + healing_skill / 2
    boost from Healing Magic skill above caster level
    +10% under Light Day
    +30% under Light Weather (or -30% under Dark)

Public surface
--------------
    CureSpec catalog (Cure I-V, Curaga I-V)
    compute_cure_amount(...) -> int
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class CureSpec:
    spell_id: str
    label: str
    base_amount: int
    mnd_factor: float
    is_aoe: bool = False


CURE_SPELLS: tuple[CureSpec, ...] = (
    CureSpec("cure", "Cure",     base_amount=20,
             mnd_factor=1.0),
    CureSpec("cure_ii", "Cure II", base_amount=80,
             mnd_factor=1.5),
    CureSpec("cure_iii", "Cure III", base_amount=200,
             mnd_factor=2.0),
    CureSpec("cure_iv", "Cure IV", base_amount=400,
             mnd_factor=2.5),
    CureSpec("cure_v", "Cure V", base_amount=700,
             mnd_factor=3.0),
    CureSpec("curaga", "Curaga", base_amount=80,
             mnd_factor=1.5, is_aoe=True),
    CureSpec("curaga_ii", "Curaga II", base_amount=200,
             mnd_factor=2.0, is_aoe=True),
    CureSpec("curaga_iii", "Curaga III", base_amount=400,
             mnd_factor=2.5, is_aoe=True),
    CureSpec("curaga_iv", "Curaga IV", base_amount=600,
             mnd_factor=3.0, is_aoe=True),
    CureSpec("curaga_v", "Curaga V", base_amount=900,
             mnd_factor=3.5, is_aoe=True),
)

CURE_BY_ID: dict[str, CureSpec] = {c.spell_id: c for c in CURE_SPELLS}


# Day modifiers
LIGHT_DAY_MULT = 1.10
DARK_DAY_MULT = 0.90
LIGHT_WEATHER_MULT = 1.30
DARK_WEATHER_MULT = 0.70


@dataclasses.dataclass(frozen=True)
class CureInputs:
    spell_id: str
    caster_mnd: int
    healing_magic_skill: int
    is_light_day: bool = False
    is_dark_day: bool = False
    is_light_weather: bool = False
    is_dark_weather: bool = False
    cure_potency_pct: int = 0     # gear bonus


@dataclasses.dataclass(frozen=True)
class CureResult:
    accepted: bool
    spell_id: str
    base_amount: int = 0
    mnd_bonus: int = 0
    skill_bonus: int = 0
    final_amount: int = 0
    reason: str = ""


def compute_cure_amount(*, inputs: CureInputs) -> CureResult:
    spec = CURE_BY_ID.get(inputs.spell_id)
    if spec is None:
        return CureResult(False, inputs.spell_id,
                          reason="unknown cure")
    mnd_bonus = int((inputs.caster_mnd - 10) * spec.mnd_factor)
    skill_bonus = inputs.healing_magic_skill // 2
    base = max(1, spec.base_amount + mnd_bonus + skill_bonus)

    mult = 1.0
    if inputs.is_light_day:
        mult *= LIGHT_DAY_MULT
    elif inputs.is_dark_day:
        mult *= DARK_DAY_MULT
    if inputs.is_light_weather:
        mult *= LIGHT_WEATHER_MULT
    elif inputs.is_dark_weather:
        mult *= DARK_WEATHER_MULT
    if inputs.cure_potency_pct:
        mult *= 1.0 + inputs.cure_potency_pct / 100.0

    final = int(base * mult)
    return CureResult(
        accepted=True,
        spell_id=spec.spell_id,
        base_amount=spec.base_amount,
        mnd_bonus=mnd_bonus,
        skill_bonus=skill_bonus,
        final_amount=final,
    )


__all__ = [
    "CureSpec", "CURE_SPELLS", "CURE_BY_ID",
    "LIGHT_DAY_MULT", "DARK_DAY_MULT",
    "LIGHT_WEATHER_MULT", "DARK_WEATHER_MULT",
    "CureInputs", "CureResult",
    "compute_cure_amount",
]
