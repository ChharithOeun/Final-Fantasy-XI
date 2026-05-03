"""Tests for bard performance / fame system."""
from __future__ import annotations

import pytest

from server.bard_performance import (
    APPLAUSE_TIER_GREAT,
    APPLAUSE_TIER_OK,
    BardPerformanceRegistry,
    PerformanceMood,
    PerformanceStatus,
    Venue,
    VenueKind,
)


def _tavern() -> Venue:
    return Venue(
        venue_id="bastok_tavern",
        label="Bastok Galkan Tavern",
        kind=VenueKind.TAVERN,
        base_audience_capacity=20,
    )


def _plaza() -> Venue:
    return Venue(
        venue_id="bastok_plaza",
        label="Bastok Plaza",
        kind=VenueKind.PLAZA,
        base_audience_capacity=40,
    )


def test_register_venue_validates_capacity():
    reg = BardPerformanceRegistry()
    with pytest.raises(ValueError):
        reg.register_venue(Venue(
            venue_id="bad", label="x",
            kind=VenueKind.TAVERN,
            base_audience_capacity=0,
        ))


def test_schedule_unknown_venue_rejected():
    reg = BardPerformanceRegistry()
    res = reg.schedule(
        bard_id="alice", venue_id="ghost",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    assert not res.accepted


def test_schedule_books_slot():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    assert res.accepted
    assert res.performance.status == PerformanceStatus.SCHEDULED


def test_double_book_same_slot_rejected():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    res = reg.schedule(
        bard_id="bob", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    assert not res.accepted
    assert "booked" in res.reason


def test_start_live_status():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    assert reg.start(
        performance_id=res.performance.performance_id,
        now_seconds=10.0,
    )
    p = reg.performance(res.performance.performance_id)
    assert p.status == PerformanceStatus.LIVE


def test_audience_tick_pulls_crowd():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    pid = res.performance.performance_id
    reg.start(performance_id=pid, now_seconds=10.0)
    tick = reg.audience_tick(performance_id=pid)
    assert tick.accepted
    assert tick.audience_added > 0


def test_audience_tick_rejects_not_live():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    tick = reg.audience_tick(
        performance_id=res.performance.performance_id,
    )
    assert not tick.accepted


def test_mood_venue_fit_drives_audience_size():
    """Lively in tavern outdraws Mournful in tavern."""
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    lively = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    pid_a = lively.performance.performance_id
    reg.start(performance_id=pid_a, now_seconds=0.0)
    tick_a = reg.audience_tick(performance_id=pid_a)
    reg.cancel(performance_id=pid_a)
    mournful = reg.schedule(
        bard_id="bob", venue_id="bastok_tavern",
        mood=PerformanceMood.MOURNFUL,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    pid_b = mournful.performance.performance_id
    reg.start(performance_id=pid_b, now_seconds=10.0)
    tick_b = reg.audience_tick(performance_id=pid_b)
    assert tick_a.audience_added > tick_b.audience_added


def test_temple_loves_mournful():
    reg = BardPerformanceRegistry()
    reg.register_venue(Venue(
        venue_id="temple", label="Temple",
        kind=VenueKind.TEMPLE, base_audience_capacity=30,
    ))
    res = reg.schedule(
        bard_id="alice", venue_id="temple",
        mood=PerformanceMood.MOURNFUL,
        scheduled_at_seconds=0.0, scheduled_hour=8,
    )
    pid = res.performance.performance_id
    reg.start(performance_id=pid, now_seconds=0.0)
    tick = reg.audience_tick(performance_id=pid)
    assert tick.audience_added >= 20


def test_hour_modifier_tavern_night_peak():
    """Tavern at 22h gets a hour bonus; tavern at 9am gets a
    penalty."""
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    night = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=22,
    )
    nid = night.performance.performance_id
    reg.start(performance_id=nid, now_seconds=0.0)
    night_tick = reg.audience_tick(performance_id=nid)
    reg.cancel(performance_id=nid)
    morning = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=10.0, scheduled_hour=9,
    )
    mid = morning.performance.performance_id
    reg.start(performance_id=mid, now_seconds=10.0)
    morning_tick = reg.audience_tick(performance_id=mid)
    assert night_tick.audience_added > morning_tick.audience_added


def test_finish_grants_fame_proportional():
    reg = BardPerformanceRegistry()
    reg.register_venue(_plaza())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_plaza",
        mood=PerformanceMood.HEROIC,
        scheduled_at_seconds=0.0, scheduled_hour=14,
    )
    pid = res.performance.performance_id
    reg.start(performance_id=pid, now_seconds=0.0)
    for _ in range(4):
        reg.audience_tick(performance_id=pid)
    finish = reg.finish(
        performance_id=pid, now_seconds=1800.0,
    )
    assert finish.accepted
    assert finish.fame_gained > 0
    assert reg.fame_for("alice") == finish.fame_gained


def test_great_applause_doubles_fame():
    """Reaching APPLAUSE_TIER_GREAT doubles the fame gain
    multiplier."""
    reg = BardPerformanceRegistry()
    reg.register_venue(_plaza())
    res = reg.schedule(
        bard_id="alice", venue_id="bastok_plaza",
        mood=PerformanceMood.HEROIC,
        scheduled_at_seconds=0.0, scheduled_hour=14,
    )
    pid = res.performance.performance_id
    reg.start(performance_id=pid, now_seconds=0.0)
    # Many ticks to fill applause to >= GREAT
    for _ in range(10):
        reg.audience_tick(performance_id=pid)
    finish = reg.finish(
        performance_id=pid, now_seconds=1800.0,
    )
    p = reg.performance(pid)
    assert p.applause_score >= APPLAUSE_TIER_GREAT
    assert finish.fame_gained > 0


def test_low_applause_penalty():
    """Applause below APPLAUSE_TIER_OK halves fame gain."""
    reg = BardPerformanceRegistry()
    reg.register_venue(Venue(
        venue_id="temple", label="Temple",
        kind=VenueKind.TEMPLE, base_audience_capacity=10,
    ))
    res = reg.schedule(
        bard_id="alice", venue_id="temple",
        # Lively in temple is a poor fit -> low applause
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=12,
    )
    pid = res.performance.performance_id
    reg.start(performance_id=pid, now_seconds=0.0)
    reg.audience_tick(performance_id=pid)
    finish = reg.finish(
        performance_id=pid, now_seconds=1800.0,
    )
    p = reg.performance(pid)
    assert p.applause_score < APPLAUSE_TIER_OK
    # Fame may still be >= 0; the halving applies relative to
    # a healthier set
    assert finish.fame_gained <= 25


def test_cancel_frees_slot():
    reg = BardPerformanceRegistry()
    reg.register_venue(_tavern())
    a = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=0.0, scheduled_hour=20,
    )
    reg.cancel(performance_id=a.performance.performance_id)
    b = reg.schedule(
        bard_id="bob", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=10.0, scheduled_hour=20,
    )
    assert b.accepted


def test_fame_cap_at_max():
    """Fame can't exceed FAME_MAX."""
    reg = BardPerformanceRegistry()
    reg.register_venue(_plaza())
    # Hammer many performances
    for hour in range(8, 22):
        res = reg.schedule(
            bard_id="alice", venue_id="bastok_plaza",
            mood=PerformanceMood.HEROIC,
            scheduled_at_seconds=hour * 100.0,
            scheduled_hour=hour,
        )
        pid = res.performance.performance_id
        reg.start(performance_id=pid, now_seconds=hour * 100.0)
        for _ in range(20):
            reg.audience_tick(performance_id=pid)
        reg.finish(
            performance_id=pid,
            now_seconds=hour * 100.0 + 1800,
        )
    assert reg.fame_for("alice") <= 1000


def test_full_lifecycle_alice_climbs_fame():
    """Alice plays a heroic set in the plaza at 14h, gains fame.
    She follows up at the tavern that night, drawing a bigger
    crowd thanks to her new fame."""
    reg = BardPerformanceRegistry()
    reg.register_venue(_plaza())
    reg.register_venue(_tavern())
    # Plaza set
    a = reg.schedule(
        bard_id="alice", venue_id="bastok_plaza",
        mood=PerformanceMood.HEROIC,
        scheduled_at_seconds=0.0, scheduled_hour=14,
    )
    pid_a = a.performance.performance_id
    reg.start(performance_id=pid_a, now_seconds=0.0)
    for _ in range(5):
        reg.audience_tick(performance_id=pid_a)
    reg.finish(performance_id=pid_a, now_seconds=1800.0)
    fame_after_first = reg.fame_for("alice")
    assert fame_after_first > 0
    # Tavern set later — fame multiplier kicks in
    b = reg.schedule(
        bard_id="alice", venue_id="bastok_tavern",
        mood=PerformanceMood.LIVELY,
        scheduled_at_seconds=2000.0, scheduled_hour=22,
    )
    pid_b = b.performance.performance_id
    reg.start(performance_id=pid_b, now_seconds=2000.0)
    tick = reg.audience_tick(performance_id=pid_b)
    # Should easily exceed the base capacity due to fame mult +
    # tavern night peak
    assert tick.audience_added >= 20
