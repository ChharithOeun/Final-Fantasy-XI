"""Tests for the caravan ambush AI."""
from __future__ import annotations

from server.caravan_ambush_ai import (
    AmbushKind,
    AmbushSeverity,
    CaravanAmbushAI,
    OutcomeKind,
)


def test_schedule_ambush():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="bastok_to_jeuno",
        kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.MODERATE,
        caravan_strength=300,
        scheduled_at_seconds=0.0,
        fires_in_seconds=10.0,
    )
    assert amb is not None
    assert amb.outcome == OutcomeKind.PENDING


def test_schedule_invalid_route():
    a = CaravanAmbushAI()
    assert a.schedule_ambush(
        route_id="", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
    ) is None


def test_schedule_zero_caravan_strength():
    a = CaravanAmbushAI()
    assert a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=0,
    ) is None


def test_intervene_too_early():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=30.0,
    )
    res = a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="alice",
        intervener_strength=500,
        now_seconds=10.0,    # before fires_at
    )
    assert not res.accepted
    assert "not fired" in res.reason


def test_intervene_after_window_expired():
    a = CaravanAmbushAI(intervention_window_seconds=20.0)
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=10.0,
    )
    res = a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="alice",
        intervener_strength=500,
        now_seconds=100.0,
    )
    assert not res.accepted


def test_intervene_drives_off_strong_player():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=0.0,
    )
    res = a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="alice",
        intervener_strength=500,
        now_seconds=1.0,
    )
    assert res.accepted
    assert res.outcome == OutcomeKind.DRIVEN_OFF
    assert res.reward_payout_gil > 0


def test_intervene_overwhelmed_loses():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BEASTMEN,
        severity=AmbushSeverity.CATASTROPHIC,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=0.0,
    )
    res = a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="alice",
        intervener_strength=10,
        now_seconds=1.0,
    )
    assert res.outcome == OutcomeKind.PLAYER_DEFEATED
    assert res.reward_payout_gil == 0


def test_intervene_unknown_ambush():
    a = CaravanAmbushAI()
    res = a.intervene(
        ambush_id="ghost",
        intervener_id="alice",
        intervener_strength=500,
        now_seconds=1.0,
    )
    assert not res.accepted


def test_intervene_already_resolved():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=0.0,
    )
    a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="alice",
        intervener_strength=999,
        now_seconds=1.0,
    )
    res = a.intervene(
        ambush_id=amb.ambush_id,
        intervener_id="bob",
        intervener_strength=999,
        now_seconds=1.0,
    )
    assert not res.accepted
    assert "already resolved" in res.reason


def test_resolve_unattended_caravan_loses():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.HEAVY,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
    )
    outcome = a.resolve_unattended(
        ambush_id=amb.ambush_id, now_seconds=100.0,
    )
    assert outcome == OutcomeKind.CARAVAN_LOST
    # Insurance claim should issue
    claims = a.claims_for_route("r")
    assert len(claims) == 1


def test_resolve_unattended_caravan_survives():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=10000,
        scheduled_at_seconds=0.0,
    )
    outcome = a.resolve_unattended(
        ambush_id=amb.ambush_id,
    )
    assert outcome == OutcomeKind.DRIVEN_OFF


def test_route_risk_increases_after_loss():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.HEAVY,
        caravan_strength=10,
    )
    a.resolve_unattended(ambush_id=amb.ambush_id)
    assert a.route_risk_pct("r") == 10


def test_route_risk_decreases_after_save():
    a = CaravanAmbushAI()
    # First raise risk
    amb1 = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.HEAVY,
        caravan_strength=10,
    )
    a.resolve_unattended(ambush_id=amb1.ambush_id)
    # Now intervene successfully
    amb2 = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        scheduled_at_seconds=0.0,
        fires_in_seconds=0.0,
    )
    a.intervene(
        ambush_id=amb2.ambush_id,
        intervener_id="alice",
        intervener_strength=999,
        now_seconds=1.0,
    )
    assert a.route_risk_pct("r") == 7   # 10 - 3


def test_active_ambushes_on_route():
    a = CaravanAmbushAI()
    a.schedule_ambush(
        route_id="r1", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
    )
    a.schedule_ambush(
        route_id="r2", kind=AmbushKind.BEASTMEN,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
    )
    assert len(a.active_ambushes_on_route("r1")) == 1


def test_tick_resolves_expired():
    a = CaravanAmbushAI(intervention_window_seconds=10.0)
    a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.HEAVY,
        caravan_strength=10,
        scheduled_at_seconds=0.0,
        fires_in_seconds=0.0,
    )
    outcomes = a.tick(now_seconds=50.0)
    assert len(outcomes) == 1


def test_tick_keeps_pending():
    a = CaravanAmbushAI()
    a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.HEAVY,
        caravan_strength=10,
        scheduled_at_seconds=0.0,
        fires_in_seconds=10.0,
    )
    outcomes = a.tick(now_seconds=5.0)
    assert outcomes == ()


def test_total_counts():
    a = CaravanAmbushAI()
    a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
    )
    a.schedule_ambush(
        route_id="r", kind=AmbushKind.PIRATES,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
    )
    assert a.total_ambushes() == 2
    assert a.total_claims() == 0


def test_ambusher_strength_explicit_override():
    a = CaravanAmbushAI()
    amb = a.schedule_ambush(
        route_id="r", kind=AmbushKind.BANDITS,
        severity=AmbushSeverity.LIGHT,
        caravan_strength=100,
        ambusher_strength=42,
    )
    assert amb.ambusher_strength == 42
