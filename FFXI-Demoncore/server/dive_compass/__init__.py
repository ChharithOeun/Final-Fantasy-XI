"""Dive compass — bearing + depth + ascent warning.

The wayfinder_compass shows you a 2D bearing in surface
zones. Underwater you also need to know how far up or down
the target is. The dive compass extends bearing-distance
with a vertical delta and an ascent-rate warning when the
player is rising too fast (the FFXI version of decompression
sickness — surface too fast and you take damage).

Bands map to canonical depth meters:
    SURFACE  -> 0
    SHALLOW  -> 30
    MID      -> 100
    DEEP     -> 300
    ABYSSAL  -> 800

Players pin a target by absolute coords + band. The compass
returns:
    bearing_degrees      - 0=N, 90=E, etc.
    horizontal_distance  - 2D xy distance
    depth_delta_meters   - positive = target is below you
                           negative = target is above you
    ascent_warning       - true if the player's last reported
                           ascent rate exceeds MAX_SAFE_ASCENT

Public surface
--------------
    DiveBearing dataclass (frozen)
    DiveCompass
        .pin_target(player_id, x, y, band)
        .clear_pin(player_id)
        .bearing_for(player_id, current_x, current_y,
                     current_band) -> Optional[DiveBearing]
        .report_ascent(player_id, ascent_rate_m_per_s)
        .ascent_warning_for(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import math
import typing as t


# canonical depth in meters per band
BAND_DEPTH_M: dict[int, float] = {
    0: 0.0,      # SURFACE
    1: 30.0,     # SHALLOW
    2: 100.0,    # MID
    3: 300.0,    # DEEP
    4: 800.0,    # ABYSSAL
}


# rising faster than this for too long causes decompression
# damage in damage_physics; the compass surfaces a warning
# the moment the player crosses the threshold
MAX_SAFE_ASCENT_RATE_M_PER_S = 9.0


@dataclasses.dataclass(frozen=True)
class _PinnedTarget:
    x: float
    y: float
    band: int


@dataclasses.dataclass(frozen=True)
class DiveBearing:
    bearing_degrees: float
    horizontal_distance: float
    depth_delta_meters: float
    ascent_warning: bool


def _depth_of(band: int) -> float:
    return BAND_DEPTH_M.get(band, 0.0)


def _bearing_degrees(
    from_x: float, from_y: float,
    to_x: float, to_y: float,
) -> float:
    dx = to_x - from_x
    dy = to_y - from_y
    if dx == 0 and dy == 0:
        return 0.0
    # 0 = north (+y), 90 = east (+x)
    rad = math.atan2(dx, dy)
    deg = math.degrees(rad)
    return (deg + 360.0) % 360.0


@dataclasses.dataclass
class DiveCompass:
    _pins: dict[str, _PinnedTarget] = dataclasses.field(default_factory=dict)
    _ascent_warn: dict[str, bool] = dataclasses.field(default_factory=dict)

    def pin_target(
        self, *, player_id: str,
        x: float, y: float, band: int,
    ) -> bool:
        if not player_id:
            return False
        if band not in BAND_DEPTH_M:
            return False
        self._pins[player_id] = _PinnedTarget(x=x, y=y, band=band)
        return True

    def clear_pin(self, *, player_id: str) -> bool:
        return self._pins.pop(player_id, None) is not None

    def bearing_for(
        self, *, player_id: str,
        current_x: float, current_y: float,
        current_band: int,
    ) -> t.Optional[DiveBearing]:
        target = self._pins.get(player_id)
        if target is None:
            return None
        bearing = _bearing_degrees(
            current_x, current_y, target.x, target.y,
        )
        h = math.sqrt(
            (target.x - current_x) ** 2
            + (target.y - current_y) ** 2,
        )
        depth_delta = _depth_of(target.band) - _depth_of(current_band)
        return DiveBearing(
            bearing_degrees=bearing,
            horizontal_distance=h,
            depth_delta_meters=depth_delta,
            ascent_warning=self._ascent_warn.get(player_id, False),
        )

    def report_ascent(
        self, *, player_id: str,
        ascent_rate_m_per_s: float,
    ) -> bool:
        warn = ascent_rate_m_per_s > MAX_SAFE_ASCENT_RATE_M_PER_S
        self._ascent_warn[player_id] = warn
        return warn

    def ascent_warning_for(
        self, *, player_id: str,
    ) -> bool:
        return self._ascent_warn.get(player_id, False)


__all__ = [
    "DiveBearing", "DiveCompass",
    "BAND_DEPTH_M", "MAX_SAFE_ASCENT_RATE_M_PER_S",
]
