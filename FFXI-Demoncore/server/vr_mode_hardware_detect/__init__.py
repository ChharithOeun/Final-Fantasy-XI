"""VR mode hardware detect — switch FP to VR when HMD is
present.

When the player is in FIRST_PERSON mode AND a VR HMD is
connected, we switch to VR_FIRST_PERSON: stereoscopic
render, head tracking drives yaw/pitch, hand controllers
map to attack/cast inputs. Without an HMD we never enter
VR mode (it's pointless on a flat screen).

The HMD itself is hardware Demoncore doesn't ship — we
expect a 3rd-party VR runtime (OpenXR / SteamVR / Oculus)
to register an HmdProfile here at session start. The
profile says "I'm a Quest 3, I have inside-out tracking,
my IPD is 63mm, here's my comfort settings."

Comfort settings reduce VR sickness:
    snap_turning_deg     0 (smooth) or 30/45/60/90 ticks
    vignette_on_motion   bool — black peripheral while
                         the player is moving
    seated_recenter      bool — re-zero forward pose to
                         the chair
    ipd_mm               inter-pupillary distance, 55-72

We never auto-switch INTO VR mode. The player explicitly
toggles it (a setting + an in-game toggle hotkey). This
respects players who own VR hardware but don't want to
play in VR right now.

Public surface
--------------
    HmdProfile dataclass (frozen)
    VrSettings dataclass (frozen)
    VrModeHardwareDetect
        .register_hmd(player_id, profile) -> bool
        .unregister_hmd(player_id) -> bool
        .has_hmd(player_id) -> bool
        .enable_vr(player_id, settings) -> bool
        .disable_vr(player_id) -> bool
        .is_vr_enabled(player_id) -> bool
        .settings_for(player_id) -> Optional[VrSettings]
"""
from __future__ import annotations

import dataclasses
import typing as t


_VALID_SNAP_DEG = (0, 30, 45, 60, 90)
_MIN_IPD_MM = 55.0
_MAX_IPD_MM = 72.0


@dataclasses.dataclass(frozen=True)
class HmdProfile:
    player_id: str
    runtime: str           # "openxr", "steamvr", "oculus"
    model: str             # "Quest 3", "Index", etc.
    has_inside_out: bool
    has_hand_tracking: bool


@dataclasses.dataclass(frozen=True)
class VrSettings:
    player_id: str
    snap_turning_deg: int   # 0=smooth, else snap angle
    vignette_on_motion: bool
    seated_recenter: bool
    ipd_mm: float


@dataclasses.dataclass
class VrModeHardwareDetect:
    _hmds: dict[str, HmdProfile] = dataclasses.field(
        default_factory=dict,
    )
    _enabled: dict[str, VrSettings] = dataclasses.field(
        default_factory=dict,
    )

    def register_hmd(
        self, *, player_id: str, profile: HmdProfile,
    ) -> bool:
        if not player_id or profile.player_id != player_id:
            return False
        if not profile.runtime or not profile.model:
            return False
        self._hmds[player_id] = profile
        return True

    def unregister_hmd(self, *, player_id: str) -> bool:
        if player_id not in self._hmds:
            return False
        del self._hmds[player_id]
        # Disabling VR if it was active — can't VR without
        # an HMD
        self._enabled.pop(player_id, None)
        return True

    def has_hmd(self, *, player_id: str) -> bool:
        return player_id in self._hmds

    def enable_vr(
        self, *, player_id: str, settings: VrSettings,
    ) -> bool:
        if player_id != settings.player_id:
            return False
        if not self.has_hmd(player_id=player_id):
            return False  # no HMD = no VR
        if settings.snap_turning_deg not in _VALID_SNAP_DEG:
            return False
        if (settings.ipd_mm < _MIN_IPD_MM
                or settings.ipd_mm > _MAX_IPD_MM):
            return False
        self._enabled[player_id] = settings
        return True

    def disable_vr(self, *, player_id: str) -> bool:
        return self._enabled.pop(player_id, None) is not None

    def is_vr_enabled(self, *, player_id: str) -> bool:
        return player_id in self._enabled

    def settings_for(
        self, *, player_id: str,
    ) -> t.Optional[VrSettings]:
        return self._enabled.get(player_id)

    def total_hmds(self) -> int:
        return len(self._hmds)

    def total_vr_enabled(self) -> int:
        return len(self._enabled)


__all__ = [
    "HmdProfile", "VrSettings", "VrModeHardwareDetect",
]
