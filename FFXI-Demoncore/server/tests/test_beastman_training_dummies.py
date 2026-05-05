"""Tests for the beastman training dummies."""
from __future__ import annotations

from server.beastman_training_dummies import (
    BeastmanTrainingDummies,
    DummyKind,
)


def _seed(t):
    t.register_dummy(
        dummy_id="oz_plate_dummy",
        kind=DummyKind.HEAVY_PLATE,
        hp_pool=10_000,
    )


def test_register():
    t = BeastmanTrainingDummies()
    _seed(t)
    assert t.total_dummies() == 1


def test_register_duplicate():
    t = BeastmanTrainingDummies()
    _seed(t)
    res = t.register_dummy(
        dummy_id="oz_plate_dummy",
        kind=DummyKind.LIGHT_LEATHER,
        hp_pool=5000,
    )
    assert res is None


def test_register_zero_hp():
    t = BeastmanTrainingDummies()
    res = t.register_dummy(
        dummy_id="bad", kind=DummyKind.HEAVY_PLATE, hp_pool=0,
    )
    assert res is None


def test_strike_basic():
    t = BeastmanTrainingDummies()
    _seed(t)
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=200,
        now_seconds=0,
    )
    assert res.accepted
    assert res.damage_dealt == 200
    assert res.insight_after == 1


def test_strike_below_bucket_no_stack():
    t = BeastmanTrainingDummies()
    _seed(t)
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=100,
        now_seconds=0,
    )
    assert res.insight_after == 0


def test_strike_accumulates_pool():
    t = BeastmanTrainingDummies()
    _seed(t)
    t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=100,
        now_seconds=0,
    )
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=100,
        now_seconds=10,
    )
    assert res.insight_after == 1


def test_strike_unknown_dummy():
    t = BeastmanTrainingDummies()
    res = t.strike(
        player_id="kraw",
        dummy_id="ghost",
        damage=200,
        now_seconds=0,
    )
    assert not res.accepted


def test_strike_zero_damage():
    t = BeastmanTrainingDummies()
    _seed(t)
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=0,
        now_seconds=0,
    )
    assert not res.accepted


def test_strike_insight_caps_at_10():
    t = BeastmanTrainingDummies()
    _seed(t)
    for i in range(20):
        t.strike(
            player_id="kraw",
            dummy_id="oz_plate_dummy",
            damage=200,
            now_seconds=i,
        )
    snap = t.insight_for(
        player_id="kraw",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=20,
    )
    assert snap.stacks == 10


def test_dummy_resets_on_depletion():
    t = BeastmanTrainingDummies()
    t.register_dummy(
        dummy_id="weak",
        kind=DummyKind.LIGHT_LEATHER,
        hp_pool=200,
    )
    res = t.strike(
        player_id="kraw",
        dummy_id="weak",
        damage=500,
        now_seconds=0,
    )
    # Dummy reset to full pool after depletion
    assert res.hp_remaining == 200
    # Damage_dealt was clamped to remaining HP (200)
    assert res.damage_dealt == 200


def test_insight_decay_after_window():
    t = BeastmanTrainingDummies()
    _seed(t)
    for _ in range(5):
        t.strike(
            player_id="kraw",
            dummy_id="oz_plate_dummy",
            damage=200,
            now_seconds=0,
        )
    # Stacks at 5
    snap = t.insight_for(
        player_id="kraw",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=0,
    )
    assert snap.stacks == 5
    # 360s later → 1 decay
    snap = t.insight_for(
        player_id="kraw",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=360,
    )
    assert snap.stacks == 4
    # 1800s past last gain → 5 decays from 5 = 0
    snap = t.insight_for(
        player_id="kraw",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=2000,
    )
    assert snap.stacks == 0


def test_insight_for_default_zero():
    t = BeastmanTrainingDummies()
    snap = t.insight_for(
        player_id="ghost",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=0,
    )
    assert snap.stacks == 0


def test_per_kind_isolation():
    t = BeastmanTrainingDummies()
    _seed(t)
    t.register_dummy(
        dummy_id="leather",
        kind=DummyKind.LIGHT_LEATHER,
        hp_pool=10_000,
    )
    t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=400,
        now_seconds=0,
    )
    plate = t.insight_for(
        player_id="kraw",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=0,
    )
    leather = t.insight_for(
        player_id="kraw",
        kind=DummyKind.LIGHT_LEATHER,
        now_seconds=0,
    )
    assert plate.stacks == 2
    assert leather.stacks == 0


def test_per_player_isolation():
    t = BeastmanTrainingDummies()
    _seed(t)
    t.strike(
        player_id="alice",
        dummy_id="oz_plate_dummy",
        damage=400,
        now_seconds=0,
    )
    snap_bob = t.insight_for(
        player_id="bob",
        kind=DummyKind.HEAVY_PLATE,
        now_seconds=0,
    )
    assert snap_bob.stacks == 0


def test_continued_strikes_refresh_decay_anchor():
    t = BeastmanTrainingDummies()
    _seed(t)
    # Stack to 1
    t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=200,
        now_seconds=0,
    )
    # Strike again 200s later (should not decay yet)
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=200,
        now_seconds=200,
    )
    assert res.insight_after == 2


def test_evasive_ghost_dummy():
    t = BeastmanTrainingDummies()
    t.register_dummy(
        dummy_id="ghost",
        kind=DummyKind.EVASIVE_GHOST,
        hp_pool=5000,
    )
    res = t.strike(
        player_id="kraw",
        dummy_id="ghost",
        damage=200,
        now_seconds=0,
    )
    assert res.accepted


def test_magic_ward_dummy():
    t = BeastmanTrainingDummies()
    t.register_dummy(
        dummy_id="ward",
        kind=DummyKind.MAGIC_WARD,
        hp_pool=5000,
    )
    res = t.strike(
        player_id="kraw",
        dummy_id="ward",
        damage=600,
        now_seconds=0,
    )
    assert res.insight_after == 3


def test_negative_damage_rejected():
    t = BeastmanTrainingDummies()
    _seed(t)
    res = t.strike(
        player_id="kraw",
        dummy_id="oz_plate_dummy",
        damage=-10,
        now_seconds=0,
    )
    assert not res.accepted
