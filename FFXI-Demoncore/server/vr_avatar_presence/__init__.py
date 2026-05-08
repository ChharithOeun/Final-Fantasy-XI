"""VR avatar presence — multiplayer IK rig sync.

When a VR player swings a sword in your direction, OTHER
players (VR or flat-screen) need to see that swing
ACTUALLY HAPPEN on the player's avatar — not the canned
auto-attack animation. This module is the network layer
that ships head + hands pose data so a remote viewer can
drive the avatar's IK rig.

Per VR player we track three transforms:
    head    HMD pose (position + rotation)
    left    left controller (position + rotation)
    right   right controller (position + rotation)

A "transform" is (x, y, z) position + (qx, qy, qz, qw)
quaternion rotation. We store the latest sample plus a
short rolling buffer for interpolation on the receiver.

Update rate: VR runtimes deliver pose at 72-120Hz, but we
don't ship every sample. Adjacent samples within
_MIN_DELTA (3 cm position OR 5 deg rotation) are dropped.
Otherwise we'd flood the network with imperceptible jitter.

Public surface
--------------
    Joint enum  (HEAD, LEFT_HAND, RIGHT_HAND)
    Pose dataclass (frozen) — (x, y, z, qx, qy, qz, qw,
                                 timestamp_ms)
    AvatarSnapshot dataclass (frozen) — head + left + right
                                         + player_id + ts
    VrAvatarPresence
        .ingest(player_id, joint, pose) -> bool
        .snapshot(player_id) -> Optional[AvatarSnapshot]
        .all_visible(viewer_player_id, visibility_predicate)
            -> list[AvatarSnapshot]
        .clear(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


_MIN_POS_DELTA_M = 0.03
_MIN_ROT_DELTA_DEG = 5.0


class Joint(str, enum.Enum):
    HEAD = "head"
    LEFT_HAND = "left_hand"
    RIGHT_HAND = "right_hand"


@dataclasses.dataclass(frozen=True)
class Pose:
    x: float
    y: float
    z: float
    qx: float
    qy: float
    qz: float
    qw: float
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class AvatarSnapshot:
    player_id: str
    head: Pose
    left_hand: Pose
    right_hand: Pose
    timestamp_ms: int


def _quat_angle_deg(a: Pose, b: Pose) -> float:
    """Angle (deg) between two quaternions as rotations."""
    dot = (a.qx * b.qx + a.qy * b.qy
           + a.qz * b.qz + a.qw * b.qw)
    dot = max(-1.0, min(1.0, abs(dot)))
    return math.degrees(2.0 * math.acos(dot))


def _pos_delta(a: Pose, b: Pose) -> float:
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


@dataclasses.dataclass
class VrAvatarPresence:
    _last: dict[
        tuple[str, Joint], Pose,
    ] = dataclasses.field(default_factory=dict)

    def ingest(
        self, *, player_id: str, joint: Joint, pose: Pose,
    ) -> bool:
        if not player_id:
            return False
        key = (player_id, joint)
        prev = self._last.get(key)
        if prev is not None:
            # Reject out-of-order timestamps
            if pose.timestamp_ms < prev.timestamp_ms:
                return False
            # Drop sub-threshold jitter
            if (_pos_delta(prev, pose) < _MIN_POS_DELTA_M
                    and _quat_angle_deg(prev, pose)
                    < _MIN_ROT_DELTA_DEG):
                return False
        self._last[key] = pose
        return True

    def snapshot(
        self, *, player_id: str,
    ) -> t.Optional[AvatarSnapshot]:
        head = self._last.get((player_id, Joint.HEAD))
        left = self._last.get((player_id, Joint.LEFT_HAND))
        right = self._last.get((player_id, Joint.RIGHT_HAND))
        if head is None or left is None or right is None:
            return None
        ts = max(head.timestamp_ms,
                 left.timestamp_ms,
                 right.timestamp_ms)
        return AvatarSnapshot(
            player_id=player_id, head=head,
            left_hand=left, right_hand=right,
            timestamp_ms=ts,
        )

    def all_visible(
        self, *, viewer_player_id: str,
        visibility_predicate: t.Callable[[str], bool],
    ) -> list[AvatarSnapshot]:
        seen_players: set[str] = set()
        for (pid, _) in self._last.keys():
            seen_players.add(pid)
        out = []
        for pid in seen_players:
            if pid == viewer_player_id:
                continue  # don't render your own rig to you
            if not visibility_predicate(pid):
                continue  # sneak/invis filter from caller
            snap = self.snapshot(player_id=pid)
            if snap is not None:
                out.append(snap)
        out.sort(key=lambda s: s.player_id)
        return out

    def clear(self, *, player_id: str) -> bool:
        keys = [k for k in self._last if k[0] == player_id]
        for k in keys:
            del self._last[k]
        return bool(keys)


__all__ = [
    "Joint", "Pose", "AvatarSnapshot", "VrAvatarPresence",
]
