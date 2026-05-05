"""Tests for kraken world boss."""
from __future__ import annotations

from server.kraken_world_boss import (
    DEFAULT_HP_MAX,
    KrakenPhase,
    KrakenStage,
    KrakenWorldBoss,
)


def test_dormant_when_unscheduled():
    k = KrakenWorldBoss()
    assert k.observe(now_seconds=0) == KrakenStage.DORMANT
    assert k.observe(now_seconds=999_999) == KrakenStage.DORMANT


def test_dormant_before_stir():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=10_000)
    assert k.observe(now_seconds=5_000) == KrakenStage.DORMANT


def test_stirring_during_lead():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    # within first hour of stir
    assert k.observe(now_seconds=30 * 60) == KrakenStage.STIRRING


def test_surfaced_during_window():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    # 1h+15min in -> surfaced
    assert k.observe(
        now_seconds=3_600 + 15 * 60,
    ) == KrakenStage.SURFACED


def test_retreating_after_window():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    # past 1h + 30min, before 1h+30+5min
    assert k.observe(
        now_seconds=3_600 + 32 * 60,
    ) == KrakenStage.RETREATING


def test_recovering_long_after():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    # well past retreating
    assert k.observe(
        now_seconds=3_600 + 60 * 60,
    ) == KrakenStage.RECOVERING


def test_phase_lookup_full_hp():
    assert KrakenWorldBoss.resolve_phase(
        hp_remaining_pct=100,
    ) == KrakenPhase.SUBMERGED


def test_phase_lookup_60pct():
    assert KrakenWorldBoss.resolve_phase(
        hp_remaining_pct=60,
    ) == KrakenPhase.INK_CLOUD


def test_phase_lookup_25pct():
    assert KrakenWorldBoss.resolve_phase(
        hp_remaining_pct=25,
    ) == KrakenPhase.ENRAGE_DEEP


def test_phase_lookup_5pct():
    assert KrakenWorldBoss.resolve_phase(
        hp_remaining_pct=5,
    ) == KrakenPhase.BLEEDING_GOD


def test_apply_damage_blocked_when_dormant():
    k = KrakenWorldBoss()
    r = k.apply_damage(dmg=100, now_seconds=0)
    assert r.accepted is False
    assert r.reason == "not surfaced"


def test_apply_damage_during_surfaced():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    # 300k damage -> 70% HP -> INK_CLOUD phase
    r = k.apply_damage(
        dmg=300_000,
        now_seconds=3_600 + 5 * 60,
    )
    assert r.accepted is True
    assert r.hp_remaining == DEFAULT_HP_MAX - 300_000
    assert r.phase == KrakenPhase.INK_CLOUD


def test_apply_damage_to_zero_defeats():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    r = k.apply_damage(
        dmg=DEFAULT_HP_MAX,
        now_seconds=3_600 + 5 * 60,
    )
    assert r.accepted is True
    assert r.hp_remaining == 0
    assert r.defeated is True
    assert r.phase == KrakenPhase.BLEEDING_GOD


def test_apply_damage_negative_rejected():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    r = k.apply_damage(
        dmg=-1, now_seconds=3_600 + 60,
    )
    assert r.accepted is False


def test_schedule_resets_hp():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0)
    k.apply_damage(dmg=999_999, now_seconds=3_600 + 60)
    # should be near-dead
    k.schedule_next_stir(seed_seconds=10_000)
    # HP reset
    assert k.hp_remaining == DEFAULT_HP_MAX


def test_weeks_offset_advances_stir():
    k = KrakenWorldBoss()
    k.schedule_next_stir(seed_seconds=0, weeks_offset=2)
    # 2 weeks of recovery
    assert k.next_stir_at_seconds == 2 * 7 * 24 * 3_600
