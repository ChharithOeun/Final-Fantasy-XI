"""Tests for sea pirate factions."""
from __future__ import annotations

from server.sea_pirate_factions import (
    EncounterOutcome,
    PirateFleet,
    PlunderKind,
    SeaPirateFactions,
    Threat,
)


def test_total_fleets_is_four():
    f = SeaPirateFactions()
    assert f.total_fleets() == 4


def test_tangled_flag_low_threat_gil_only():
    f = SeaPirateFactions()
    p = f.profile_for(fleet=PirateFleet.TANGLED_FLAG)
    assert p.threat == Threat.LOW
    assert p.plunder == PlunderKind.GIL_ONLY
    assert p.flagship == "rusted_starboard"
    assert p.primary_zone_id == "tideplate_shallows"


def test_corsairs_mid_threat_gil_and_cargo():
    f = SeaPirateFactions()
    p = f.profile_for(fleet=PirateFleet.CORSAIRS_OF_BRINE)
    assert p.threat == Threat.MID
    assert p.plunder == PlunderKind.GIL_AND_CARGO
    assert p.flagship == "emerald_sovereign"
    assert p.primary_zone_id == "kelp_labyrinth"


def test_sunken_crown_high_full_take():
    f = SeaPirateFactions()
    p = f.profile_for(fleet=PirateFleet.SUNKEN_CROWN)
    assert p.threat == Threat.HIGH
    assert p.plunder == PlunderKind.FULL_TAKE_ABDUCT
    assert p.flagship == "black_lullaby"
    assert p.primary_zone_id == "wreckage_graveyard"


def test_drowned_princes_abyssal_full_take():
    f = SeaPirateFactions()
    p = f.profile_for(fleet=PirateFleet.DROWNED_PRINCES)
    assert p.threat == Threat.ABYSSAL
    assert p.plunder == PlunderKind.FULL_TAKE_ABDUCT
    assert p.flagship == "hollow_admiral"
    assert p.escort_count == 6
    assert p.primary_zone_id == "abyss_trench"


def test_register_sighting_appends():
    f = SeaPirateFactions()
    ok = f.register_sighting(
        fleet=PirateFleet.TANGLED_FLAG,
        zone_id="tideplate_shallows",
        now_seconds=1_000,
    )
    assert ok is True
    sights = f.recent_sightings(
        fleet=PirateFleet.TANGLED_FLAG, since_seconds=0,
    )
    assert len(sights) == 1
    assert sights[0].zone_id == "tideplate_shallows"


def test_register_sighting_rejects_blank_zone():
    f = SeaPirateFactions()
    ok = f.register_sighting(
        fleet=PirateFleet.TANGLED_FLAG, zone_id="", now_seconds=1,
    )
    assert ok is False


def test_recent_sightings_filters_by_time():
    f = SeaPirateFactions()
    f.register_sighting(
        fleet=PirateFleet.CORSAIRS_OF_BRINE,
        zone_id="kelp_labyrinth",
        now_seconds=100,
    )
    f.register_sighting(
        fleet=PirateFleet.CORSAIRS_OF_BRINE,
        zone_id="kelp_labyrinth",
        now_seconds=500,
    )
    sights = f.recent_sightings(
        fleet=PirateFleet.CORSAIRS_OF_BRINE, since_seconds=200,
    )
    assert len(sights) == 1
    assert sights[0].seen_at == 500


def test_recent_sightings_filters_by_fleet():
    f = SeaPirateFactions()
    f.register_sighting(
        fleet=PirateFleet.TANGLED_FLAG,
        zone_id="tideplate_shallows",
        now_seconds=10,
    )
    f.register_sighting(
        fleet=PirateFleet.SUNKEN_CROWN,
        zone_id="wreckage_graveyard",
        now_seconds=10,
    )
    sights = f.recent_sightings(
        fleet=PirateFleet.TANGLED_FLAG, since_seconds=0,
    )
    assert len(sights) == 1


def test_resolve_encounter_navy_repels():
    f = SeaPirateFactions()
    r = f.resolve_encounter(
        fleet=PirateFleet.TANGLED_FLAG,
        naval_strength=100,
        pirate_strength_roll=50,
    )
    assert r.accepted is True
    assert r.outcome == EncounterOutcome.NAVY_REPELS
    assert r.abducted is False


def test_resolve_encounter_pirates_board_gil_only():
    f = SeaPirateFactions()
    r = f.resolve_encounter(
        fleet=PirateFleet.TANGLED_FLAG,
        naval_strength=50,
        pirate_strength_roll=60,
    )
    assert r.accepted is True
    assert r.outcome == EncounterOutcome.PIRATES_BOARD
    assert r.plunder == PlunderKind.GIL_ONLY
    assert r.abducted is False


def test_resolve_encounter_pirates_board_full_take_abducts():
    f = SeaPirateFactions()
    # gap is small (<50% of naval) so we get PIRATES_BOARD with abducted=True
    r = f.resolve_encounter(
        fleet=PirateFleet.SUNKEN_CROWN,
        naval_strength=100,
        pirate_strength_roll=110,
    )
    assert r.accepted is True
    assert r.outcome == EncounterOutcome.PIRATES_BOARD
    assert r.plunder == PlunderKind.FULL_TAKE_ABDUCT
    assert r.abducted is True


def test_resolve_encounter_ship_lost_severe_gap():
    f = SeaPirateFactions()
    # gap >= naval/2 → SHIP_LOST
    r = f.resolve_encounter(
        fleet=PirateFleet.DROWNED_PRINCES,
        naval_strength=50,
        pirate_strength_roll=200,
    )
    assert r.accepted is True
    assert r.outcome == EncounterOutcome.SHIP_LOST
    assert r.abducted is True


def test_resolve_encounter_invalid_strength():
    f = SeaPirateFactions()
    r = f.resolve_encounter(
        fleet=PirateFleet.TANGLED_FLAG,
        naval_strength=-1,
        pirate_strength_roll=10,
    )
    assert r.accepted is False
    assert r.reason == "invalid strength"


def test_resolve_encounter_unknown_fleet():
    f = SeaPirateFactions()

    class FakeFleet:
        value = "ghost_fleet"

    r = f.resolve_encounter(
        fleet=FakeFleet(),
        naval_strength=10,
        pirate_strength_roll=10,
    )
    assert r.accepted is False
    assert r.reason == "unknown fleet"


def test_full_take_fleets_only_gil_and_cargo_does_not_abduct():
    f = SeaPirateFactions()
    r = f.resolve_encounter(
        fleet=PirateFleet.CORSAIRS_OF_BRINE,
        naval_strength=10,
        pirate_strength_roll=200,
    )
    # corsairs only do GIL_AND_CARGO; never abduct
    assert r.abducted is False
    assert r.plunder == PlunderKind.GIL_AND_CARGO
