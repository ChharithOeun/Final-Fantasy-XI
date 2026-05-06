"""Campfire system — light + cook + sleep-quality.

A campfire is the survivor's everything: warm zone of
+30 exposure (offsets cold), 8-yalm illumination radius,
cooking station for raw food, and a sleep-quality booster
that lifts a BEDROLL location to 60% (between BEDROLL
and INN).

A fire has fuel (wood) that burns down per tick. Adding
wood extends the timer. When fuel hits 0, the fire dies
and all benefits drop.

Public surface
--------------
    CampfireState dataclass (mutable)
    CampfireSystem
        .build_fire(fire_id, zone_id, position,
                    initial_fuel, started_at) -> bool
        .add_wood(fire_id, fuel_added) -> int
        .tick(fire_id, dt_seconds, now_seconds) -> int
        .extinguish(fire_id) -> bool
        .is_lit(fire_id, now_seconds) -> bool
        .warmth_offset(fire_id, distance_yalms) -> int
        .cook(fire_id, food_kind) -> str
"""
from __future__ import annotations

import dataclasses
import typing as t


_DEFAULT_FUEL_PER_SEC = 1
_WARMTH_RADIUS = 8
_LIGHT_RADIUS = 8
_FULL_WARMTH = 30


@dataclasses.dataclass
class CampfireState:
    fire_id: str
    zone_id: str
    position: tuple[float, float, float]
    fuel_remaining: int
    started_at: int


@dataclasses.dataclass
class CampfireSystem:
    _fires: dict[str, CampfireState] = dataclasses.field(
        default_factory=dict,
    )
    _fuel_per_sec: int = _DEFAULT_FUEL_PER_SEC

    def build_fire(
        self, *, fire_id: str, zone_id: str,
        position: tuple[float, float, float],
        initial_fuel: int, started_at: int,
    ) -> bool:
        if not fire_id or not zone_id:
            return False
        if initial_fuel <= 0:
            return False
        if fire_id in self._fires:
            return False
        self._fires[fire_id] = CampfireState(
            fire_id=fire_id, zone_id=zone_id,
            position=position, fuel_remaining=initial_fuel,
            started_at=started_at,
        )
        return True

    def add_wood(
        self, *, fire_id: str, fuel_added: int,
    ) -> int:
        f = self._fires.get(fire_id)
        if f is None:
            return 0
        if fuel_added <= 0:
            return f.fuel_remaining
        f.fuel_remaining += fuel_added
        return f.fuel_remaining

    def tick(
        self, *, fire_id: str, dt_seconds: int,
        now_seconds: int,
    ) -> int:
        f = self._fires.get(fire_id)
        if f is None:
            return 0
        if dt_seconds <= 0:
            return f.fuel_remaining
        spent = dt_seconds * self._fuel_per_sec
        f.fuel_remaining = max(0, f.fuel_remaining - spent)
        if f.fuel_remaining == 0:
            del self._fires[fire_id]
            return 0
        return f.fuel_remaining

    def extinguish(self, *, fire_id: str) -> bool:
        if fire_id not in self._fires:
            return False
        del self._fires[fire_id]
        return True

    def is_lit(
        self, *, fire_id: str, now_seconds: int,
    ) -> bool:
        return fire_id in self._fires

    def warmth_offset(
        self, *, fire_id: str, distance_yalms: int,
    ) -> int:
        if fire_id not in self._fires:
            return 0
        if distance_yalms < 0:
            distance_yalms = 0
        if distance_yalms > _WARMTH_RADIUS:
            return 0
        # linear falloff
        scale = (_WARMTH_RADIUS - distance_yalms) / _WARMTH_RADIUS
        return int(_FULL_WARMTH * scale)

    def light_radius(
        self, *, fire_id: str,
    ) -> int:
        if fire_id not in self._fires:
            return 0
        return _LIGHT_RADIUS

    def cook(
        self, *, fire_id: str, food_kind: str,
    ) -> str:
        if fire_id not in self._fires:
            return ""
        if not food_kind:
            return ""
        if food_kind.startswith("raw_"):
            return "cooked_" + food_kind[4:]
        # already cooked or unknown
        return food_kind


__all__ = ["CampfireState", "CampfireSystem"]
