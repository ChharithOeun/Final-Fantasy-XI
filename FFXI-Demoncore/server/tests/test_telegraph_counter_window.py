"""Tests for telegraph_counter_window."""
from __future__ import annotations

from server.telegraph_counter_window import (
    CounterKind,
    ENMITY_LOSS_PER_COUNTER,
    TelegraphCounterWindow,
    TP_REFUND_PCT_OF_PREVENTED,
    VULN_AMPLIFIER,
    VULN_WINDOW_SECONDS,
)


def test_register_window_happy():
    w = TelegraphCounterWindow()
    ok = w.register_window(
        boss_id="vorrak", fight_id="f1",
        ability_id="spirit_surge",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK, CounterKind.PARRY],
    )
    assert ok is True


def test_invalid_window_blocked():
    w = TelegraphCounterWindow()
    bad = w.register_window(
        boss_id="vorrak", fight_id="f1", ability_id="x",
        opens_at=10, expires_at=10,
        prevented_damage=100,
        valid_kinds=[CounterKind.BLOCK],
    )
    assert bad is False


def test_zero_damage_blocked():
    w = TelegraphCounterWindow()
    out = w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=12,
        prevented_damage=0,
        valid_kinds=[CounterKind.BLOCK],
    )
    assert out is False


def test_no_valid_kinds_blocked():
    w = TelegraphCounterWindow()
    out = w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=12,
        prevented_damage=100, valid_kinds=[],
    )
    assert out is False


def test_attempt_too_early():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=5,
    )
    assert out.accepted is False
    assert out.reason == "too early"


def test_attempt_too_late():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=20,
    )
    assert out.accepted is False
    assert out.reason == "too late"


def test_attempt_in_window_success():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=12,
    )
    assert out.accepted is True
    assert out.success is True
    assert out.tp_refunded == 240   # 12% of 2000
    assert out.vuln_window_seconds == VULN_WINDOW_SECONDS
    assert out.vuln_amplifier == VULN_AMPLIFIER
    assert out.enmity_loss == ENMITY_LOSS_PER_COUNTER


def test_wrong_counter_kind():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.PARRY,
        player_id="alice", now_seconds=12,
    )
    assert out.accepted is False


def test_window_consumed_after_success():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=14,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=12,
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="bob", now_seconds=13,
    )
    assert out.accepted is False
    assert out.reason == "already countered"


def test_no_window_registered():
    w = TelegraphCounterWindow()
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="ghost",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=12,
    )
    assert out.accepted is False


def test_total_counters():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=0, expires_at=100,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=10,
    )
    assert w.total_counters(player_id="alice") == 1


def test_blank_player_blocked():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=0, expires_at=100,
        prevented_damage=2000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="", now_seconds=10,
    )
    assert out.accepted is False


def test_is_window_active():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=10, expires_at=20,
        prevented_damage=100,
        valid_kinds=[CounterKind.BLOCK],
    )
    assert w.is_window_active(
        boss_id="v", fight_id="f", ability_id="x",
        now_seconds=5,
    ) is False
    assert w.is_window_active(
        boss_id="v", fight_id="f", ability_id="x",
        now_seconds=15,
    ) is True
    assert w.is_window_active(
        boss_id="v", fight_id="f", ability_id="x",
        now_seconds=25,
    ) is False


def test_dispel_kind_for_caster_abilities():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="mirahna", fight_id="f", ability_id="meteor",
        opens_at=0, expires_at=10,
        prevented_damage=5000,
        valid_kinds=[CounterKind.DISPEL, CounterKind.INTERRUPT],
    )
    out = w.attempt_counter(
        boss_id="mirahna", fight_id="f", ability_id="meteor",
        counter_kind=CounterKind.DISPEL,
        player_id="rdm", now_seconds=5,
    )
    assert out.success is True


def test_intervene_kind_for_pld():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="cone_of_doom",
        opens_at=0, expires_at=10,
        prevented_damage=3000,
        valid_kinds=[CounterKind.INTERVENE],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="cone_of_doom",
        counter_kind=CounterKind.INTERVENE,
        player_id="pld", now_seconds=5,
    )
    assert out.success is True


def test_six_counter_kinds():
    assert len(list(CounterKind)) == 6


def test_re_register_after_consume():
    """After a window is consumed, registering same boss/ability
    again should be allowed (next telegraph for the same ability)."""
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=0, expires_at=10,
        prevented_damage=100,
        valid_kinds=[CounterKind.BLOCK],
    )
    w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=5,
    )
    # consumed; new window can register
    ok = w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=20, expires_at=30,
        prevented_damage=200,
        valid_kinds=[CounterKind.BLOCK],
    )
    assert ok is True


def test_tp_refund_calculation():
    w = TelegraphCounterWindow()
    w.register_window(
        boss_id="v", fight_id="f", ability_id="x",
        opens_at=0, expires_at=10,
        prevented_damage=10000,
        valid_kinds=[CounterKind.BLOCK],
    )
    out = w.attempt_counter(
        boss_id="v", fight_id="f", ability_id="x",
        counter_kind=CounterKind.BLOCK,
        player_id="alice", now_seconds=5,
    )
    # 12% of 10000 = 1200
    assert out.tp_refunded == 1200
    assert TP_REFUND_PCT_OF_PREVENTED == 12
