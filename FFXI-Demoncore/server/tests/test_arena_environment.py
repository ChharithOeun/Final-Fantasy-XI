"""Tests for arena_environment."""
from __future__ import annotations

from server.arena_environment import (
    ArenaEnvironment,
    ArenaFeature,
    FeatureKind,
    FeatureState,
)


def _seed():
    return [
        ArenaFeature(
            feature_id="north_wall", kind=FeatureKind.WALL,
            hp_max=10000, band=2,
            element_mults={"fire": 1.5},
        ),
        ArenaFeature(
            feature_id="floor_main", kind=FeatureKind.FLOOR,
            hp_max=20000, band=1,
        ),
        ArenaFeature(
            feature_id="ice_lake", kind=FeatureKind.ICE_SHEET,
            hp_max=4000, band=0,
            element_mults={"fire": 3.0, "ice": 0.0},
        ),
    ]


def test_register_arena_happy():
    e = ArenaEnvironment()
    assert e.register_arena(arena_id="a1", features=_seed()) is True


def test_register_blank_arena_blocked():
    e = ArenaEnvironment()
    assert e.register_arena(arena_id="", features=_seed()) is False


def test_register_no_features_blocked():
    e = ArenaEnvironment()
    assert e.register_arena(arena_id="a1", features=[]) is False


def test_register_dup_arena_blocked():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    assert e.register_arena(arena_id="a1", features=_seed()) is False


def test_register_dup_feature_blocked():
    e = ArenaEnvironment()
    bad = [
        ArenaFeature(feature_id="x", kind=FeatureKind.WALL, hp_max=100),
        ArenaFeature(feature_id="x", kind=FeatureKind.FLOOR, hp_max=100),
    ]
    assert e.register_arena(arena_id="a1", features=bad) is False


def test_zero_hp_feature_blocked():
    e = ArenaEnvironment()
    bad = [ArenaFeature(feature_id="w", kind=FeatureKind.WALL, hp_max=0)]
    assert e.register_arena(arena_id="a1", features=bad) is False


def test_initial_state_intact():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    assert e.state(arena_id="a1", feature_id="north_wall") == FeatureState.INTACT
    assert e.hp(arena_id="a1", feature_id="north_wall") == 10000


def test_apply_damage_reduces_hp():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    out = e.apply_damage(
        arena_id="a1", feature_id="north_wall", amount=1000,
    )
    assert out.accepted is True
    assert out.hp_remaining == 9000


def test_element_multiplier_scales():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    # ice_lake: fire = 3.0, hp_max=4000, 1000 fire = 3000 dmg
    out = e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=1000, element="fire",
    )
    assert out.hp_remaining == 1000


def test_ice_immune_to_ice():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    out = e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=10000, element="ice",
    )
    assert out.hp_remaining == 4000   # 0 mult
    assert out.new_state == FeatureState.INTACT


def test_crossed_crack_event():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    # ice_lake hp_max=4000, crack at 25% = 1000hp
    out = e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=1000, element="fire",  # 3000 dmg → hp 1000
    )
    # exactly at crack threshold
    assert out.crossed_crack is True
    assert out.new_state == FeatureState.CRACKED


def test_crossed_break_event():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    out = e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=10000, element="fire",
    )
    assert out.crossed_break is True
    assert out.new_state == FeatureState.BROKEN
    assert out.hp_remaining == 0


def test_already_broken_rejected():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=10000, element="fire",
    )
    out = e.apply_damage(
        arena_id="a1", feature_id="ice_lake",
        amount=100,
    )
    assert out.accepted is False


def test_negative_damage_rejected():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    out = e.apply_damage(
        arena_id="a1", feature_id="north_wall", amount=-50,
    )
    assert out.accepted is False


def test_unknown_arena():
    e = ArenaEnvironment()
    assert e.feature(arena_id="ghost", feature_id="x") is None
    assert e.hp(arena_id="ghost", feature_id="x") == 0
    assert e.state(arena_id="ghost", feature_id="x") == FeatureState.INTACT


def test_features_for_lists_all():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    out = e.features_for(arena_id="a1")
    assert len(out) == 3


def test_reset_restores_hp():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    e.apply_damage(arena_id="a1", feature_id="north_wall", amount=5000)
    assert e.hp(arena_id="a1", feature_id="north_wall") == 5000
    e.reset(arena_id="a1")
    assert e.hp(arena_id="a1", feature_id="north_wall") == 10000


def test_damaged_state():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=_seed())
    # north_wall hp_max=10000, damaged below 75% = 7500
    e.apply_damage(arena_id="a1", feature_id="north_wall", amount=3000)
    assert e.state(arena_id="a1", feature_id="north_wall") == FeatureState.DAMAGED
