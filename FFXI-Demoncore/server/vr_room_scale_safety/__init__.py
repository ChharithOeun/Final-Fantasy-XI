"""VR room-scale safety — guardian boundary + auto-pause.

Real-world VR injuries happen when a player walks into
a wall, trips over furniture, or punches a TV. This
module is the SOFTWARE side of preventing that — the
hardware "guardian" / "chaperone" / "play area" feature
implemented for our server.

Each player declares a PlaySpace: a rectangle on the floor
they're free to move within, expressed in metres relative
to a center origin. They also pick a Mode:
    ROOM_SCALE   walk-around play (3m x 3m typical)
    SEATED       sit-down play (small box, recenter to chair)

The HMD reports an HmdPosition each frame (we only care
about x/z — height is irrelevant for floor safety). We
update the SafetyState:
    SAFE            inside, well away from walls
    WARNING         within WARNING_MARGIN of an edge
    EDGE_CROSSED    outside the box — gameplay PAUSES
    RECENTERING     player requested a recenter; we wait
                    for the next sample inside the box

A pause is non-negotiable. The user keeps moving in real
life — game stops driving until they're back in safe
space. resume() is called when their HMD returns inside
the box; that returns to SAFE.

Why pause and not just warn:
    A player playing FFXI in VR while moving toward a
    real-world wall who only sees a "warning" overlay can
    talk themselves into "I'll just do this last GCD" and
    bonk their head. Hard pause means the only way the
    game keeps progressing is to physically retreat. That's
    safety as a constraint, not a suggestion.

The VR-comfort settings (snap-turning, vignette, IPD)
live in vr_mode_hardware_detect; this module is purely
the BOUNDARY layer.

Public surface
--------------
    PlayMode enum
    SafetyState enum
    PlaySpace dataclass (frozen)
    HmdPosition dataclass (frozen)
    SafetyEvent dataclass (frozen)
    VrRoomScaleSafety
        .register_playspace(player_id, playspace) -> bool
        .update_hmd(player_id, hmd) -> SafetyState
        .recenter(player_id) -> bool
        .is_paused(player_id) -> bool
        .events_for(player_id) -> list[SafetyEvent]
        .clear_player(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_WARNING_MARGIN_M = 0.3
_EDGE_BUFFER_M = 0.0  # exact edge = crossed


class PlayMode(str, enum.Enum):
    ROOM_SCALE = "room_scale"
    SEATED = "seated"


class SafetyState(str, enum.Enum):
    SAFE = "safe"
    WARNING = "warning"
    EDGE_CROSSED = "edge_crossed"
    RECENTERING = "recentering"


@dataclasses.dataclass(frozen=True)
class PlaySpace:
    width_m: float        # along X axis
    depth_m: float        # along Z axis
    mode: PlayMode


@dataclasses.dataclass(frozen=True)
class HmdPosition:
    x: float              # metres from origin
    z: float              # metres from origin (Z = forward)
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class SafetyEvent:
    player_id: str
    state: SafetyState
    distance_to_edge_m: float
    timestamp_ms: int


@dataclasses.dataclass
class _PlayerSafety:
    playspace: PlaySpace
    state: SafetyState = SafetyState.SAFE
    paused: bool = False
    recenter_requested: bool = False


@dataclasses.dataclass
class VrRoomScaleSafety:
    _players: dict[str, _PlayerSafety] = dataclasses.field(
        default_factory=dict,
    )
    _events: list[SafetyEvent] = dataclasses.field(
        default_factory=list,
    )

    def register_playspace(
        self, *, player_id: str, playspace: PlaySpace,
    ) -> bool:
        if not player_id:
            return False
        if playspace.width_m <= 0 or playspace.depth_m <= 0:
            return False
        # Seated requires a small box; room-scale requires
        # at least 1.5m in both dimensions (Quest minimum).
        if playspace.mode == PlayMode.ROOM_SCALE:
            if playspace.width_m < 1.5 or playspace.depth_m < 1.5:
                return False
        self._players[player_id] = _PlayerSafety(
            playspace=playspace,
        )
        return True

    def update_hmd(
        self, *, player_id: str, hmd: HmdPosition,
    ) -> SafetyState:
        if player_id not in self._players:
            return SafetyState.SAFE  # no playspace, no boundary
        ps = self._players[player_id]
        space = ps.playspace
        half_w = space.width_m / 2.0
        half_d = space.depth_m / 2.0
        # Distance to nearest edge along each axis
        x_clearance = half_w - abs(hmd.x)
        z_clearance = half_d - abs(hmd.z)
        # Smaller one is the binding edge
        edge_clearance = min(x_clearance, z_clearance)
        if edge_clearance < -_EDGE_BUFFER_M:
            new_state = SafetyState.EDGE_CROSSED
            ps.paused = True
        elif edge_clearance < _WARNING_MARGIN_M:
            new_state = SafetyState.WARNING
        else:
            # If they were paused, they need to recenter
            # or resume — we set SAFE but the paused flag
            # only clears on a recenter() call.
            new_state = (
                SafetyState.RECENTERING
                if ps.recenter_requested
                else SafetyState.SAFE
            )
        if new_state != ps.state:
            self._events.append(SafetyEvent(
                player_id=player_id,
                state=new_state,
                distance_to_edge_m=round(edge_clearance, 3),
                timestamp_ms=hmd.timestamp_ms,
            ))
        ps.state = new_state
        # If they walked back inside after EDGE_CROSSED,
        # auto-clear the pause. The 'recenter' path is
        # different — that's a deliberate user action.
        if (new_state in (SafetyState.SAFE, SafetyState.WARNING)
                and ps.paused
                and not ps.recenter_requested):
            ps.paused = False
        return new_state

    def recenter(self, *, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        ps = self._players[player_id]
        ps.recenter_requested = True
        ps.paused = False
        return True

    def is_paused(self, *, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        return self._players[player_id].paused

    def events_for(
        self, *, player_id: str,
    ) -> list[SafetyEvent]:
        return [
            e for e in self._events
            if e.player_id == player_id
        ]

    def clear_player(self, *, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        del self._players[player_id]
        before = len(self._events)
        self._events = [
            e for e in self._events
            if e.player_id != player_id
        ]
        return True


__all__ = [
    "PlayMode", "SafetyState", "PlaySpace",
    "HmdPosition", "SafetyEvent", "VrRoomScaleSafety",
]
