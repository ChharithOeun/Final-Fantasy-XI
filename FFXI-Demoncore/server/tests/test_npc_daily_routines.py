"""Tests for NPC daily routine schedules."""
from __future__ import annotations

import pytest

from server.npc_daily_routines import (
    NPCRoutineRegistry,
    NPCSchedule,
    Posture,
    Routine,
    TimeWindow,
    patrol_guard_schedule,
    shopkeeper_schedule,
)


def test_time_window_basic_coverage():
    w = TimeWindow(8, 12, Routine.TEND_SHOP, "shop_1")
    assert w.covers(8)
    assert w.covers(11)
    assert not w.covers(12)
    assert not w.covers(7)
    assert w.duration_hours == 4


def test_time_window_rejects_zero_or_negative_duration():
    with pytest.raises(ValueError):
        TimeWindow(8, 8, Routine.TEND_SHOP, "shop_1")
    with pytest.raises(ValueError):
        TimeWindow(12, 8, Routine.TEND_SHOP, "shop_1")


def test_time_window_wrap_past_midnight():
    """A window from 22 to 27 (which is 3am the next day) covers
    22, 23, 0, 1, 2."""
    w = TimeWindow(22, 27, Routine.SOCIALIZE, "tavern_1")
    assert w.covers(22)
    assert w.covers(23)
    assert w.covers(0)
    assert w.covers(2)
    assert not w.covers(3)
    assert not w.covers(21)


def test_overlapping_windows_rejected():
    with pytest.raises(ValueError):
        NPCSchedule(
            npc_id="bad",
            windows=(
                TimeWindow(8, 12, Routine.TEND_SHOP, "shop"),
                TimeWindow(11, 14, Routine.LUNCH, "shop"),
            ),
        )


def test_active_window_at_finds_match():
    sched = NPCSchedule(
        npc_id="alice",
        windows=(
            TimeWindow(8, 12, Routine.TEND_SHOP, "shop"),
            TimeWindow(13, 18, Routine.TEND_SHOP, "shop"),
        ),
    )
    w = sched.active_window_at(10)
    assert w is not None
    assert w.routine == Routine.TEND_SHOP


def test_active_window_at_returns_none_for_gap():
    sched = NPCSchedule(
        npc_id="alice",
        windows=(
            TimeWindow(8, 12, Routine.TEND_SHOP, "shop"),
        ),
    )
    assert sched.active_window_at(15) is None


def test_next_window_after_finds_following_window():
    sched = NPCSchedule(
        npc_id="alice",
        windows=(
            TimeWindow(8, 12, Routine.TEND_SHOP, "shop"),
            TimeWindow(13, 18, Routine.TEND_SHOP, "shop"),
            TimeWindow(19, 22, Routine.SOCIALIZE, "tavern"),
        ),
    )
    nw = sched.next_window_at(11)
    assert nw is not None
    assert nw.start_hour == 13
    nw2 = sched.next_window_at(20)
    # No window after 20 in the same day -> wraps to the first
    assert nw2.start_hour == 8


def test_shopkeeper_schedule_canonical():
    sched = shopkeeper_schedule(
        npc_id="dabihook",
        shop_waypoint="bastok_market_stall_3",
        home_waypoint="bastok_residence_3",
        tavern_waypoint="bastok_galkan_tavern",
    )
    # 9am = TEND_SHOP
    assert sched.active_window_at(9).routine == Routine.TEND_SHOP
    # 12:30 = LUNCH
    assert sched.active_window_at(12).routine == Routine.LUNCH
    # 20:30 = SOCIALIZE
    assert sched.active_window_at(20).routine == Routine.SOCIALIZE
    # 3am = SLEEP
    assert sched.active_window_at(3).routine == Routine.SLEEP


def test_patrol_guard_schedule_canonical():
    sched = patrol_guard_schedule(
        npc_id="guard_1",
        beat_waypoint="bastok_main_gate",
        barracks_waypoint="bastok_metalworks_barracks",
    )
    # 4am = PATROL
    assert sched.active_window_at(4).routine == Routine.PATROL
    # Posture is walking
    assert sched.active_window_at(4).posture == Posture.WALKING
    # 18:00 = SLEEP
    assert sched.active_window_at(18).routine == Routine.SLEEP


def test_registry_register_and_active_routine():
    reg = NPCRoutineRegistry()
    sched = shopkeeper_schedule(
        npc_id="dabihook",
        shop_waypoint="stall", home_waypoint="home",
        tavern_waypoint="tavern",
    )
    reg.register(schedule=sched)
    ar = reg.active_routine(npc_id="dabihook", hour=10)
    assert ar is not None
    assert ar.routine == Routine.TEND_SHOP
    assert ar.waypoint_id == "stall"


def test_registry_unknown_npc_returns_none():
    reg = NPCRoutineRegistry()
    assert reg.active_routine(npc_id="ghost", hour=10) is None


def test_registry_gap_resolves_to_on_call():
    """A schedule with allow_gaps=True returns ON_CALL at gap."""
    reg = NPCRoutineRegistry()
    sched = NPCSchedule(
        npc_id="quest_giver",
        windows=(
            TimeWindow(8, 10, Routine.OPEN_SHOP, "shop"),
        ),
        allow_gaps=True,
    )
    reg.register(schedule=sched)
    ar = reg.active_routine(npc_id="quest_giver", hour=15)
    assert ar.routine == Routine.ON_CALL


def test_registry_gap_with_no_allow_returns_none():
    reg = NPCRoutineRegistry()
    sched = NPCSchedule(
        npc_id="patrol",
        windows=(
            TimeWindow(8, 10, Routine.PATROL, "beat"),
        ),
        allow_gaps=False,
    )
    reg.register(schedule=sched)
    assert reg.active_routine(npc_id="patrol", hour=15) is None


def test_npcs_in_routine_filters():
    reg = NPCRoutineRegistry()
    for i in range(3):
        reg.register(schedule=shopkeeper_schedule(
            npc_id=f"shop_{i}",
            shop_waypoint="stall", home_waypoint="home",
            tavern_waypoint="tavern",
        ))
    reg.register(schedule=patrol_guard_schedule(
        npc_id="guard_1",
        beat_waypoint="gate",
        barracks_waypoint="barracks",
    ))
    # At 10am, all 3 shopkeepers should be tending shop
    tending = reg.npcs_in_routine(
        routine=Routine.TEND_SHOP, hour=10,
    )
    assert len(tending) == 3
    patrolling = reg.npcs_in_routine(
        routine=Routine.PATROL, hour=4,
    )
    assert "guard_1" in patrolling


def test_active_routine_hours_remaining():
    sched = NPCSchedule(
        npc_id="alice",
        windows=(
            TimeWindow(8, 12, Routine.TEND_SHOP, "shop"),
        ),
    )
    reg = NPCRoutineRegistry()
    reg.register(schedule=sched)
    ar = reg.active_routine(npc_id="alice", hour=8)
    assert ar.hours_remaining == 4
    ar2 = reg.active_routine(npc_id="alice", hour=11)
    assert ar2.hours_remaining == 1


def test_full_lifecycle_full_day():
    """Walk a full 24-hour day for a shopkeeper, verify each
    routine fires at the right time."""
    reg = NPCRoutineRegistry()
    reg.register(schedule=shopkeeper_schedule(
        npc_id="dabihook",
        shop_waypoint="stall", home_waypoint="home",
        tavern_waypoint="tavern",
    ))
    timeline: dict[int, Routine] = {}
    for hour in range(24):
        ar = reg.active_routine(npc_id="dabihook", hour=hour)
        timeline[hour] = ar.routine
    # Sanity sweep
    assert timeline[3] == Routine.SLEEP
    assert timeline[7] == Routine.TRAVEL
    assert timeline[10] == Routine.TEND_SHOP
    assert timeline[12] == Routine.LUNCH
    assert timeline[15] == Routine.TEND_SHOP
    assert timeline[19] == Routine.SOCIALIZE
    assert timeline[22] == Routine.TRAVEL
