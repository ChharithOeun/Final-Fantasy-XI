"""Wind currents — per-zone aerial vector field + jet streams.

The sky version of underwater currents. Each (zone, band)
has a wind vector. Airships travelling with the wind get a
speed bonus; against it, a penalty. At STRATOSPHERE band
some routes pass through JET STREAMS — narrow corridors
that triple the wind speed and serve as the canonical
"fastest way to cross the continent" if you can survive
the dragon territory up there.

Public surface
--------------
    Wind dataclass (frozen)
    JetStream dataclass (frozen)
    WindEffect dataclass (frozen)
    WindCurrents
        .register_zone(zone_id, wind_by_band)
        .register_jet_stream(jet_id, zone_id, band,
                             direction_x, direction_y, speed)
        .wind_at(zone_id, band) -> Wind or None
        .effect_on(zone_id, band, ship_dir_x, ship_dir_y,
                   ship_base_speed) -> WindEffect
        .jet_streams_in(zone_id) -> tuple[JetStream, ...]
"""
from __future__ import annotations

import dataclasses
import math
import typing as t


JET_STREAM_BAND = 4  # STRATOSPHERE
JET_STREAM_MULTIPLIER = 3.0
# alignment in [-1, 1]; this is how much we modulate ship speed
WIND_BOOST_PCT = 30   # max boost when fully aligned
WIND_PENALTY_PCT = 30  # max penalty when fully against


@dataclasses.dataclass(frozen=True)
class Wind:
    dx: float
    dy: float
    speed: float


@dataclasses.dataclass(frozen=True)
class JetStream:
    jet_id: str
    zone_id: str
    band: int
    dx: float
    dy: float
    speed: float


@dataclasses.dataclass(frozen=True)
class WindEffect:
    base_speed: float
    effective_speed: float
    boost_pct: int       # signed: + if helping, - if hindering
    in_jet_stream: bool


def _normalize(x: float, y: float) -> tuple[float, float]:
    mag = math.sqrt(x * x + y * y)
    if mag == 0:
        return 0.0, 0.0
    return x / mag, y / mag


@dataclasses.dataclass
class WindCurrents:
    _winds: dict[str, dict[int, Wind]] = dataclasses.field(
        default_factory=dict,
    )
    _jets: dict[str, list[JetStream]] = dataclasses.field(
        default_factory=dict,
    )

    def register_zone(
        self, *, zone_id: str,
        wind_by_band: dict[int, Wind],
    ) -> bool:
        if not zone_id:
            return False
        self._winds[zone_id] = dict(wind_by_band)
        return True

    def register_jet_stream(
        self, *, jet_id: str, zone_id: str,
        dx: float, dy: float, speed: float,
    ) -> bool:
        if not jet_id or not zone_id:
            return False
        self._jets.setdefault(zone_id, []).append(JetStream(
            jet_id=jet_id, zone_id=zone_id,
            band=JET_STREAM_BAND,
            dx=dx, dy=dy, speed=speed,
        ))
        return True

    def wind_at(
        self, *, zone_id: str, band: int,
    ) -> t.Optional[Wind]:
        z = self._winds.get(zone_id)
        if z is None:
            return None
        return z.get(band)

    def effect_on(
        self, *, zone_id: str, band: int,
        ship_dir_x: float, ship_dir_y: float,
        ship_base_speed: float,
    ) -> WindEffect:
        # check jet stream first (only at STRATOSPHERE)
        in_jet = False
        wind_dx, wind_dy, wind_speed = 0.0, 0.0, 0.0
        if band == JET_STREAM_BAND:
            for js in self._jets.get(zone_id, []):
                if js.band == band:
                    in_jet = True
                    wind_dx, wind_dy = js.dx, js.dy
                    wind_speed = js.speed * JET_STREAM_MULTIPLIER
                    break
        if not in_jet:
            w = self.wind_at(zone_id=zone_id, band=band)
            if w is not None:
                wind_dx, wind_dy, wind_speed = w.dx, w.dy, w.speed
        # alignment dot product on normalized vectors
        sx, sy = _normalize(ship_dir_x, ship_dir_y)
        wx, wy = _normalize(wind_dx, wind_dy)
        alignment = sx * wx + sy * wy
        # alignment in [-1, 1]; map to [-WIND_PENALTY_PCT, WIND_BOOST_PCT]
        if alignment >= 0:
            boost_pct = int(alignment * WIND_BOOST_PCT)
        else:
            boost_pct = int(alignment * WIND_PENALTY_PCT)
        # scale by wind speed strength so weak winds barely matter;
        # treat speed=1 as full strength, lower scales linearly down
        scale = min(1.0, wind_speed)
        boost_pct = int(boost_pct * scale)
        # additional jet-stream tail boost on top of alignment
        if in_jet and alignment > 0:
            boost_pct += int(alignment * 30)
        effective = ship_base_speed * (100 + boost_pct) / 100.0
        return WindEffect(
            base_speed=ship_base_speed,
            effective_speed=effective,
            boost_pct=boost_pct,
            in_jet_stream=in_jet,
        )

    def jet_streams_in(
        self, *, zone_id: str,
    ) -> tuple[JetStream, ...]:
        return tuple(self._jets.get(zone_id, []))


__all__ = [
    "Wind", "JetStream", "WindEffect", "WindCurrents",
    "JET_STREAM_BAND", "JET_STREAM_MULTIPLIER",
    "WIND_BOOST_PCT", "WIND_PENALTY_PCT",
]
