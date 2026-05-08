"""Camera lock pin — keep the camera at a chosen distance.

Players who like the chess-board view want it to STAY
chess-board. Retail re-zooms when you engage a target,
when you cross a zone, when a cutscene ends, when the
camera collides with terrain. That's helpful for new
players and infuriating for the player who picked
40-yalm tactical for a reason.

Pinning records:
    pinned_distance      the distance the player chose
    pinned_pitch_deg     the angle they chose
    sticky_through       which auto-zoom triggers we
                         override

Sticky triggers (StickyKind):
    ENGAGE         don't auto-zoom in when target locked
    DISENGAGE      don't auto-zoom out on disengage
    ZONE_CHANGE    re-apply pin after zone load
    CUTSCENE_END   re-apply pin after cutscene
    COMBAT_TICK    don't drift mid-combat (camera bob etc)

We DO NOT override:
    TERRAIN_COLLISION  the camera still pushes in when
                       a wall is between camera and
                       player — physics safety always wins
    CINEMATIC          forced cinematic camera (skillchain
                       finishers, mob 2hr) still plays;
                       the pin re-applies after

Pinning is opt-in; default is unpinned (retail behavior).
unpin() restores fluid camera. The actual camera position
is owned by camera_modes; this module just stores the
pin record and answers "should auto-zoom override fire
right now?".

Public surface
--------------
    StickyKind enum
    CameraPin dataclass (frozen)
    CameraLockPin
        .pin(player_id, distance, pitch_deg,
             sticky_through, pinned_at) -> bool
        .unpin(player_id) -> bool
        .is_pinned(player_id) -> bool
        .pin_for(player_id) -> Optional[CameraPin]
        .should_override(player_id, trigger) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StickyKind(str, enum.Enum):
    ENGAGE = "engage"
    DISENGAGE = "disengage"
    ZONE_CHANGE = "zone_change"
    CUTSCENE_END = "cutscene_end"
    COMBAT_TICK = "combat_tick"


@dataclasses.dataclass(frozen=True)
class CameraPin:
    player_id: str
    pinned_distance: float
    pinned_pitch_deg: float
    sticky_through: tuple[StickyKind, ...]
    pinned_at: int


@dataclasses.dataclass
class CameraLockPin:
    _pins: dict[str, CameraPin] = dataclasses.field(
        default_factory=dict,
    )

    def pin(
        self, *, player_id: str, distance: float,
        pitch_deg: float,
        sticky_through: list[StickyKind],
        pinned_at: int,
    ) -> bool:
        if not player_id:
            return False
        if distance < 0 or distance > 80.0:
            return False
        if pitch_deg < -90.0 or pitch_deg > 90.0:
            return False
        # De-dupe sticky list
        sticky_t = tuple(dict.fromkeys(sticky_through))
        self._pins[player_id] = CameraPin(
            player_id=player_id,
            pinned_distance=distance,
            pinned_pitch_deg=pitch_deg,
            sticky_through=sticky_t,
            pinned_at=pinned_at,
        )
        return True

    def unpin(self, *, player_id: str) -> bool:
        return self._pins.pop(player_id, None) is not None

    def is_pinned(self, *, player_id: str) -> bool:
        return player_id in self._pins

    def pin_for(
        self, *, player_id: str,
    ) -> t.Optional[CameraPin]:
        return self._pins.get(player_id)

    def should_override(
        self, *, player_id: str, trigger: StickyKind,
    ) -> bool:
        """Return True if the auto-zoom for this trigger
        should be suppressed because the player has the
        camera pinned through it."""
        pin = self._pins.get(player_id)
        if pin is None:
            return False
        return trigger in pin.sticky_through

    def total_pinned(self) -> int:
        return len(self._pins)


__all__ = [
    "StickyKind", "CameraPin", "CameraLockPin",
]
