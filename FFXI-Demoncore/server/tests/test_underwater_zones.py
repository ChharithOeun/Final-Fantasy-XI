"""Tests for underwater zones."""
from __future__ import annotations

from server.underwater_zones import (
    LightLevel,
    UnderwaterBiome,
    UnderwaterCity,
    UnderwaterZoneRegistry,
)


def test_total_cities():
    r = UnderwaterZoneRegistry()
    assert r.total_cities() == 5


def test_total_biomes():
    r = UnderwaterZoneRegistry()
    assert r.total_biomes() == 4


def test_silmaril_mermaid_seat():
    r = UnderwaterZoneRegistry()
    p = r.city_profile(city=UnderwaterCity.SILMARIL_SIRENHALL)
    assert p.population_seat_for == "mermaid"


def test_drowned_void_dark():
    r = UnderwaterZoneRegistry()
    p = r.city_profile(city=UnderwaterCity.DROWNED_VOID)
    assert p.light == LightLevel.ABYSSAL_BLACK
    assert p.encounter_density == 8


def test_luminous_drift_sunlit():
    r = UnderwaterZoneRegistry()
    p = r.city_profile(city=UnderwaterCity.LUMINOUS_DRIFT)
    assert p.light == LightLevel.SUNLIT


def test_reef_spire_shark_seat():
    r = UnderwaterZoneRegistry()
    p = r.city_profile(city=UnderwaterCity.REEF_SPIRE)
    assert p.population_seat_for == "shark_humanoid"


def test_coral_caverns_octopi():
    r = UnderwaterZoneRegistry()
    p = r.city_profile(city=UnderwaterCity.CORAL_CAVERNS)
    assert p.population_seat_for == "octopi_squid"


def test_biome_tideplate_sunlit():
    r = UnderwaterZoneRegistry()
    p = r.biome_profile(biome=UnderwaterBiome.TIDEPLATE_SHALLOWS)
    assert p.light == LightLevel.SUNLIT


def test_biome_abyss_dark():
    r = UnderwaterZoneRegistry()
    p = r.biome_profile(biome=UnderwaterBiome.ABYSS_TRENCH)
    assert p.light == LightLevel.ABYSSAL_BLACK


def test_biomes_linked_silmaril():
    r = UnderwaterZoneRegistry()
    bs = r.biomes_linked_to(city=UnderwaterCity.SILMARIL_SIRENHALL)
    assert UnderwaterBiome.TIDEPLATE_SHALLOWS in bs
    assert UnderwaterBiome.KELP_LABYRINTH in bs


def test_biomes_linked_drowned_void():
    r = UnderwaterZoneRegistry()
    bs = r.biomes_linked_to(city=UnderwaterCity.DROWNED_VOID)
    assert UnderwaterBiome.ABYSS_TRENCH in bs
    assert UnderwaterBiome.WRECKAGE_GRAVEYARD in bs


def test_biomes_linked_reef_spire():
    r = UnderwaterZoneRegistry()
    bs = r.biomes_linked_to(city=UnderwaterCity.REEF_SPIRE)
    assert UnderwaterBiome.WRECKAGE_GRAVEYARD in bs


def test_drowned_void_depth_deepest():
    r = UnderwaterZoneRegistry()
    drowned = r.city_profile(
        city=UnderwaterCity.DROWNED_VOID,
    ).base_depth_yalms
    sirenhall = r.city_profile(
        city=UnderwaterCity.SILMARIL_SIRENHALL,
    ).base_depth_yalms
    assert drowned > sirenhall


def test_wreckage_graveyard_dense():
    r = UnderwaterZoneRegistry()
    p = r.biome_profile(biome=UnderwaterBiome.WRECKAGE_GRAVEYARD)
    assert p.encounter_density >= 5


def test_unknown_city_none():
    r = UnderwaterZoneRegistry()
    # passing wrong type returns None gracefully
    class Fake:
        value = "ghost"
    assert r.city_profile(city=Fake()) is None
