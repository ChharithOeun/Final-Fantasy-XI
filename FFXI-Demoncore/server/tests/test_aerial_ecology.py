"""Tests for aerial ecology."""
from __future__ import annotations

from server.aerial_ecology import (
    AerialEcology,
    CARRYING_CAPACITY,
    SkySpecies,
)


def test_register_cell_happy():
    e = AerialEcology()
    assert e.register_cell(
        zone_id="sky_z", band=2,
        populations={SkySpecies.SKY_FISH: 100},
    ) is True


def test_register_blank():
    e = AerialEcology()
    assert e.register_cell(zone_id="", band=2) is False


def test_register_double_blocked():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    assert e.register_cell(zone_id="sky_z", band=2) is False


def test_set_population_happy():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    assert e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.ROC, count=10,
    ) is True


def test_set_population_clamps_negative():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.SKY_FISH, count=-5,
    )
    assert e.populations_in(
        zone_id="sky_z", band=2,
    )[SkySpecies.SKY_FISH] == 0


def test_set_population_unknown_cell():
    e = AerialEcology()
    assert e.set_population(
        zone_id="ghost", band=2,
        species=SkySpecies.ROC, count=1,
    ) is False


def test_populations_in_unknown_returns_empty():
    e = AerialEcology()
    assert e.populations_in(zone_id="ghost", band=2) == {}


def test_prey_grows_toward_capacity():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=1)
    cap = CARRYING_CAPACITY[SkySpecies.SKY_FISH]
    e.set_population(
        zone_id="sky_z", band=1,
        species=SkySpecies.SKY_FISH, count=cap // 2,
    )
    e.tick(now_seconds=0)
    after = e.populations_in(
        zone_id="sky_z", band=1,
    )[SkySpecies.SKY_FISH]
    assert after > cap // 2


def test_prey_capped_at_capacity():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=1)
    cap = CARRYING_CAPACITY[SkySpecies.SKY_FISH]
    e.set_population(
        zone_id="sky_z", band=1,
        species=SkySpecies.SKY_FISH, count=cap,
    )
    e.tick(now_seconds=0)
    after = e.populations_in(
        zone_id="sky_z", band=1,
    )[SkySpecies.SKY_FISH]
    assert after <= cap


def test_predator_eats_prey():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.SKY_FISH, count=500,
    )
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.ROC, count=15,
    )
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="sky_z", band=2)
    assert pops[SkySpecies.SKY_FISH] < 500 + 50


def test_predator_starves_when_no_prey():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=3)
    e.set_population(
        zone_id="sky_z", band=3,
        species=SkySpecies.SKY_FISH, count=0,
    )
    e.set_population(
        zone_id="sky_z", band=3,
        species=SkySpecies.STORM_PETREL, count=0,
    )
    e.set_population(
        zone_id="sky_z", band=3,
        species=SkySpecies.ROC, count=10,
    )
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="sky_z", band=3)
    assert pops[SkySpecies.ROC] < 10


def test_wyvern_eats_petrel_and_roc():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=4)
    e.set_population(
        zone_id="sky_z", band=4,
        species=SkySpecies.STORM_PETREL, count=150,
    )
    e.set_population(
        zone_id="sky_z", band=4,
        species=SkySpecies.ROC, count=20,
    )
    e.set_population(
        zone_id="sky_z", band=4,
        species=SkySpecies.WYVERN, count=3,
    )
    for _ in range(20):
        e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="sky_z", band=4)
    assert (
        pops[SkySpecies.STORM_PETREL] < 150
        or pops[SkySpecies.ROC] < 20
    )


def test_migration_flagged_on_low_prey():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    e.register_cell(zone_id="sky_z", band=3)
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.SKY_FISH, count=10,
    )
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.ROC, count=10,
    )
    e.tick(now_seconds=0)
    targets = e.migration_targets(zone_id="sky_z", band=2)
    assert ("sky_z", 3) in targets


def test_no_migration_when_prey_healthy():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    e.register_cell(zone_id="sky_z", band=3)
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.SKY_FISH,
        count=CARRYING_CAPACITY[SkySpecies.SKY_FISH],
    )
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.ROC, count=10,
    )
    e.tick(now_seconds=0)
    assert e.migration_targets(zone_id="sky_z", band=2) == ()


def test_migration_only_to_existing_cells():
    e = AerialEcology()
    e.register_cell(zone_id="sky_z", band=2)
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.SKY_FISH, count=0,
    )
    e.set_population(
        zone_id="sky_z", band=2,
        species=SkySpecies.ROC, count=10,
    )
    e.tick(now_seconds=0)
    assert e.migration_targets(zone_id="sky_z", band=2) == ()
