"""Tests for the scheduler.

Run:  python -m pytest server/tests/test_scheduler.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.db import AgentDB
from agent_orchestrator.game_clock import (
    WALL_SECONDS_PER_VANADIEL_DAY,
    WALL_SECONDS_PER_VANADIEL_HOUR,
    vanadiel_at,
)
from agent_orchestrator.loader import AgentProfile
from agent_orchestrator.scheduler import Scheduler


def make_profile(agent_id: str, *, schedule=None, role: str = None,
                 mood_axes=None, tier: str = "2_reflection",
                 zone: str = "bastok_markets") -> AgentProfile:
    raw = {
        "id": agent_id,
        "name": agent_id.title(),
        "zone": zone,
        "position": [0, 0, 0],
        "tier": tier,
        "role": role or agent_id,
        "race": "hume",
        "gender": "m",
        "personality": "Generic",
        "starting_memory": "I exist",
        "mood_axes": mood_axes or ["content", "gruff", "drunk", "alert"],
        "starting_mood": "content",
        "bark_pool": {"content": ["hi"]},
        "schedule": schedule or [],
        "relationships": {},
        "goals": ["x"],
        "journal_seed": "Day 0",
    }
    return AgentProfile(
        id=raw["id"], name=raw["name"], zone=raw["zone"],
        position=tuple(raw["position"]), tier=raw["tier"],
        role=raw["role"], race=raw["race"], gender=raw["gender"],
        voice_profile=None, appearance=None, raw=raw,
    )


def test_scheduler_fires_morning_environmental():
    """At Vana'diel hour 7 (daily_loop_morning fires for tavern_drunk
    role -> mood content +0.2)."""
    db = AgentDB(":memory:")
    profile = make_profile("bondrak", role="tavern_drunk",
                           mood_axes=["content", "drunk", "melancholy"])
    db.upsert_agent(profile)
    db.update_tier2("bondrak", "drunk", "still drunk from last night")

    scheduler = Scheduler(db)
    vana_morning = vanadiel_at(7 * WALL_SECONDS_PER_VANADIEL_HOUR)
    report = scheduler.tick(vana_morning, {profile.id: profile})

    assert ("bastok_markets", "daily_loop_morning") in \
        report["environmental_events_fired"]

    # The mood event should have flipped Bondrak from drunk -> content
    state = db.get_tier2_state("bondrak")
    assert state.mood == "content"


def test_scheduler_fires_evening_to_drunk():
    """Bondrak goes drunk at 18:00."""
    db = AgentDB(":memory:")
    profile = make_profile("bondrak", role="tavern_drunk",
                           mood_axes=["content", "drunk", "melancholy"])
    db.upsert_agent(profile)
    db.update_tier2("bondrak", "content", "")

    scheduler = Scheduler(db)
    vana_evening = vanadiel_at(18 * WALL_SECONDS_PER_VANADIEL_HOUR)
    scheduler.tick(vana_evening, {profile.id: profile})

    state = db.get_tier2_state("bondrak")
    assert state.mood == "drunk"


def test_scheduler_idempotent_within_same_hour():
    """Calling tick twice in the same Vana'diel hour fires environmental
    events only once."""
    db = AgentDB(":memory:")
    profile = make_profile("bondrak", role="tavern_drunk",
                           mood_axes=["content", "drunk"])
    db.upsert_agent(profile)
    scheduler = Scheduler(db)

    vana = vanadiel_at(7 * WALL_SECONDS_PER_VANADIEL_HOUR)
    r1 = scheduler.tick(vana, {profile.id: profile})
    r2 = scheduler.tick(vana, {profile.id: profile})
    assert r1["environmental_events_fired"]
    assert not r2["environmental_events_fired"]


def test_scheduler_re_fires_next_day():
    """The same hour next Vana'diel-day fires the event again."""
    db = AgentDB(":memory:")
    profile = make_profile("bondrak", role="tavern_drunk",
                           mood_axes=["content", "drunk"])
    db.upsert_agent(profile)
    scheduler = Scheduler(db)

    vana_today = vanadiel_at(7 * WALL_SECONDS_PER_VANADIEL_HOUR)
    scheduler.tick(vana_today, {profile.id: profile})

    vana_tomorrow = vanadiel_at(
        7 * WALL_SECONDS_PER_VANADIEL_HOUR + WALL_SECONDS_PER_VANADIEL_DAY
    )
    r2 = scheduler.tick(vana_tomorrow, {profile.id: profile})
    assert ("bastok_markets", "daily_loop_morning") in \
        r2["environmental_events_fired"]


def test_scheduler_advances_through_schedule_slots():
    """As Vana'diel time progresses, the agent's schedule slot advances."""
    schedule = [
        ["06:00", "stall_setup",  "setup_stall"],
        ["12:00", "tavern_lunch", "lunch_break"],
        ["19:00", "stall_pack",   "evening_pack_up"],
    ]
    db = AgentDB(":memory:")
    profile = make_profile("zaldon", schedule=schedule, role="vendor_zaldon",
                           mood_axes=["content", "gruff"])
    db.upsert_agent(profile)
    scheduler = Scheduler(db)

    morning = vanadiel_at(8 * WALL_SECONDS_PER_VANADIEL_HOUR)
    afternoon = vanadiel_at(15 * WALL_SECONDS_PER_VANADIEL_HOUR)
    evening = vanadiel_at(20 * WALL_SECONDS_PER_VANADIEL_HOUR)

    r1 = scheduler.tick(morning, {profile.id: profile})
    r2 = scheduler.tick(afternoon, {profile.id: profile})
    r3 = scheduler.tick(evening, {profile.id: profile})

    fired_indices = [
        idx for (aid, idx) in (r1["schedule_events_fired"]
                                + r2["schedule_events_fired"]
                                + r3["schedule_events_fired"])
        if aid == "zaldon"
    ]
    assert fired_indices == [0, 1, 2]


def test_scheduler_pickpocket_alert_at_daytime():
    """Mavi the pickpocket goes from content (night) to alert (daytime).

    Per the event_deltas table:
        ("daytime", "*pickpocket*") -> ("alert", +0.2)
    """
    db = AgentDB(":memory:")
    profile = make_profile("mavi", role="pickpocket",
                           mood_axes=["alert", "content", "fearful"])
    db.upsert_agent(profile)

    schedule = [
        ["09:00", "alley", "scout_marks"],
    ]
    profile.raw["schedule"] = schedule

    scheduler = Scheduler(db)
    db.update_tier2("mavi", "content", "")

    # Morning hour fires both daily_loop_morning AND the schedule slot's
    # animation hint "scout_marks" -> "daytime" event.
    morning = vanadiel_at(9 * WALL_SECONDS_PER_VANADIEL_HOUR)
    scheduler.tick(morning, {profile.id: profile})

    state = db.get_tier2_state("mavi")
    assert state.mood == "alert"


def test_scheduler_zone_isolation():
    """Environmental events fire per zone — agents in different zones
    don't interfere."""
    db = AgentDB(":memory:")
    p1 = make_profile("bastok_npc", zone="bastok_markets")
    p2 = make_profile("sandy_npc",  zone="northern_san_doria")
    db.upsert_agent(p1)
    db.upsert_agent(p2)

    scheduler = Scheduler(db)
    vana = vanadiel_at(18 * WALL_SECONDS_PER_VANADIEL_HOUR)
    report = scheduler.tick(vana, {p.id: p for p in (p1, p2)})

    # Both zones got the event
    zones_fired = {z for (z, _) in report["environmental_events_fired"]}
    assert zones_fired == {"bastok_markets", "northern_san_doria"}
