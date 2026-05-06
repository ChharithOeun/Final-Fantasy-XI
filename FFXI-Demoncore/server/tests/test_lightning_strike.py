"""Tests for lightning_strike."""
from __future__ import annotations

from server.lightning_strike import LightningStrikeEngine


def test_blank_target():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="", intensity=100, rng_roll_pct=0,
    )
    assert out.struck is False


def test_zero_intensity_no_strike():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=0, rng_roll_pct=0,
    )
    assert out.struck is False


def test_low_chance_misses_high_roll():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=0, on_high_ground=False,
        rng_roll_pct=99,
    )
    # base 1% with no metal, no high ground → low chance
    assert out.struck is False


def test_metal_armor_increases_chance():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=30, on_high_ground=False,
        rng_roll_pct=20,
    )
    # 1 + 30 = 31% chance, roll 20 < 31 → struck
    assert out.struck is True


def test_high_ground_adds_5():
    e = LightningStrikeEngine()
    # base 1% + 5 high_ground = 6%
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=0, on_high_ground=True,
        rng_roll_pct=4,
    )
    assert out.struck is True
    out_miss = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=0, on_high_ground=True,
        rng_roll_pct=10,
    )
    assert out_miss.struck is False


def test_lightning_rod_always_strikes():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        has_lightning_rod=True, rng_roll_pct=99,
    )
    assert out.struck is True
    assert out.redirected is True
    assert out.chance_pct == 100


def test_lightning_rod_halves_damage():
    e = LightningStrikeEngine()
    no_rod = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=99, rng_roll_pct=0, resist_pct=0,
    )
    with_rod = e.roll_strike(
        target_id="alice", intensity=100,
        has_lightning_rod=True, resist_pct=0,
    )
    # with_rod halves
    assert with_rod.damage <= no_rod.damage // 2 + 1


def test_resist_pct_reduces_damage():
    e = LightningStrikeEngine()
    full = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=99, rng_roll_pct=0, resist_pct=0,
    )
    half = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=99, rng_roll_pct=0, resist_pct=50,
    )
    assert half.damage == full.damage // 2


def test_resist_100_negates():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=99, rng_roll_pct=0, resist_pct=100,
    )
    assert out.struck is True
    assert out.damage == 0


def test_low_intensity_low_damage():
    e = LightningStrikeEngine()
    out_high = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=99, rng_roll_pct=0,
    )
    out_low = e.roll_strike(
        target_id="alice", intensity=20,
        metal_mass=99, rng_roll_pct=0,
    )
    assert out_low.damage < out_high.damage


def test_chance_capped_at_100():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=200, on_high_ground=True,
        rng_roll_pct=0,
    )
    assert out.chance_pct <= 100


def test_chance_floor_at_zero():
    e = LightningStrikeEngine()
    # negative metal mass shouldn't push chance below 0
    out = e.roll_strike(
        target_id="alice", intensity=1,
        metal_mass=-100, on_high_ground=False,
        rng_roll_pct=50,
    )
    assert out.struck is False
    assert out.chance_pct >= 0


def test_chance_pct_returned():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=15, on_high_ground=False,
        rng_roll_pct=50,
    )
    # 1 + 15 = 16
    assert out.chance_pct == 16


def test_roll_below_chance_strikes():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=80, on_high_ground=True,
        rng_roll_pct=10,
    )
    # 1 + 80 + 5 = 86 chance, 10 < 86
    assert out.struck is True


def test_damage_zero_when_not_struck():
    e = LightningStrikeEngine()
    out = e.roll_strike(
        target_id="alice", intensity=100,
        metal_mass=0, rng_roll_pct=99,
    )
    assert out.damage == 0
