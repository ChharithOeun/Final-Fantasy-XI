"""Exposure damage — cold zones drain HP, hot zones drain MP.

The body has limits. Stand in a blizzard with no insulation
and you take HP damage per tick. Stand in lava-rock zones
under a high sun and your MP boils away. Insulation rating
on equipped clothing mitigates exposure.

Exposure level (computed by caller, this module just
applies):
    -100 .. -1   COLD (HP drain)
       0         neutral
       1 ..  100 HOT (MP drain)

Per tick, exposure converts to damage:
    abs(exposure) above 30 → enabling damage
    damage_per_sec = (abs(exposure) - 30) / 5  (rounded)
    HP damage if exposure < 0; MP damage if > 0
    damage halves if shelter_active is True

Public surface
--------------
    ExposureKind enum (NEUTRAL/COLD/HOT)
    ExposureResult dataclass (frozen)
    ExposureCalculator
        .compute(exposure_level, dt_seconds,
                 insulation_rating, shelter_active)
            -> ExposureResult
"""
from __future__ import annotations

import dataclasses
import enum


class ExposureKind(str, enum.Enum):
    NEUTRAL = "neutral"
    COLD = "cold"
    HOT = "hot"


_THRESHOLD = 30
_DIVISOR = 5


@dataclasses.dataclass(frozen=True)
class ExposureResult:
    kind: ExposureKind
    hp_damage: int
    mp_damage: int
    effective_exposure: int


@dataclasses.dataclass
class ExposureCalculator:

    def compute(
        self, *, exposure_level: int, dt_seconds: int,
        insulation_rating: int = 0,
        shelter_active: bool = False,
    ) -> ExposureResult:
        if dt_seconds <= 0:
            return ExposureResult(
                kind=ExposureKind.NEUTRAL,
                hp_damage=0, mp_damage=0,
                effective_exposure=exposure_level,
            )
        # insulation reduces magnitude
        magnitude = abs(exposure_level)
        if insulation_rating > 0:
            magnitude = max(0, magnitude - insulation_rating)
        sign = 1 if exposure_level > 0 else -1
        if magnitude == 0:
            return ExposureResult(
                kind=ExposureKind.NEUTRAL,
                hp_damage=0, mp_damage=0,
                effective_exposure=0,
            )
        eff = magnitude * sign
        if magnitude <= _THRESHOLD:
            kind = (
                ExposureKind.COLD if sign < 0
                else ExposureKind.HOT
            )
            return ExposureResult(
                kind=kind, hp_damage=0, mp_damage=0,
                effective_exposure=eff,
            )
        per_sec = (magnitude - _THRESHOLD) // _DIVISOR
        if per_sec <= 0:
            per_sec = 1
        if shelter_active:
            per_sec = max(1, per_sec // 2)
        total = per_sec * dt_seconds
        if sign < 0:
            return ExposureResult(
                kind=ExposureKind.COLD,
                hp_damage=total, mp_damage=0,
                effective_exposure=eff,
            )
        return ExposureResult(
            kind=ExposureKind.HOT,
            hp_damage=0, mp_damage=total,
            effective_exposure=eff,
        )


__all__ = ["ExposureKind", "ExposureResult", "ExposureCalculator"]
