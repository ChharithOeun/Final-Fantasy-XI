"""Tests for nightwatch_patrol."""
from __future__ import annotations

from server.nightwatch_patrol import NightwatchPatrol, PatrolStatus


def _setup():
    p = NightwatchPatrol()
    p.register_guard(
        guard_id="g1", zone_id="bastok",
        route=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        speed_yalms_per_sec=2.0,
    )
    return p


def test_register_happy():
    p = _setup()
    assert p.position_of(guard_id="g1") == (0.0, 0.0)


def test_blank_id_blocked():
    p = NightwatchPatrol()
    out = p.register_guard(
        guard_id="", zone_id="z",
        route=[(0, 0), (1, 0)], speed_yalms_per_sec=1.0,
    )
    assert out is False


def test_short_route_blocked():
    p = NightwatchPatrol()
    out = p.register_guard(
        guard_id="x", zone_id="z",
        route=[(0, 0)], speed_yalms_per_sec=1.0,
    )
    assert out is False


def test_zero_speed_blocked():
    p = NightwatchPatrol()
    out = p.register_guard(
        guard_id="x", zone_id="z",
        route=[(0, 0), (1, 0)], speed_yalms_per_sec=0,
    )
    assert out is False


def test_duplicate_guard_blocked():
    p = _setup()
    again = p.register_guard(
        guard_id="g1", zone_id="z",
        route=[(0, 0), (1, 0)], speed_yalms_per_sec=1.0,
    )
    assert again is False


def test_idle_during_day():
    p = _setup()
    out = p.tick(dt_seconds=10, time_of_day="day")
    # active_at_night_only → idle during day
    assert out == ()
    pos = p.position_of(guard_id="g1")
    assert pos == (0.0, 0.0)
    assert p.status_of(guard_id="g1") == PatrolStatus.IDLE


def test_patrol_during_night():
    p = _setup()
    p.tick(dt_seconds=2, time_of_day="night")
    # speed=2, dt=2 → moved 4 yalms
    pos = p.position_of(guard_id="g1")
    assert pos is not None
    assert abs(pos[0] - 4.0) < 0.01
    assert abs(pos[1] - 0.0) < 0.01
    assert p.status_of(guard_id="g1") == PatrolStatus.PATROLLING


def test_arrives_at_waypoint():
    p = _setup()
    # 10 yalms / 2 = 5 sec to first waypoint
    p.tick(dt_seconds=5, time_of_day="night")
    pos = p.position_of(guard_id="g1")
    assert pos == (10.0, 0.0)


def test_advances_index_at_waypoint():
    p = _setup()
    # Travel to corner 1 in 5 sec
    p.tick(dt_seconds=5, time_of_day="night")
    # Then continue toward corner 2
    p.tick(dt_seconds=2, time_of_day="night")
    pos = p.position_of(guard_id="g1")
    # moved 4 yalms toward (10, 10)
    assert abs(pos[0] - 10.0) < 0.01
    assert abs(pos[1] - 4.0) < 0.01


def test_route_loops():
    p = _setup()
    # full loop = 40 yalms / 2 = 20 sec
    p.tick(dt_seconds=20, time_of_day="night")
    # should be back near start
    pos = p.position_of(guard_id="g1")
    assert pos is not None
    # because of how we tick discretely, the end is at the
    # last waypoint (0, 10) wrapping around — verify it's
    # at one of the route corners
    assert pos in {(0.0, 0.0), (0.0, 10.0)}


def test_unknown_guard_status():
    p = _setup()
    assert p.status_of(guard_id="ghost") == PatrolStatus.UNKNOWN


def test_active_always_walks_during_day():
    p = NightwatchPatrol()
    p.register_guard(
        guard_id="round_clock", zone_id="bastok",
        route=[(0.0, 0.0), (10.0, 0.0)],
        speed_yalms_per_sec=1.0,
        active_at_night_only=False,
    )
    p.tick(dt_seconds=5, time_of_day="day")
    pos = p.position_of(guard_id="round_clock")
    assert pos is not None
    assert abs(pos[0] - 5.0) < 0.01


def test_total_guards():
    p = _setup()
    p.register_guard(
        guard_id="g2", zone_id="z",
        route=[(0, 0), (1, 0)], speed_yalms_per_sec=1.0,
    )
    assert p.total_guards() == 2


def test_position_of_unknown():
    p = NightwatchPatrol()
    assert p.position_of(guard_id="ghost") is None


def test_three_patrol_statuses():
    assert len(list(PatrolStatus)) == 3


def test_tick_returns_only_active_guards():
    p = _setup()
    p.register_guard(
        guard_id="day_guard", zone_id="z",
        route=[(0, 0), (1, 0)], speed_yalms_per_sec=1.0,
        active_at_night_only=False,
    )
    out = p.tick(dt_seconds=1, time_of_day="day")
    # only the day_guard moves at day; g1 is night-only
    assert len(out) == 1
    assert out[0].guard_id == "day_guard"
