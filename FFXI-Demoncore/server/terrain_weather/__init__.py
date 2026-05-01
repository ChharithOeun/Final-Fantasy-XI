"""Terrain + weather + lighting environmental modifier engine.

Per the user direction following mob_resistances:
- Terrain affects characters globally (grassland, rain, desert, water,
  lightning, wind, etc.)
- Fomors are strong at night and in dungeons where there's no sunlight
- A party can pull an NM to another zone where the terrain / weather
  gives the NM a debuff
- Each race has different terrain buffs/debuffs (hume/elvaan/taru/
  mithra/galka)
- SCH (Strategos arts) and GEO (geomancy) can manipulate the local
  terrain and weather for advantage
- Monster parties (intelligent mob squads) can use the same logic
  against players

This module is the composer: given a unit (race, job, fomor or not)
in a ZoneEnvironment (terrain + weather + lighting), produce an
EffectiveModifier bundle of speed/accuracy/elemental/cast multipliers
that downstream systems (combat, weight_physics) consume.

Public surface:
    TerrainType, WeatherType, LightingState
    ZoneEnvironment
    RACE_TERRAIN_PROFILES, race_profile_for(race)
    EnvironmentEffectComposer, EffectiveModifier
    fomor_lighting_strength(lighting)
    SchManipulator, GeoManipulator
"""
from .composer import (
    EffectiveModifier,
    EnvironmentEffectComposer,
)
from .fomor_lighting import (
    DUNGEON_FOMOR_MULTIPLIER,
    NIGHT_FOMOR_MULTIPLIER,
    fomor_lighting_strength,
)
from .manipulators import (
    GeoBubble,
    GeoManipulator,
    SchArts,
    SchManipulator,
)
from .race_modifiers import (
    RACE_TERRAIN_PROFILES,
    RaceTerrainProfile,
    race_profile_for,
)
from .terrain import (
    LightingState,
    TerrainType,
    ZoneEnvironment,
)
from .weather import (
    WeatherType,
    weather_elemental_amp,
)

__all__ = [
    "TerrainType",
    "WeatherType",
    "LightingState",
    "ZoneEnvironment",
    "RACE_TERRAIN_PROFILES",
    "RaceTerrainProfile",
    "race_profile_for",
    "EnvironmentEffectComposer",
    "EffectiveModifier",
    "fomor_lighting_strength",
    "DUNGEON_FOMOR_MULTIPLIER",
    "NIGHT_FOMOR_MULTIPLIER",
    "weather_elemental_amp",
    "SchManipulator",
    "SchArts",
    "GeoManipulator",
    "GeoBubble",
]
