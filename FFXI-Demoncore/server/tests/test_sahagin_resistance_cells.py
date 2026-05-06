"""Tests for sahagin resistance cells."""
from __future__ import annotations

from server.sahagin_resistance_cells import (
    CellKind,
    CellStatus,
    SahaginResistanceCells,
)


def test_establish_happy():
    s = SahaginResistanceCells()
    assert s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    ) is True


def test_establish_blank_id():
    s = SahaginResistanceCells()
    assert s.establish(
        cell_id="", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    ) is False


def test_establish_double_blocked():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    )
    assert s.establish(
        cell_id="c1", kind=CellKind.WAR_FORGE,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    ) is False


def test_establish_zero_hp_blocked():
    s = SahaginResistanceCells()
    assert s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=0,
        bounty_on_kill=100,
    ) is False


def test_establish_negative_bounty_blocked():
    s = SahaginResistanceCells()
    assert s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=100,
        bounty_on_kill=-1,
    ) is False


def test_damage_partial_keeps_active():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    )
    out = s.damage(
        cell_id="c1", amount=100, attacker_id="p1", now_seconds=0,
    )
    assert out.accepted is True
    assert out.cell_wiped is False
    assert out.hp_remaining == 900


def test_damage_below_half_marks_damaged():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=2500,
    )
    s.damage(
        cell_id="c1", amount=600, attacker_id="p1", now_seconds=0,
    )
    assert s.status_of(cell_id="c1") == CellStatus.DAMAGED


def test_damage_to_zero_wipes():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.WAR_FORGE,
        zone_id="reef", band=2, hp_max=1000,
        bounty_on_kill=5000,
    )
    out = s.damage(
        cell_id="c1", amount=2000, attacker_id="p1", now_seconds=100,
    )
    assert out.cell_wiped is True
    assert out.bounty_paid == 5000
    assert s.status_of(cell_id="c1") == CellStatus.WIPED


def test_wiped_cell_cannot_be_damaged_again():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.WAR_FORGE,
        zone_id="reef", band=2, hp_max=100,
        bounty_on_kill=5000,
    )
    s.damage(
        cell_id="c1", amount=200, attacker_id="p1", now_seconds=100,
    )
    out = s.damage(
        cell_id="c1", amount=10, attacker_id="p1", now_seconds=200,
    )
    assert out.accepted is False
    assert out.reason == "already wiped"


def test_damage_unknown_cell():
    s = SahaginResistanceCells()
    out = s.damage(
        cell_id="ghost", amount=100, attacker_id="p1", now_seconds=0,
    )
    assert out.accepted is False


def test_damage_zero_blocked():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SMUGGLERS_DEN,
        zone_id="reef", band=2, hp_max=100,
        bounty_on_kill=100,
    )
    out = s.damage(
        cell_id="c1", amount=0, attacker_id="p1", now_seconds=0,
    )
    assert out.accepted is False


def test_cells_in_zone():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SCOUT_HIDE,
        zone_id="reef", band=2, hp_max=100, bounty_on_kill=100,
    )
    s.establish(
        cell_id="c2", kind=CellKind.SABOTEURS_CACHE,
        zone_id="trench", band=3, hp_max=100, bounty_on_kill=100,
    )
    out = s.cells_in(zone_id="reef")
    assert len(out) == 1


def test_active_kinds_excludes_wiped():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SCOUT_HIDE,
        zone_id="reef", band=2, hp_max=100, bounty_on_kill=100,
    )
    s.establish(
        cell_id="c2", kind=CellKind.WAR_FORGE,
        zone_id="reef", band=2, hp_max=100, bounty_on_kill=100,
    )
    s.damage(
        cell_id="c1", amount=200, attacker_id="p1", now_seconds=0,
    )
    kinds = s.active_kinds_in(zone_id="reef")
    assert CellKind.SCOUT_HIDE not in kinds
    assert CellKind.WAR_FORGE in kinds


def test_wiped_count():
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.SCOUT_HIDE,
        zone_id="reef", band=2, hp_max=100, bounty_on_kill=100,
    )
    s.establish(
        cell_id="c2", kind=CellKind.WAR_FORGE,
        zone_id="trench", band=3, hp_max=100, bounty_on_kill=100,
    )
    s.damage(
        cell_id="c1", amount=200, attacker_id="p1", now_seconds=0,
    )
    s.damage(
        cell_id="c2", amount=200, attacker_id="p1", now_seconds=0,
    )
    assert s.wiped_count() == 2


def test_status_of_unknown():
    s = SahaginResistanceCells()
    assert s.status_of(cell_id="ghost") is None


def test_kingdom_loses_assassination_capacity():
    """Kill the only ASSASSINS_ROOST in zone — that kind goes dark."""
    s = SahaginResistanceCells()
    s.establish(
        cell_id="c1", kind=CellKind.ASSASSINS_ROOST,
        zone_id="reef", band=3, hp_max=500, bounty_on_kill=10000,
    )
    assert CellKind.ASSASSINS_ROOST in s.active_kinds_in(zone_id="reef")
    s.damage(
        cell_id="c1", amount=500, attacker_id="p1", now_seconds=0,
    )
    assert (
        CellKind.ASSASSINS_ROOST
        not in s.active_kinds_in(zone_id="reef")
    )
