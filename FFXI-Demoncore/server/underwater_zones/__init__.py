"""Underwater zones — city + biome registry for the deep.

The underwater expansion adds 5 NPC cities and 4 wider open
biomes that link them. Cities anchor the lore (each is the home
of an NPC race from underwater_races); biomes carry encounter
density, predator population, and ambient lighting.

Cities (population_seat for race):
  SILMARIL_SIRENHALL  - mermaid matriarchy
  LUMINOUS_DRIFT      - jellyfish gel-cities, bioluminescent
  REEF_SPIRE          - shark-humanoid sea-warriors
  CORAL_CAVERNS       - octopi/squid scholars
  DROWNED_VOID        - underwater fomor; ghost-city, mostly empty

Biomes:
  TIDEPLATE_SHALLOWS  - sunlit, low risk, surface trade lane
  KELP_LABYRINTH      - mid-depth maze, ambush risk
  ABYSS_TRENCH        - deep cold dark, crushing pressure
  WRECKAGE_GRAVEYARD  - scattered missing-ship wrecks (see
                        missing_ship_registry)

Public surface
--------------
    UnderwaterCity enum
    UnderwaterBiome enum
    LightLevel enum     SUNLIT / DIM / DARK / ABYSSAL_BLACK
    ZoneProfile dataclass
    UnderwaterZoneRegistry
        .city_profile(city)
        .biome_profile(biome)
        .biomes_linked_to(city)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class UnderwaterCity(str, enum.Enum):
    SILMARIL_SIRENHALL = "silmaril_sirenhall"
    LUMINOUS_DRIFT = "luminous_drift"
    REEF_SPIRE = "reef_spire"
    CORAL_CAVERNS = "coral_caverns"
    DROWNED_VOID = "drowned_void"


class UnderwaterBiome(str, enum.Enum):
    TIDEPLATE_SHALLOWS = "tideplate_shallows"
    KELP_LABYRINTH = "kelp_labyrinth"
    ABYSS_TRENCH = "abyss_trench"
    WRECKAGE_GRAVEYARD = "wreckage_graveyard"


class LightLevel(str, enum.Enum):
    SUNLIT = "sunlit"
    DIM = "dim"
    DARK = "dark"
    ABYSSAL_BLACK = "abyssal_black"


@dataclasses.dataclass(frozen=True)
class ZoneProfile:
    zone_id: str
    light: LightLevel
    base_depth_yalms: int
    encounter_density: int      # 1..10
    population_seat_for: t.Optional[str] = None
    description: str = ""


_CITIES: dict[UnderwaterCity, ZoneProfile] = {
    UnderwaterCity.SILMARIL_SIRENHALL: ZoneProfile(
        zone_id="silmaril_sirenhall",
        light=LightLevel.DIM,
        base_depth_yalms=80,
        encounter_density=2,
        population_seat_for="mermaid",
        description="Pearl-and-shell matriarchy.",
    ),
    UnderwaterCity.LUMINOUS_DRIFT: ZoneProfile(
        zone_id="luminous_drift",
        light=LightLevel.SUNLIT,
        base_depth_yalms=40,
        encounter_density=1,
        population_seat_for="jellyfish",
        description="Floating bioluminescent gel-spires.",
    ),
    UnderwaterCity.REEF_SPIRE: ZoneProfile(
        zone_id="reef_spire",
        light=LightLevel.DIM,
        base_depth_yalms=120,
        encounter_density=3,
        population_seat_for="shark_humanoid",
        description="Coral citadel of shark-warriors.",
    ),
    UnderwaterCity.CORAL_CAVERNS: ZoneProfile(
        zone_id="coral_caverns",
        light=LightLevel.DARK,
        base_depth_yalms=200,
        encounter_density=2,
        population_seat_for="octopi_squid",
        description="Cephalopod scholar warrens.",
    ),
    UnderwaterCity.DROWNED_VOID: ZoneProfile(
        zone_id="drowned_void",
        light=LightLevel.ABYSSAL_BLACK,
        base_depth_yalms=400,
        encounter_density=8,
        population_seat_for="fomor_underwater",
        description="Ghost-city; drowned echoes wander it.",
    ),
}


_BIOMES: dict[UnderwaterBiome, ZoneProfile] = {
    UnderwaterBiome.TIDEPLATE_SHALLOWS: ZoneProfile(
        zone_id="tideplate_shallows",
        light=LightLevel.SUNLIT,
        base_depth_yalms=20,
        encounter_density=2,
        description="Sunlit shallows; surface trade lane.",
    ),
    UnderwaterBiome.KELP_LABYRINTH: ZoneProfile(
        zone_id="kelp_labyrinth",
        light=LightLevel.DIM,
        base_depth_yalms=90,
        encounter_density=5,
        description="Mid-depth maze, ambush risk.",
    ),
    UnderwaterBiome.ABYSS_TRENCH: ZoneProfile(
        zone_id="abyss_trench",
        light=LightLevel.ABYSSAL_BLACK,
        base_depth_yalms=350,
        encounter_density=7,
        description="Deep cold dark; crushing pressure.",
    ),
    UnderwaterBiome.WRECKAGE_GRAVEYARD: ZoneProfile(
        zone_id="wreckage_graveyard",
        light=LightLevel.DARK,
        base_depth_yalms=180,
        encounter_density=6,
        description="Wrecks of missing ships littered across the floor.",
    ),
}


# Adjacency map: city → biomes that border it
_CITY_BIOMES: dict[UnderwaterCity, tuple[UnderwaterBiome, ...]] = {
    UnderwaterCity.SILMARIL_SIRENHALL: (
        UnderwaterBiome.TIDEPLATE_SHALLOWS,
        UnderwaterBiome.KELP_LABYRINTH,
    ),
    UnderwaterCity.LUMINOUS_DRIFT: (
        UnderwaterBiome.TIDEPLATE_SHALLOWS,
    ),
    UnderwaterCity.REEF_SPIRE: (
        UnderwaterBiome.KELP_LABYRINTH,
        UnderwaterBiome.WRECKAGE_GRAVEYARD,
    ),
    UnderwaterCity.CORAL_CAVERNS: (
        UnderwaterBiome.KELP_LABYRINTH,
        UnderwaterBiome.ABYSS_TRENCH,
    ),
    UnderwaterCity.DROWNED_VOID: (
        UnderwaterBiome.ABYSS_TRENCH,
        UnderwaterBiome.WRECKAGE_GRAVEYARD,
    ),
}


@dataclasses.dataclass
class UnderwaterZoneRegistry:
    def city_profile(
        self, *, city: UnderwaterCity,
    ) -> t.Optional[ZoneProfile]:
        return _CITIES.get(city)

    def biome_profile(
        self, *, biome: UnderwaterBiome,
    ) -> t.Optional[ZoneProfile]:
        return _BIOMES.get(biome)

    def biomes_linked_to(
        self, *, city: UnderwaterCity,
    ) -> tuple[UnderwaterBiome, ...]:
        return _CITY_BIOMES.get(city, ())

    def total_cities(self) -> int:
        return len(_CITIES)

    def total_biomes(self) -> int:
        return len(_BIOMES)


__all__ = [
    "UnderwaterCity", "UnderwaterBiome", "LightLevel",
    "ZoneProfile",
    "UnderwaterZoneRegistry",
]
