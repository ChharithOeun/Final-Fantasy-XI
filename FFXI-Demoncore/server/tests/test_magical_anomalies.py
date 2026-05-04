"""Tests for magical anomalies."""
from __future__ import annotations

from server.magical_anomalies import (
    AnomalyKind,
    AnomalyStatus,
    AnomalyTier,
    MagicalAnomalies,
)


def test_spawn_anomaly():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="ronfaure",
        kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.MODERATE,
        spawned_at_seconds=0.0,
    )
    assert a is not None
    assert a.status == AnomalyStatus.OPEN


def test_spawn_empty_zone_rejected():
    m = MagicalAnomalies()
    assert m.spawn_anomaly(
        zone_id="",
        kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    ) is None


def test_participate_succeeds():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.AURORA_STORM,
        tier=AnomalyTier.MODERATE,
    )
    res = m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=10,
    )
    assert res.accepted
    assert res.cumulative_contribution == 10


def test_participate_unknown():
    m = MagicalAnomalies()
    res = m.participate(
        anomaly_id="ghost",
        player_id="alice", contribution=1,
    )
    assert not res.accepted


def test_participate_after_window_rejected():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
        spawned_at_seconds=0.0,
        window_seconds=10.0,
    )
    res = m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=1,
        now_seconds=100.0,
    )
    assert not res.accepted
    assert "expired" in res.reason


def test_participate_zero_rejected():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    res = m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=0,
    )
    assert not res.accepted


def test_resolve_distributes_pool():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.AURORA_STORM,
        tier=AnomalyTier.MODERATE,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=2,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="bob", contribution=3,
    )
    payout = m.resolve(anomaly_id=a.anomaly_id)
    assert payout is not None
    # MODERATE = 500 pool. Alice 2/5 = 200, Bob 3/5 = 300.
    payouts = dict(payout.payouts)
    assert payouts["alice"] == 200
    assert payouts["bob"] == 300


def test_resolve_no_contributors():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    payout = m.resolve(anomaly_id=a.anomaly_id)
    assert payout is not None
    assert payout.payouts == ()
    assert payout.total_pool == 0


def test_resolve_unknown_returns_none():
    m = MagicalAnomalies()
    assert m.resolve(anomaly_id="ghost") is None


def test_resolve_already_resolved_returns_none():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    m.resolve(anomaly_id=a.anomaly_id)
    assert m.resolve(anomaly_id=a.anomaly_id) is None


def test_tick_expires_unattended():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
        spawned_at_seconds=0.0,
        window_seconds=10.0,
    )
    flipped = m.tick(now_seconds=100.0)
    assert a.anomaly_id in flipped
    assert m.get(a.anomaly_id).status == (
        AnomalyStatus.EXPIRED
    )


def test_tick_cascades_when_unattended():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.PRIMAL_SURGE,
        tier=AnomalyTier.LESSER,
        spawned_at_seconds=0.0,
        window_seconds=10.0,
        cascades_into=AnomalyTier.GREATER,
    )
    m.tick(now_seconds=100.0)
    assert m.get(a.anomaly_id).status == AnomalyStatus.CASCADED
    # A new GREATER anomaly should exist
    actives = m.active_in_zone("z")
    assert any(
        a2.tier == AnomalyTier.GREATER for a2 in actives
    )


def test_tick_keeps_open_inside_window():
    m = MagicalAnomalies()
    m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.AURORA_STORM,
        tier=AnomalyTier.MODERATE,
        spawned_at_seconds=0.0,
        window_seconds=100.0,
    )
    flipped = m.tick(now_seconds=10.0)
    assert flipped == ()


def test_active_in_zone_filter():
    m = MagicalAnomalies()
    m.spawn_anomaly(
        zone_id="z1", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    m.spawn_anomaly(
        zone_id="z2", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    z1 = m.active_in_zone("z1")
    assert len(z1) == 1


def test_active_in_zone_excludes_resolved():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    m.resolve(anomaly_id=a.anomaly_id)
    assert m.active_in_zone("z") == ()


def test_participate_accumulates_per_player():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.MOONSHADOW_WELL,
        tier=AnomalyTier.LESSER,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=3,
    )
    res = m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=2,
    )
    assert res.cumulative_contribution == 5


def test_payouts_sorted_descending():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.AURORA_STORM,
        tier=AnomalyTier.MODERATE,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=1,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="bob", contribution=4,
    )
    payout = m.resolve(anomaly_id=a.anomaly_id)
    # bob's larger payout should appear first
    assert payout.payouts[0][0] == "bob"


def test_world_shaking_pool_largest():
    m = MagicalAnomalies()
    a = m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.PRIMAL_SURGE,
        tier=AnomalyTier.WORLD_SHAKING,
    )
    m.participate(
        anomaly_id=a.anomaly_id,
        player_id="alice", contribution=1,
    )
    payout = m.resolve(anomaly_id=a.anomaly_id)
    assert payout.total_pool == 12000


def test_total_anomalies():
    m = MagicalAnomalies()
    m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.VOID_RIFT,
        tier=AnomalyTier.LESSER,
    )
    m.spawn_anomaly(
        zone_id="z", kind=AnomalyKind.AURORA_STORM,
        tier=AnomalyTier.LESSER,
    )
    assert m.total_anomalies() == 2
