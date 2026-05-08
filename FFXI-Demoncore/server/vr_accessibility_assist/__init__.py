"""VR accessibility assist — make VR work for more bodies.

Default VR assumes a player who can stand, has two
working hands, and is the average height. Real players
vary. This module is the per-player accommodation set
that makes the same VR character playable across:

    one_handed_mode     player has one usable hand —
                        right-controller actions get
                        moved to the left, gestures
                        that need both hands trigger via
                        a held grip + button instead.
                        Mutually exclusive: pick LEFT or
                        RIGHT as the active hand.

    height_offset_m     virtual elevation added to the
                        player's HMD-tracked Y so a
                        seated short player feels the
                        same eye-line as a standing tall
                        player. Range -1.0..+1.5m.

    aim_assist_strength gentle "snap to soft target"
                        pull on attack/cast actions —
                        helps players with tremor or
                        limited dexterity. 0.0=off,
                        1.0=full magnetic. Default 0.0.

    cast_dwell_ms       how long a player needs to hold
                        a cast pose before it fires.
                        Higher dwell = forgiving of
                        slow-finger sequences. 0..2000ms.

    motion_safe_zone_m  shrinks the safety boundary
                        (vr_room_scale_safety) for
                        players who tend to drift. e.g.
                        a 3m room treated as 2.5m.

    auto_recenter_after a player who sits in one place
                        gets auto-recentered if drift
                        > X seconds. 0=disabled.

The module is purely the configuration registry. Other
modules (vr_controller_bindings, vr_gesture_recognizer,
vr_room_scale_safety) READ this state to adjust their
behavior. We don't store cross-module state here.

Public surface
--------------
    ActiveHand enum
    AccessibilityProfile dataclass (frozen)
    VrAccessibilityAssist
        .set_one_handed(player_id, active_hand) -> bool
        .clear_one_handed(player_id) -> bool
        .set_height_offset(player_id, meters) -> bool
        .set_aim_assist(player_id, strength) -> bool
        .set_cast_dwell(player_id, ms) -> bool
        .set_motion_safe_shrink(player_id, m) -> bool
        .set_auto_recenter_after(player_id, seconds) -> bool
        .profile(player_id) -> AccessibilityProfile
        .reset(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_HEIGHT_MIN_M = -1.0
_HEIGHT_MAX_M = 1.5
_AIM_ASSIST_MIN = 0.0
_AIM_ASSIST_MAX = 1.0
_CAST_DWELL_MIN_MS = 0
_CAST_DWELL_MAX_MS = 2000
_SAFE_SHRINK_MIN_M = 0.0
_SAFE_SHRINK_MAX_M = 1.5
_RECENTER_MIN_S = 0
_RECENTER_MAX_S = 600


class ActiveHand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class AccessibilityProfile:
    one_handed: t.Optional[ActiveHand]
    height_offset_m: float
    aim_assist_strength: float
    cast_dwell_ms: int
    motion_safe_shrink_m: float
    auto_recenter_after_s: int


_DEFAULT = AccessibilityProfile(
    one_handed=None,
    height_offset_m=0.0,
    aim_assist_strength=0.0,
    cast_dwell_ms=0,
    motion_safe_shrink_m=0.0,
    auto_recenter_after_s=0,
)


@dataclasses.dataclass
class VrAccessibilityAssist:
    _profiles: dict[
        str, AccessibilityProfile,
    ] = dataclasses.field(default_factory=dict)

    def _get(self, player_id: str) -> AccessibilityProfile:
        return self._profiles.get(player_id, _DEFAULT)

    def _set(
        self, player_id: str,
        profile: AccessibilityProfile,
    ) -> None:
        self._profiles[player_id] = profile

    def set_one_handed(
        self, *, player_id: str, active_hand: ActiveHand,
    ) -> bool:
        if not player_id:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, one_handed=active_hand,
        ))
        return True

    def clear_one_handed(
        self, *, player_id: str,
    ) -> bool:
        prof = self._get(player_id)
        if prof.one_handed is None:
            return False
        self._set(player_id, dataclasses.replace(
            prof, one_handed=None,
        ))
        return True

    def set_height_offset(
        self, *, player_id: str, meters: float,
    ) -> bool:
        if not player_id:
            return False
        if meters < _HEIGHT_MIN_M or meters > _HEIGHT_MAX_M:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, height_offset_m=meters,
        ))
        return True

    def set_aim_assist(
        self, *, player_id: str, strength: float,
    ) -> bool:
        if not player_id:
            return False
        if (strength < _AIM_ASSIST_MIN
                or strength > _AIM_ASSIST_MAX):
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, aim_assist_strength=strength,
        ))
        return True

    def set_cast_dwell(
        self, *, player_id: str, ms: int,
    ) -> bool:
        if not player_id:
            return False
        if ms < _CAST_DWELL_MIN_MS or ms > _CAST_DWELL_MAX_MS:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, cast_dwell_ms=ms,
        ))
        return True

    def set_motion_safe_shrink(
        self, *, player_id: str, m: float,
    ) -> bool:
        if not player_id:
            return False
        if m < _SAFE_SHRINK_MIN_M or m > _SAFE_SHRINK_MAX_M:
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, motion_safe_shrink_m=m,
        ))
        return True

    def set_auto_recenter_after(
        self, *, player_id: str, seconds: int,
    ) -> bool:
        if not player_id:
            return False
        if (seconds < _RECENTER_MIN_S
                or seconds > _RECENTER_MAX_S):
            return False
        prof = self._get(player_id)
        self._set(player_id, dataclasses.replace(
            prof, auto_recenter_after_s=seconds,
        ))
        return True

    def profile(
        self, *, player_id: str,
    ) -> AccessibilityProfile:
        return self._get(player_id)

    def reset(self, *, player_id: str) -> bool:
        if player_id not in self._profiles:
            return False
        del self._profiles[player_id]
        return True


__all__ = [
    "ActiveHand", "AccessibilityProfile",
    "VrAccessibilityAssist",
]
