"""Tests for the death recap."""
from __future__ import annotations

from server.death_recap import (
    CauseOfDeath,
    DamageType,
    DeathRecapSystem,
    MitigationKind,
)


def test_record_damage():
    d = DeathRecapSystem()
    assert d.record_damage(
        player_id="alice",
        source_id="orc_chief",
        dmg_type=DamageType.PHYSICAL,
        amount=300, hp_after=200,
        at_seconds=1.0,
    )


def test_record_negative_rejected():
    d = DeathRecapSystem()
    assert not d.record_damage(
        player_id="alice",
        source_id="x",
        dmg_type=DamageType.PHYSICAL,
        amount=-10, hp_after=0,
    )


def test_compose_recap_unknown_player():
    d = DeathRecapSystem()
    assert d.compose_recap(
        player_id="ghost",
        killing_blow_at_seconds=0.0,
    ) is None


def test_compose_recap_no_events():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100, at_seconds=0.0,
    )
    # Killing blow at t=1000 — events outside window
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=1000.0,
    )
    assert recap is None


def test_compose_recap_basic():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=200, hp_after=300,
        at_seconds=0.0,
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=300, hp_after=0,
        at_seconds=1.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=1.0,
    )
    assert recap is not None
    assert recap.total_damage == 500
    assert recap.killer_id == "orc"


def test_diagnose_fall_damage():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="cliff",
        dmg_type=DamageType.FALL,
        amount=2000, hp_after=0,
        at_seconds=0.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=0.0,
    )
    assert recap.cause == CauseOfDeath.FALL_DAMAGE


def test_diagnose_dot_tick():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="poison",
        dmg_type=DamageType.DOT,
        amount=50, hp_after=0,
        at_seconds=0.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=0.0,
    )
    assert recap.cause == CauseOfDeath.DOT_TICK


def test_diagnose_burst_combo():
    d = DeathRecapSystem()
    for i in range(4):
        d.record_damage(
            player_id="alice",
            source_id="orc",
            dmg_type=DamageType.PHYSICAL,
            amount=100, hp_after=0,
            at_seconds=float(i) * 0.5,
        )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=2.0,
    )
    assert recap.cause == CauseOfDeath.BURST_COMBO


def test_diagnose_killing_blow_overflow():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="boss",
        dmg_type=DamageType.MAGIC,
        amount=2000, hp_after=0,
        at_seconds=0.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=0.0,
    )
    assert recap.cause == CauseOfDeath.KILLING_BLOW_OVERFLOW


def test_diagnose_unknown_for_modest_single_hit():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="boss",
        dmg_type=DamageType.MAGIC,
        amount=300, hp_after=0,
        at_seconds=0.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=0.0,
    )
    assert recap.cause == CauseOfDeath.UNKNOWN


def test_burst_window_total_excludes_old():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=200,
        at_seconds=0.0,
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100,
        at_seconds=8.0,    # within window but outside burst
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=300,
        at_seconds=10.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=10.0,
    )
    # burst window is last 3 seconds: amounts at 8 and 10
    assert recap.burst_window_total == 400


def test_streak_no_mitigation():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100,
        mitigation=MitigationKind.NONE,
        at_seconds=0.0,
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100,
        mitigation=MitigationKind.NONE,
        at_seconds=1.0,
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=50,
        mitigation=MitigationKind.STONESKIN,
        at_seconds=2.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=2.0,
    )
    assert recap.longest_no_mitigation_streak == 2


def test_recap_filters_window():
    d = DeathRecapSystem(recap_window=5.0)
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100, at_seconds=0.0,
    )
    d.record_damage(
        player_id="alice",
        source_id="orc",
        dmg_type=DamageType.PHYSICAL,
        amount=100, at_seconds=20.0,
    )
    recap = d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=20.0,
    )
    # Only the late event is in the 5s window
    assert len(recap.events) == 1


def test_reset_clears_buffer():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice",
        source_id="x",
        dmg_type=DamageType.PHYSICAL,
        amount=10, at_seconds=0.0,
    )
    assert d.reset(player_id="alice")
    assert d.compose_recap(
        player_id="alice",
        killing_blow_at_seconds=0.0,
    ) is None


def test_reset_unknown_returns_false():
    d = DeathRecapSystem()
    assert not d.reset(player_id="ghost")


def test_max_events_cap():
    d = DeathRecapSystem(max_events=3)
    for i in range(10):
        d.record_damage(
            player_id="alice",
            source_id="x",
            dmg_type=DamageType.PHYSICAL,
            amount=10,
            at_seconds=float(i),
        )
    buf = d._events["alice"]
    assert len(buf) == 3


def test_total_players_tracked():
    d = DeathRecapSystem()
    d.record_damage(
        player_id="alice", source_id="x",
        dmg_type=DamageType.PHYSICAL,
        amount=10, at_seconds=0.0,
    )
    d.record_damage(
        player_id="bob", source_id="x",
        dmg_type=DamageType.PHYSICAL,
        amount=10, at_seconds=0.0,
    )
    assert d.total_players_tracked() == 2
