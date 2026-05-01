"""Tests for the crafting engine.

Run:  python -m pytest server/tests/test_crafting.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from crafting import (
    Craft,
    CraftLevels,
    CraftTier,
    GAME_DAY_SECONDS,
    HQ_BASE_TABLE,
    HqTier,
    MASTER_SYNTHESIS_MIN_HQ,
    MASTER_SYNTHESIS_SIGNED_CHANCE,
    MOOD_MODIFIERS,
    MasterSynthesisLB,
    Recipe,
    SynthesisOutcome,
    SynthesisResolver,
    grant_xp,
    reputation_cap_raise,
    sample_recipe_catalog,
    tier_for_level,
    title_for_grandmaster,
)
from crafting.crafter_state import (
    can_use_master_synthesis,
    stable_hands_active,
    xp_for_synth,
    xp_required_for_level,
)
from crafting.synthesis import base_success_rate


# ----------------------------------------------------------------------
# Tier brackets
# ----------------------------------------------------------------------

@pytest.mark.parametrize("level, expected", [
    (0, CraftTier.APPRENTICE),
    (15, CraftTier.APPRENTICE),
    (16, CraftTier.JOURNEYMAN),
    (40, CraftTier.JOURNEYMAN),
    (41, CraftTier.ARTISAN),
    (65, CraftTier.ARTISAN),
    (66, CraftTier.MASTER),
    (89, CraftTier.MASTER),
    (90, CraftTier.GRANDMASTER),
    (99, CraftTier.GRANDMASTER),
])
def test_tier_for_level(level, expected):
    assert tier_for_level(level) == expected


def test_negative_level_clamps_to_apprentice():
    assert tier_for_level(-5) == CraftTier.APPRENTICE


# ----------------------------------------------------------------------
# Recipe catalog
# ----------------------------------------------------------------------

def test_catalog_covers_all_crafts():
    catalog = sample_recipe_catalog()
    crafts_seen = {r.craft for r in catalog.values()}
    for craft in Craft:
        assert craft in crafts_seen


def test_catalog_recipes_have_unique_ids():
    catalog = sample_recipe_catalog()
    assert len(catalog) >= 12   # one per craft + extras
    # IDs must be unique
    assert len({r.recipe_id for r in catalog.values()}) == len(catalog)


# ----------------------------------------------------------------------
# CraftLevels + XP curve
# ----------------------------------------------------------------------

def test_new_crafter_starts_at_zero():
    state = CraftLevels(actor_id="alice", nation="bastok")
    for craft in Craft:
        assert state.level(craft) == 0
        assert state.tier(craft) == CraftTier.APPRENTICE


def test_xp_for_synth_curve():
    """Same level: 1.0; below: 0.5; above: 2.0."""
    assert xp_for_synth(recipe_level=20, crafter_level=20) == 1.0
    assert xp_for_synth(recipe_level=10, crafter_level=20) == 0.5
    assert xp_for_synth(recipe_level=30, crafter_level=20) == 2.0


def test_grant_xp_levels_up():
    state = CraftLevels(actor_id="alice")
    # Level 1 needs 100 XP
    grant_xp(state, Craft.SMITHING, xp=100)
    assert state.level(Craft.SMITHING) == 1


def test_grant_xp_rolls_through_multiple_levels():
    state = CraftLevels(actor_id="alice")
    # 100 + 200 = 300 XP gets us through 1->2
    grant_xp(state, Craft.SMITHING, xp=300)
    assert state.level(Craft.SMITHING) == 2


def test_grandmaster_award_grants_title():
    state = CraftLevels(actor_id="alice", nation="bastok")
    # Manually set near grandmaster
    state.levels[Craft.SMITHING] = 89
    state.xp_into_level[Craft.SMITHING] = 0
    # Need 90 * 100 = 9000 XP to reach 90
    grant_xp(state, Craft.SMITHING, xp=9000)
    assert state.is_grandmaster(Craft.SMITHING)
    assert "Bastok Master Smith" in state.titles_earned


def test_grandmaster_count_and_rep_cap():
    state = CraftLevels(actor_id="alice", nation="windurst")
    state.levels[Craft.SMITHING] = 90
    state.levels[Craft.ALCHEMY] = 95
    state.levels[Craft.CLOTH] = 99
    assert state.grandmaster_count() == 3
    assert reputation_cap_raise(state) == 3000


def test_titles_per_craft():
    assert title_for_grandmaster(Craft.SMITHING, "bastok") == "Bastok Master Smith"
    assert title_for_grandmaster(Craft.CLOTH, "windurst") == "Windurst Master Loomweaver"
    assert title_for_grandmaster(Craft.WOODWORKING, "sandoria") == "Sandoria Master Carpenter"


# ----------------------------------------------------------------------
# Stable hands
# ----------------------------------------------------------------------

def test_stable_hands_kicks_in_at_5():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 4
    assert stable_hands_active(state, Craft.SMITHING) is False
    state.levels[Craft.SMITHING] = 5
    assert stable_hands_active(state, Craft.SMITHING) is True


# ----------------------------------------------------------------------
# Base success rate
# ----------------------------------------------------------------------

def test_below_minus_10_diff_zero_success():
    """A recipe more than 10 levels above the crafter is impossible."""
    rate = base_success_rate(crafter_level=10, recipe_level=25,
                                skill_score=1.0, has_stable_hands=False)
    assert rate == 0.0


def test_at_parity_50_percent_baseline():
    """At parity with skill 1.0, no stable hands: ~50%."""
    rate = base_success_rate(crafter_level=20, recipe_level=20,
                                skill_score=1.0, has_stable_hands=False)
    assert rate == 0.50


def test_above_recipe_caps_at_95():
    rate = base_success_rate(crafter_level=99, recipe_level=10,
                                skill_score=1.0, has_stable_hands=False)
    assert rate == 0.95


def test_skill_score_lifts_rate():
    low = base_success_rate(crafter_level=20, recipe_level=20,
                              skill_score=0.0, has_stable_hands=False)
    high = base_success_rate(crafter_level=20, recipe_level=20,
                                skill_score=1.0, has_stable_hands=False)
    assert high > low
    # 50% baseline; at score=0 we get 70% of that = 35%
    assert low == pytest.approx(0.35, abs=0.001)


def test_stable_hands_lifts_low_skill():
    sloppy = base_success_rate(crafter_level=20, recipe_level=20,
                                  skill_score=0.0, has_stable_hands=True)
    sloppy_no_hands = base_success_rate(crafter_level=20, recipe_level=20,
                                            skill_score=0.0,
                                            has_stable_hands=False)
    assert sloppy > sloppy_no_hands


# ----------------------------------------------------------------------
# SynthesisResolver — basic outcomes
# ----------------------------------------------------------------------

def _force_succeed_rng() -> random.Random:
    """RNG that always rolls 0.0 — every check passes; HQ goes high."""
    rng = random.Random()
    rng.random = lambda: 0.0   # type: ignore[assignment]
    return rng


def _force_fail_rng() -> random.Random:
    rng = random.Random()
    rng.random = lambda: 0.999   # always fails
    return rng


def test_furious_mood_refuses():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 50
    catalog = sample_recipe_catalog()
    recipe = catalog["mythril_sword"]
    resolver = SynthesisResolver(rng=_force_succeed_rng())
    result = resolver.attempt(
        recipe=recipe, crafter=state, mood="furious", skill_score=1.0,
    )
    assert result.outcome == SynthesisOutcome.REFUSED
    assert result.output_id is None


def test_success_grants_xp_and_output():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 35   # at parity with mythril_sword
    catalog = sample_recipe_catalog()
    resolver = SynthesisResolver(rng=_force_succeed_rng())
    result = resolver.attempt(
        recipe=catalog["mythril_sword"], crafter=state,
        mood="content", skill_score=1.0,
    )
    assert result.outcome == SynthesisOutcome.SUCCESS
    assert result.output_id == "mythril_sword"
    assert result.xp_gained == 1.0   # parity


def test_failure_consumes_materials_and_drops_mood():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 40
    catalog = sample_recipe_catalog()
    resolver = SynthesisResolver(rng=_force_fail_rng())
    result = resolver.attempt(
        recipe=catalog["mythril_sword"], crafter=state,
        mood="content", skill_score=0.0,
    )
    assert result.outcome == SynthesisOutcome.FAILED
    assert result.output_id is None
    assert result.tool_durability_lost_pct == 0.10
    assert ("weary", 0.10) in result.mood_deltas


def test_weary_mundane_proc_doubles_output():
    """Weary mood + always-roll-low rng -> mundane proc fires."""
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.ALCHEMY] = 50
    catalog = sample_recipe_catalog()
    rng = _force_succeed_rng()
    resolver = SynthesisResolver(rng=rng)
    result = resolver.attempt(
        recipe=catalog["hi_potion"], crafter=state,
        mood="weary", skill_score=0.7,
    )
    if result.outcome == SynthesisOutcome.SUCCESS:
        # hi_potion outputs 3 base; mundane bonus doubles to 6
        assert result.output_qty in (3, 6)
        # With force-succeed (always rolling 0.0) the mundane proc fires
        assert result.output_qty == 6


def test_above_level_synth_grants_double_xp():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 30   # crafting a level-35 recipe
    catalog = sample_recipe_catalog()
    resolver = SynthesisResolver(rng=_force_succeed_rng())
    result = resolver.attempt(
        recipe=catalog["mythril_sword"], crafter=state,
        mood="content", skill_score=1.0,
    )
    if result.outcome == SynthesisOutcome.SUCCESS:
        assert result.xp_gained == 2.0


def test_below_level_synth_grants_half_xp():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 50
    catalog = sample_recipe_catalog()
    resolver = SynthesisResolver(rng=_force_succeed_rng())
    result = resolver.attempt(
        recipe=catalog["bronze_sword"], crafter=state,
        mood="content", skill_score=1.0,
    )
    if result.outcome == SynthesisOutcome.SUCCESS:
        assert result.xp_gained == 0.5


# ----------------------------------------------------------------------
# HQ tiers
# ----------------------------------------------------------------------

def test_hq_table_sums_close_to_1():
    """Standard table is the success-pool distribution."""
    total = sum(HQ_BASE_TABLE.values())
    assert total == pytest.approx(1.0, abs=0.001)


def test_force_succeed_lands_high_hq():
    """RNG=0 picks the rare apex tier in the iteration order."""
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 50
    catalog = sample_recipe_catalog()
    resolver = SynthesisResolver(rng=_force_succeed_rng())
    result = resolver.attempt(
        recipe=catalog["mythril_sword"], crafter=state,
        mood="content", skill_score=1.0,
    )
    assert result.outcome == SynthesisOutcome.SUCCESS
    assert result.hq_tier == HqTier.PLUS_3   # rare-apex due to roll=0


def test_contemplative_mood_increases_high_tier_pool():
    """contemplative shifts mass into +2 / +3."""
    cfg = MOOD_MODIFIERS["contemplative"]
    assert cfg.high_tier_bonus == 0.15


# ----------------------------------------------------------------------
# Master Synthesis LB
# ----------------------------------------------------------------------

def test_lb_unavailable_below_grandmaster():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 89   # one short
    lb = MasterSynthesisLB()
    assert lb.can_use(state, Craft.SMITHING, now=0) is False


def test_lb_available_at_grandmaster():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 90
    lb = MasterSynthesisLB()
    assert lb.can_use(state, Craft.SMITHING, now=0) is True


def test_lb_one_per_game_day():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 95
    state.last_master_synthesis[Craft.SMITHING] = 0
    lb = MasterSynthesisLB()
    # Same day: not available
    assert lb.can_use(state, Craft.SMITHING, now=GAME_DAY_SECONDS - 1) is False
    # One game-day later: available
    assert lb.can_use(state, Craft.SMITHING, now=GAME_DAY_SECONDS + 1) is True


def test_lb_forces_minimum_hq_2():
    """Even on a successful synth that would normally roll +0 / +1,
    Master Synthesis bumps the floor to +2."""
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 95
    catalog = sample_recipe_catalog()
    # Custom RNG: high enough to land STANDARD on the underlying roll
    # (~ 0.85), then a few more 0s for any signed/+3 rolls
    rng = random.Random(42)
    seq = iter([
        0.10,   # success_check (passes)
        0.85,   # hq_tier roll → STANDARD
        0.99,   # plus_3_bias_roll (no bump)
        0.99,   # signed roll (no signed)
    ])
    rng.random = lambda: next(seq)   # type: ignore
    lb = MasterSynthesisLB(rng=rng)
    result = lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="content", skill_score=1.0, now=0,
    )
    # Result should be at the LB floor
    assert result.outcome == SynthesisOutcome.SUCCESS
    assert result.hq_tier >= MASTER_SYNTHESIS_MIN_HQ
    assert "Master Synthesis!" in result.callouts


def test_lb_5pct_signed_chance():
    """When the 5% roll lands, hq goes to +4 with signed_by set."""
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 95
    catalog = sample_recipe_catalog()
    # success → STANDARD (bump to +2) → +3 bias (skip) → signed (HIT)
    seq = iter([
        0.10,   # success_check (passes)
        0.85,   # hq STANDARD (will be bumped)
        0.99,   # +3 bias (no bump beyond +2)
        0.01,   # signed roll (HIT — under 5%)
    ])
    rng = random.Random()
    rng.random = lambda: next(seq)   # type: ignore
    lb = MasterSynthesisLB(rng=rng)
    result = lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="content", skill_score=1.0, now=0,
    )
    assert result.hq_tier == HqTier.PLUS_4
    assert result.signed_by == "Cid"
    assert any("Crafted by Cid" in c for c in result.callouts)


def test_lb_consumes_cooldown_on_use():
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 95
    catalog = sample_recipe_catalog()
    rng = random.Random(42)
    lb = MasterSynthesisLB(rng=rng)
    lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="content", skill_score=1.0, now=100,
    )
    assert state.last_master_synthesis[Craft.SMITHING] == 100


def test_lb_doesnt_burn_cooldown_on_furious():
    """Refused synth (furious) shouldn't consume the LB."""
    state = CraftLevels(actor_id="alice")
    state.levels[Craft.SMITHING] = 95
    catalog = sample_recipe_catalog()
    lb = MasterSynthesisLB()
    lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="furious", skill_score=1.0, now=100,
    )
    assert state.last_master_synthesis[Craft.SMITHING] is None


def test_lb_signed_chance_constant_matches_doc():
    assert MASTER_SYNTHESIS_SIGNED_CHANCE == 0.05


# ----------------------------------------------------------------------
# Integration: full-day master smith workflow
# ----------------------------------------------------------------------

def test_grandmaster_smith_day_workflow():
    """Cid (grandmaster smith, content mood, perfect skill) crafts an
    Excalibur via Master Synthesis. Verify: HQ floor honored, audible
    callouts present, cooldown locked."""
    state = CraftLevels(actor_id="cid", nation="bastok")
    state.levels[Craft.SMITHING] = 95
    state.titles_earned.add("Bastok Master Smith")
    catalog = sample_recipe_catalog()
    rng = random.Random(2026)
    lb = MasterSynthesisLB(rng=rng)

    result = lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="content", skill_score=1.0, now=1000,
    )
    assert result.outcome == SynthesisOutcome.SUCCESS
    assert result.hq_tier >= MASTER_SYNTHESIS_MIN_HQ
    assert "Master Synthesis!" in result.callouts

    # Try another LB the same day: should fall through to standard synth
    fallback = lb.attempt(
        recipe=catalog["excalibur"], crafter=state,
        crafter_name="Cid", mood="content", skill_score=1.0, now=1500,
    )
    # Fallback synth doesn't add the "Master Synthesis!" callout
    assert "Master Synthesis!" not in fallback.callouts
