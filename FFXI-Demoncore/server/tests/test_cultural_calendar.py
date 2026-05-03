"""Tests for the cultural calendar."""
from __future__ import annotations

import pytest

from server.cultural_calendar import (
    CulturalCalendar,
    CulturalEvent,
    EventStance,
    PeriodKind,
    VendorSpecial,
    seed_default_calendar,
)


def _basic_event(
    event_id: str = "test_event",
    start: int = 100, end: int = 105,
    stance: EventStance = EventStance.WELCOMING,
) -> CulturalEvent:
    return CulturalEvent(
        event_id=event_id,
        label="Test Event",
        faction_id="bastok",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=start,
        end_day_of_year=end,
        stance=stance,
    )


def test_event_doy_validation():
    with pytest.raises(ValueError):
        _basic_event(start=0, end=5)
    with pytest.raises(ValueError):
        _basic_event(start=100, end=400)


def test_event_active_within_window():
    e = _basic_event(start=100, end=105)
    assert e.is_active_on(100)
    assert e.is_active_on(102)
    assert e.is_active_on(105)
    assert not e.is_active_on(99)
    assert not e.is_active_on(106)


def test_event_wraps_year_end():
    e = _basic_event(start=360, end=5)
    assert e.is_active_on(360)
    assert e.is_active_on(364)
    assert e.is_active_on(1)
    assert e.is_active_on(5)
    assert not e.is_active_on(6)
    assert not e.is_active_on(359)


def test_register_and_active_at():
    cal = CulturalCalendar()
    cal.register(_basic_event(event_id="a", start=100, end=105))
    cal.register(_basic_event(event_id="b", start=200, end=205))
    active = cal.active_events_at(day_of_year=102)
    assert len(active) == 1
    assert active[0].event_id == "a"


def test_active_at_filters_by_faction():
    cal = CulturalCalendar()
    cal.register(_basic_event(event_id="a", start=100, end=105))
    e2 = CulturalEvent(
        event_id="b", label="x", faction_id="windurst",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=100, end_day_of_year=105,
    )
    cal.register(e2)
    active = cal.active_events_at(
        day_of_year=102, faction_id="bastok",
    )
    assert {e.event_id for e in active} == {"a"}


def test_event_stance_lookup():
    cal = CulturalCalendar()
    cal.register(_basic_event(
        event_id="hostile_event",
        stance=EventStance.HOSTILE,
    ))
    assert cal.event_stance_for_outsider(
        "hostile_event",
    ) == EventStance.HOSTILE
    assert cal.event_stance_for_outsider("ghost") is None


def test_vendor_specials_listed():
    e = CulturalEvent(
        event_id="festival", label="x", faction_id="bastok",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=100, end_day_of_year=102,
        vendor_specials=(
            VendorSpecial(
                item_id="commemorative_pin",
                is_event_exclusive=True,
            ),
        ),
    )
    cal = CulturalCalendar()
    cal.register(e)
    specials = cal.vendor_specials_for("festival")
    assert len(specials) == 1
    assert specials[0].item_id == "commemorative_pin"


def test_participate_unknown_event_rejected():
    cal = CulturalCalendar()
    res = cal.participate(
        player_id="alice", event_id="ghost",
        day_of_year=100,
    )
    assert not res.accepted


def test_participate_outside_window_rejected():
    cal = CulturalCalendar()
    cal.register(_basic_event(
        event_id="festival", start=100, end=102,
    ))
    res = cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=200,
    )
    assert not res.accepted
    assert "not currently active" in res.reason


def test_participate_hostile_event_rejected():
    cal = CulturalCalendar()
    cal.register(_basic_event(
        event_id="yagudo_equinox", start=80, end=82,
        stance=EventStance.HOSTILE,
    ))
    res = cal.participate(
        player_id="alice", event_id="yagudo_equinox",
        day_of_year=80,
    )
    assert not res.accepted


def test_participate_first_time_grants_rep():
    cal = CulturalCalendar()
    cal.register(CulturalEvent(
        event_id="festival", label="x", faction_id="bastok",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=100, end_day_of_year=102,
        participation_rep_reward=20,
    ))
    res = cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=101,
    )
    assert res.accepted
    assert res.rep_gained == 20


def test_participate_twice_in_same_cycle_rejected():
    cal = CulturalCalendar()
    cal.register(CulturalEvent(
        event_id="festival", label="x", faction_id="bastok",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=100, end_day_of_year=102,
        participation_rep_reward=20,
    ))
    cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=101,
    )
    res = cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=102,
    )
    assert not res.accepted
    assert "already" in res.reason


def test_reset_year_clears_participation():
    cal = CulturalCalendar()
    cal.register(CulturalEvent(
        event_id="festival", label="x", faction_id="bastok",
        period_kind=PeriodKind.ANNUAL_FIXED,
        start_day_of_year=100, end_day_of_year=102,
        participation_rep_reward=20,
    ))
    cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=101,
    )
    cal.reset_year()
    res = cal.participate(
        player_id="alice", event_id="festival",
        day_of_year=101,
    )
    assert res.accepted


def test_default_seed_includes_canonical_events():
    cal = seed_default_calendar(CulturalCalendar())
    assert cal.event("bastok_republic_day") is not None
    assert cal.event("yagudo_equinox") is not None
    assert cal.event("goblin_market_festival") is not None
    assert cal.event("orc_war_song_night") is not None
    # Yagudo is HOSTILE; Bastok is WELCOMING
    assert cal.event_stance_for_outsider(
        "yagudo_equinox",
    ) == EventStance.HOSTILE
    assert cal.event_stance_for_outsider(
        "bastok_republic_day",
    ) == EventStance.WELCOMING


def test_default_seed_orc_event_wraps_year_end():
    cal = seed_default_calendar(CulturalCalendar())
    e = cal.event("orc_war_song_night")
    assert e.is_active_on(361)
    assert e.is_active_on(2)
    assert not e.is_active_on(100)


def test_full_lifecycle_alice_attends_festivals():
    """Alice attends Bastok Republic Day, then Goblin Market
    Festival. Both grant rep. She tries to crash the Yagudo
    Equinox and gets rejected."""
    cal = seed_default_calendar(CulturalCalendar())
    bastok = cal.participate(
        player_id="alice",
        event_id="bastok_republic_day",
        day_of_year=121,
    )
    assert bastok.accepted
    goblin = cal.participate(
        player_id="alice",
        event_id="goblin_market_festival",
        day_of_year=302,
    )
    assert goblin.accepted
    yagudo = cal.participate(
        player_id="alice",
        event_id="yagudo_equinox",
        day_of_year=80,
    )
    assert not yagudo.accepted
    # Participation tracked
    seen = cal.participations_of("alice")
    assert "bastok_republic_day" in seen
    assert "goblin_market_festival" in seen
    assert "yagudo_equinox" not in seen
