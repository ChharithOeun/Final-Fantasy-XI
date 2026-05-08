"""Tests for server_age_milestones."""
from __future__ import annotations

from server.server_age_milestones import (
    Milestone, ServerAgeMilestones,
)


def test_set_launch_day():
    s = ServerAgeMilestones()
    assert s.set_launch_day(day=0) is True


def test_set_launch_negative_blocked():
    s = ServerAgeMilestones()
    assert s.set_launch_day(day=-1) is False


def test_set_launch_immutable():
    s = ServerAgeMilestones()
    s.set_launch_day(day=10)
    assert s.set_launch_day(day=20) is False


def test_age_in_days_no_launch_zero():
    s = ServerAgeMilestones()
    assert s.age_in_days(now_day=100) == 0


def test_age_in_days_after_launch():
    s = ServerAgeMilestones()
    s.set_launch_day(day=10)
    assert s.age_in_days(now_day=40) == 30


def test_age_clamps_zero():
    s = ServerAgeMilestones()
    s.set_launch_day(day=10)
    assert s.age_in_days(now_day=5) == 0


def test_tick_no_launch_empty():
    s = ServerAgeMilestones()
    assert s.tick(now_day=100) == []


def test_tick_fires_first_milestone():
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    events = s.tick(now_day=30)
    assert len(events) == 1
    assert events[0].milestone == Milestone.DAY_30


def test_tick_doesnt_refire():
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    s.tick(now_day=30)
    events = s.tick(now_day=31)
    assert events == []


def test_tick_fires_multiple_at_once():
    """If ticked very late, missed milestones fire all at once."""
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    events = s.tick(now_day=200)
    fired = {e.milestone for e in events}
    assert Milestone.DAY_30 in fired
    assert Milestone.DAY_90 in fired
    assert Milestone.DAY_180 in fired
    assert Milestone.DAY_365 not in fired


def test_next_milestone():
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    s.tick(now_day=30)
    nxt = s.next_milestone(now_day=30)
    assert nxt == Milestone.DAY_90


def test_next_milestone_no_launch():
    s = ServerAgeMilestones()
    assert s.next_milestone(now_day=100) is None


def test_next_milestone_post_5_year():
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    s.tick(now_day=2000)
    # All fired
    assert s.next_milestone(now_day=2001) is None


def test_fired_milestones():
    s = ServerAgeMilestones()
    s.set_launch_day(day=0)
    s.tick(now_day=400)
    fired = s.fired_milestones()
    assert Milestone.DAY_30 in fired
    assert Milestone.DAY_90 in fired
    assert Milestone.DAY_180 in fired
    assert Milestone.DAY_365 in fired
    assert Milestone.DAY_730 not in fired


def test_event_carries_correct_age():
    s = ServerAgeMilestones()
    s.set_launch_day(day=10)
    events = s.tick(now_day=400)
    # 400 - 10 = 390 server days
    for ev in events:
        assert ev.server_age_days == 390


def test_seven_milestones():
    assert len(list(Milestone)) == 7
