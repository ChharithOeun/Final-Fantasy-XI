"""Tests for net_replication."""
from __future__ import annotations

import pytest

from server.net_replication import (
    DEFAULT_INTEREST_RADIUS_M,
    EntityKind,
    NetReplicationSystem,
    PARTY_RADIUS_MULTIPLIER,
    PREDICTION_SNAP_DELTA_CM,
    ReplicationTier,
    Snapshot,
)


def _snap(
    eid="p1",
    kind=EntityKind.PLAYER,
    pos=(0.0, 0.0, 0.0),
    vel=(0.0, 0.0, 0.0),
    yaw=0.0,
    hp=1.0,
    mp=1.0,
    tp=0,
    flags=0,
    anim=0,
    tick=1,
    ts=1000,
):
    return Snapshot(
        entity_id=eid,
        kind=kind,
        position_xyz=pos,
        velocity_xyz=vel,
        yaw_deg=yaw,
        hp_pct=hp,
        mp_pct=mp,
        tp=tp,
        status_flags_bitmap=flags,
        anim_state_id=anim,
        server_tick=tick,
        timestamp_ms=ts,
    )


# ---- enum coverage ----

def test_entity_kind_count():
    assert len(list(EntityKind)) == 7


def test_entity_kind_has_projectile():
    assert EntityKind.PROJECTILE in list(EntityKind)


def test_entity_kind_has_destructible():
    assert EntityKind.DESTRUCTIBLE_PROP in list(EntityKind)


def test_replication_tier_has_local_player():
    assert ReplicationTier.LOCAL_PLAYER in list(ReplicationTier)


def test_replication_tier_count():
    assert len(list(ReplicationTier)) == 8


# ---- register ----

def test_register_entity():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    assert s.is_registered("p1")
    assert s.kind_of("p1") == EntityKind.PLAYER
    assert s.entity_count() == 1


def test_register_empty_id_raises():
    s = NetReplicationSystem()
    with pytest.raises(ValueError):
        s.register_entity("", EntityKind.PLAYER)


def test_register_duplicate_raises():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    with pytest.raises(ValueError):
        s.register_entity("p1", EntityKind.MOB)


def test_kind_unknown_raises():
    s = NetReplicationSystem()
    with pytest.raises(KeyError):
        s.kind_of("ghost")


# ---- snapshots ----

def test_record_snapshot():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap())
    assert s.history_size("p1") == 1
    assert s.latest_snapshot("p1").entity_id == "p1"


def test_record_snapshot_unknown_entity_raises():
    s = NetReplicationSystem()
    with pytest.raises(KeyError):
        s.record_snapshot(_snap())


def test_record_snapshot_kind_mismatch_raises():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    with pytest.raises(ValueError):
        s.record_snapshot(_snap(kind=EntityKind.MOB))


def test_history_bounded():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    for i in range(200):
        s.record_snapshot(_snap(ts=1000 + i))
    # Default cap is 64.
    assert s.history_size("p1") == 64


# ---- interest radius ----

def test_default_interest_radius():
    s = NetReplicationSystem()
    assert s.interest_radius("p1") == DEFAULT_INTEREST_RADIUS_M


def test_set_interest_radius():
    s = NetReplicationSystem()
    s.set_interest_radius("p1", 75.0)
    assert s.interest_radius("p1") == 75.0


def test_negative_interest_radius_raises():
    s = NetReplicationSystem()
    with pytest.raises(ValueError):
        s.set_interest_radius("p1", -1)


# ---- social link ----

def test_link_social():
    s = NetReplicationSystem()
    s.link_social("p1", ["p2", "p3"])
    assert s.is_linked("p1", "p2")
    assert s.is_linked("p1", "p3")
    assert not s.is_linked("p1", "p4")


def test_clear_social():
    s = NetReplicationSystem()
    s.link_social("p1", ["p2"])
    s.clear_social("p1")
    assert not s.is_linked("p1", "p2")


# ---- relevancy ----

def test_relevant_includes_self():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap())
    out = s.relevant_entities_for("p1", ["p1"])
    assert "p1" in out


def test_relevant_filters_far():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.register_entity("p2", EntityKind.PLAYER)
    s.record_snapshot(_snap(eid="p1", pos=(0, 0, 0)))
    s.record_snapshot(_snap(eid="p2", pos=(500, 0, 0)))
    out = s.relevant_entities_for("p1", ["p1", "p2"])
    assert "p2" not in out


def test_relevant_includes_near():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.register_entity("p2", EntityKind.PLAYER)
    s.record_snapshot(_snap(eid="p1", pos=(0, 0, 0)))
    s.record_snapshot(_snap(eid="p2", pos=(30, 0, 0)))
    out = s.relevant_entities_for("p1", ["p1", "p2"])
    assert "p2" in out


def test_relevant_party_extends_radius():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.register_entity("p2", EntityKind.PLAYER)
    s.record_snapshot(_snap(eid="p1", pos=(0, 0, 0)))
    # 260m — past base 200m radius, inside 200*1.5=300m party.
    s.record_snapshot(_snap(eid="p2", pos=(260, 0, 0)))
    base = s.relevant_entities_for("p1", ["p1", "p2"])
    assert "p2" not in base
    s.link_social("p1", ["p2"])
    extended = s.relevant_entities_for("p1", ["p1", "p2"])
    assert "p2" in extended


def test_party_multiplier_value():
    # Documented multiplier should be 1.5.
    assert PARTY_RADIUS_MULTIPLIER == 1.5


# ---- replication tier ----

def test_tier_local_player():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "p1", 0.0, EntityKind.PLAYER)
    assert t == ReplicationTier.LOCAL_PLAYER


def test_tier_projectile():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "arrow", 10.0, EntityKind.PROJECTILE)
    assert t == ReplicationTier.PROJECTILE


def test_tier_nearby_close():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "p2", 25.0, EntityKind.PLAYER)
    assert t == ReplicationTier.NEARBY_PLAYER_CLOSE


def test_tier_nearby_mid():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "p2", 100.0, EntityKind.PLAYER)
    assert t == ReplicationTier.NEARBY_PLAYER_MID


def test_tier_nearby_far():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "p2", 250.0, EntityKind.PLAYER)
    assert t == ReplicationTier.NEARBY_PLAYER_FAR


def test_tier_mob_combat():
    s = NetReplicationSystem()
    s.set_mob_combat("m1", True)
    t = s.replication_tier_for("p1", "m1", 20.0, EntityKind.MOB)
    assert t == ReplicationTier.MOB_COMBAT


def test_tier_mob_idle():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "m1", 20.0, EntityKind.MOB)
    assert t == ReplicationTier.MOB_IDLE


def test_tier_npc_static():
    s = NetReplicationSystem()
    t = s.replication_tier_for("p1", "n1", 20.0, EntityKind.NPC)
    assert t == ReplicationTier.STATIC_ON_CHANGE


def test_tier_dropped_item_static():
    s = NetReplicationSystem()
    t = s.replication_tier_for(
        "p1", "i1", 5.0, EntityKind.DROPPED_ITEM,
    )
    assert t == ReplicationTier.STATIC_ON_CHANGE


def test_replication_rate_local_60hz():
    s = NetReplicationSystem()
    r = s.replication_rate_for("p1", "p1", 0.0, EntityKind.PLAYER)
    assert r == 60.0


def test_replication_rate_far_2hz():
    s = NetReplicationSystem()
    r = s.replication_rate_for("p1", "p2", 250.0, EntityKind.PLAYER)
    assert r == 2.0


def test_replication_rate_projectile_60hz():
    s = NetReplicationSystem()
    r = s.replication_rate_for(
        "p1", "arrow", 10.0, EntityKind.PROJECTILE,
    )
    assert r == 60.0


def test_negative_distance_raises():
    s = NetReplicationSystem()
    with pytest.raises(ValueError):
        s.replication_tier_for(
            "p1", "p2", -1.0, EntityKind.PLAYER,
        )


# ---- prediction ----

def test_predict_position_stationary():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap(pos=(5, 0, 0)))
    p = s.predict_position("p1", 100)
    assert p == (5.0, 0.0, 0.0)


def test_predict_position_moving():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap(pos=(0, 0, 0), vel=(10, 0, 0)))
    p = s.predict_position("p1", 100)
    # 10 m/s * 0.1s = 1.0m
    assert abs(p[0] - 1.0) < 1e-6


def test_predict_negative_t_raises():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap())
    with pytest.raises(ValueError):
        s.predict_position("p1", -1)


# ---- reconcile ----

def test_reconcile_no_delta_no_snap():
    s = NetReplicationSystem()
    s.set_client_predicted("p1", (10.0, 0.0, 0.0))
    server = _snap(eid="p1", pos=(10.0, 0.0, 0.0))
    r = s.reconcile("p1", server)
    assert r.delta_cm == 0.0
    assert not r.should_snap
    assert r.blend_ms == 100


def test_reconcile_small_delta_blend():
    s = NetReplicationSystem()
    s.set_client_predicted("p1", (10.0, 0.0, 0.0))
    # 20cm = 0.2m delta — below snap threshold.
    server = _snap(eid="p1", pos=(10.2, 0.0, 0.0))
    r = s.reconcile("p1", server)
    assert abs(r.delta_cm - 20.0) < 0.001
    assert not r.should_snap


def test_reconcile_large_delta_snap():
    s = NetReplicationSystem()
    s.set_client_predicted("p1", (10.0, 0.0, 0.0))
    # 1m delta — way above 50cm threshold.
    server = _snap(eid="p1", pos=(11.0, 0.0, 0.0))
    r = s.reconcile("p1", server)
    assert r.delta_cm == 100.0
    assert r.should_snap
    assert r.blend_ms == 0


def test_prediction_snap_threshold_value():
    assert PREDICTION_SNAP_DELTA_CM == 50.0


# ---- snapshot interpolation ----

def test_snapshot_at_single_history():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap(pos=(5, 0, 0), ts=1000))
    p = s.snapshot_at("p1", 50)
    assert p == (5.0, 0.0, 0.0)


def test_snapshot_at_interpolates_midpoint():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap(pos=(0, 0, 0), ts=1000))
    s.record_snapshot(_snap(pos=(10, 0, 0), ts=1100))
    # 50ms in the past from latest (1100) => 1050 => midpoint.
    p = s.snapshot_at("p1", 50)
    assert abs(p[0] - 5.0) < 1e-6


def test_snapshot_at_clamps_to_oldest():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap(pos=(0, 0, 0), ts=1000))
    s.record_snapshot(_snap(pos=(10, 0, 0), ts=1100))
    # 9999ms in past — clamps to oldest.
    p = s.snapshot_at("p1", 9999)
    assert p == (0.0, 0.0, 0.0)


def test_snapshot_at_negative_raises():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    s.record_snapshot(_snap())
    with pytest.raises(ValueError):
        s.snapshot_at("p1", -1)


def test_snapshot_at_unknown_raises():
    s = NetReplicationSystem()
    with pytest.raises(KeyError):
        s.snapshot_at("ghost", 50)


# ---- pruning ----

def test_prune_history_before():
    s = NetReplicationSystem()
    s.register_entity("p1", EntityKind.PLAYER)
    for ts in (1000, 1100, 1200, 1300):
        s.record_snapshot(_snap(ts=ts))
    removed = s.prune_history_before("p1", 1150)
    assert removed == 2
    assert s.history_size("p1") == 2


def test_latest_snapshot_unknown_raises():
    s = NetReplicationSystem()
    with pytest.raises(KeyError):
        s.latest_snapshot("ghost")
