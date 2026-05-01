"""SCH (Strategos arts) + GEO (Geomancy) terrain/weather manipulation.

Per the user direction: SCH and GEO can manipulate terrain and
weather to gain advantage. Monster parties (intelligent mob squads)
can use the same logic against players.

SCH model: Strategos arts + a wide variety of group buff/debuff
spells. SCH manipulates the GLOBAL weather elemental amp by
shifting the in-zone weather state itself (e.g. casting Stormsurge
forces RAIN for 60 seconds).

GEO model: Geomancer drops a local 'bubble' (luopan ground-circle)
that overrides the environment within a radius. Indi spells affect
the caster + party who stay in the bubble; Geo spells anchor on
the ground and affect anyone inside.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .terrain import ZoneEnvironment
from .weather import WeatherType


class SchArts(str, enum.Enum):
    """Two opposing scholarly stances. Light Arts boosts healing/
    protective magic + boosts ELEMENTAL_AMP for light/water/wind;
    Dark Arts boosts offensive magic + boosts dark/fire/earth/lightning.
    """
    LIGHT_ARTS = "light_arts"
    DARK_ARTS = "dark_arts"


# Weather forced by specific Strategos Spells.
SCH_WEATHER_OVERRIDES = {
    "stormsurge": WeatherType.RAIN,
    "thunderstorm": WeatherType.THUNDER,
    "sandblast": WeatherType.SANDSTORM,
    "voidsurge": WeatherType.GLOOM,
    "celestial_bloom": WeatherType.AURORA,
    "auroraform": WeatherType.AURORA,
    "blizzardcall": WeatherType.BLIZZARD,
    "heat_signal": WeatherType.HEAT_WAVE,
    "winddance": WeatherType.WIND_GALES,
}


class SchManipulator:
    """Apply Strategos spells to a ZoneEnvironment.

    Mutates the environment in place; caller persists the result and
    the next composer call sees the new weather.
    """

    def __init__(self) -> None:
        # Track currently-active overrides per zone for expiration
        self._active: dict[str, tuple[WeatherType, float]] = {}

    def cast_strategos(self,
                        env: ZoneEnvironment,
                        *,
                        spell_name: str,
                        now: float,
                        duration_seconds: float = 60.0) -> bool:
        """Force a weather change via Strategos. Returns True if the
        spell mapped to a known override, False otherwise."""
        spell_key = spell_name.lower().replace(" ", "_")
        new_weather = SCH_WEATHER_OVERRIDES.get(spell_key)
        if new_weather is None:
            return False
        env.weather = new_weather
        env.weather_intensity = 1.0
        self._active[env.zone_id] = (new_weather, now + duration_seconds)
        return True

    def tick_expirations(self,
                           env: ZoneEnvironment,
                           *,
                           now: float,
                           default_weather: WeatherType = WeatherType.CLEAR
                           ) -> bool:
        """If the active override has expired, restore the default
        weather. Returns True if an expiration fired."""
        active = self._active.get(env.zone_id)
        if active is None:
            return False
        weather, expires_at = active
        if now >= expires_at:
            env.weather = default_weather
            del self._active[env.zone_id]
            return True
        return False


@dataclasses.dataclass
class GeoBubble:
    """A geomancer ground-circle. Anyone inside the radius reads the
    bubble's `terrain` + `weather` overrides instead of the zone's."""
    bubble_id: str
    caster_id: str
    center_xy: tuple[float, float]
    radius_cm: float
    terrain_override: t.Optional["TerrainType"] = None
    weather_override: t.Optional[WeatherType] = None
    elemental_boost: t.Optional[tuple[str, float]] = None   # ("fire", 1.20)
    expires_at: t.Optional[float] = None

    def contains(self, pos_xy: tuple[float, float]) -> bool:
        dx = pos_xy[0] - self.center_xy[0]
        dy = pos_xy[1] - self.center_xy[1]
        return (dx * dx + dy * dy) ** 0.5 <= self.radius_cm


class GeoManipulator:
    """Track active GEO bubbles per zone. Composer queries which
    bubble (if any) a unit is standing in."""

    def __init__(self) -> None:
        self._bubbles: dict[str, list[GeoBubble]] = {}

    def cast(self, zone_id: str, bubble: GeoBubble) -> None:
        self._bubbles.setdefault(zone_id, []).append(bubble)

    def remove(self, zone_id: str, bubble_id: str) -> bool:
        bubbles = self._bubbles.get(zone_id, [])
        for i, b in enumerate(bubbles):
            if b.bubble_id == bubble_id:
                bubbles.pop(i)
                return True
        return False

    def tick_expirations(self, *, now: float) -> int:
        """Drop expired bubbles. Returns the number removed."""
        removed = 0
        for zone_id, bubbles in list(self._bubbles.items()):
            kept = []
            for b in bubbles:
                if b.expires_at is not None and now >= b.expires_at:
                    removed += 1
                else:
                    kept.append(b)
            self._bubbles[zone_id] = kept
        return removed

    def bubble_at(self,
                    zone_id: str,
                    pos_xy: tuple[float, float]) -> t.Optional[GeoBubble]:
        """Return the first bubble containing pos_xy, or None.
        Last-cast wins on overlap (innermost in spawn-order list)."""
        bubbles = self._bubbles.get(zone_id, [])
        for b in reversed(bubbles):
            if b.contains(pos_xy):
                return b
        return None


# Late import to avoid circular reference (terrain imports nothing from
# this module either way; this is just for the GeoBubble type hint).
from .terrain import TerrainType   # noqa: E402, F401
