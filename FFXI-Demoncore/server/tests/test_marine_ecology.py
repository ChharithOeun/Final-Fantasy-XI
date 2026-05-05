"""Tests for marine ecology."""
from __future__ import annotations

from server.marine_ecology import (
    CARRYING_CAPACITY,
    MarineEcology,
    Species,
)


def test_register_cell_happy():
    e = MarineEcology()
    assert e.register_cell(
        zone_id="reef", band=2,
        populations={Species.FISH: 100},
    ) is True


def test_register_cell_blank_zone():
    e = MarineEcology()
    assert e.register_cell(zone_id="", band=2) is False


def test_register_cell_double_blocked():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    assert e.register_cell(zone_id="reef", band=2) is False


def test_set_population_happy():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    assert e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=10,
    ) is True


def test_set_population_unknown_cell():
    e = MarineEcology()
    assert e.set_population(
        zone_id="ghost", band=2,
        species=Species.SHARK, count=1,
    ) is False


def test_set_population_clamps_negative():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    e.set_population(
        zone_id="reef", band=2, species=Species.FISH, count=-5,
    )
    pops = e.populations_in(zone_id="reef", band=2)
    assert pops[Species.FISH] == 0


def test_populations_in_unknown_returns_empty():
    e = MarineEcology()
    assert e.populations_in(zone_id="ghost", band=2) == {}


def test_prey_grows_toward_capacity():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    cap = CARRYING_CAPACITY[Species.FISH]
    # start at half capacity
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=cap // 2,
    )
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="reef", band=2)
    assert pops[Species.FISH] > cap // 2


def test_prey_capped_at_capacity():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    cap = CARRYING_CAPACITY[Species.FISH]
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=cap,
    )
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="reef", band=2)
    assert pops[Species.FISH] <= cap


def test_predator_eats_prey():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=400,
    )
    e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=20,
    )
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="reef", band=2)
    # fish should drop after predation
    assert pops[Species.FISH] < 400 + 50  # allow some growth too


def test_predator_starves_when_no_prey():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=0,
    )
    e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=10,
    )
    before = 10
    e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="reef", band=2)
    assert pops[Species.SHARK] < before


def test_kraken_eats_sharks_and_sahuagin():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=4)
    e.set_population(
        zone_id="reef", band=4,
        species=Species.SHARK, count=20,
    )
    e.set_population(
        zone_id="reef", band=4,
        species=Species.SAHUAGIN, count=20,
    )
    e.set_population(
        zone_id="reef", band=4,
        species=Species.KRAKEN, count=2,
    )
    # need a few ticks because kraken eats slowly relative to count
    for _ in range(20):
        e.tick(now_seconds=0)
    pops = e.populations_in(zone_id="reef", band=4)
    # at least one of the two predator-prey species should drop
    assert pops[Species.SHARK] < 20 or pops[Species.SAHUAGIN] < 20


def test_migration_flagged_on_low_prey():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    e.register_cell(zone_id="reef", band=3)
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=10,
    )
    e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=10,
    )
    e.tick(now_seconds=0)
    targets = e.migration_targets(zone_id="reef", band=2)
    assert ("reef", 3) in targets


def test_migration_only_to_existing_cells():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    # band 1 and 3 do NOT exist
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH, count=0,
    )
    e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=10,
    )
    e.tick(now_seconds=0)
    assert e.migration_targets(zone_id="reef", band=2) == ()


def test_no_migration_when_prey_healthy():
    e = MarineEcology()
    e.register_cell(zone_id="reef", band=2)
    e.register_cell(zone_id="reef", band=3)
    e.set_population(
        zone_id="reef", band=2,
        species=Species.FISH,
        count=CARRYING_CAPACITY[Species.FISH],
    )
    e.set_population(
        zone_id="reef", band=2,
        species=Species.SHARK, count=10,
    )
    e.tick(now_seconds=0)
    assert e.migration_targets(zone_id="reef", band=2) == ()
