"""Tests for the beastman seasonal events."""
from __future__ import annotations

from server.beastman_seasonal_events import (
    BeastmanSeasonalEvents,
    EventRace,
    EventState,
)


def _seed(s):
    s.register_event(
        event_id="egg_feast",
        race=EventRace.YAGUDO,
        start_day=80,
        duration_days=14,
        prize_per_day_limit=2,
        prize_item_id="prime_feather",
    )


def test_register():
    s = BeastmanSeasonalEvents()
    _seed(s)
    assert s.total_events() == 1


def test_register_duplicate():
    s = BeastmanSeasonalEvents()
    _seed(s)
    res = s.register_event(
        event_id="egg_feast",
        race=EventRace.QUADAV,
        start_day=10,
        duration_days=5,
        prize_per_day_limit=1,
        prize_item_id="x",
    )
    assert res is None


def test_register_zero_duration():
    s = BeastmanSeasonalEvents()
    res = s.register_event(
        event_id="bad",
        race=EventRace.YAGUDO,
        start_day=0,
        duration_days=0,
        prize_per_day_limit=1,
        prize_item_id="x",
    )
    assert res is None


def test_register_zero_limit():
    s = BeastmanSeasonalEvents()
    res = s.register_event(
        event_id="bad",
        race=EventRace.YAGUDO,
        start_day=0,
        duration_days=5,
        prize_per_day_limit=0,
        prize_item_id="x",
    )
    assert res is None


def test_register_empty_item():
    s = BeastmanSeasonalEvents()
    res = s.register_event(
        event_id="bad",
        race=EventRace.YAGUDO,
        start_day=0,
        duration_days=5,
        prize_per_day_limit=1,
        prize_item_id="",
    )
    assert res is None


def test_register_negative_start():
    s = BeastmanSeasonalEvents()
    res = s.register_event(
        event_id="bad",
        race=EventRace.YAGUDO,
        start_day=-1,
        duration_days=5,
        prize_per_day_limit=1,
        prize_item_id="x",
    )
    assert res is None


def test_open_before_start_rejected():
    s = BeastmanSeasonalEvents()
    _seed(s)
    res = s.open_event(event_id="egg_feast", now_day=50)
    assert not res


def test_open_at_start():
    s = BeastmanSeasonalEvents()
    _seed(s)
    assert s.open_event(event_id="egg_feast", now_day=80)


def test_open_unknown():
    s = BeastmanSeasonalEvents()
    assert not s.open_event(event_id="ghost", now_day=0)


def test_open_double_rejected():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    res = s.open_event(event_id="egg_feast", now_day=82)
    assert not res


def test_close_event():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    assert s.close_event(event_id="egg_feast", now_day=85)


def test_close_unopened():
    s = BeastmanSeasonalEvents()
    _seed(s)
    res = s.close_event(event_id="egg_feast", now_day=85)
    assert not res


def test_state_lazy_auto_close():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    state = s.state_for(event_id="egg_feast", now_day=200)
    assert state == EventState.CLOSED


def test_state_unknown_pending():
    s = BeastmanSeasonalEvents()
    assert s.state_for(
        event_id="ghost", now_day=0,
    ) == EventState.PENDING


def test_claim_basic():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    res = s.claim(
        player_id="kraw",
        event_id="egg_feast",
        now_day=85,
    )
    assert res.accepted
    assert res.item_id == "prime_feather"
    assert res.claims_today == 1


def test_claim_daily_limit():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    s.claim(player_id="kraw", event_id="egg_feast", now_day=85)
    s.claim(player_id="kraw", event_id="egg_feast", now_day=85)
    res = s.claim(
        player_id="kraw", event_id="egg_feast", now_day=85,
    )
    assert not res.accepted


def test_claim_resets_next_day():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    s.claim(player_id="kraw", event_id="egg_feast", now_day=85)
    s.claim(player_id="kraw", event_id="egg_feast", now_day=85)
    res = s.claim(
        player_id="kraw", event_id="egg_feast", now_day=86,
    )
    assert res.accepted


def test_claim_after_close():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    s.close_event(event_id="egg_feast", now_day=82)
    res = s.claim(
        player_id="kraw", event_id="egg_feast", now_day=83,
    )
    assert not res.accepted


def test_claim_not_open():
    s = BeastmanSeasonalEvents()
    _seed(s)
    res = s.claim(
        player_id="kraw", event_id="egg_feast", now_day=85,
    )
    assert not res.accepted


def test_claim_unknown_event():
    s = BeastmanSeasonalEvents()
    res = s.claim(
        player_id="kraw", event_id="ghost", now_day=0,
    )
    assert not res.accepted


def test_per_player_isolation():
    s = BeastmanSeasonalEvents()
    _seed(s)
    s.open_event(event_id="egg_feast", now_day=80)
    s.claim(player_id="alice", event_id="egg_feast", now_day=85)
    s.claim(player_id="alice", event_id="egg_feast", now_day=85)
    # Bob still gets full daily allotment
    res1 = s.claim(
        player_id="bob", event_id="egg_feast", now_day=85,
    )
    res2 = s.claim(
        player_id="bob", event_id="egg_feast", now_day=85,
    )
    assert res1.accepted
    assert res2.accepted
