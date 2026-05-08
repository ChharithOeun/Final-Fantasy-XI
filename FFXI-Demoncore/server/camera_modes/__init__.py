"""Camera modes — per-player view state.

Retail FFXI gives you maybe 3-5 yalms of zoom range
behind your character. We blow that out: zoom from
0 yalms (first-person, eyes-out) all the way to ~80
yalms straight overhead — a tactical chess-board view
of the whole encounter. Players can lock the camera
at whatever distance they find tactical.

Mode states (camera kind, not zoom value):
    FIRST_PERSON       distance ~0; eyes-out
    OVER_SHOULDER      retail-style 3rd person, 4-12y
    TACTICAL           pulled back, 12-40y; angled down
    TOP_DOWN           directly overhead, 40-80y; the
                       chess-board view
    VR_FIRST_PERSON    same position as FIRST_PERSON but
                       VR HMD active (head tracking,
                       stereoscopic) — see vr_mode_hardware_detect

Mode transitions are driven by zoom distance via the
canonical_mode_for_distance() helper. The actual mode
field is set by camera_zoom_curve when the zoom changes;
this module just owns the per-player CameraState and
transition validation.

Public surface
--------------
    CameraMode enum
    CameraState dataclass (frozen)
    CameraModes
        .set_state(player_id, mode, distance, pitch_deg,
                   yaw_deg) -> bool
        .state_for(player_id) -> Optional[CameraState]
        .canonical_mode_for_distance(distance) -> CameraMode
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CameraMode(str, enum.Enum):
    FIRST_PERSON = "first_person"
    OVER_SHOULDER = "over_shoulder"
    TACTICAL = "tactical"
    TOP_DOWN = "top_down"
    VR_FIRST_PERSON = "vr_first_person"


@dataclasses.dataclass(frozen=True)
class CameraState:
    player_id: str
    mode: CameraMode
    distance: float        # yalms behind/above player
    pitch_deg: float       # -90 (straight down) .. 90 (up)
    yaw_deg: float         # 0..360


# Distance band → canonical CameraMode for a non-VR player.
# VR_FIRST_PERSON is set by vr_mode_hardware_detect; we
# never auto-transition into VR from distance alone.
_DISTANCE_BANDS = (
    # (max_distance_inclusive, mode)
    (0.5, CameraMode.FIRST_PERSON),
    (12.0, CameraMode.OVER_SHOULDER),
    (40.0, CameraMode.TACTICAL),
    (80.0, CameraMode.TOP_DOWN),
)


@dataclasses.dataclass
class CameraModes:
    _states: dict[str, CameraState] = dataclasses.field(
        default_factory=dict,
    )

    @staticmethod
    def canonical_mode_for_distance(
        distance: float,
    ) -> CameraMode:
        for max_d, mode in _DISTANCE_BANDS:
            if distance <= max_d:
                return mode
        return CameraMode.TOP_DOWN

    def set_state(
        self, *, player_id: str, mode: CameraMode,
        distance: float, pitch_deg: float, yaw_deg: float,
    ) -> bool:
        if not player_id:
            return False
        if distance < 0 or distance > 80.0:
            return False
        if pitch_deg < -90.0 or pitch_deg > 90.0:
            return False
        # Normalize yaw to [0, 360)
        yaw = yaw_deg % 360.0
        # VR mode pins distance to ~0; reject inconsistent
        if mode == CameraMode.VR_FIRST_PERSON and distance > 0.5:
            return False
        # TOP_DOWN expects steep pitch (looking down).
        # Below -45 means pretty top-down. We don't hard-
        # block other pitches because the player can lean
        # the chess-board angle a bit; but require pitch
        # negative (camera looking down) for TOP_DOWN.
        if mode == CameraMode.TOP_DOWN and pitch_deg > -10.0:
            return False
        self._states[player_id] = CameraState(
            player_id=player_id, mode=mode,
            distance=distance, pitch_deg=pitch_deg,
            yaw_deg=yaw,
        )
        return True

    def state_for(
        self, *, player_id: str,
    ) -> t.Optional[CameraState]:
        return self._states.get(player_id)

    def total_states(self) -> int:
        return len(self._states)


__all__ = [
    "CameraMode", "CameraState", "CameraModes",
]
