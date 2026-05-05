"""Tide & currents — global underwater rhythm.

Two coupled cycles drive the underwater world's tempo:

TIDE PHASE — short cycle, 6 in-game hours per phase:
    HIGH        - water at peak, shallow zones flooded
    MID_FALLING - water dropping
    LOW         - water at trough, certain caves expose
    MID_RISING  - water rising back

SPRING/NEAP — long cycle, 28 in-game days:
    SPRING tide every ~14 days = stronger HIGH/LOW extremes;
    NEAP tide between = flatter cycle. SPRING tides at LOW
    are when "tide-locked" zones (caves, sea-floor entrances)
    open up — NM windows and quest gates anchor here.

CURRENTS — per-zone vector field. Sub speed is modified by
its alignment with the local current. Calling current_at
returns the (dx, dy, dz) push for a given zone+band; the
calling code is expected to apply this to its own physics.

Public surface
--------------
    TidePhase enum
    LongPhase enum (SPRING/NEAP)
    Current dataclass (frozen)
    TideCurrents
        .register_zone(zone_id, current_by_band)
        .phase_at(now_game_hours) -> TidePhase
        .long_phase_at(now_game_hours) -> LongPhase
        .tide_modifier(now_game_hours) -> float (0..1.5)
        .current_at(zone_id, band) -> Optional[Current]
        .is_spring_low(now_game_hours) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TidePhase(str, enum.Enum):
    HIGH = "high"
    MID_FALLING = "mid_falling"
    LOW = "low"
    MID_RISING = "mid_rising"


class LongPhase(str, enum.Enum):
    SPRING = "spring"
    NEAP = "neap"


# 6 game-hours per tide phase => 24-hour full cycle
HOURS_PER_TIDE_PHASE = 6
HOURS_PER_TIDE_CYCLE = HOURS_PER_TIDE_PHASE * 4
# spring/neap alternate every 14 game-days
HOURS_PER_LONG_PHASE = 14 * 24

_TIDE_ORDER = (
    TidePhase.HIGH,
    TidePhase.MID_FALLING,
    TidePhase.LOW,
    TidePhase.MID_RISING,
)


@dataclasses.dataclass(frozen=True)
class Current:
    dx: float
    dy: float
    dz: float


@dataclasses.dataclass
class TideCurrents:
    # zone_id -> {band: Current}
    _currents: dict[str, dict[int, Current]] = dataclasses.field(
        default_factory=dict,
    )

    def register_zone(
        self, *, zone_id: str,
        current_by_band: dict[int, Current],
    ) -> bool:
        if not zone_id:
            return False
        self._currents[zone_id] = dict(current_by_band)
        return True

    def phase_at(
        self, *, now_game_hours: int,
    ) -> TidePhase:
        idx = (now_game_hours // HOURS_PER_TIDE_PHASE) % 4
        return _TIDE_ORDER[idx]

    def long_phase_at(
        self, *, now_game_hours: int,
    ) -> LongPhase:
        idx = (now_game_hours // HOURS_PER_LONG_PHASE) % 2
        return LongPhase.SPRING if idx == 0 else LongPhase.NEAP

    def tide_modifier(
        self, *, now_game_hours: int,
    ) -> float:
        # peak = 1.5 at spring HIGH; trough = 0.5 at spring LOW;
        # neap flattens both toward 1.0
        phase = self.phase_at(now_game_hours=now_game_hours)
        long_phase = self.long_phase_at(now_game_hours=now_game_hours)
        amp = 0.5 if long_phase == LongPhase.SPRING else 0.2
        if phase == TidePhase.HIGH:
            return 1.0 + amp
        if phase == TidePhase.LOW:
            return 1.0 - amp
        return 1.0

    def current_at(
        self, *, zone_id: str, band: int,
    ) -> t.Optional[Current]:
        zone = self._currents.get(zone_id)
        if zone is None:
            return None
        return zone.get(band)

    def is_spring_low(
        self, *, now_game_hours: int,
    ) -> bool:
        return (
            self.phase_at(now_game_hours=now_game_hours) == TidePhase.LOW
            and self.long_phase_at(
                now_game_hours=now_game_hours,
            ) == LongPhase.SPRING
        )


__all__ = [
    "TidePhase", "LongPhase", "Current", "TideCurrents",
    "HOURS_PER_TIDE_PHASE", "HOURS_PER_TIDE_CYCLE",
    "HOURS_PER_LONG_PHASE",
]
