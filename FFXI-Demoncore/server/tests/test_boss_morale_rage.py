"""Tests for boss_morale_rage."""
from __future__ import annotations

from server.boss_morale_rage import (
    BAND_THRESHOLDS,
    BossMoraleRage,
    PROVOCATION_GAIN,
    Provocation,
    RAGE_DECAY_AFTER_QUIET_SECONDS,
    RAGE_DECAY_PER_SECOND,
    RAGE_MAX,
    RageBand,
)


def test_start_fight_happy():
    b = BossMoraleRage()
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", now_seconds=0,
    ) is True


def test_dup_fight_blocked():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    assert b.start_fight(
        boss_id="vorrak", fight_id="f1", now_seconds=10,
    ) is False


def test_initial_band_calm():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    assert b.band(boss_id="vorrak", fight_id="f1") == RageBand.CALM


def test_tick_accumulates_rage():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    # tick within the quiet window — no decay
    b.tick(
        boss_id="vorrak", fight_id="f1",
        dt_seconds=20, now_seconds=20,
    )
    assert b.rage_value(boss_id="vorrak", fight_id="f1") == 20


def test_provocation_immediately_raises():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
    )
    assert b.rage_value(
        boss_id="vorrak", fight_id="f1",
    ) == PROVOCATION_GAIN[Provocation.PHASE_CROSSED]


def test_band_thresholds():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    # push to AGITATED
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=2,
    )
    assert b.band(boss_id="vorrak", fight_id="f1") == RageBand.AGITATED
    # push to ENRAGED
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=20,
        magnitude=3,
    )
    assert b.band(boss_id="vorrak", fight_id="f1") == RageBand.ENRAGED


def test_apocalyptic_caps_at_max():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=20,
    )
    assert b.rage_value(boss_id="vorrak", fight_id="f1") == RAGE_MAX
    assert b.band(
        boss_id="vorrak", fight_id="f1",
    ) == RageBand.APOCALYPTIC


def test_quiet_decay():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=3,
    )
    rage_before = b.rage_value(boss_id="vorrak", fight_id="f1")
    # tick well past quiet threshold
    b.tick(
        boss_id="vorrak", fight_id="f1",
        dt_seconds=10,
        now_seconds=10 + RAGE_DECAY_AFTER_QUIET_SECONDS + 5,
    )
    rage_after = b.rage_value(boss_id="vorrak", fight_id="f1")
    # baseline gain (10) plus decay (-50) = net -40
    assert rage_after < rage_before


def test_calm_reduces():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
    )
    b.calm(
        boss_id="vorrak", fight_id="f1", amount=30, now_seconds=15,
    )
    assert b.rage_value(boss_id="vorrak", fight_id="f1") == 70


def test_modifiers_scale_with_band():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    calm = b.modifiers(boss_id="vorrak", fight_id="f1")
    assert calm.damage_out_pct == 100
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=10,
    )
    apoc = b.modifiers(boss_id="vorrak", fight_id="f1")
    assert apoc.damage_out_pct == 200
    assert apoc.mitigation_ignore_pct == 100


def test_ability_tier_unlocked_by_band():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    # tier 0 always
    assert b.ability_unlocked(
        boss_id="vorrak", fight_id="f1", ability_tier=0,
    ) is True
    # tier 4 (APOCALYPTIC) blocked at start
    assert b.ability_unlocked(
        boss_id="vorrak", fight_id="f1", ability_tier=4,
    ) is False
    # push to apocalyptic
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=10,
    )
    assert b.ability_unlocked(
        boss_id="vorrak", fight_id="f1", ability_tier=4,
    ) is True


def test_unknown_fight_safe():
    b = BossMoraleRage()
    assert b.band(boss_id="ghost", fight_id="x") == RageBand.CALM
    assert b.modifiers(
        boss_id="ghost", fight_id="x",
    ).damage_out_pct == 100
    assert b.rage_value(boss_id="ghost", fight_id="x") == 0


def test_provoke_zero_magnitude_blocked():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    assert b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
        magnitude=0,
    ) is False


def test_calm_below_zero_clamped():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.calm(
        boss_id="vorrak", fight_id="f1", amount=10000, now_seconds=10,
    )
    assert b.rage_value(boss_id="vorrak", fight_id="f1") == 0


def test_provocation_resets_quiet_timer():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PHASE_CROSSED, now_seconds=10,
    )
    # tick after long pause but with fresh provocation
    b.provoke(
        boss_id="vorrak", fight_id="f1",
        provocation=Provocation.PARRIED_OR_DODGED,
        now_seconds=100,
    )
    rage_before = b.rage_value(boss_id="vorrak", fight_id="f1")
    b.tick(
        boss_id="vorrak", fight_id="f1",
        dt_seconds=5, now_seconds=105,
    )
    # quiet timer just reset, no decay yet → rage should grow
    rage_after = b.rage_value(boss_id="vorrak", fight_id="f1")
    assert rage_after > rage_before


def test_band_count():
    """5 distinct bands defined."""
    bands = {band for _, band in BAND_THRESHOLDS}
    assert len(bands) == 5


def test_negative_dt_no_change():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    before = b.rage_value(boss_id="vorrak", fight_id="f1")
    b.tick(
        boss_id="vorrak", fight_id="f1",
        dt_seconds=-1, now_seconds=10,
    )
    assert b.rage_value(boss_id="vorrak", fight_id="f1") == before


def test_invalid_ability_tier():
    b = BossMoraleRage()
    b.start_fight(boss_id="vorrak", fight_id="f1", now_seconds=0)
    assert b.ability_unlocked(
        boss_id="vorrak", fight_id="f1", ability_tier=99,
    ) is False
