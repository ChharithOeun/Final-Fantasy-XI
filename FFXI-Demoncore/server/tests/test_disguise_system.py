"""Tests for the disguise system."""
from __future__ import annotations

from server.disguise_system import (
    DEFAULT_PIERCE_THRESHOLD,
    DisguiseKind,
    DisguiseSystem,
    PierceResult,
)


def _seed(d: DisguiseSystem, pid="alice"):
    d.register_real_identity(
        player_id=pid, name="Alice",
        race="Hume", job="WAR75/NIN37",
    )


def test_disguise_creates_active():
    d = DisguiseSystem()
    _seed(d)
    res = d.disguise(
        player_id="alice",
        kind=DisguiseKind.RP_ONLY,
        alias_name="Veiled Wanderer",
        alias_race="Elvaan",
        alias_job="???",
        duration_seconds=600.0,
    )
    assert res is not None
    assert d.is_disguised(player_id="alice")


def test_disguise_double_rejected():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    res = d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="a", alias_race="b", alias_job="c",
        duration_seconds=100.0,
    )
    assert res is None


def test_disguise_zero_duration_rejected():
    d = DisguiseSystem()
    _seed(d)
    res = d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=0.0,
    )
    assert res is None


def test_disguise_empty_alias_rejected():
    d = DisguiseSystem()
    _seed(d)
    res = d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="", alias_race="y", alias_job="z",
        duration_seconds=10.0,
    )
    assert res is None


def test_duration_clamped_to_max():
    d = DisguiseSystem(max_duration=60.0)
    _seed(d)
    res = d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=99999.0,
        now_seconds=0.0,
    )
    assert res.expires_at_seconds == 60.0


def test_reveal_voluntarily():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    assert d.reveal(player_id="alice")
    assert not d.is_disguised(player_id="alice")


def test_reveal_when_not_disguised():
    d = DisguiseSystem()
    assert not d.reveal(player_id="alice")


def test_visible_identity_disguised_to_others():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="Mystery", alias_race="Mithra",
        alias_job="???",
        duration_seconds=100.0,
    )
    vi = d.visible_identity(
        viewer_id="bob", target_id="alice",
    )
    assert vi.name == "Mystery"
    assert vi.is_disguised_view


def test_visible_identity_self_unmasked():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="Mystery", alias_race="Mithra",
        alias_job="???",
        duration_seconds=100.0,
    )
    vi = d.visible_identity(
        viewer_id="alice", target_id="alice",
    )
    assert vi.name == "Alice"
    assert not vi.is_disguised_view


def test_visible_identity_unknown_returns_none():
    d = DisguiseSystem()
    assert d.visible_identity(
        viewer_id="bob", target_id="ghost",
    ) is None


def test_pierce_below_threshold_no_effect():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    res = d.pierce(
        viewer_id="bob", target_id="alice",
        perception=10,
    )
    assert res == PierceResult.NO_EFFECT


def test_pierce_at_threshold_partial():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    res = d.pierce(
        viewer_id="bob", target_id="alice",
        perception=DEFAULT_PIERCE_THRESHOLD,
    )
    assert res == PierceResult.PARTIAL_PIERCE


def test_pierce_three_witnesses_reveals():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    for viewer in ("bob", "carol", "dan"):
        res = d.pierce(
            viewer_id=viewer, target_id="alice",
            perception=200,
        )
    assert res == PierceResult.REVEALED
    assert not d.is_disguised(player_id="alice")


def test_pierce_self_no_effect():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    res = d.pierce(
        viewer_id="alice", target_id="alice",
        perception=999,
    )
    assert res == PierceResult.NO_EFFECT


def test_pierce_dedup_per_viewer():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    d.pierce(
        viewer_id="bob", target_id="alice",
        perception=200,
    )
    res = d.pierce(
        viewer_id="bob", target_id="alice",
        perception=200,
    )
    assert res == PierceResult.PARTIAL_PIERCE
    assert d.is_disguised(player_id="alice")


def test_pierce_no_active_disguise():
    d = DisguiseSystem()
    _seed(d)
    res = d.pierce(
        viewer_id="bob", target_id="alice",
        perception=999,
    )
    assert res == PierceResult.NO_EFFECT


def test_piercer_sees_real_identity():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="Mystery", alias_race="Mithra",
        alias_job="???",
        duration_seconds=100.0,
    )
    d.pierce(
        viewer_id="bob", target_id="alice",
        perception=200,
    )
    vi_bob = d.visible_identity(
        viewer_id="bob", target_id="alice",
    )
    vi_carol = d.visible_identity(
        viewer_id="carol", target_id="alice",
    )
    assert vi_bob.name == "Alice"
    assert vi_carol.name == "Mystery"


def test_tick_expires_old():
    d = DisguiseSystem()
    _seed(d)
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=10.0,
        now_seconds=0.0,
    )
    expired = d.tick(now_seconds=100.0)
    assert "alice" in expired
    assert not d.is_disguised(player_id="alice")


def test_register_real_identity_empty_rejected():
    d = DisguiseSystem()
    assert not d.register_real_identity(
        player_id="alice", name="",
        race="Hume", job="WAR",
    )


def test_total_active_disguises():
    d = DisguiseSystem()
    _seed(d, "alice")
    _seed(d, "bob")
    d.disguise(
        player_id="alice", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    d.disguise(
        player_id="bob", kind=DisguiseKind.RP_ONLY,
        alias_name="x", alias_race="y", alias_job="z",
        duration_seconds=100.0,
    )
    assert d.total_active_disguises() == 2
