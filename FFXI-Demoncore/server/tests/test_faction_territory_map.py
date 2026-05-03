"""Tests for faction territory map."""
from __future__ import annotations

from server.faction_territory_map import (
    CAPTURE_THRESHOLD,
    CONTEST_THRESHOLD,
    FactionTerritoryMap,
    INITIAL_CONTROL_STRENGTH,
    MAX_STRENGTH,
    RegionStatus,
)


def test_register_region_with_controller():
    m = FactionTerritoryMap()
    rc = m.register_region(
        region_id="ronfaure_north", zone_id="ronfaure",
        controlling_faction="san_doria",
    )
    assert rc is not None
    assert rc.status == RegionStatus.HELD


def test_register_neutral_region():
    m = FactionTerritoryMap()
    rc = m.register_region(
        region_id="wilds_a", zone_id="wilds",
    )
    assert rc.status == RegionStatus.NEUTRAL


def test_double_register_rejected():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
    )
    second = m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="b",
    )
    assert second is None


def test_build_controlling_strength():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=100,
    )
    assert m.build_strength(
        region_id="r1", faction="a", amount=50,
    )
    assert m.region("r1").control_strength == 150


def test_build_clamped_at_max():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=180,
    )
    m.build_strength(
        region_id="r1", faction="a", amount=500,
    )
    assert m.region("r1").control_strength == MAX_STRENGTH


def test_build_challenger_strength():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
    )
    m.build_strength(
        region_id="r1", faction="b", amount=40,
    )
    assert m.region("r1").challenger_strength["b"] == 40


def test_erode_controlling_strength():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=100,
    )
    m.erode_strength(
        region_id="r1", faction="a", amount=30,
    )
    assert m.region("r1").control_strength == 70


def test_erode_below_contest_threshold():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=40,
    )
    m.erode_strength(
        region_id="r1", faction="a", amount=20,
    )
    # 20 < CONTEST_THRESHOLD = 30, so CONTESTED
    assert m.region("r1").status == RegionStatus.CONTESTED


def test_erode_challenger_to_zero_removes_entry():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
    )
    m.build_strength(
        region_id="r1", faction="b", amount=20,
    )
    m.erode_strength(
        region_id="r1", faction="b", amount=20,
    )
    assert "b" not in m.region("r1").challenger_strength


def test_capture_attempt_below_threshold_rejected():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=10,    # already contested
    )
    m.build_strength(
        region_id="r1", faction="b",
        amount=CAPTURE_THRESHOLD - 1,
    )
    res = m.capture_attempt(
        region_id="r1", by_faction="b",
    )
    assert not res.accepted
    assert "insufficient" in res.reason


def test_capture_attempt_against_strong_defender_rejected():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=100,
    )
    m.build_strength(
        region_id="r1", faction="b",
        amount=CAPTURE_THRESHOLD + 5,
    )
    res = m.capture_attempt(
        region_id="r1", by_faction="b",
    )
    assert not res.accepted
    assert "too strong" in res.reason


def test_capture_attempt_succeeds_on_contested():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=10,    # CONTESTED
    )
    m.build_strength(
        region_id="r1", faction="b",
        amount=CAPTURE_THRESHOLD + 10,
    )
    res = m.capture_attempt(
        region_id="r1", by_faction="b",
    )
    assert res.accepted
    assert res.new_controller == "b"
    assert res.old_controller == "a"
    assert m.region("r1").controlling_faction == "b"


def test_capture_attempt_succeeds_on_neutral():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
    )
    m.build_strength(
        region_id="r1", faction="a",
        amount=CAPTURE_THRESHOLD + 5,
    )
    res = m.capture_attempt(
        region_id="r1", by_faction="a",
    )
    assert res.accepted


def test_capture_attempt_already_controlling():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=10,
    )
    res = m.capture_attempt(
        region_id="r1", by_faction="a",
    )
    assert not res.accepted
    assert "already" in res.reason


def test_capture_attempt_unknown_region():
    m = FactionTerritoryMap()
    res = m.capture_attempt(
        region_id="ghost", by_faction="x",
    )
    assert not res.accepted


def test_capture_count_increments():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
        initial_strength=10,
    )
    m.build_strength(
        region_id="r1", faction="b",
        amount=CAPTURE_THRESHOLD + 5,
    )
    m.capture_attempt(region_id="r1", by_faction="b")
    assert m.region("r1").capture_count == 1


def test_controlled_by_lookup():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z1",
        controlling_faction="bastok",
    )
    m.register_region(
        region_id="r2", zone_id="z2",
        controlling_faction="bastok",
    )
    m.register_region(
        region_id="r3", zone_id="z3",
        controlling_faction="san_doria",
    )
    bastok_regions = m.controlled_by("bastok")
    assert len(bastok_regions) == 2


def test_total_regions():
    m = FactionTerritoryMap()
    m.register_region(region_id="r1", zone_id="z")
    m.register_region(region_id="r2", zone_id="z")
    assert m.total_regions() == 2


def test_negative_amount_rejected():
    m = FactionTerritoryMap()
    m.register_region(
        region_id="r1", zone_id="z",
        controlling_faction="a",
    )
    assert not m.build_strength(
        region_id="r1", faction="a", amount=-1,
    )
    assert not m.erode_strength(
        region_id="r1", faction="a", amount=0,
    )
