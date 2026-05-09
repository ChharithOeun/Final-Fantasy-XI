"""Tests for beastman_officer_roster."""
from __future__ import annotations

from server.beastman_officer_roster import (
    BeastmanOfficerRosterSystem, BeastmanRace,
    Trait, BeastmanStatus, BeastmanStats,
)


def _stats(**overrides):
    args = dict(
        martial=85, intellect=60, leadership=75,
        charisma=55, loyalty=80,
    )
    args.update(overrides)
    return BeastmanStats(**args)


def _enlist(s, **overrides):
    args = dict(
        officer_id="orc_argath", name="Argath",
        race=BeastmanRace.ORC,
        home_city="davoi", stats=_stats(),
        trait=Trait.WARLORD, age=35,
        enlisted_day=10,
    )
    args.update(overrides)
    return s.enlist(**args)


def test_enlist_happy():
    s = BeastmanOfficerRosterSystem()
    assert _enlist(s) is True


def test_enlist_blank_id():
    s = BeastmanOfficerRosterSystem()
    assert _enlist(s, officer_id="") is False


def test_enlist_blank_home():
    s = BeastmanOfficerRosterSystem()
    assert _enlist(s, home_city="") is False


def test_enlist_invalid_stat():
    s = BeastmanOfficerRosterSystem()
    assert _enlist(
        s, stats=_stats(martial=0),
    ) is False


def test_enlist_dup_blocked():
    s = BeastmanOfficerRosterSystem()
    _enlist(s)
    assert _enlist(s) is False


def test_enlist_serving_starts_at_home():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    o = s.officer(officer_id="orc_argath")
    assert o.serving_faction == "davoi"


def test_transfer_faction():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    assert s.transfer_faction(
        officer_id="orc_argath",
        new_faction="bastok", now_day=50,
    ) is True
    o = s.officer(officer_id="orc_argath")
    assert o.serving_faction == "bastok"
    assert o.relocated_day == 50


def test_transfer_same_blocked():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    assert s.transfer_faction(
        officer_id="orc_argath",
        new_faction="davoi", now_day=50,
    ) is False


def test_days_in_foreign_service():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    s.transfer_faction(
        officer_id="orc_argath",
        new_faction="bastok", now_day=50,
    )
    assert s.days_in_foreign_service(
        officer_id="orc_argath", now_day=80,
    ) == 30


def test_days_at_home_zero():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    assert s.days_in_foreign_service(
        officer_id="orc_argath", now_day=80,
    ) == 0


def test_is_in_foreign_service():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, home_city="davoi")
    assert s.is_in_foreign_service(
        officer_id="orc_argath",
    ) is False
    s.transfer_faction(
        officer_id="orc_argath",
        new_faction="bastok", now_day=50,
    )
    assert s.is_in_foreign_service(
        officer_id="orc_argath",
    ) is True


def test_adjust_loyalty_clamps():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, stats=_stats(loyalty=95))
    s.adjust_loyalty(
        officer_id="orc_argath", delta=20,
    )
    assert s.officer(
        officer_id="orc_argath",
    ).stats.loyalty == 100


def test_capture_then_exile():
    s = BeastmanOfficerRosterSystem()
    _enlist(s)
    s.capture(officer_id="orc_argath", now_day=50)
    assert s.exile(
        officer_id="orc_argath", now_day=60,
    ) is True
    assert s.officer(
        officer_id="orc_argath",
    ).status == BeastmanStatus.EXILED


def test_kill_then_kill_blocked():
    s = BeastmanOfficerRosterSystem()
    _enlist(s)
    s.kill(officer_id="orc_argath", now_day=10)
    assert s.kill(
        officer_id="orc_argath", now_day=11,
    ) is False


def test_serving_in_filters():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, officer_id="a", home_city="davoi")
    _enlist(s, officer_id="b", home_city="davoi",
            name="B")
    _enlist(s, officer_id="c", home_city="windy",
            race=BeastmanRace.YAGUDO, name="C")
    s.transfer_faction(
        officer_id="b", new_faction="bastok",
        now_day=50,
    )
    out = s.serving_in(faction="davoi")
    ids = [o.officer_id for o in out]
    assert "a" in ids
    assert "b" not in ids


def test_by_race():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, officer_id="a",
            race=BeastmanRace.ORC, name="A")
    _enlist(s, officer_id="b",
            race=BeastmanRace.YAGUDO,
            home_city="windy", name="B")
    _enlist(s, officer_id="c",
            race=BeastmanRace.ORC, name="C")
    out = s.by_race(race=BeastmanRace.ORC)
    assert len(out) == 2


def test_expatriates():
    s = BeastmanOfficerRosterSystem()
    _enlist(s, officer_id="a", home_city="davoi")
    _enlist(s, officer_id="b", home_city="davoi",
            name="B")
    s.transfer_faction(
        officer_id="b", new_faction="bastok",
        now_day=50,
    )
    out = s.expatriates()
    ids = [o.officer_id for o in out]
    assert "a" not in ids
    assert "b" in ids


def test_transfer_dead_blocked():
    s = BeastmanOfficerRosterSystem()
    _enlist(s)
    s.kill(officer_id="orc_argath", now_day=10)
    assert s.transfer_faction(
        officer_id="orc_argath",
        new_faction="bastok", now_day=11,
    ) is False


def test_officer_unknown():
    s = BeastmanOfficerRosterSystem()
    assert s.officer(
        officer_id="ghost",
    ) is None


def test_enum_counts():
    assert len(list(BeastmanRace)) == 8
    assert len(list(Trait)) == 8
    assert len(list(BeastmanStatus)) == 4
