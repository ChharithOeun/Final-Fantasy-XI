"""Terrain types + lighting state + ZoneEnvironment dataclass.

A ZoneEnvironment is the per-zone-instant snapshot of:
    - terrain (grassland, dungeon, desert, ...)
    - weather (clear, rain, thunder, ...)
    - lighting (daytime, nighttime, dungeon-no-sunlight)
    - weather intensity (0..1; affects modifier magnitude)

The composer reads this and produces per-unit modifiers.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .weather import WeatherType


class TerrainType(str, enum.Enum):
    """Per-zone biome classification."""
    GRASSLAND = "grassland"
    DESERT = "desert"
    WATER = "water"            # rivers, lakes, ocean shallows
    SWAMP = "swamp"
    DUNGEON = "dungeon"        # underground, no sunlight
    URBAN = "urban"            # cities, paved
    SNOW = "snow"
    VOLCANIC = "volcanic"
    FOREST = "forest"
    MOUNTAINS = "mountains"
    SKY = "sky"                # floating zones (Sky / Tu'Lia)
    SEA = "sea"                # deep water (Sea / Al'Taieu)


class LightingState(str, enum.Enum):
    """Whether sunlight reaches the unit. Drives fomor strength
    and (eventually) BLM nuke amplification, WHM holy bonuses, etc.
    """
    DAYTIME = "daytime"
    NIGHTTIME = "nighttime"
    DUNGEON = "dungeon"            # no sunlight, indoors
    ETERNAL_NIGHT = "eternal_night"   # Dynamis / Sky-of-Eternal-Twilight
    DAWN = "dawn"
    DUSK = "dusk"


# Lighting categories that count as "no sunlight" for fomor strength
NO_SUNLIGHT_STATES = frozenset({
    LightingState.NIGHTTIME,
    LightingState.DUNGEON,
    LightingState.ETERNAL_NIGHT,
})


@dataclasses.dataclass
class ZoneEnvironment:
    """Per-zone-instant snapshot. Mutable so SCH/GEO manipulation can
    rewrite it before the composer runs."""
    zone_id: str
    terrain: TerrainType
    weather: WeatherType
    lighting: LightingState
    weather_intensity: float = 0.5         # 0..1
    elevation_meters: float = 0.0          # affects mountain bonus

    def is_no_sunlight(self) -> bool:
        return self.lighting in NO_SUNLIGHT_STATES
