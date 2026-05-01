"""Tests for the AI world density engine.

Run:  python -m pytest server/tests/test_ai_density.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from ai_density import (
    AiTier,
    BarkAgent,
    DailyScheduleEntry,
    DensityBudget,
    DensitySnapshot,
    HeroAgent,
    MEMORY_SUMMARY_MAX_CHARS,
    REACTIVE_PRIMITIVES,
    REFLECTION_INTERVAL_SECONDS,
    ReactiveBehavior,
    ReactiveTrigger,
    ReflectionAgent,
    Relationship,
    ScheduleEntry,
    ZONE_DENSITY_TARGETS,
    admit_entity,
    classify_tier,
    current_density,
    pick_bark,
    react_to,
    reflect_on_events,
)
from ai_density.hero_agent import (
    add_goal,
    add_relationship,
    adjust_affinity,
    current_activity,
    needs_snapshot,
    progress_goal,
    snapshot_taken,
    write_journal_entry,
)
from ai_density.reflection_agent import (
    add_witnessed_event,
    needs_reflection,
)
from ai_density.scripted_bark import (
    current_schedule_entry,
    update_mood,
)
from ai_density.density_budget import DEFAULT_ZONE_TARGETS


# ----------------------------------------------------------------------
# Tier classifier
# ----------------------------------------------------------------------

def test_wildlife_classified_reactive():
    assert classify_tier(archetype="wildlife") == AiTier.REACTIVE


def test_vendor_classified_reflection():
    assert classify_tier(archetype="vendor") == AiTier.REFLECTION


def test_hero_npc_classified_hero():
    assert classify_tier(archetype="hero_npc") == AiTier.HERO


def test_mob_classified_rl_policy():
    assert classify_tier(archetype="mob") == AiTier.RL_POLICY


def test_is_hero_override_wins():
    assert classify_tier(archetype="vendor", is_hero=True) == AiTier.HERO


def test_unknown_archetype_safe_default():
    assert classify_tier(archetype="random_string") == AiTier.SCRIPTED_BARK


# ----------------------------------------------------------------------
# Tier-0 reactive primitives
# ----------------------------------------------------------------------

def test_reactive_catalog_present():
    for required in ("fish_school_avoidance", "bird_startle",
                       "rat_flee", "banner_flap", "lantern_flicker",
                       "wildlife_hop"):
        assert required in REACTIVE_PRIMITIVES


def test_react_to_returns_matching_behavior():
    behaviors = react_to(
        archetype="bird",
        trigger=ReactiveTrigger.SWORD_DRAWN_NEARBY,
    )
    assert len(behaviors) == 1
    assert behaviors[0].behavior_id == "bird_startle"


def test_react_to_no_match():
    behaviors = react_to(
        archetype="bird",
        trigger=ReactiveTrigger.AOE_DETONATION,
    )
    assert behaviors == []


def test_townfolk_duck_on_sword_draw():
    """Even Tier-1 townfolk run a Tier-0 reflex when threatened."""
    behaviors = react_to(
        archetype="ambient_townfolk",
        trigger=ReactiveTrigger.SWORD_DRAWN_NEARBY,
    )
    assert any(b.behavior_id == "scared_bystander_duck" for b in behaviors)


# ----------------------------------------------------------------------
# Tier-1 BarkAgent
# ----------------------------------------------------------------------

def _zaldon_bark() -> BarkAgent:
    return BarkAgent(
        agent_id="zaldon", name="Zaldon",
        archetype="vendor", home_zone="bastok_markets",
        bark_pool=[
            "Fresh from the harbor!",
            "Welcome to my stall.",
            "Tired? Long day, friend.",
            "Splendid catch today.",
            "Get out — I'm closing!",
        ],
        schedule=[
            ScheduleEntry(vana_hour=8, zone="bastok_markets",
                            position_xy=(100, 100), activity="open_shop"),
            ScheduleEntry(vana_hour=20, zone="bastok_markets",
                            position_xy=(50, 50), activity="close_shop"),
        ],
    )


def test_pick_bark_returns_one_of_pool():
    agent = _zaldon_bark()
    rng = random.Random(0)
    bark = pick_bark(agent, rng=rng)
    assert bark in agent.bark_pool


def test_pick_bark_empty_pool_returns_none():
    agent = BarkAgent(agent_id="x", name="X", archetype="vendor",
                       home_zone="z")
    assert pick_bark(agent) is None


def test_mood_weighted_bark_selection():
    """Furious mood biases toward the 'get out' line."""
    agent = _zaldon_bark()
    update_mood(agent, "furious")
    rng = random.Random(42)
    counts = {line: 0 for line in agent.bark_pool}
    for _ in range(200):
        bark = pick_bark(agent, rng=rng)
        counts[bark] += 1
    # 'Get out' should be picked more often than the average baseline
    avg = 200 / len(agent.bark_pool)
    assert counts["Get out — I'm closing!"] > avg


def test_current_schedule_entry_resolves():
    agent = _zaldon_bark()
    entry = current_schedule_entry(agent, vana_hour=10)
    assert entry is not None
    assert entry.activity == "open_shop"
    entry = current_schedule_entry(agent, vana_hour=22)
    assert entry.activity == "close_shop"


def test_current_schedule_entry_wraps_midnight():
    agent = _zaldon_bark()
    entry = current_schedule_entry(agent, vana_hour=2)
    assert entry is not None
    # 2am: latest scheduled entry from yesterday is 20:00 (close_shop)
    assert entry.activity == "close_shop"


# ----------------------------------------------------------------------
# Tier-2 ReflectionAgent
# ----------------------------------------------------------------------

def _reflection_zaldon() -> ReflectionAgent:
    return ReflectionAgent(
        agent_id="zaldon", name="Zaldon",
        role="fish vendor in Bastok Markets",
        personality="blunt, proud of his catch, hates beastmen",
        home_zone="bastok_markets",
        bark_pool=["Fresh!", "Nice catch."],
    )


def test_reflection_constants_match_doc():
    assert REFLECTION_INTERVAL_SECONDS == 3600.0
    assert MEMORY_SUMMARY_MAX_CHARS == 240


def test_reflection_with_no_events_keeps_state_calm():
    agent = _reflection_zaldon()
    # No pending events: no reflection needed
    assert needs_reflection(agent, now=10) is False


def test_reflection_after_events_changes_mood():
    agent = _reflection_zaldon()
    add_witnessed_event(
        agent, kind="outlaw_broke_barrel",
        summary="An outlaw broke a barrel near my stall",
        valence=-0.7, timestamp=100,
    )
    add_witnessed_event(
        agent, kind="outlaw_broke_barrel",
        summary="Another barrel down",
        valence=-0.6, timestamp=200,
    )
    new_mood, summary = reflect_on_events(agent, now=300)
    assert new_mood == "furious"
    assert "barrel" in summary.lower()
    # Pending events cleared after reflection
    assert agent.pending_events == []


def test_positive_events_lift_mood():
    agent = _reflection_zaldon()
    add_witnessed_event(
        agent, kind="festival",
        summary="A festival came through Bastok Markets",
        valence=0.7, timestamp=100,
    )
    new_mood, summary = reflect_on_events(agent, now=200)
    assert new_mood == "content"


def test_reflection_uses_llm_when_provided():
    agent = _reflection_zaldon()
    add_witnessed_event(
        agent, kind="x", summary="raw event", valence=0.0, timestamp=0,
    )
    def fake_llm(a, events):
        return "I had a perfectly typical day."
    new_mood, summary = reflect_on_events(
        agent, now=10, llm_summarizer=fake_llm,
    )
    assert "typical" in summary


def test_llm_failure_falls_back_to_deterministic():
    agent = _reflection_zaldon()
    add_witnessed_event(
        agent, kind="x", summary="thing happened", valence=0.0, timestamp=0,
    )
    def broken_llm(a, events):
        raise RuntimeError("ollama unavailable")
    new_mood, summary = reflect_on_events(
        agent, now=10, llm_summarizer=broken_llm,
    )
    # Fallback runs; summary drawn from deterministic helper
    assert summary != ""


def test_summary_truncated_at_max_chars():
    agent = _reflection_zaldon()
    long_summary = "x" * 1000
    add_witnessed_event(
        agent, kind="x", summary=long_summary,
        valence=0.5, timestamp=0,
    )
    new_mood, summary = reflect_on_events(agent, now=1)
    assert len(summary) <= MEMORY_SUMMARY_MAX_CHARS


def test_needs_reflection_after_interval():
    agent = _reflection_zaldon()
    add_witnessed_event(
        agent, kind="x", summary="thing", valence=0.0, timestamp=0,
    )
    reflect_on_events(agent, now=0)
    assert needs_reflection(agent, now=1800) is False
    assert needs_reflection(agent, now=3700) is True


# ----------------------------------------------------------------------
# Tier-3 HeroAgent
# ----------------------------------------------------------------------

def _cid() -> HeroAgent:
    """Doc example hero: Cid the airship engineer."""
    return HeroAgent(
        agent_id="cid", name="Cid", role="airship engineer",
        home_zone="bastok_metalworks",
        schedule=[
            DailyScheduleEntry(vana_hour=8, activity="workshop_airship_design",
                                  location="bastok_workshop"),
            DailyScheduleEntry(vana_hour=12, activity="lunch_with_daughter",
                                  location="cid_residence",
                                  relationship_focus="cid_daughter"),
            DailyScheduleEntry(vana_hour=18, activity="politics_with_volker",
                                  location="bastok_presidential",
                                  relationship_focus="volker"),
            DailyScheduleEntry(vana_hour=22, activity="sleep",
                                  location="cid_residence"),
        ],
    )


def test_current_activity_resolves():
    cid = _cid()
    activity = current_activity(cid, vana_hour=13)
    assert activity is not None
    assert activity.activity == "lunch_with_daughter"


def test_relationship_tracked():
    cid = _cid()
    add_relationship(cid, other_agent_id="volker",
                       other_name="Volker",
                       relationship_kind="friend",
                       affinity=0.6)
    assert "volker" in cid.relationships
    assert cid.relationships["volker"].affinity == 0.6


def test_affinity_clamps():
    cid = _cid()
    add_relationship(cid, other_agent_id="volker", other_name="Volker",
                       affinity=0.9)
    new = adjust_affinity(cid, other_agent_id="volker", delta=0.5, now=0)
    assert new == 1.0   # clamped at +1
    new = adjust_affinity(cid, other_agent_id="volker", delta=-3.0, now=0)
    assert new == -1.0


def test_goal_tracked():
    cid = _cid()
    goal = add_goal(cid, goal_id="airship_v2",
                      description="Build a new airship",
                      target_completion_day=180)
    assert goal in cid.goals
    progress = progress_goal(cid, goal_id="airship_v2", delta_pct=15.0)
    assert progress == 15.0


def test_journal_entry_generated():
    cid = _cid()
    write_journal_entry(cid, text="Volker asked about the airship.",
                          timestamp=100)
    assert len(cid.journal) == 1


def test_journal_can_spawn_quest():
    cid = _cid()
    write_journal_entry(cid,
                          text="I need someone to find me Mythril.",
                          timestamp=100,
                          spawned_quest_id="cid_mythril_quest")
    assert cid.journal[0].spawned_quest_id == "cid_mythril_quest"


def test_snapshot_cadence():
    cid = _cid()
    assert needs_snapshot(cid, now=0) is True
    snapshot_taken(cid, now=0)
    # 1 minute real time = 1 game minute @ default; needs 5 game-min cadence
    assert needs_snapshot(cid, now=60) is False
    assert needs_snapshot(cid, now=400) is True


# ----------------------------------------------------------------------
# Density budget
# ----------------------------------------------------------------------

def test_zone_density_targets_match_doc():
    """Bastok Markets target row from the doc table."""
    bastok = ZONE_DENSITY_TARGETS["bastok_markets"]
    assert bastok[AiTier.REACTIVE] == 200
    assert bastok[AiTier.SCRIPTED_BARK] == 80
    assert bastok[AiTier.REFLECTION] == 25
    assert bastok[AiTier.HERO] == 4
    assert bastok[AiTier.RL_POLICY] == 0


def test_south_gustaberg_targets():
    sg = ZONE_DENSITY_TARGETS["south_gustaberg"]
    assert sg[AiTier.REACTIVE] == 500
    assert sg[AiTier.HERO] == 0
    assert sg[AiTier.RL_POLICY] == 30


def test_castle_oztroja_has_one_hero():
    """The doc says Maat fight = 1 hero in Oztroja."""
    oz = ZONE_DENSITY_TARGETS["castle_oztroja"]
    assert oz[AiTier.HERO] == 1


def test_admit_under_cap():
    bud = DensityBudget()
    admitted, reason = bud.admit(
        zone="bastok_markets", tier=AiTier.HERO, entity_id="cid",
    )
    assert admitted is True


def test_admit_at_cap_blocks():
    bud = DensityBudget()
    # Bastok hero cap is 4; admit 4
    for i in range(4):
        admitted, _ = bud.admit(
            zone="bastok_markets", tier=AiTier.HERO,
            entity_id=f"hero_{i}",
        )
        assert admitted is True
    # 5th: blocked
    admitted, reason = bud.admit(
        zone="bastok_markets", tier=AiTier.HERO, entity_id="hero_5",
    )
    assert admitted is False
    assert "cap" in reason


def test_evict_makes_room():
    bud = DensityBudget()
    for _ in range(4):
        bud.admit(zone="bastok_markets", tier=AiTier.HERO,
                    entity_id="x")
    assert bud.is_at_cap(zone="bastok_markets", tier=AiTier.HERO)
    bud.evict(zone="bastok_markets", tier=AiTier.HERO)
    admitted, _ = bud.admit(
        zone="bastok_markets", tier=AiTier.HERO, entity_id="y",
    )
    assert admitted is True


def test_remaining_capacity_query():
    bud = DensityBudget()
    bud.admit(zone="bastok_markets", tier=AiTier.HERO, entity_id="cid")
    remaining = bud.remaining_capacity(
        zone="bastok_markets", tier=AiTier.HERO,
    )
    assert remaining == 3


def test_unknown_zone_uses_default_targets():
    bud = DensityBudget()
    admitted_count = 0
    for i in range(DEFAULT_ZONE_TARGETS[AiTier.HERO] + 1):
        admitted, _ = bud.admit(
            zone="some_random_zone", tier=AiTier.HERO,
            entity_id=f"x{i}",
        )
        if admitted:
            admitted_count += 1
    assert admitted_count == DEFAULT_ZONE_TARGETS[AiTier.HERO]


def test_module_level_admit_uses_singleton():
    # The default singleton tracks across calls
    snapshot = current_density(zone="bastok_markets")
    assert isinstance(snapshot, DensitySnapshot)


# ----------------------------------------------------------------------
# Integration: a hero NPC's day
# ----------------------------------------------------------------------

def test_full_hero_day_loop():
    """Cid's day from the doc: 8am workshop, 12pm lunch, 6pm politics, 10pm sleep."""
    cid = _cid()
    # 8am
    activity = current_activity(cid, vana_hour=8)
    assert activity.activity == "workshop_airship_design"
    # 12pm
    activity = current_activity(cid, vana_hour=12)
    assert activity.activity == "lunch_with_daughter"
    # 6pm
    activity = current_activity(cid, vana_hour=18)
    assert activity.activity == "politics_with_volker"
    # 10pm
    activity = current_activity(cid, vana_hour=22)
    assert activity.activity == "sleep"


def test_density_doc_table_complete():
    """All 3 zones from the doc table are present."""
    for zone in ("bastok_markets", "south_gustaberg", "castle_oztroja"):
        assert zone in ZONE_DENSITY_TARGETS
        # Every tier has an entry
        for tier in AiTier:
            assert tier in ZONE_DENSITY_TARGETS[zone]
