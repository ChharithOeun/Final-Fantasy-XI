"""Weather zone state — per-zone active weather + intensity.

terrain_weather already exists for static modifiers. This
module is the LIVE state: which zones currently have what
weather, how intense, and when does it change.

Each zone has a current_weather (an opaque tag) and
intensity 0-100. Weather can be SET directly (admin-driven)
or ADVANCED on a tick (engine rolls a transition).

Public surface
--------------
    WeatherKind enum (CLEAR / RAIN / THUNDERSTORM /
        SNOW / BLIZZARD / FOG / SANDSTORM / AURORAS)
    ZoneWeather dataclass (mutable)
    WeatherZoneState
        .set_weather(zone_id, kind, intensity, set_at) -> bool
        .advance_tick(zone_id, dt_seconds, now_seconds,
                      target_kind=None,
                      transition_speed=10) -> bool
        .current(zone_id) -> Optional[ZoneWeather]
        .intensity_in(zone_id) -> int
        .is_kind(zone_id, kind) -> bool
        .all_zones_with(kind) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WeatherKind(str, enum.Enum):
    CLEAR = "clear"
    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    AURORAS = "auroras"


@dataclasses.dataclass
class ZoneWeather:
    zone_id: str
    kind: WeatherKind
    intensity: int        # 0..100
    last_changed_at: int


@dataclasses.dataclass
class WeatherZoneState:
    _zones: dict[str, ZoneWeather] = dataclasses.field(
        default_factory=dict,
    )

    def set_weather(
        self, *, zone_id: str, kind: WeatherKind,
        intensity: int, set_at: int,
    ) -> bool:
        if not zone_id:
            return False
        if intensity < 0 or intensity > 100:
            return False
        existing = self._zones.get(zone_id)
        if existing is None:
            self._zones[zone_id] = ZoneWeather(
                zone_id=zone_id, kind=kind,
                intensity=intensity, last_changed_at=set_at,
            )
        else:
            existing.kind = kind
            existing.intensity = intensity
            existing.last_changed_at = set_at
        return True

    def advance_tick(
        self, *, zone_id: str, dt_seconds: int,
        now_seconds: int,
        target_kind: t.Optional[WeatherKind] = None,
        transition_speed: int = 10,
    ) -> bool:
        zw = self._zones.get(zone_id)
        if zw is None:
            return False
        if transition_speed < 0:
            return False
        if target_kind is None or target_kind == zw.kind:
            # ramp toward intensity 0 if CLEAR, else 100
            if zw.kind == WeatherKind.CLEAR:
                desired = 0
            else:
                desired = 100
        else:
            # transitioning kinds — ramp current down to 0,
            # then switch to target_kind
            if zw.intensity > 0:
                step = min(zw.intensity, transition_speed)
                zw.intensity -= step
                zw.last_changed_at = now_seconds
                return True
            # switched
            zw.kind = target_kind
            zw.intensity = 0
            zw.last_changed_at = now_seconds
            return True

        if zw.intensity == desired:
            return True
        if zw.intensity < desired:
            zw.intensity = min(desired, zw.intensity + transition_speed)
        else:
            zw.intensity = max(desired, zw.intensity - transition_speed)
        zw.last_changed_at = now_seconds
        return True

    def current(
        self, *, zone_id: str,
    ) -> t.Optional[ZoneWeather]:
        return self._zones.get(zone_id)

    def intensity_in(self, *, zone_id: str) -> int:
        zw = self._zones.get(zone_id)
        if zw is None:
            return 0
        return zw.intensity

    def is_kind(
        self, *, zone_id: str, kind: WeatherKind,
    ) -> bool:
        zw = self._zones.get(zone_id)
        if zw is None:
            return False
        return zw.kind == kind

    def all_zones_with(
        self, *, kind: WeatherKind,
    ) -> tuple[str, ...]:
        return tuple(sorted(
            zid for zid, zw in self._zones.items()
            if zw.kind == kind
        ))

    def total_zones(self) -> int:
        return len(self._zones)


__all__ = ["WeatherKind", "ZoneWeather", "WeatherZoneState"]
