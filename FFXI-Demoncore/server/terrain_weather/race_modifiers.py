"""Per-race terrain/weather affinity profiles.

Each FFXI race has a different relationship to terrain and weather:

- HUME: adaptable. Mild buffs/debuffs across the board; the
        balanced baseline race.
- ELVAAN: knights of the San d'Oria woods. Strong in grassland +
        forest, weak in swamp + dungeon (claustrophobia).
- TARUTARU: small, wisdom-attuned. Strong in clear/aurora weather
        and urban + sky zones; very weak in heavy weather (wind
        gales / blizzard / sandstorm batter the small body).
- MITHRA: tropical forest hunters. Strong in forest + desert (heat
        tolerant feline), weak in snow + blizzard (cold-averse fur).
- GALKA: stone-bodied Bastok mountain folk. Strong in dungeon +
        mountains + volcanic, weak in water (too heavy to swim well).

These are buffs/debuffs to a single composite "vitality" multiplier.
The composer translates that into the actual stat tweaks.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .terrain import TerrainType
from .weather import WeatherType


@dataclasses.dataclass(frozen=True)
class RaceTerrainProfile:
    """Per-race environmental affinities.

    Values are multiplicative tweaks applied to the unit's combat
    vitality. 1.0 = neutral; 1.10 = +10% bonus; 0.90 = -10% penalty.
    Missing entries default to 1.0.
    """
    race: str
    terrain_buffs: dict[TerrainType, float]
    weather_buffs: dict[WeatherType, float]
    notes: str = ""


RACE_TERRAIN_PROFILES: dict[str, RaceTerrainProfile] = {
    "hume": RaceTerrainProfile(
        race="hume",
        terrain_buffs={
            TerrainType.URBAN: 1.05,
            TerrainType.GRASSLAND: 1.03,
        },
        weather_buffs={
            WeatherType.CLEAR: 1.03,
        },
        notes="adaptable; mild bonuses everywhere; no big debuffs",
    ),
    "elvaan": RaceTerrainProfile(
        race="elvaan",
        terrain_buffs={
            TerrainType.GRASSLAND: 1.10,
            TerrainType.FOREST: 1.10,
            TerrainType.MOUNTAINS: 1.05,
            TerrainType.SWAMP: 0.85,         # San d'Orian woodsmen hate the muck
            TerrainType.DUNGEON: 0.90,       # claustrophobic
        },
        weather_buffs={
            WeatherType.CLEAR: 1.05,
            WeatherType.SUNSHOWER: 1.05,
            WeatherType.FOG: 0.95,
        },
        notes="grassland/forest knights; weak in tight enclosed spaces",
    ),
    "tarutaru": RaceTerrainProfile(
        race="tarutaru",
        terrain_buffs={
            TerrainType.URBAN: 1.10,
            TerrainType.SKY: 1.10,
            TerrainType.DESERT: 0.85,        # too hot for the small body
            TerrainType.SNOW: 0.90,
        },
        weather_buffs={
            WeatherType.CLEAR: 1.08,
            WeatherType.AURORA: 1.15,        # wisdom-attuned to light
            WeatherType.WIND_GALES: 0.75,    # gets battered
            WeatherType.BLIZZARD: 0.75,
            WeatherType.SANDSTORM: 0.80,
        },
        notes="wisdom-attuned scholars; small body suffers in heavy weather",
    ),
    "mithra": RaceTerrainProfile(
        race="mithra",
        terrain_buffs={
            TerrainType.FOREST: 1.12,
            TerrainType.DESERT: 1.08,        # heat-tolerant feline
            TerrainType.GRASSLAND: 1.05,
            TerrainType.SNOW: 0.85,
        },
        weather_buffs={
            WeatherType.HEAT_WAVE: 1.10,
            WeatherType.CLEAR: 1.05,
            WeatherType.BLIZZARD: 0.80,      # cold-averse fur
            WeatherType.SNOW_LIGHT: 0.90,
        },
        notes="tropical forest hunters; cold-averse fur",
    ),
    "galka": RaceTerrainProfile(
        race="galka",
        terrain_buffs={
            TerrainType.DUNGEON: 1.12,       # stone-loving Bastok mountain folk
            TerrainType.MOUNTAINS: 1.10,
            TerrainType.VOLCANIC: 1.08,
            TerrainType.WATER: 0.80,         # heavy, swim poorly
            TerrainType.SEA: 0.80,
        },
        weather_buffs={
            WeatherType.HEAT_WAVE: 1.05,
            WeatherType.BLIZZARD: 0.95,      # tough but cold still bites
            WeatherType.RAIN: 0.95,          # waterlogged plate
        },
        notes="stone-bodied; thrives underground / in mountains",
    ),
}


# A neutral fallback for non-canonical races (NPC/mob entities)
NEUTRAL_PROFILE = RaceTerrainProfile(
    race="neutral", terrain_buffs={}, weather_buffs={},
    notes="fallback; no environmental affinities",
)


def race_profile_for(race: str) -> RaceTerrainProfile:
    return RACE_TERRAIN_PROFILES.get(race.lower(), NEUTRAL_PROFILE)


def race_terrain_multiplier(race: str, terrain: TerrainType) -> float:
    profile = race_profile_for(race)
    return profile.terrain_buffs.get(terrain, 1.0)


def race_weather_multiplier(race: str, weather: WeatherType) -> float:
    profile = race_profile_for(race)
    return profile.weather_buffs.get(weather, 1.0)
