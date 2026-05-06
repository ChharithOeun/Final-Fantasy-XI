"""Tests for environment_damage."""
from __future__ import annotations

from server.arena_environment import (
    ArenaEnvironment, ArenaFeature, FeatureKind,
)
from server.environment_damage import (
    DamageEvent, DamageSource, EnvironmentDamage,
)


def _seed_env():
    e = ArenaEnvironment()
    e.register_arena(arena_id="a1", features=[
        ArenaFeature(
            feature_id="north_wall", kind=FeatureKind.WALL,
            hp_max=10000, band=2,
        ),
        ArenaFeature(
            feature_id="floor_main", kind=FeatureKind.FLOOR,
            hp_max=20000, band=1,
        ),
        ArenaFeature(
            feature_id="ice_lake", kind=FeatureKind.ICE_SHEET,
            hp_max=4000, band=0,
            element_mults={"fire": 3.0},
        ),
        ArenaFeature(
            feature_id="east_pillar", kind=FeatureKind.PILLAR,
            hp_max=5000, band=2,
        ),
    ])
    return e


def test_spell_aoe_hits_band_features():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.SPELL_AOE,
        amount=2000, element="fire",
        origin_band=2, band_radius=0,
    )
    impacts = ed.submit(arena_id="a1", event=event)
    # only band-2 features: north_wall and east_pillar
    ids = {i.feature_id for i in impacts}
    assert ids == {"north_wall", "east_pillar"}


def test_band_radius_includes_adjacent():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.BOSS_2HR,
        amount=2000, origin_band=2, band_radius=1,
    )
    impacts = ed.submit(arena_id="a1", event=event)
    ids = {i.feature_id for i in impacts}
    # north_wall (b2), east_pillar (b2), floor_main (b1)
    assert ids == {"north_wall", "east_pillar", "floor_main"}


def test_band_attenuation():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.SPELL_AOE,
        amount=2000, element="fire",
        origin_band=2, band_radius=2,
    )
    impacts = ed.submit(arena_id="a1", event=event)
    # ice_lake at band 0, gap 2, attenuation 0.25, fire mult 3 → 1500
    ice = [i for i in impacts if i.feature_id == "ice_lake"][0]
    assert ice.damage_dealt == 500   # input scaled = 2000*0.25 = 500


def test_target_feature_ids_pin_to_specific():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.CANNON_VOLLEY,
        amount=3000, origin_band=2,
        target_feature_ids=("north_wall",),
    )
    impacts = ed.submit(arena_id="a1", event=event)
    assert len(impacts) == 1
    assert impacts[0].feature_id == "north_wall"


def test_target_kinds_filter():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.BOSS_TELL,
        amount=500, origin_band=2, band_radius=2,
        target_kinds=(FeatureKind.PILLAR,),
    )
    impacts = ed.submit(arena_id="a1", event=event)
    assert len(impacts) == 1
    assert impacts[0].feature_id == "east_pillar"


def test_total_running_total_accumulates():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    ed.submit(arena_id="a1", event=DamageEvent(
        source=DamageSource.SPELL_AOE, amount=500, origin_band=2,
        band_radius=0,
    ))
    ed.submit(arena_id="a1", event=DamageEvent(
        source=DamageSource.SPELL_AOE, amount=500, origin_band=2,
        band_radius=0,
    ))
    # 2 hits × 2 features × 500 = 2000
    assert ed.total_environmental_damage(arena_id="a1") == 2000


def test_unknown_arena_returns_empty():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    out = ed.submit(arena_id="ghost", event=DamageEvent(
        source=DamageSource.SPELL_AOE, amount=100,
    ))
    assert out == ()


def test_break_event_propagates():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    impacts = ed.submit(arena_id="a1", event=DamageEvent(
        source=DamageSource.BOSS_2HR, amount=20000,
        origin_band=0, band_radius=0,
        target_feature_ids=("ice_lake",), element="fire",
    ))
    assert impacts[0].crossed_break is True


def test_zero_dmg_after_attenuation_skipped():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.SPELL_AOE, amount=1,
        origin_band=2, band_radius=4,
    )
    impacts = ed.submit(arena_id="a1", event=event)
    # 1 / 2^2 = 0 — features at band 0 attenuated to 0
    ids = {i.feature_id for i in impacts}
    assert "ice_lake" not in ids


def test_debris_fall_chain_source():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    event = DamageEvent(
        source=DamageSource.DEBRIS_FALL, amount=500,
        origin_band=1, band_radius=0,
    )
    impacts = ed.submit(arena_id="a1", event=event)
    assert any(i.feature_id == "floor_main" for i in impacts)


def test_multi_event_progressive_break():
    env = _seed_env()
    ed = EnvironmentDamage(arena_env=env)
    ed.submit(arena_id="a1", event=DamageEvent(
        source=DamageSource.SPELL_AOE, amount=4000,
        origin_band=2, band_radius=0,
        target_feature_ids=("north_wall",),
    ))
    impacts = ed.submit(arena_id="a1", event=DamageEvent(
        source=DamageSource.SPELL_AOE, amount=8000,
        origin_band=2, band_radius=0,
        target_feature_ids=("north_wall",),
    ))
    assert impacts[0].crossed_break is True
