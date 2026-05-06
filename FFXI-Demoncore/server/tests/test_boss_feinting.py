"""Tests for boss_feinting."""
from __future__ import annotations

from server.boss_feinting import (
    BossFeinting,
    DEFAULT_FEINT_COOLDOWN,
    PRESSURE_BONUS_PCT_PER_BURN,
)


def test_start_fight_happy():
    b = BossFeinting()
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
    ) is True


def test_dup_fight_blocked():
    b = BossFeinting()
    b.start_fight(boss_id="vorrak", fight_id="f1", started_at=0)
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
    ) is False


def test_invalid_chance_blocked():
    b = BossFeinting()
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=-5,
    ) is False
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=150,
    ) is False


def test_zero_chance_never_feints():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=0,
    )
    out = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10,
        rng_roll_pct=1,
    )
    assert out.is_feint is False


def test_high_chance_feints():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=100,
    )
    out = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10,
        rng_roll_pct=50,
    )
    assert out.is_feint is True


def test_feint_cooldown_blocks_next():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=100,
    )
    first = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10, rng_roll_pct=50,
    )
    assert first.is_feint is True
    second = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="y", now_seconds=15, rng_roll_pct=50,
    )
    assert second.is_feint is False
    assert second.feint_cooldown_remaining > 0


def test_feint_after_cooldown_works():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=100,
    )
    b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10, rng_roll_pct=50,
    )
    later = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="y",
        now_seconds=10 + DEFAULT_FEINT_COOLDOWN + 1,
        rng_roll_pct=50,
    )
    assert later.is_feint is True


def test_pressure_burn_increases_chance():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=10,
    )
    # without pressure: roll 30 > 10% → no feint
    no_press = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10, rng_roll_pct=30,
    )
    assert no_press.is_feint is False
    # add pressure — 5 burns (after 1s decay = 4 burns = +20%)
    b.note_reactive_cooldown_burn(
        boss_id="vorrak", fight_id="f1",
        burn_count=5, now_seconds=11,
    )
    # at now=12, 1s decay drops pressure 5→4, bonus = 20%
    # chance = 10 + 20 = 30; roll 25 <= 30 → feint
    with_press = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="y", now_seconds=12, rng_roll_pct=25,
    )
    assert with_press.is_feint is True
    assert with_press.chance_used_pct == 30


def test_pressure_decays_over_time():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
    )
    b.note_reactive_cooldown_burn(
        boss_id="vorrak", fight_id="f1",
        burn_count=3, now_seconds=10,
    )
    # Roll way later — pressure should be decayed
    out = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=200, rng_roll_pct=50,
    )
    # pressure decayed to 0 → chance_used = base only (15)
    assert b.pressure_score(
        boss_id="vorrak", fight_id="f1",
    ) == 0


def test_total_feints_counter():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=100, cooldown_seconds=0,
    )
    b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10, rng_roll_pct=50,
    )
    b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="y", now_seconds=20, rng_roll_pct=50,
    )
    assert b.total_feints(
        boss_id="vorrak", fight_id="f1",
    ) == 2


def test_unknown_fight_safe():
    b = BossFeinting()
    out = b.roll_feint(
        boss_id="ghost", fight_id="x",
        ability_id="a", now_seconds=10, rng_roll_pct=50,
    )
    assert out.accepted is False


def test_invalid_rng_roll():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
    )
    out = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=10, rng_roll_pct=0,
    )
    assert out.accepted is False


def test_blank_boss_or_fight():
    b = BossFeinting()
    assert b.start_fight(
        boss_id="", fight_id="f1", started_at=0,
    ) is False
    assert b.start_fight(
        boss_id="v", fight_id="", started_at=0,
    ) is False


def test_feint_resets_pressure():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=100,
    )
    b.note_reactive_cooldown_burn(
        boss_id="vorrak", fight_id="f1",
        burn_count=3, now_seconds=10,
    )
    assert b.pressure_score(
        boss_id="vorrak", fight_id="f1",
    ) == 3
    b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=11, rng_roll_pct=50,
    )
    assert b.pressure_score(
        boss_id="vorrak", fight_id="f1",
    ) == 0


def test_chance_capped_at_100():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
        base_chance_pct=80,
    )
    b.note_reactive_cooldown_burn(
        boss_id="vorrak", fight_id="f1",
        burn_count=99, now_seconds=10,
    )
    out = b.roll_feint(
        boss_id="vorrak", fight_id="f1",
        ability_id="x", now_seconds=11, rng_roll_pct=100,
    )
    assert out.chance_used_pct == 100


def test_zero_burn_count_blocked():
    b = BossFeinting()
    b.start_fight(
        boss_id="vorrak", fight_id="f1", started_at=0,
    )
    assert b.note_reactive_cooldown_burn(
        boss_id="vorrak", fight_id="f1",
        burn_count=0, now_seconds=10,
    ) is False
