"""Tests for missing ship registry."""
from __future__ import annotations

from server.missing_ship_registry import (
    MissingShipRegistry,
    WreckCause,
    WreckState,
)


def test_file_loss_creates_wreck():
    r = MissingShipRegistry()
    ok = r.file_loss(
        ship_id="argo_1",
        zone_id="wreckage_graveyard",
        cause=WreckCause.PIRATE_BOARD,
        crew_lost=5,
        cargo_value=200,
        now_seconds=1_000,
    )
    assert ok is True
    open_w = r.open_wrecks(zone_id="wreckage_graveyard")
    assert len(open_w) == 1
    assert open_w[0].state == WreckState.FRESH
    assert open_w[0].cargo_remaining == 200


def test_file_loss_rejects_duplicate():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="argo_1",
        zone_id="wreckage_graveyard",
        cause=WreckCause.STORM,
        crew_lost=3,
        cargo_value=100,
        now_seconds=1,
    )
    ok = r.file_loss(
        ship_id="argo_1",
        zone_id="wreckage_graveyard",
        cause=WreckCause.STORM,
        crew_lost=3,
        cargo_value=100,
        now_seconds=2,
    )
    assert ok is False


def test_file_loss_rejects_negative_values():
    r = MissingShipRegistry()
    assert r.file_loss(
        ship_id="bad",
        zone_id="z",
        cause=WreckCause.STORM,
        crew_lost=-1,
        cargo_value=10,
        now_seconds=1,
    ) is False
    assert r.file_loss(
        ship_id="bad2",
        zone_id="z",
        cause=WreckCause.STORM,
        crew_lost=1,
        cargo_value=-10,
        now_seconds=1,
    ) is False


def test_file_loss_rejects_blank_ids():
    r = MissingShipRegistry()
    assert r.file_loss(
        ship_id="",
        zone_id="z",
        cause=WreckCause.STORM,
        crew_lost=0,
        cargo_value=0,
        now_seconds=0,
    ) is False
    assert r.file_loss(
        ship_id="x",
        zone_id="",
        cause=WreckCause.STORM,
        crew_lost=0,
        cargo_value=0,
        now_seconds=0,
    ) is False


def test_pirate_board_crew_fate_all_abducted():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="argo_2",
        zone_id="wreckage_graveyard",
        cause=WreckCause.PIRATE_BOARD,
        crew_lost=4,
        cargo_value=50,
        now_seconds=1,
    )
    fate = r.resolve_crew_fate(ship_id="argo_2")
    assert fate == ("abducted", "abducted", "abducted", "abducted")


def test_siren_shipwreck_crew_fate_all_fomor():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="hymnal",
        zone_id="abyss_trench",
        cause=WreckCause.SIREN_SHIPWRECK,
        crew_lost=3,
        cargo_value=10,
        now_seconds=1,
    )
    fate = r.resolve_crew_fate(ship_id="hymnal")
    assert fate == (
        "drowned_to_fomor",
        "drowned_to_fomor",
        "drowned_to_fomor",
    )


def test_siren_divert_crew_fate_mixed():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="lull_1",
        zone_id="kelp_labyrinth",
        cause=WreckCause.SIREN_DIVERT,
        crew_lost=4,
        cargo_value=10,
        now_seconds=1,
    )
    fate = r.resolve_crew_fate(ship_id="lull_1")
    assert fate.count("abducted") == 2
    assert fate.count("drowned_to_fomor") == 2


def test_storm_crew_fate_drowned():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="storm_1",
        zone_id="tideplate_shallows",
        cause=WreckCause.STORM,
        crew_lost=2,
        cargo_value=0,
        now_seconds=1,
    )
    assert r.resolve_crew_fate(
        ship_id="storm_1",
    ) == ("drowned", "drowned")


def test_zero_crew_no_fate():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="dry_1",
        zone_id="z",
        cause=WreckCause.STORM,
        crew_lost=0,
        cargo_value=10,
        now_seconds=1,
    )
    assert r.resolve_crew_fate(ship_id="dry_1") == ()


def test_salvage_partial_then_strip():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="argo_3",
        zone_id="wreckage_graveyard",
        cause=WreckCause.PIRATE_BOARD,
        crew_lost=1,
        cargo_value=100,
        now_seconds=0,
    )
    s1 = r.salvage(ship_id="argo_3", diver_skill=40, now_seconds=10)
    assert s1.accepted is True
    assert s1.cargo_recovered == 40
    assert s1.new_state == WreckState.PICKED_OVER
    s2 = r.salvage(ship_id="argo_3", diver_skill=200, now_seconds=20)
    assert s2.cargo_recovered == 60
    assert s2.new_state == WreckState.STRIPPED


def test_salvage_rejects_after_strip():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="argo_4",
        zone_id="z",
        cause=WreckCause.STORM,
        crew_lost=0,
        cargo_value=10,
        now_seconds=0,
    )
    r.salvage(ship_id="argo_4", diver_skill=10, now_seconds=1)
    s = r.salvage(ship_id="argo_4", diver_skill=10, now_seconds=2)
    assert s.accepted is False
    assert s.reason == "already stripped"


def test_salvage_rejects_unknown_wreck():
    r = MissingShipRegistry()
    s = r.salvage(ship_id="ghost", diver_skill=10, now_seconds=1)
    assert s.accepted is False
    assert s.reason == "unknown wreck"


def test_salvage_invalid_skill():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="ship", zone_id="z",
        cause=WreckCause.STORM, crew_lost=0, cargo_value=10,
        now_seconds=0,
    )
    s = r.salvage(ship_id="ship", diver_skill=0, now_seconds=1)
    assert s.accepted is False


def test_open_wrecks_filters_zone_and_state():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="a", zone_id="wreckage_graveyard",
        cause=WreckCause.STORM, crew_lost=0, cargo_value=100,
        now_seconds=0,
    )
    r.file_loss(
        ship_id="b", zone_id="abyss_trench",
        cause=WreckCause.STORM, crew_lost=0, cargo_value=100,
        now_seconds=0,
    )
    # strip ship a
    r.salvage(ship_id="a", diver_skill=1_000, now_seconds=1)
    open_grave = r.open_wrecks(zone_id="wreckage_graveyard")
    open_abyss = r.open_wrecks(zone_id="abyss_trench")
    assert len(open_grave) == 0
    assert len(open_abyss) == 1


def test_total_open_counts_only_unstripped():
    r = MissingShipRegistry()
    r.file_loss(
        ship_id="x", zone_id="z",
        cause=WreckCause.STORM, crew_lost=0, cargo_value=10,
        now_seconds=0,
    )
    assert r.total_open() == 1
    r.salvage(ship_id="x", diver_skill=100, now_seconds=1)
    assert r.total_open() == 0
