"""Tests for the beastman scrying pool."""
from __future__ import annotations

from server.beastman_scrying_pool import (
    BeastmanScryingPool,
    ScheduledEvent,
    ScryRank,
)


def _events() -> tuple[ScheduledEvent, ...]:
    return (
        ScheduledEvent(
            event_id="nm_spawn_a",
            fires_at=300,
            short_description="A king will rise.",
        ),
        ScheduledEvent(
            event_id="weather_shift_b",
            fires_at=4000,
            short_description="The skies will weep.",
        ),
        ScheduledEvent(
            event_id="festival_c",
            fires_at=50_000,
            short_description="A feast will gather.",
        ),
    )


def test_grant_focus():
    p = BeastmanScryingPool()
    assert p.grant_focus(player_id="kraw", amount=20)
    assert p.focus_for(player_id="kraw") == 20


def test_grant_focus_zero_rejected():
    p = BeastmanScryingPool()
    assert not p.grant_focus(player_id="kraw", amount=0)


def test_grant_focus_negative_rejected():
    p = BeastmanScryingPool()
    assert not p.grant_focus(player_id="kraw", amount=-5)


def test_focus_for_default():
    p = BeastmanScryingPool()
    assert p.focus_for(player_id="ghost") == 0


def test_focus_accumulates():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    p.grant_focus(player_id="kraw", amount=15)
    assert p.focus_for(player_id="kraw") == 25


def test_scry_light_basic():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=0,
        scheduled_events=_events(),
    )
    assert res.accepted
    assert res.focus_charged == 5
    # Light horizon = 600s; only nm_spawn_a at 300 is in window
    assert len(res.hits) == 1
    assert res.hits[0].event_id == "nm_spawn_a"


def test_scry_deep_includes_more():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=50)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.DEEP,
        now_seconds=0,
        scheduled_events=_events(),
    )
    assert res.focus_charged == 25
    assert len(res.hits) == 2


def test_scry_true_includes_all():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=100)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=0,
        scheduled_events=_events(),
    )
    assert res.focus_charged == 100
    assert len(res.hits) == 3


def test_scry_insufficient_focus():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=2)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=0,
        scheduled_events=_events(),
    )
    assert not res.accepted


def test_scry_true_cooldown():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=200)
    p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=0,
        scheduled_events=_events(),
    )
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=1000,
        scheduled_events=_events(),
    )
    assert not res.accepted


def test_scry_true_after_cooldown():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=200)
    p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=0,
        scheduled_events=_events(),
    )
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=86_500,
        scheduled_events=_events(),
    )
    assert res.accepted


def test_scry_charges_focus():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=0,
        scheduled_events=_events(),
    )
    assert p.focus_for(player_id="kraw") == 5


def test_scry_no_events_in_window():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=10_000,
        scheduled_events=_events(),
    )
    assert res.accepted
    assert res.hits == ()


def test_scry_excludes_past_events():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=400,
        scheduled_events=_events(),
    )
    # nm_spawn_a at 300 is now in the past, should be excluded
    assert all(h.fires_at >= 400 for h in res.hits)


def test_scry_sorted_output():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=200)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.TRUE,
        now_seconds=0,
        scheduled_events=_events(),
    )
    times = [h.fires_at for h in res.hits]
    assert times == sorted(times)


def test_per_player_focus_isolation():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="alice", amount=10)
    assert p.focus_for(player_id="bob") == 0


def test_per_player_true_cooldown_isolation():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="alice", amount=200)
    p.grant_focus(player_id="bob", amount=200)
    p.scry(
        player_id="alice",
        rank=ScryRank.TRUE,
        now_seconds=0,
        scheduled_events=_events(),
    )
    res = p.scry(
        player_id="bob",
        rank=ScryRank.TRUE,
        now_seconds=100,
        scheduled_events=_events(),
    )
    assert res.accepted


def test_total_players_with_focus():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="alice", amount=10)
    p.grant_focus(player_id="bob", amount=20)
    assert p.total_players_with_focus() == 2


def test_scry_empty_event_list():
    p = BeastmanScryingPool()
    p.grant_focus(player_id="kraw", amount=10)
    res = p.scry(
        player_id="kraw",
        rank=ScryRank.LIGHT,
        now_seconds=0,
        scheduled_events=(),
    )
    assert res.accepted
    assert res.hits == ()
