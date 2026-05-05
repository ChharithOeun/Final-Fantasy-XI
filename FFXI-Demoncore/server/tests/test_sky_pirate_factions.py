"""Tests for sky pirate factions."""
from __future__ import annotations

from server.sky_pirate_factions import (
    HOSTILE_REPUTATION_THRESHOLD,
    REPUTATION_CEILING,
    REPUTATION_FLOOR,
    SkyFaction,
    SkyPirateFactions,
)


def test_get_profile_returns_data():
    f = SkyPirateFactions()
    p = f.get_profile(faction=SkyFaction.CORSAIRS_OF_THE_GALE)
    assert p.name == "Corsairs of the Gale"
    assert p.rival == SkyFaction.IRON_WING_DOMINION


def test_get_profile_wyvern_no_rival():
    f = SkyPirateFactions()
    p = f.get_profile(faction=SkyFaction.WYVERN_LORDS)
    assert p.rival is None


def test_reputation_default_zero():
    f = SkyPirateFactions()
    assert f.reputation_of(
        player_id="p1", faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) == 0


def test_adjust_reputation_increases():
    f = SkyPirateFactions()
    new = f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=20,
    )
    assert new == 20


def test_adjust_reputation_floors():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=-200,
    )
    assert f.reputation_of(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) == REPUTATION_FLOOR


def test_adjust_reputation_ceilings():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=500,
    )
    assert f.reputation_of(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) == REPUTATION_CEILING


def test_rival_moves_opposite():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=20,
    )
    rival_rep = f.reputation_of(
        player_id="p1",
        faction=SkyFaction.IRON_WING_DOMINION,
    )
    # rival should drop by half the delta
    assert rival_rep == -10


def test_wyvern_no_rival_propagation():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.WYVERN_LORDS,
        delta=20,
    )
    # nothing should propagate
    assert f.reputation_of(
        player_id="p1", faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) == 0


def test_is_hostile_threshold():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=HOSTILE_REPUTATION_THRESHOLD,
    )
    assert f.is_hostile(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) is True


def test_is_hostile_above_threshold_friendly():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=HOSTILE_REPUTATION_THRESHOLD + 5,
    )
    assert f.is_hostile(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) is False


def test_factions_active_at_band():
    f = SkyPirateFactions()
    # band 1 (LOW) — only Corsairs
    out = f.factions_active_at(band=1)
    assert SkyFaction.CORSAIRS_OF_THE_GALE in out
    assert SkyFaction.IRON_WING_DOMINION not in out
    assert SkyFaction.WYVERN_LORDS not in out


def test_factions_active_at_high():
    f = SkyPirateFactions()
    out = f.factions_active_at(band=3)
    assert SkyFaction.IRON_WING_DOMINION in out
    assert SkyFaction.WYVERN_LORDS in out


def test_factions_active_at_stratosphere():
    f = SkyPirateFactions()
    out = f.factions_active_at(band=4)
    assert out == (SkyFaction.WYVERN_LORDS,)


def test_blank_player_rejected():
    f = SkyPirateFactions()
    new = f.adjust_reputation(
        player_id="",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=20,
    )
    assert new == 0


def test_per_player_isolation():
    f = SkyPirateFactions()
    f.adjust_reputation(
        player_id="p1",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
        delta=20,
    )
    assert f.reputation_of(
        player_id="p2",
        faction=SkyFaction.CORSAIRS_OF_THE_GALE,
    ) == 0
