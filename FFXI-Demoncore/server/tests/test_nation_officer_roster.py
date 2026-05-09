"""Tests for nation_officer_roster."""
from __future__ import annotations

from server.nation_officer_roster import (
    NationOfficerRosterSystem, OfficerStatus,
    Assignment, OfficerStats,
)


def _stats(**overrides):
    args = dict(
        martial=80, intellect=60, leadership=75,
        charisma=70, loyalty=85,
    )
    args.update(overrides)
    return OfficerStats(**args)


def _enlist(s, **overrides):
    args = dict(
        officer_id="off_volker", name="Volker",
        nation_id="bastok", stats=_stats(),
        age=42, enlisted_day=10,
    )
    args.update(overrides)
    return s.enlist(**args)


def test_enlist_happy():
    s = NationOfficerRosterSystem()
    assert _enlist(s) is True


def test_enlist_blank():
    s = NationOfficerRosterSystem()
    assert _enlist(s, officer_id="") is False


def test_enlist_zero_age():
    s = NationOfficerRosterSystem()
    assert _enlist(s, age=0) is False


def test_enlist_invalid_stat():
    s = NationOfficerRosterSystem()
    assert _enlist(
        s, stats=_stats(martial=0),
    ) is False


def test_enlist_stat_over_max():
    s = NationOfficerRosterSystem()
    assert _enlist(
        s, stats=_stats(loyalty=101),
    ) is False


def test_enlist_dup_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert _enlist(s) is False


def test_assign_happy():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.assign(
        officer_id="off_volker",
        assignment=Assignment.ARMY_COMMAND,
    ) is True


def test_assign_dead_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s)
    s.kill(officer_id="off_volker", now_day=20)
    assert s.assign(
        officer_id="off_volker",
        assignment=Assignment.COUNCIL,
    ) is False


def test_adjust_loyalty():
    s = NationOfficerRosterSystem()
    _enlist(s, stats=_stats(loyalty=70))
    s.adjust_loyalty(
        officer_id="off_volker", delta=10,
    )
    assert s.officer(
        officer_id="off_volker",
    ).stats.loyalty == 80


def test_adjust_loyalty_caps_high():
    s = NationOfficerRosterSystem()
    _enlist(s, stats=_stats(loyalty=95))
    s.adjust_loyalty(
        officer_id="off_volker", delta=20,
    )
    assert s.officer(
        officer_id="off_volker",
    ).stats.loyalty == 100


def test_adjust_loyalty_caps_low():
    s = NationOfficerRosterSystem()
    _enlist(s, stats=_stats(loyalty=5))
    s.adjust_loyalty(
        officer_id="off_volker", delta=-50,
    )
    assert s.officer(
        officer_id="off_volker",
    ).stats.loyalty == 1


def test_transfer_nation():
    s = NationOfficerRosterSystem()
    _enlist(s, nation_id="bastok")
    assert s.transfer_nation(
        officer_id="off_volker",
        new_nation="windy",
    ) is True
    o = s.officer(officer_id="off_volker")
    assert o.nation_id == "windy"
    assert o.assignment == Assignment.UNASSIGNED


def test_transfer_same_nation_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s, nation_id="bastok")
    assert s.transfer_nation(
        officer_id="off_volker",
        new_nation="bastok",
    ) is False


def test_capture_release():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.capture(
        officer_id="off_volker", now_day=50,
    ) is True
    assert s.officer(
        officer_id="off_volker",
    ).status == OfficerStatus.CAPTURED
    s.release(officer_id="off_volker", now_day=60)
    assert s.officer(
        officer_id="off_volker",
    ).status == OfficerStatus.ACTIVE


def test_release_not_captured_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.release(
        officer_id="off_volker", now_day=10,
    ) is False


def test_retire():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.retire(
        officer_id="off_volker", now_day=999,
    ) is True


def test_retire_dead_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s)
    s.kill(officer_id="off_volker", now_day=10)
    assert s.retire(
        officer_id="off_volker", now_day=11,
    ) is False


def test_kill_then_kill_blocked():
    s = NationOfficerRosterSystem()
    _enlist(s)
    s.kill(officer_id="off_volker", now_day=10)
    assert s.kill(
        officer_id="off_volker", now_day=11,
    ) is False


def test_roster_for_filters_active():
    s = NationOfficerRosterSystem()
    _enlist(s, officer_id="a", name="A")
    _enlist(s, officer_id="b", name="B")
    _enlist(s, officer_id="c", name="C",
            nation_id="windy")
    s.kill(officer_id="b", now_day=10)
    out = s.roster_for(nation_id="bastok")
    assert len(out) == 1
    assert out[0].officer_id == "a"


def test_by_assignment():
    s = NationOfficerRosterSystem()
    _enlist(s, officer_id="a", name="A")
    _enlist(s, officer_id="b", name="B")
    s.assign(
        officer_id="a",
        assignment=Assignment.ARMY_COMMAND,
    )
    s.assign(
        officer_id="b",
        assignment=Assignment.NAVY_COMMAND,
    )
    out = s.by_assignment(
        nation_id="bastok",
        assignment=Assignment.ARMY_COMMAND,
    )
    assert len(out) == 1
    assert out[0].officer_id == "a"


def test_top_by_martial():
    s = NationOfficerRosterSystem()
    _enlist(s, officer_id="a", name="A",
            stats=_stats(martial=85))
    _enlist(s, officer_id="b", name="B",
            stats=_stats(martial=95))
    _enlist(s, officer_id="c", name="C",
            stats=_stats(martial=70))
    out = s.top_by(
        nation_id="bastok", stat="martial", limit=2,
    )
    assert [o.officer_id for o in out] == ["b", "a"]


def test_top_by_invalid_stat():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.top_by(
        nation_id="bastok", stat="charm",
        limit=5,
    ) == []


def test_top_by_zero_limit():
    s = NationOfficerRosterSystem()
    _enlist(s)
    assert s.top_by(
        nation_id="bastok", stat="martial",
        limit=0,
    ) == []


def test_officer_unknown():
    s = NationOfficerRosterSystem()
    assert s.officer(officer_id="ghost") is None


def test_enum_counts():
    assert len(list(OfficerStatus)) == 4
    assert len(list(Assignment)) == 8
