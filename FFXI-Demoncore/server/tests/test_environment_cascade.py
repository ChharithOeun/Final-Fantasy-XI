"""Tests for environment_cascade."""
from __future__ import annotations

from server.arena_environment import (
    ArenaEnvironment, ArenaFeature, FeatureKind,
)
from server.environment_damage import EnvironmentDamage
from server.environment_cascade import (
    CascadeRule, CascadeTrigger, EnvironmentCascade,
    MAX_CASCADE_DEPTH,
)


def _setup(seed_features=None):
    env = ArenaEnvironment()
    feats = seed_features or [
        ArenaFeature(feature_id="east_pillar", kind=FeatureKind.PILLAR,
                     hp_max=5000, band=2),
        ArenaFeature(feature_id="ceiling", kind=FeatureKind.CEILING,
                     hp_max=10000, band=3),
        ArenaFeature(feature_id="floor_main", kind=FeatureKind.FLOOR,
                     hp_max=20000, band=1),
        ArenaFeature(feature_id="ice_lake", kind=FeatureKind.ICE_SHEET,
                     hp_max=4000, band=0),
    ]
    env.register_arena(arena_id="a1", features=feats)
    ed = EnvironmentDamage(arena_env=env)
    casc = EnvironmentCascade(arena_env=env, environment_damage=ed)
    return env, ed, casc


def test_register_rule_happy():
    _, _, c = _setup()
    ok = c.register_rule(CascadeRule(
        rule_id="r1", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=2000,
    ))
    assert ok is True


def test_register_blank_rule_blocked():
    _, _, c = _setup()
    bad = CascadeRule(
        rule_id="", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="x", target_feature_id="y",
        followup_damage=100,
    )
    assert c.register_rule(bad) is False


def test_register_zero_damage_blocked():
    _, _, c = _setup()
    bad = CascadeRule(
        rule_id="r", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="x", target_feature_id="y",
        followup_damage=0,
    )
    assert c.register_rule(bad) is False


def test_register_self_target_blocked():
    _, _, c = _setup()
    bad = CascadeRule(
        rule_id="r", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="east_pillar",
        followup_damage=100,
    )
    assert c.register_rule(bad) is False


def test_register_dup_rule_id_blocked():
    _, _, c = _setup()
    rule = CascadeRule(
        rule_id="r1", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=100,
    )
    c.register_rule(rule)
    assert c.register_rule(rule) is False


def test_break_fires_downstream_damage():
    env, ed, c = _setup()
    c.register_rule(CascadeRule(
        rule_id="pillar_to_ceiling", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=2000,
    ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    assert len(steps) == 1
    assert steps[0].target_feature_id == "ceiling"
    assert steps[0].damage_dealt == 2000


def test_unknown_target_no_step():
    env, ed, c = _setup()
    c.register_rule(CascadeRule(
        rule_id="r", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ghost",
        followup_damage=2000,
    ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    assert steps == ()


def test_cascade_chains_when_target_breaks():
    env, ed, c = _setup([
        ArenaFeature(feature_id="dam", kind=FeatureKind.DAM,
                     hp_max=1000, band=0),
        ArenaFeature(feature_id="ice", kind=FeatureKind.ICE_SHEET,
                     hp_max=500, band=0),
        ArenaFeature(feature_id="floor", kind=FeatureKind.FLOOR,
                     hp_max=400, band=1),
    ])
    c.register_rule(CascadeRule(
        rule_id="dam_to_ice", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="dam", target_feature_id="ice",
        followup_damage=600,   # > ice hp 500 → break
    ))
    c.register_rule(CascadeRule(
        rule_id="ice_to_floor", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="ice", target_feature_id="floor",
        followup_damage=500,   # > floor 400 → break
    ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="dam", now_seconds=10,
    )
    assert len(steps) == 2
    rule_ids = {s.rule_id for s in steps}
    assert rule_ids == {"dam_to_ice", "ice_to_floor"}


def test_cascade_does_not_exceed_depth():
    env, ed, c = _setup([
        ArenaFeature(feature_id=f"f{i}", kind=FeatureKind.FLOOR,
                     hp_max=10, band=i)
        for i in range(MAX_CASCADE_DEPTH + 3)
    ])
    # chain f0 → f1 → f2 → ...
    for i in range(MAX_CASCADE_DEPTH + 2):
        c.register_rule(CascadeRule(
            rule_id=f"r{i}", trigger=CascadeTrigger.ON_BREAK,
            source_feature_id=f"f{i}", target_feature_id=f"f{i+1}",
            followup_damage=100, depth_budget=MAX_CASCADE_DEPTH,
        ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="f0", now_seconds=10,
    )
    # depth-limited
    max_depth = max(s.depth for s in steps)
    assert max_depth <= MAX_CASCADE_DEPTH


def test_crack_trigger_separate_from_break():
    env, ed, c = _setup()
    c.register_rule(CascadeRule(
        rule_id="brk", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=100,
    ))
    c.register_rule(CascadeRule(
        rule_id="crk", trigger=CascadeTrigger.ON_CRACK,
        source_feature_id="east_pillar", target_feature_id="floor_main",
        followup_damage=100,
    ))
    brk_steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    crk_steps = c.on_crack(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    assert len(brk_steps) == 1 and brk_steps[0].rule_id == "brk"
    assert len(crk_steps) == 1 and crk_steps[0].rule_id == "crk"


def test_multiple_rules_per_source():
    env, ed, c = _setup()
    for tgt in ("ceiling", "floor_main", "ice_lake"):
        c.register_rule(CascadeRule(
            rule_id=f"r_{tgt}", trigger=CascadeTrigger.ON_BREAK,
            source_feature_id="east_pillar", target_feature_id=tgt,
            followup_damage=100,
        ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    targets = {s.target_feature_id for s in steps}
    assert targets == {"ceiling", "floor_main", "ice_lake"}


def test_no_rule_no_step():
    env, ed, c = _setup()
    steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=10,
    )
    assert steps == ()


def test_delay_seconds_in_step():
    env, ed, c = _setup()
    c.register_rule(CascadeRule(
        rule_id="r", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=100, delay_seconds=15,
    ))
    steps = c.on_break(
        arena_id="a1", source_feature_id="east_pillar", now_seconds=100,
    )
    assert steps[0].fired_at == 115


def test_invalid_depth_budget_blocked():
    _, _, c = _setup()
    bad = CascadeRule(
        rule_id="r", trigger=CascadeTrigger.ON_BREAK,
        source_feature_id="east_pillar", target_feature_id="ceiling",
        followup_damage=100, depth_budget=MAX_CASCADE_DEPTH + 5,
    )
    assert c.register_rule(bad) is False
