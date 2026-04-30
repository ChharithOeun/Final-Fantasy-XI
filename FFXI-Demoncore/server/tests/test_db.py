"""Tests for the sqlite persistence layer.

Run:  python -m pytest server/tests/test_db.py -v
"""
import time
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.db import AgentDB
from agent_orchestrator.loader import AgentProfile


def make_profile(agent_id: str, tier: str = "2_reflection", **overrides) -> AgentProfile:
    raw = {
        "id": agent_id,
        "name": agent_id.title(),
        "zone": "bastok_markets",
        "position": [0, 0, 0],
        "tier": tier,
        "role": agent_id,
        "race": "hume",
        "gender": "m",
        "starting_memory": "I existed yesterday",
        "personality": "Generic",
        "mood_axes": ["content", "gruff"],
        "starting_mood": "content",
        "goals": ["test goal one", "test goal two"],
        "journal_seed": "Day 0. I exist.",
    }
    raw.update(overrides)
    return AgentProfile(
        id=raw["id"], name=raw["name"], zone=raw["zone"],
        position=tuple(raw["position"]),
        tier=raw["tier"], role=raw["role"],
        race=raw["race"], gender=raw["gender"],
        voice_profile=None, appearance=None, raw=raw,
    )


def test_upsert_and_list():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("a1"))
    db.upsert_agent(make_profile("a2", zone="windurst_woods"))
    assert len(db.list_agents()) == 2
    assert len(db.list_agents(zone="bastok_markets")) == 1
    assert len(db.list_agents(tier="2_reflection")) == 2


def test_tier2_state_bootstrapped():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("zaldon"))
    state = db.get_tier2_state("zaldon")
    assert state is not None
    assert state.mood == "content"
    assert "yesterday" in state.memory_summary


def test_tier3_state_bootstrapped():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("cid", tier="3_hero"))
    state = db.get_tier3_state("cid")
    assert state is not None
    assert state.current_goal == "test goal one"
    assert len(state.journal) == 1
    assert state.journal[0]["entry"] == "Day 0. I exist."


def test_tier2_update_and_due():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("zaldon"))
    # Just-loaded agent is due (last_reflection_at = 0)
    assert "zaldon" in db.tier2_due_for_reflection(interval_seconds=10)
    db.update_tier2("zaldon", "gruff", "Outlaw broke a barrel near my stall")
    state = db.get_tier2_state("zaldon")
    assert state.mood == "gruff"
    # Now reflected; not due for the next 5 minutes
    due = db.tier2_due_for_reflection(interval_seconds=300)
    assert "zaldon" not in due


def test_tier3_update_appends_journal():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("cid", tier="3_hero"))
    db.update_tier3(
        "cid",
        current_goal="test goal two",
        append_journal={"ts": int(time.time()), "entry": "Day 1. Workshop fire."},
    )
    state = db.get_tier3_state("cid")
    assert state.current_goal == "test goal two"
    assert len(state.journal) == 2
    assert "Workshop fire" in state.journal[1]["entry"]


def test_event_inbox_fifo():
    db = AgentDB(":memory:")
    db.upsert_agent(make_profile("zaldon"))
    db.push_event("zaldon", "aoe_near", {"distance": 200})
    db.push_event("zaldon", "outlaw_walked_past", None)
    drained = db.drain_events("zaldon")
    assert len(drained) == 2
    assert drained[0]["event_kind"] == "aoe_near"
    # Idempotent: re-draining yields no events
    assert db.drain_events("zaldon") == []


def test_upsert_idempotent():
    db = AgentDB(":memory:")
    p = make_profile("zaldon")
    db.upsert_agent(p)
    db.update_tier2("zaldon", "gruff", "I am gruff now")
    # Re-upsert (e.g. orchestrator hot-reloads agents on YAML edit)
    db.upsert_agent(p)
    # State should NOT be reset (INSERT OR IGNORE on the state row)
    state = db.get_tier2_state("zaldon")
    assert state.mood == "gruff"
    assert state.memory_summary == "I am gruff now"
