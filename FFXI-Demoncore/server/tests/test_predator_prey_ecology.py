"""Tests for predator-prey ecology."""
from __future__ import annotations

from server.predator_prey_ecology import (
    PredatorPreyEcology,
    SpeciesRole,
)


def test_seed_then_query_population():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="ronfaure", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=50,
    )
    assert eco.population(
        zone_id="ronfaure", species_id="rabbit",
    ) == 50


def test_unknown_zone_population_zero():
    eco = PredatorPreyEcology()
    assert eco.population(
        zone_id="ghost", species_id="x",
    ) == 0


def test_link_unknown_species_rejected():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=10,
    )
    assert not eco.add_predator_prey_link(
        zone_id="z", predator="ghost", prey="rabbit",
    )


def test_herbivore_grows_naturally():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=1000,
        baseline_growth=0.01,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=10.0)
    assert res.deltas["rabbit"] > 0


def test_predator_decays_without_prey():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="wolf",
        role=SpeciesRole.PREDATOR, population=1000,
        baseline_decay=0.01,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=10.0)
    assert res.deltas["wolf"] < 0


def test_predator_eats_prey():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="wolf",
        role=SpeciesRole.PREDATOR, population=100,
    )
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=500,
    )
    eco.add_predator_prey_link(
        zone_id="z", predator="wolf", prey="rabbit",
        kill_efficiency=1.0,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=1.0)
    # Rabbit population should drop
    assert res.deltas["rabbit"] < 0


def test_predator_grows_when_eating():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="wolf",
        role=SpeciesRole.PREDATOR, population=100,
        baseline_decay=0.0,
    )
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=10000,
    )
    eco.add_predator_prey_link(
        zone_id="z", predator="wolf", prey="rabbit",
        kill_efficiency=1.0, conversion=0.1,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=1.0)
    # Wolf population should rise from kills
    assert res.deltas["wolf"] > 0


def test_crashed_flag():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=2,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=1.0)
    assert "rabbit" in res.crashed_species


def test_boom_flag():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=100,
        baseline_growth=1.0,    # absurd, just to trigger boom
    )
    res = eco.tick(zone_id="z", elapsed_seconds=1.0)
    assert "rabbit" in res.booming_species


def test_forage_cap_starves_excess():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=1000,
        baseline_growth=0.0,
    )
    eco.add_forage_link(
        zone_id="z", herbivore="rabbit",
        forage_capacity=200,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=10.0)
    assert eco.population(
        zone_id="z", species_id="rabbit",
    ) < 1000


def test_forage_cap_holds_at_capacity():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=200,
        baseline_growth=0.0,
    )
    eco.add_forage_link(
        zone_id="z", herbivore="rabbit",
        forage_capacity=200,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=10.0)
    # No excess, no decay
    assert eco.population(
        zone_id="z", species_id="rabbit",
    ) == 200


def test_unknown_zone_tick_empty():
    eco = PredatorPreyEcology()
    res = eco.tick(zone_id="ghost", elapsed_seconds=1.0)
    assert res.deltas == {}


def test_zero_elapsed_no_change():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=100,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=0.0)
    assert res.deltas == {}


def test_predator_cant_kill_more_than_prey_alive():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="wolf",
        role=SpeciesRole.PREDATOR, population=100,
    )
    eco.seed(
        zone_id="z", species_id="rabbit",
        role=SpeciesRole.HERBIVORE, population=5,
    )
    eco.add_predator_prey_link(
        zone_id="z", predator="wolf", prey="rabbit",
        kill_efficiency=10.0,    # absurdly high
    )
    eco.tick(zone_id="z", elapsed_seconds=10.0)
    assert eco.population(
        zone_id="z", species_id="rabbit",
    ) >= 0


def test_total_zones_count():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z1", species_id="r",
        role=SpeciesRole.HERBIVORE, population=10,
    )
    eco.seed(
        zone_id="z2", species_id="r",
        role=SpeciesRole.HERBIVORE, population=10,
    )
    assert eco.total_zones() == 2


def test_apex_decays_like_predator():
    eco = PredatorPreyEcology()
    eco.seed(
        zone_id="z", species_id="dragon",
        role=SpeciesRole.APEX, population=100,
        baseline_decay=0.01,
    )
    res = eco.tick(zone_id="z", elapsed_seconds=10.0)
    assert res.deltas["dragon"] < 0
