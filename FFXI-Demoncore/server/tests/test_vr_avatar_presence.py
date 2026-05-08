"""Tests for vr_avatar_presence."""
from __future__ import annotations

from server.vr_avatar_presence import (
    Joint, Pose, VrAvatarPresence,
)


def _identity_pose(t=1000, x=0.0, y=1.5, z=0.0):
    return Pose(
        x=x, y=y, z=z,
        qx=0.0, qy=0.0, qz=0.0, qw=1.0,
        timestamp_ms=t,
    )


def _full_rig(p, t=1000):
    """Ingest head + both hands for player p at time t."""
    p_a = VrAvatarPresence() if isinstance(p, str) else p
    return p_a


def test_ingest_happy():
    a = VrAvatarPresence()
    assert a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(),
    ) is True


def test_ingest_blank_player_blocked():
    a = VrAvatarPresence()
    assert a.ingest(
        player_id="", joint=Joint.HEAD,
        pose=_identity_pose(),
    ) is False


def test_ingest_out_of_order_blocked():
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=2000),
    )
    out = a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1000),
    )
    assert out is False


def test_ingest_jitter_dropped():
    """Tiny moves under threshold are dropped."""
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1000),
    )
    out = a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1100, x=0.01),  # 1cm
    )
    assert out is False


def test_ingest_real_motion_accepted():
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1000),
    )
    out = a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1100, x=0.1),  # 10cm
    )
    assert out is True


def test_snapshot_requires_all_three_joints():
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(),
    )
    # Missing hands -> no snapshot
    assert a.snapshot(player_id="bob") is None


def test_snapshot_full_rig():
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(t=1000),
    )
    a.ingest(
        player_id="bob", joint=Joint.LEFT_HAND,
        pose=_identity_pose(t=1010, x=-0.3),
    )
    a.ingest(
        player_id="bob", joint=Joint.RIGHT_HAND,
        pose=_identity_pose(t=1020, x=0.3),
    )
    snap = a.snapshot(player_id="bob")
    assert snap is not None
    assert snap.head.x == 0.0
    assert snap.left_hand.x == -0.3
    assert snap.right_hand.x == 0.3
    assert snap.timestamp_ms == 1020


def test_snapshot_unknown_player():
    a = VrAvatarPresence()
    assert a.snapshot(player_id="ghost") is None


def test_all_visible_filters_self():
    a = VrAvatarPresence()
    for j in Joint:
        a.ingest(
            player_id="bob", joint=j,
            pose=_identity_pose(),
        )
    out = a.all_visible(
        viewer_player_id="bob",
        visibility_predicate=lambda _: True,
    )
    assert out == []  # don't render own rig


def test_all_visible_filters_invisible():
    a = VrAvatarPresence()
    for j in Joint:
        a.ingest(
            player_id="bob", joint=j,
            pose=_identity_pose(),
        )
    for j in Joint:
        a.ingest(
            player_id="cara", joint=j,
            pose=_identity_pose(),
        )
    # Predicate hides bob (e.g. he sneaked)
    out = a.all_visible(
        viewer_player_id="dave",
        visibility_predicate=lambda pid: pid != "bob",
    )
    pids = {s.player_id for s in out}
    assert pids == {"cara"}


def test_all_visible_partial_rig_excluded():
    """Player with only head, no hands, isn't listed."""
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=_identity_pose(),
    )
    out = a.all_visible(
        viewer_player_id="dave",
        visibility_predicate=lambda _: True,
    )
    assert out == []


def test_clear_removes_player():
    a = VrAvatarPresence()
    for j in Joint:
        a.ingest(
            player_id="bob", joint=j,
            pose=_identity_pose(),
        )
    assert a.clear(player_id="bob") is True
    assert a.snapshot(player_id="bob") is None


def test_clear_unknown():
    a = VrAvatarPresence()
    assert a.clear(player_id="ghost") is False


def test_three_joints():
    assert len(list(Joint)) == 3


def test_rotation_jitter_dropped():
    """Sub-threshold rotation deltas are dropped too."""
    a = VrAvatarPresence()
    a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=Pose(x=0, y=1.5, z=0,
                  qx=0, qy=0, qz=0, qw=1.0,
                  timestamp_ms=1000),
    )
    # Tiny rotation (~2 degrees) — below 5 deg threshold
    out = a.ingest(
        player_id="bob", joint=Joint.HEAD,
        pose=Pose(x=0, y=1.5, z=0,
                  qx=0, qy=0.017, qz=0, qw=0.9998,
                  timestamp_ms=1100),
    )
    assert out is False
