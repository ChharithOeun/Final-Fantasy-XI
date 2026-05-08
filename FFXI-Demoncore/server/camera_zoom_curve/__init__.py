"""Camera zoom curve — non-linear distance + snap zones.

Linear scroll-wheel zoom feels bad over an 80-yalm
range (one wheel tick = 80/N yalms; either too coarse
near FP or too granular at TOP_DOWN). We use a
non-linear curve so:

    - near FP, each tick is ~0.5 yalms (precision for
      VR-handoff and shoulder framing)
    - mid-range (OVER_SHOULDER → TACTICAL), each tick is
      ~2 yalms
    - high-range (TACTICAL → TOP_DOWN), each tick is
      ~5 yalms (fast pull-back)

Snap zones — magnetic distances the camera lightly
clings to so the player can park at "the obvious good
viewpoint" without fiddling:

    SNAP_FP          0.0   (eyes-out)
    SNAP_SHOULDER    6.0   (canonical retail framing)
    SNAP_TACTICAL    25.0  (mid pull-back)
    SNAP_RAID        50.0  (whole-arena, party visible)
    SNAP_TOPDOWN     75.0  (chess-board)

Snap is HINTING — if the player scrolls within 1.5y of
a snap distance, the camera quietly settles on the snap
distance. They can scroll past it freely; snap doesn't
trap.

apply_tick(current, ticks) computes the new distance
given a number of scroll ticks (negative = zoom in,
positive = zoom out). The result clamps to [0, 80] and
applies snap.

Public surface
--------------
    SNAP_DISTANCES tuple[float, ...]
    CameraZoomCurve
        .apply_tick(current_distance, ticks) -> float
        .snap_to_nearest(distance) -> float
        .yalms_per_tick(distance) -> float
"""
from __future__ import annotations

import dataclasses


_MIN_DISTANCE = 0.0
_MAX_DISTANCE = 80.0
_SNAP_RADIUS = 1.5

SNAP_DISTANCES: tuple[float, ...] = (
    0.0, 6.0, 25.0, 50.0, 75.0,
)


@dataclasses.dataclass
class CameraZoomCurve:

    @staticmethod
    def yalms_per_tick(distance: float) -> float:
        """How many yalms one scroll tick moves the camera
        at this distance. Non-linear: tighter near FP."""
        if distance < 6.0:
            return 0.5
        if distance < 25.0:
            return 2.0
        return 5.0

    @staticmethod
    def snap_to_nearest(distance: float) -> float:
        """If distance is within SNAP_RADIUS of a snap,
        return the snap distance; otherwise return
        distance unchanged."""
        for snap in SNAP_DISTANCES:
            if abs(distance - snap) <= _SNAP_RADIUS:
                return snap
        return distance

    @classmethod
    def apply_tick(
        cls, *, current_distance: float, ticks: int,
    ) -> float:
        """Negative ticks = zoom in, positive = zoom out.
        Each tick moves yalms_per_tick(current). Result
        is clamped + snapped."""
        d = current_distance
        if ticks == 0:
            return cls.snap_to_nearest(d)
        step = 1 if ticks > 0 else -1
        for _ in range(abs(ticks)):
            d = d + step * cls.yalms_per_tick(d)
            if d < _MIN_DISTANCE:
                d = _MIN_DISTANCE
                break
            if d > _MAX_DISTANCE:
                d = _MAX_DISTANCE
                break
        return cls.snap_to_nearest(d)


__all__ = [
    "SNAP_DISTANCES", "CameraZoomCurve",
]
