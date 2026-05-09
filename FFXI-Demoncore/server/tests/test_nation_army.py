"""Tests for nation_army."""
from __future__ import annotations

from server.nation_army import (
    NationArmySystem, UnitKind, Readiness,
)


def _raise(s, **overrides):
    args = dict(
        nation_id="bastok", unit_id="iron_legion",
        kind=UnitKind.HEAVY_INFANTRY,
        commander_id="captain_volker",
        strength=1000, raised_day=10,
    )
    args.update(overrides)
    return s.raise_unit(**args)


def test_raise_unit_happy():
    s = NationArmySystem()
    assert _raise(s) is True


def test_raise_blank_id():
    s = NationArmySystem()
    assert _raise(s, unit_id="") is False


def test_raise_zero_strength():
    s = NationArmySystem()
    assert _raise(s, strength=0) is False


def test_raise_dup_unit_blocked():
    s = NationArmySystem()
    _raise(s)
    assert _raise(s) is False


def test_deploy_happy():
    s = NationArmySystem()
    _raise(s)
    assert s.deploy(
        unit_id="iron_legion", zone_id="ronfaure",
        now_day=15,
    ) is True


def test_deploy_blank_zone():
    s = NationArmySystem()
    _raise(s)
    assert s.deploy(
        unit_id="iron_legion", zone_id="",
        now_day=15,
    ) is False


def test_double_deploy_blocked():
    s = NationArmySystem()
    _raise(s)
    s.deploy(unit_id="iron_legion",
             zone_id="ronfaure", now_day=15)
    assert s.deploy(
        unit_id="iron_legion", zone_id="zulkheim",
        now_day=16,
    ) is False


def test_recall_happy():
    s = NationArmySystem()
    _raise(s)
    s.deploy(unit_id="iron_legion",
             zone_id="ronfaure", now_day=15)
    assert s.recall(
        unit_id="iron_legion", now_day=20,
    ) is True


def test_recall_when_not_deployed():
    s = NationArmySystem()
    _raise(s)
    assert s.recall(
        unit_id="iron_legion", now_day=20,
    ) is False


def test_take_casualties_reduces_strength():
    s = NationArmySystem()
    _raise(s, strength=1000)
    s.take_casualties(
        unit_id="iron_legion", lost=200,
    )
    u = s.unit(unit_id="iron_legion")
    assert u.strength == 800


def test_casualties_below_50pct_understrength():
    s = NationArmySystem()
    _raise(s, strength=1000)
    s.take_casualties(
        unit_id="iron_legion", lost=600,
    )
    u = s.unit(unit_id="iron_legion")
    assert u.state == Readiness.UNDERSTRENGTH


def test_casualties_to_zero_disbands():
    s = NationArmySystem()
    _raise(s, strength=1000)
    s.take_casualties(
        unit_id="iron_legion", lost=1000,
    )
    u = s.unit(unit_id="iron_legion")
    assert u.state == Readiness.DISBANDED


def test_reinforce_caps_at_base():
    s = NationArmySystem()
    _raise(s, strength=1000)
    s.take_casualties(
        unit_id="iron_legion", lost=300,
    )
    s.reinforce(unit_id="iron_legion", troops=500)
    u = s.unit(unit_id="iron_legion")
    assert u.strength == 1000


def test_reinforce_recovers_to_ready():
    s = NationArmySystem()
    _raise(s, strength=1000)
    s.take_casualties(
        unit_id="iron_legion", lost=600,
    )
    assert s.unit(
        unit_id="iron_legion",
    ).state == Readiness.UNDERSTRENGTH
    s.reinforce(unit_id="iron_legion", troops=500)
    assert s.unit(
        unit_id="iron_legion",
    ).state == Readiness.READY


def test_reinforce_disbanded_blocked():
    s = NationArmySystem()
    _raise(s, strength=100)
    s.take_casualties(
        unit_id="iron_legion", lost=100,
    )
    assert s.reinforce(
        unit_id="iron_legion", troops=50,
    ) is False


def test_promote_commander():
    s = NationArmySystem()
    _raise(s)
    assert s.promote_commander(
        unit_id="iron_legion",
        new_commander="lieutenant_ayame",
    ) is True
    u = s.unit(unit_id="iron_legion")
    assert u.commander_id == "lieutenant_ayame"


def test_promote_blank_blocked():
    s = NationArmySystem()
    _raise(s)
    assert s.promote_commander(
        unit_id="iron_legion", new_commander="",
    ) is False


def test_disband_happy():
    s = NationArmySystem()
    _raise(s)
    assert s.disband(
        unit_id="iron_legion", now_day=100,
    ) is True


def test_double_disband_blocked():
    s = NationArmySystem()
    _raise(s)
    s.disband(unit_id="iron_legion", now_day=100)
    assert s.disband(
        unit_id="iron_legion", now_day=101,
    ) is False


def test_tick_finishes_regroup():
    s = NationArmySystem()
    _raise(s)
    s.deploy(unit_id="iron_legion",
             zone_id="ronfaure", now_day=15)
    s.recall(unit_id="iron_legion", now_day=20)
    # _REGROUP_DAYS = 5 -> ready at 25
    s.tick(now_day=25)
    u = s.unit(unit_id="iron_legion")
    assert u.state == Readiness.READY
    assert u.deployed_zone == ""


def test_tick_skips_within_regroup():
    s = NationArmySystem()
    _raise(s)
    s.deploy(unit_id="iron_legion",
             zone_id="ronfaure", now_day=15)
    s.recall(unit_id="iron_legion", now_day=20)
    s.tick(now_day=22)
    u = s.unit(unit_id="iron_legion")
    assert u.state == Readiness.REGROUPING


def test_units_for_nation():
    s = NationArmySystem()
    _raise(s, nation_id="bastok",
           unit_id="iron_legion")
    _raise(s, nation_id="bastok",
           unit_id="mythril_guard",
           commander_id="naji")
    _raise(s, nation_id="windy",
           unit_id="windy_corps",
           commander_id="kerutoto")
    out = s.units_for(nation_id="bastok")
    assert len(out) == 2


def test_deployed_in_zone():
    s = NationArmySystem()
    _raise(s, unit_id="a")
    _raise(s, unit_id="b", commander_id="x")
    s.deploy(unit_id="a", zone_id="ronfaure",
             now_day=15)
    s.deploy(unit_id="b", zone_id="zulkheim",
             now_day=15)
    out = s.deployed_in(zone_id="ronfaure")
    assert len(out) == 1
    assert out[0].unit_id == "a"


def test_total_strength_excludes_disbanded():
    s = NationArmySystem()
    _raise(s, unit_id="a", strength=1000)
    _raise(s, unit_id="b", commander_id="x",
           strength=500)
    s.disband(unit_id="b", now_day=100)
    assert s.total_strength(
        nation_id="bastok",
    ) == 1000


def test_unit_unknown():
    s = NationArmySystem()
    assert s.unit(unit_id="ghost") is None


def test_enum_counts():
    assert len(list(UnitKind)) == 9
    assert len(list(Readiness)) == 5
