"""Tests for the mood propagation module.

Run:  python -m pytest server/tests/test_mood_propagation.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.db import AgentDB
from agent_orchestrator.event_deltas import lookup_delta, nearest_in_axes
from agent_orchestrator.loader import AgentProfile
from agent_orchestrator.mood_propagation import (
    apply_event,
    propagate_once,
    _infer_relationship_kind,
)


def make_profile(agent_id: str, *, role: str = None,
                 mood_axes=None, relationships=None,
                 tier: str = "2_reflection") -> AgentProfile:
    raw = {
        "id": agent_id,
        "name": agent_id.title(),
        "zone": "bastok_markets",
        "position": [0, 0, 0],
        "tier": tier,
        "role": role or agent_id,
        "race": "hume",
        "gender": "m",
        "personality": "Generic",
        "starting_memory": "I existed",
        "mood_axes": mood_axes or ["content", "gruff", "melancholy"],
        "starting_mood": "content",
        "bark_pool": {"content": ["hi"]},
        "schedule": [],
        "relationships": relationships or {},
        "goals": ["x"],
        "journal_seed": "Day 0",
    }
    return AgentProfile(
        id=raw["id"], name=raw["name"], zone=raw["zone"],
        position=tuple(raw["position"]), tier=raw["tier"],
        role=raw["role"], race=raw["race"], gender=raw["gender"],
        voice_profile=None, appearance=None, raw=raw,
    )


# -------------------------- event lookup ----------------------------

def test_lookup_aoe_near_vendor():
    result = lookup_delta("aoe_near", "vendor_zaldon")
    assert result == ("gruff", 0.30)


def test_lookup_outlaw_pickpocket_is_content():
    """Pickpockets like seeing other criminals — peer recognition."""
    result = lookup_delta("outlaw_walked_past", "pickpocket_lurking")
    assert result == ("content", 0.20)


def test_lookup_no_match_returns_none():
    result = lookup_delta("never_heard_of_this_event", "anyone")
    assert result is None


def test_lookup_falls_through_to_wildcard():
    """aoe_near has a non-vendor wildcard fallback."""
    result = lookup_delta("aoe_near", "child_running")
    assert result == ("alert", 0.20)


def test_nearest_in_axes_exact_match():
    assert nearest_in_axes("gruff", ["content", "gruff", "melancholy"]) == "gruff"


def test_nearest_in_axes_proximity():
    """furious -> gruff via proximity map."""
    assert nearest_in_axes("furious", ["content", "gruff", "melancholy"]) == "gruff"


def test_nearest_in_axes_no_match_returns_none():
    """If nothing matches and no proximity hit, return None."""
    result = nearest_in_axes("nonsense_mood", ["content", "gruff"])
    assert result is None


# -------------------------- apply_event ----------------------------

def test_apply_event_aoe_flips_zaldon_to_gruff():
    db = AgentDB(":memory:")
    p = make_profile("vendor_zaldon", role="vendor_zaldon")
    db.upsert_agent(p)
    assert apply_event(db, p, "aoe_near") is True
    state = db.get_tier2_state("vendor_zaldon")
    assert state.mood == "gruff"
    assert "aoe_near -> gruff" in state.memory_summary


def test_apply_event_idempotent_when_already_in_mood():
    db = AgentDB(":memory:")
    p = make_profile("vendor_zaldon", role="vendor_zaldon")
    db.upsert_agent(p)
    db.update_tier2("vendor_zaldon", "gruff", "already gruff")
    # Same event should not flip mood (already gruff, no change)
    assert apply_event(db, p, "aoe_near") is False


def test_apply_event_proximity_fallback():
    """furious is not in axes; falls back to gruff via proximity."""
    db = AgentDB(":memory:")
    p = make_profile("vendor_x",
                     role="vendor_x",
                     mood_axes=["content", "gruff", "melancholy"])
    db.upsert_agent(p)
    apply_event(db, p, "friend_attacked")  # delta is furious +0.6
    state = db.get_tier2_state("vendor_x")
    assert state.mood == "gruff"  # proximity fallback


def test_apply_event_no_match_no_change():
    db = AgentDB(":memory:")
    p = make_profile("vendor_x", role="vendor_x")
    db.upsert_agent(p)
    assert apply_event(db, p, "ghost_riding_event") is False
    state = db.get_tier2_state("vendor_x")
    assert state.mood == "content"  # unchanged


def test_apply_event_skips_tier1_agent():
    """Tier 1 scripted+bark agents don't have moods."""
    db = AgentDB(":memory:")
    p = make_profile("crowd_npc", role="citizen", tier="1_scripted")
    # Tier 1 has different required fields; we just need it not to error
    p.raw.pop("personality", None)
    p.raw.pop("starting_memory", None)
    p.raw.pop("mood_axes", None)
    p.raw.pop("relationships", None)
    db.upsert_agent(p)
    # apply_event should silently no-op
    assert apply_event(db, p, "aoe_near") is False


# -------------------------- relationship kind inference ----------------------------

@pytest.mark.parametrize("descr,expected", [
    ("estranged daughter; complicated love",            "family"),
    ("son who wandered off years ago",                  "family"),
    ("best friend since boyhood",                       "best_friend"),
    ("lifelong drinking buddies",                       "best_friend"),
    ("professional respect; collaborates on airships",  "professional"),
    ("apprentice who passed her metalwork exam",        "mentor"),
    ("rival in the bardic guild",                       "rival"),
    ("hates this person",                               "adversary"),
    ("just some guy",                                   "acquaintance"),
])
def test_infer_relationship_kind(descr, expected):
    assert _infer_relationship_kind(descr) == expected


# -------------------------- propagation ----------------------------

def test_propagation_pulls_neutral_to_negative():
    """Cid is content; Cornelia (family) is gruff; Cid pulls toward gruff."""
    db = AgentDB(":memory:")
    cid = make_profile("hero_cid",
                       mood_axes=["content", "gruff", "melancholy", "weary"],
                       relationships={"hero_cornelia": "estranged daughter"})
    cornelia = make_profile("hero_cornelia",
                            mood_axes=["content", "gruff", "melancholy", "fearful"],
                            relationships={"hero_cid": "estranged father"})
    db.upsert_agent(cid)
    db.upsert_agent(cornelia)
    db.update_tier2("hero_cid", "content", "I'm fine")
    db.update_tier2("hero_cornelia", "gruff", "I'm angry today")

    profiles = {p.id: p for p in (cid, cornelia)}
    changes = propagate_once(db, profiles)

    # Cid should have been pulled toward Cornelia's gruff
    assert changes.get("hero_cid") == "gruff"
    state = db.get_tier2_state("hero_cid")
    assert state.mood == "gruff"


def test_propagation_no_change_when_already_aligned():
    db = AgentDB(":memory:")
    cid = make_profile("hero_cid",
                       relationships={"hero_volker": "best friend"})
    volker = make_profile("hero_volker",
                          relationships={"hero_cid": "best friend"})
    db.upsert_agent(cid)
    db.upsert_agent(volker)
    db.update_tier2("hero_cid", "gruff", "")
    db.update_tier2("hero_volker", "gruff", "")

    profiles = {p.id: p for p in (cid, volker)}
    changes = propagate_once(db, profiles)
    assert changes == {}


def test_propagation_acquaintance_too_weak_to_pull():
    """Acquaintance weight 0.2 < threshold 0.3 — no pull."""
    db = AgentDB(":memory:")
    a = make_profile("a", relationships={"b": "just some random person"})
    b = make_profile("b")
    db.upsert_agent(a)
    db.upsert_agent(b)
    db.update_tier2("a", "content", "")
    db.update_tier2("b", "gruff", "")

    profiles = {p.id: p for p in (a, b)}
    changes = propagate_once(db, profiles)
    assert "a" not in changes  # too weak


def test_propagation_uses_proximity_when_target_mood_missing_from_axes():
    """B is furious; A's axes don't include furious; A pulls toward gruff."""
    db = AgentDB(":memory:")
    a = make_profile("a",
                     mood_axes=["content", "gruff", "weary"],
                     relationships={"b": "best friend since boyhood"})
    b = make_profile("b",
                     mood_axes=["content", "gruff", "furious"],
                     relationships={"a": "best friend since boyhood"})
    db.upsert_agent(a)
    db.upsert_agent(b)
    db.update_tier2("a", "content", "")
    db.update_tier2("b", "furious", "I am livid")

    profiles = {p.id: p for p in (a, b)}
    changes = propagate_once(db, profiles)
    assert changes.get("a") == "gruff"  # furious -> gruff via proximity
