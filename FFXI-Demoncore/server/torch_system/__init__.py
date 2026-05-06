"""Torch system — light sources with fuel + radius.

Walking into a cave at night without a torch should feel
different than walking with one. The torch_system tracks
per-player active light sources, their fuel remaining,
their illumination radius, and the consumption rate.

Light sources have a kind that determines:
    - max_fuel_seconds   how long it lasts when full
    - radius             yalms of usable light
    - consumption_per_sec normally 1, but wet conditions
                         double it

Public surface
--------------
    LightSourceKind enum
    LightProfile dataclass (frozen) — per-kind config
    LightSession dataclass (mutable) — active light state
    TorchSystem
        .define_kind(kind, max_fuel_seconds, radius,
                     consumption_per_sec) -> bool
        .light(player_id, kind, started_at) -> bool
        .extinguish(player_id, now_seconds) -> int    (fuel returned)
        .tick(player_id, dt_seconds, now_seconds, wet=False)
            -> int     (fuel remaining)
        .visible_radius(player_id, now_seconds) -> int
        .is_lit(player_id, now_seconds) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LightSourceKind(str, enum.Enum):
    BASIC_TORCH = "basic_torch"
    LANTERN = "lantern"
    OIL_LAMP = "oil_lamp"
    FAERIE_LIGHT = "faerie_light"     # mage spell, no fuel
    FOMOR_BRAZIER = "fomor_brazier"   # KI, no fuel


_BUILTIN_PROFILES = {
    LightSourceKind.BASIC_TORCH: (300, 8),     # 5 min, 8 yalms
    LightSourceKind.LANTERN: (1800, 12),       # 30 min, 12 yalms
    LightSourceKind.OIL_LAMP: (3600, 15),      # 60 min, 15 yalms
    LightSourceKind.FAERIE_LIGHT: (180, 20),   # 3 min, 20 yalms
    LightSourceKind.FOMOR_BRAZIER: (-1, 25),   # infinite, 25 yalms
}


@dataclasses.dataclass(frozen=True)
class LightProfile:
    kind: LightSourceKind
    max_fuel_seconds: int     # -1 = infinite
    radius_yalms: int
    consumption_per_sec: int


@dataclasses.dataclass
class LightSession:
    player_id: str
    kind: LightSourceKind
    fuel_remaining: int
    started_at: int


@dataclasses.dataclass
class TorchSystem:
    _profiles: dict[LightSourceKind, LightProfile] = dataclasses.field(
        default_factory=dict,
    )
    _sessions: dict[str, LightSession] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        # seed built-in profiles
        for kind, (mfs, rad) in _BUILTIN_PROFILES.items():
            self._profiles[kind] = LightProfile(
                kind=kind,
                max_fuel_seconds=mfs,
                radius_yalms=rad,
                consumption_per_sec=1,
            )

    def define_kind(
        self, *, kind: LightSourceKind,
        max_fuel_seconds: int, radius_yalms: int,
        consumption_per_sec: int = 1,
    ) -> bool:
        if max_fuel_seconds == 0:
            return False
        if radius_yalms <= 0:
            return False
        if consumption_per_sec <= 0:
            return False
        self._profiles[kind] = LightProfile(
            kind=kind, max_fuel_seconds=max_fuel_seconds,
            radius_yalms=radius_yalms,
            consumption_per_sec=consumption_per_sec,
        )
        return True

    def light(
        self, *, player_id: str,
        kind: LightSourceKind, started_at: int,
    ) -> bool:
        if not player_id:
            return False
        if kind not in self._profiles:
            return False
        if player_id in self._sessions:
            return False  # already lit
        prof = self._profiles[kind]
        fuel = prof.max_fuel_seconds
        if fuel == 0:
            return False
        self._sessions[player_id] = LightSession(
            player_id=player_id, kind=kind,
            fuel_remaining=fuel,    # -1 stays -1
            started_at=started_at,
        )
        return True

    def extinguish(
        self, *, player_id: str, now_seconds: int,
    ) -> int:
        s = self._sessions.pop(player_id, None)
        if s is None:
            return 0
        if s.fuel_remaining < 0:
            return -1
        return s.fuel_remaining

    def tick(
        self, *, player_id: str, dt_seconds: int,
        now_seconds: int, wet: bool = False,
    ) -> int:
        s = self._sessions.get(player_id)
        if s is None:
            return 0
        if s.fuel_remaining < 0:
            return -1   # infinite source
        prof = self._profiles[s.kind]
        rate = prof.consumption_per_sec
        if wet:
            rate *= 2
        spent = dt_seconds * rate
        s.fuel_remaining = max(0, s.fuel_remaining - spent)
        if s.fuel_remaining == 0:
            del self._sessions[player_id]
            return 0
        return s.fuel_remaining

    def visible_radius(
        self, *, player_id: str, now_seconds: int,
    ) -> int:
        s = self._sessions.get(player_id)
        if s is None:
            return 0
        prof = self._profiles[s.kind]
        return prof.radius_yalms

    def is_lit(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        return player_id in self._sessions

    def total_active(self) -> int:
        return len(self._sessions)


__all__ = [
    "LightSourceKind", "LightProfile", "LightSession",
    "TorchSystem",
]
