"""Player camera rig — the follow camera with modes and
transitions.

The rig is the third actor in the room. The player is one,
the world is two, and the camera is the lens that decides
what the player sees of either. FFXI shipped with a single
fixed third-person follow; modern action games run a small
state machine of camera modes — RE4 over-shoulder for
combat, Witcher 3 wider over-shoulder for traversal,
classic far-third for legacy feel, first-person for
immersion. This module is that state machine.

CameraMode covers the ten states that show up in a complete
demo: FIRST_PERSON, OVER_SHOULDER_TIGHT (RE4-style, 60mm),
OVER_SHOULDER_WIDE (Witcher 3, 75mm), THIRD_PERSON_FAR
(classic FFXI 90mm at 8m), CINEMATIC_TRACK (handed off to
director_ai during cutscenes), FREE_LOOK (player rotates
camera independent of body), CHOCOBO_RIDE (lifted higher
for mount visibility), SWIMMING_UNDERWATER (compressed FOV
+ fog), LEDGE_HANG (pulled wide to read the cliff), and
KO_ORBIT (slow circle around the downed body).

Mode transitions follow a directed graph — engaging combat
auto-zooms THIRD_PERSON_FAR -> OVER_SHOULDER_TIGHT over
0.4s; mounting a chocobo swaps to CHOCOBO_RIDE; entering
water swaps to SWIMMING_UNDERWATER. Any mode can hand off
to CINEMATIC_TRACK and the director_ai owns the camera
until reclaim_from_director is called.

Collision avoidance keeps the rig from clipping geometry —
if the camera would punch through a wall, the spring arm
shortens until collision_radius is satisfied.

Public surface
--------------
    CameraMode enum
    PlayerStateView dataclass (frozen)
    CameraRig dataclass (frozen)
    PlayerCameraRigSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CameraMode(enum.Enum):
    FIRST_PERSON = "first_person"
    OVER_SHOULDER_TIGHT = "over_shoulder_tight"
    OVER_SHOULDER_WIDE = "over_shoulder_wide"
    THIRD_PERSON_FAR = "third_person_far"
    CINEMATIC_TRACK = "cinematic_track"
    FREE_LOOK = "free_look"
    CHOCOBO_RIDE = "chocobo_ride"
    SWIMMING_UNDERWATER = "swimming_underwater"
    LEDGE_HANG = "ledge_hang"
    KO_ORBIT = "ko_orbit"


# Default FOV per mode (degrees).
_FOV_BY_MODE: dict[CameraMode, float] = {
    CameraMode.FIRST_PERSON: 90.0,
    CameraMode.OVER_SHOULDER_TIGHT: 60.0,
    CameraMode.OVER_SHOULDER_WIDE: 75.0,
    CameraMode.THIRD_PERSON_FAR: 90.0,
    CameraMode.CINEMATIC_TRACK: 50.0,
    CameraMode.FREE_LOOK: 80.0,
    CameraMode.CHOCOBO_RIDE: 85.0,
    CameraMode.SWIMMING_UNDERWATER: 70.0,
    CameraMode.LEDGE_HANG: 95.0,
    CameraMode.KO_ORBIT: 65.0,
}


# Default boom distance (meters from focus target).
_DIST_BY_MODE: dict[CameraMode, float] = {
    CameraMode.FIRST_PERSON: 0.0,
    CameraMode.OVER_SHOULDER_TIGHT: 1.6,
    CameraMode.OVER_SHOULDER_WIDE: 2.4,
    CameraMode.THIRD_PERSON_FAR: 8.0,
    CameraMode.CINEMATIC_TRACK: 6.0,
    CameraMode.FREE_LOOK: 5.0,
    CameraMode.CHOCOBO_RIDE: 6.5,
    CameraMode.SWIMMING_UNDERWATER: 3.5,
    CameraMode.LEDGE_HANG: 7.0,
    CameraMode.KO_ORBIT: 4.0,
}


# Allowed (from -> to) transitions. CINEMATIC_TRACK is
# reachable from any mode (director can take over) and
# returns via reclaim_from_director (which restores the
# previous mode). KO_ORBIT is reachable from any mode
# because death can happen anywhere.
_ALLOWED_PAIRS: frozenset[tuple[CameraMode, CameraMode]] = frozenset({
    # First-person <-> classic far third toggle
    (CameraMode.FIRST_PERSON, CameraMode.THIRD_PERSON_FAR),
    (CameraMode.THIRD_PERSON_FAR, CameraMode.FIRST_PERSON),
    # Engage zoom: far -> tight over-shoulder
    (CameraMode.THIRD_PERSON_FAR, CameraMode.OVER_SHOULDER_TIGHT),
    (CameraMode.OVER_SHOULDER_TIGHT, CameraMode.THIRD_PERSON_FAR),
    # Tight <-> wide swap during combat (player choice)
    (CameraMode.OVER_SHOULDER_TIGHT, CameraMode.OVER_SHOULDER_WIDE),
    (CameraMode.OVER_SHOULDER_WIDE, CameraMode.OVER_SHOULDER_TIGHT),
    # Wide <-> far traversal
    (CameraMode.OVER_SHOULDER_WIDE, CameraMode.THIRD_PERSON_FAR),
    (CameraMode.THIRD_PERSON_FAR, CameraMode.OVER_SHOULDER_WIDE),
    # Free-look toggle from any of the standard modes
    (CameraMode.THIRD_PERSON_FAR, CameraMode.FREE_LOOK),
    (CameraMode.FREE_LOOK, CameraMode.THIRD_PERSON_FAR),
    (CameraMode.OVER_SHOULDER_WIDE, CameraMode.FREE_LOOK),
    (CameraMode.FREE_LOOK, CameraMode.OVER_SHOULDER_WIDE),
    # Chocobo ride entry/exit
    (CameraMode.THIRD_PERSON_FAR, CameraMode.CHOCOBO_RIDE),
    (CameraMode.CHOCOBO_RIDE, CameraMode.THIRD_PERSON_FAR),
    # Swimming entry/exit
    (CameraMode.THIRD_PERSON_FAR, CameraMode.SWIMMING_UNDERWATER),
    (CameraMode.SWIMMING_UNDERWATER, CameraMode.THIRD_PERSON_FAR),
    (CameraMode.OVER_SHOULDER_WIDE, CameraMode.SWIMMING_UNDERWATER),
    (CameraMode.SWIMMING_UNDERWATER, CameraMode.OVER_SHOULDER_WIDE),
    # Ledge-hang entry/exit
    (CameraMode.THIRD_PERSON_FAR, CameraMode.LEDGE_HANG),
    (CameraMode.LEDGE_HANG, CameraMode.THIRD_PERSON_FAR),
    (CameraMode.OVER_SHOULDER_WIDE, CameraMode.LEDGE_HANG),
    (CameraMode.LEDGE_HANG, CameraMode.OVER_SHOULDER_WIDE),
})


def _is_universal_target(to_mode: CameraMode) -> bool:
    # Any mode -> CINEMATIC_TRACK or KO_ORBIT is allowed.
    return to_mode in (
        CameraMode.CINEMATIC_TRACK, CameraMode.KO_ORBIT,
    )


@dataclasses.dataclass(frozen=True)
class PlayerStateView:
    in_combat: bool = False
    engaged: bool = False
    on_chocobo: bool = False
    swimming: bool = False
    on_ledge: bool = False
    ko_state: bool = False
    in_cutscene: bool = False


@dataclasses.dataclass(frozen=True)
class CameraRig:
    rig_id: str
    current_mode: CameraMode
    fov_deg: float
    distance_m_from_target: float
    height_offset_m: float
    lerp_speed_s: float
    smoothing: float  # 0..1, lower = snappier
    collision_radius_m: float
    target_npc_id: str = ""


@dataclasses.dataclass
class _RigInternal:
    rig: CameraRig
    prev_mode: CameraMode | None = None
    director_owned: bool = False
    director_shot_kind: str = ""
    transition_t: float = 1.0  # 0..1, 1 = fully arrived
    transition_duration_s: float = 0.0
    transition_from_mode: CameraMode | None = None


@dataclasses.dataclass
class PlayerCameraRigSystem:
    _rigs: dict[str, _RigInternal] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- register
    def register_rig(self, rig: CameraRig) -> None:
        if not rig.rig_id:
            raise ValueError("rig_id required")
        if rig.rig_id in self._rigs:
            raise ValueError(
                f"duplicate rig_id: {rig.rig_id}",
            )
        if rig.fov_deg <= 0 or rig.fov_deg >= 180:
            raise ValueError("fov_deg must be in (0, 180)")
        if rig.distance_m_from_target < 0:
            raise ValueError("distance must be >= 0")
        if rig.collision_radius_m < 0:
            raise ValueError("collision_radius must be >= 0")
        if not (0.0 <= rig.smoothing <= 1.0):
            raise ValueError("smoothing must be in [0, 1]")
        self._rigs[rig.rig_id] = _RigInternal(rig=rig)

    def get_rig(self, rig_id: str) -> CameraRig:
        if rig_id not in self._rigs:
            raise KeyError(f"unknown rig_id: {rig_id}")
        return self._rigs[rig_id].rig

    def rig_count(self) -> int:
        return len(self._rigs)

    # ---------------------------------------------- modes
    def fov_for(self, mode: CameraMode) -> float:
        return _FOV_BY_MODE[mode]

    def default_distance_for(self, mode: CameraMode) -> float:
        return _DIST_BY_MODE[mode]

    def allowed_transition(
        self,
        from_mode: CameraMode,
        to_mode: CameraMode,
    ) -> bool:
        if from_mode == to_mode:
            return True
        if _is_universal_target(to_mode):
            return True
        # Any mode can return to standard exploration
        # (THIRD_PERSON_FAR) when KO_ORBIT or CINEMATIC_TRACK
        # ends — but explicit pair is required otherwise.
        return (from_mode, to_mode) in _ALLOWED_PAIRS

    def set_mode(
        self,
        rig_id: str,
        mode: CameraMode,
        transition_s: float = 0.0,
    ) -> CameraRig:
        if rig_id not in self._rigs:
            raise KeyError(f"unknown rig_id: {rig_id}")
        if transition_s < 0:
            raise ValueError("transition_s must be >= 0")
        internal = self._rigs[rig_id]
        cur_mode = internal.rig.current_mode
        if not self.allowed_transition(cur_mode, mode):
            raise ValueError(
                f"transition {cur_mode.value} -> "
                f"{mode.value} not allowed",
            )
        # Save previous for KO_ORBIT / CINEMATIC restore
        internal.prev_mode = cur_mode
        internal.transition_from_mode = cur_mode
        internal.transition_duration_s = transition_s
        internal.transition_t = 0.0 if transition_s > 0 else 1.0
        new_rig = dataclasses.replace(
            internal.rig,
            current_mode=mode,
            fov_deg=_FOV_BY_MODE[mode],
            distance_m_from_target=_DIST_BY_MODE[mode],
        )
        internal.rig = new_rig
        return new_rig

    # ---------------------------------------------- engage
    def engage_zoom(self, rig_id: str) -> CameraRig:
        """Auto-zoom THIRD_PERSON_FAR -> OVER_SHOULDER_TIGHT
        over 0.4s. Used by engage_disengage integration."""
        internal = self._rigs[rig_id]
        if internal.rig.current_mode == CameraMode.THIRD_PERSON_FAR:
            return self.set_mode(
                rig_id,
                CameraMode.OVER_SHOULDER_TIGHT,
                transition_s=0.4,
            )
        return internal.rig

    def disengage_pullout(self, rig_id: str) -> CameraRig:
        """Pull back from OVER_SHOULDER_TIGHT to
        THIRD_PERSON_FAR over 0.4s on disengage."""
        internal = self._rigs[rig_id]
        if (
            internal.rig.current_mode
            == CameraMode.OVER_SHOULDER_TIGHT
        ):
            return self.set_mode(
                rig_id,
                CameraMode.THIRD_PERSON_FAR,
                transition_s=0.4,
            )
        return internal.rig

    # ---------------------------------------------- collision
    def apply_collision(
        self,
        rig_id: str,
        clipping_distance_m: float,
    ) -> CameraRig:
        """Spring arm forward when geometry would clip the
        camera. Pass the engine-reported distance to the
        first colliding surface; rig clamps so the boom is
        no longer than (clip - collision_radius)."""
        internal = self._rigs[rig_id]
        if clipping_distance_m < 0:
            raise ValueError("clipping_distance must be >= 0")
        rad = internal.rig.collision_radius_m
        max_allowed = max(0.0, clipping_distance_m - rad)
        if internal.rig.distance_m_from_target > max_allowed:
            new_rig = dataclasses.replace(
                internal.rig,
                distance_m_from_target=max_allowed,
            )
            internal.rig = new_rig
        return internal.rig

    # ---------------------------------------------- director
    def handoff_to_director(
        self,
        rig_id: str,
        shot_kind: str,
    ) -> CameraRig:
        if not shot_kind:
            raise ValueError("shot_kind required")
        internal = self._rigs[rig_id]
        if internal.director_owned:
            raise ValueError(
                f"rig {rig_id} already owned by director",
            )
        # Save the current mode so reclaim restores it.
        internal.prev_mode = internal.rig.current_mode
        internal.director_owned = True
        internal.director_shot_kind = shot_kind
        new_rig = dataclasses.replace(
            internal.rig,
            current_mode=CameraMode.CINEMATIC_TRACK,
            fov_deg=_FOV_BY_MODE[CameraMode.CINEMATIC_TRACK],
        )
        internal.rig = new_rig
        return new_rig

    def reclaim_from_director(self, rig_id: str) -> CameraRig:
        internal = self._rigs[rig_id]
        if not internal.director_owned:
            raise ValueError(
                f"rig {rig_id} not currently owned by director",
            )
        prev = internal.prev_mode or CameraMode.THIRD_PERSON_FAR
        internal.director_owned = False
        internal.director_shot_kind = ""
        new_rig = dataclasses.replace(
            internal.rig,
            current_mode=prev,
            fov_deg=_FOV_BY_MODE[prev],
            distance_m_from_target=_DIST_BY_MODE[prev],
        )
        internal.rig = new_rig
        return new_rig

    def is_director_owned(self, rig_id: str) -> bool:
        return self._rigs[rig_id].director_owned

    def director_shot(self, rig_id: str) -> str:
        return self._rigs[rig_id].director_shot_kind

    # ---------------------------------------------- pose interp
    def interpolated_pose_at(
        self,
        rig_id: str,
        t: float,
    ) -> tuple[CameraMode, float, float]:
        """Returns (mode, fov_deg, distance_m) at
        normalized t in [0,1] through the active transition.
        Linear interp on fov + distance from the from-mode
        defaults to the to-mode defaults."""
        internal = self._rigs[rig_id]
        if t < 0:
            t = 0.0
        if t > 1:
            t = 1.0
        to_mode = internal.rig.current_mode
        from_mode = internal.transition_from_mode or to_mode
        from_fov = _FOV_BY_MODE[from_mode]
        to_fov = _FOV_BY_MODE[to_mode]
        from_dist = _DIST_BY_MODE[from_mode]
        to_dist = _DIST_BY_MODE[to_mode]
        fov = from_fov + (to_fov - from_fov) * t
        dist = from_dist + (to_dist - from_dist) * t
        return (to_mode, fov, dist)

    def tick_transition(self, rig_id: str, dt: float) -> float:
        internal = self._rigs[rig_id]
        dur = internal.transition_duration_s
        if dur <= 0:
            internal.transition_t = 1.0
            return 1.0
        internal.transition_t = min(
            1.0, internal.transition_t + dt / dur,
        )
        return internal.transition_t

    # ---------------------------------------------- hint
    def suggested_mode_for(
        self, player_state: PlayerStateView,
    ) -> CameraMode:
        if player_state.in_cutscene:
            return CameraMode.CINEMATIC_TRACK
        if player_state.ko_state:
            return CameraMode.KO_ORBIT
        if player_state.swimming:
            return CameraMode.SWIMMING_UNDERWATER
        if player_state.on_chocobo:
            return CameraMode.CHOCOBO_RIDE
        if player_state.on_ledge:
            return CameraMode.LEDGE_HANG
        if player_state.engaged or player_state.in_combat:
            return CameraMode.OVER_SHOULDER_TIGHT
        return CameraMode.THIRD_PERSON_FAR

    def reset_to_default(self, rig_id: str) -> CameraRig:
        internal = self._rigs[rig_id]
        new_rig = dataclasses.replace(
            internal.rig,
            current_mode=CameraMode.THIRD_PERSON_FAR,
            fov_deg=_FOV_BY_MODE[CameraMode.THIRD_PERSON_FAR],
            distance_m_from_target=_DIST_BY_MODE[
                CameraMode.THIRD_PERSON_FAR
            ],
        )
        internal.rig = new_rig
        internal.director_owned = False
        internal.director_shot_kind = ""
        return new_rig


__all__ = [
    "CameraMode",
    "PlayerStateView",
    "CameraRig",
    "PlayerCameraRigSystem",
]
