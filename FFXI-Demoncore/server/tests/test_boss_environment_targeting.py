"""Tests for boss_environment_targeting."""
from __future__ import annotations

from server.boss_environment_targeting import (
    BossEnvironmentTargeting,
    EnvTargetPlan,
    PlanTrigger,
)


def _setup():
    b = BossEnvironmentTargeting()
    b.register_plan(EnvTargetPlan(
        plan_id="vorrak_pillar", boss_id="vorrak",
        trigger=PlanTrigger.SCHEDULED,
        feature_id="east_pillar", damage=4000,
        scheduled_at=180, cooldown_seconds=60,
    ))
    b.register_plan(EnvTargetPlan(
        plan_id="vorrak_floor_at_50", boss_id="vorrak",
        trigger=PlanTrigger.HP_GATED,
        feature_id="floor_main", damage=8000,
        hp_pct_floor=50, cooldown_seconds=300,
    ))
    b.register_plan(EnvTargetPlan(
        plan_id="vorrak_wall_kited", boss_id="vorrak",
        trigger=PlanTrigger.REACTIVE,
        feature_id="north_wall", damage=3000,
        reactive_tag="kited_to_wall", cooldown_seconds=30,
    ))
    b.start_fight(
        boss_id="vorrak", fight_id="f1",
        hp_max=1_000_000, started_at=0,
    )
    return b


def test_register_invalid_blocks():
    b = BossEnvironmentTargeting()
    bad_no_feat = EnvTargetPlan(
        plan_id="x", boss_id="b", trigger=PlanTrigger.SCHEDULED,
        feature_id="", damage=100, scheduled_at=10,
    )
    assert b.register_plan(bad_no_feat) is False


def test_scheduled_fires_at_or_after_time():
    b = _setup()
    # before scheduled
    early = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=100,
        trigger=PlanTrigger.SCHEDULED,
    )
    assert early is None
    # at/after scheduled
    fired = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=200,
        trigger=PlanTrigger.SCHEDULED,
    )
    assert fired is not None
    assert fired.feature_id == "east_pillar"


def test_scheduled_fires_only_once():
    b = _setup()
    first = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=200,
        trigger=PlanTrigger.SCHEDULED,
    )
    assert first is not None
    second = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=600,
        trigger=PlanTrigger.SCHEDULED,
    )
    assert second is None


def test_hp_gated_fires_below_threshold():
    b = _setup()
    above = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=600_000, elapsed_seconds=10,
        trigger=PlanTrigger.HP_GATED,
    )
    assert above is None
    below = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=400_000, elapsed_seconds=20,
        trigger=PlanTrigger.HP_GATED,
    )
    assert below is not None
    assert below.feature_id == "floor_main"


def test_hp_gated_fires_only_once():
    b = _setup()
    first = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=400_000, elapsed_seconds=20,
        trigger=PlanTrigger.HP_GATED,
    )
    assert first is not None
    second = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=200_000, elapsed_seconds=400,
        trigger=PlanTrigger.HP_GATED,
    )
    assert second is None


def test_reactive_requires_tag_match():
    b = _setup()
    out_no_tag = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=10,
        trigger=PlanTrigger.REACTIVE,
    )
    assert out_no_tag is None
    out_match = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=20,
        trigger=PlanTrigger.REACTIVE,
        reactive_tag="kited_to_wall",
    )
    assert out_match is not None
    assert out_match.feature_id == "north_wall"


def test_reactive_cooldown_blocks_repeat():
    b = _setup()
    first = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=10,
        trigger=PlanTrigger.REACTIVE,
        reactive_tag="kited_to_wall",
    )
    assert first is not None
    second = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=20,
        trigger=PlanTrigger.REACTIVE,
        reactive_tag="kited_to_wall",
    )
    assert second is None
    later = b.choose_target(
        boss_id="vorrak", fight_id="f1",
        current_hp=1_000_000, elapsed_seconds=50,
        trigger=PlanTrigger.REACTIVE,
        reactive_tag="kited_to_wall",
    )
    assert later is not None


def test_fortify_avoidance_can_skip():
    b = BossEnvironmentTargeting()
    b.register_plan(EnvTargetPlan(
        plan_id="p", boss_id="boss",
        trigger=PlanTrigger.SCHEDULED,
        feature_id="floor", damage=1000,
        scheduled_at=10, fortify_avoid_pct=80,
    ))
    b.start_fight(
        boss_id="boss", fight_id="f1", hp_max=100, started_at=0,
    )
    # roll under 80 with floor fortified → avoided
    avoided = b.choose_target(
        boss_id="boss", fight_id="f1",
        current_hp=100, elapsed_seconds=20,
        trigger=PlanTrigger.SCHEDULED,
        fortified_feature_ids=["floor"],
        rng_roll_pct=10,
    )
    assert avoided is None
    # roll above 80 → fires
    fired = b.choose_target(
        boss_id="boss", fight_id="f1",
        current_hp=100, elapsed_seconds=30,
        trigger=PlanTrigger.SCHEDULED,
        fortified_feature_ids=["floor"],
        rng_roll_pct=90,
    )
    assert fired is not None


def test_unknown_fight_returns_none():
    b = _setup()
    out = b.choose_target(
        boss_id="vorrak", fight_id="ghost",
        current_hp=1, elapsed_seconds=10,
        trigger=PlanTrigger.SCHEDULED,
    )
    assert out is None


def test_double_start_fight_blocked():
    b = _setup()
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1",
        hp_max=100, started_at=0,
    ) is False


def test_invalid_hp_gated_pct_blocks_register():
    b = BossEnvironmentTargeting()
    bad = EnvTargetPlan(
        plan_id="p", boss_id="b",
        trigger=PlanTrigger.HP_GATED,
        feature_id="x", damage=100, hp_pct_floor=-5,
    )
    assert b.register_plan(bad) is False


def test_dup_plan_id_blocked():
    b = BossEnvironmentTargeting()
    p = EnvTargetPlan(
        plan_id="p", boss_id="b",
        trigger=PlanTrigger.SCHEDULED,
        feature_id="x", damage=100, scheduled_at=10,
    )
    b.register_plan(p)
    assert b.register_plan(p) is False
