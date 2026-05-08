"""VR climbing — hand-over-hand vertical traversal.

Boyahda Tree branches, ladder rungs, dungeon ropes.
In flat-screen FFXI you press forward against a vertical
surface; in VR you grab a rung with one hand, pull
yourself up, then grab the next rung with the other.

ClimbSurface registry: per surface we track its kind
(LADDER / ROPE / TREE_BRANCH / VINE / ROCK_FACE), the
two endpoints (top + bottom), and a "rung_density" — how
many implicit rungs/handholds exist along the surface
length. A rope might be 1 rung/m (you grab anywhere); a
ladder is 0.4m/rung; a rock face has discrete handholds
the level designer specified.

Climb action model:
    grab(player, hand, surface, height) — anchor hand at
    that height on the surface. Two hands required to
    actually move (one hand release-and-reach while the
    other supports body weight).

    move(player, new_height) — only succeeds if at least
    one hand is currently anchored. Player's body Y
    follows the LOWER hand by default (the one bearing
    weight).

    fall(player) — both hands released mid-climb. We
    record this as a fall event for the physics layer
    to apply damage from.

Stamina cost (optional, off by default):
    Each grab + move costs 1 stamina point. The caller
    can poll stamina_consumed() to apply gameplay cost.
    Heavy weight from weight_physics ratchets per-grab
    cost up.

Public surface
--------------
    SurfaceKind enum
    Hand enum
    ClimbSurface dataclass (frozen)
    ClimbState dataclass (frozen) — current height + hand
                                     anchors
    VrClimbing
        .register_surface(surface) -> bool
        .grab(player_id, hand, surface_id, height) -> bool
        .release(player_id, hand) -> bool
        .move_body(player_id, new_height) -> bool
        .state(player_id) -> Optional[ClimbState]
        .stamina_consumed(player_id) -> int
        .reset(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SurfaceKind(str, enum.Enum):
    LADDER = "ladder"
    ROPE = "rope"
    TREE_BRANCH = "tree_branch"
    VINE = "vine"
    ROCK_FACE = "rock_face"


class Hand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class ClimbSurface:
    surface_id: str
    kind: SurfaceKind
    bottom_y: float       # absolute world Y at bottom
    top_y: float          # absolute world Y at top
    rung_density_per_m: float = 1.0  # 1 = continuous


@dataclasses.dataclass(frozen=True)
class ClimbState:
    player_id: str
    surface_id: str
    body_y: float
    left_hand_y: t.Optional[float]
    right_hand_y: t.Optional[float]


@dataclasses.dataclass
class _PlayerClimb:
    surface_id: str
    body_y: float
    left_y: t.Optional[float] = None
    right_y: t.Optional[float] = None
    stamina: int = 0


@dataclasses.dataclass
class VrClimbing:
    _surfaces: dict[str, ClimbSurface] = dataclasses.field(
        default_factory=dict,
    )
    _climbing: dict[str, _PlayerClimb] = dataclasses.field(
        default_factory=dict,
    )
    _falls: list[tuple[str, float, float]] = dataclasses.field(
        default_factory=list,
    )

    def register_surface(
        self, surface: ClimbSurface,
    ) -> bool:
        if not surface.surface_id:
            return False
        if surface.top_y <= surface.bottom_y:
            return False
        if surface.rung_density_per_m <= 0:
            return False
        if surface.surface_id in self._surfaces:
            return False
        self._surfaces[surface.surface_id] = surface
        return True

    def grab(
        self, *, player_id: str, hand: Hand,
        surface_id: str, height: float,
    ) -> bool:
        if surface_id not in self._surfaces:
            return False
        if not player_id:
            return False
        surf = self._surfaces[surface_id]
        if height < surf.bottom_y or height > surf.top_y:
            return False
        # If player is climbing a different surface, can't
        # double-grip onto a new one without releasing
        # both hands first
        cur = self._climbing.get(player_id)
        if cur is not None and cur.surface_id != surface_id:
            if cur.left_y is not None or cur.right_y is not None:
                return False
        if cur is None or cur.surface_id != surface_id:
            cur = _PlayerClimb(
                surface_id=surface_id, body_y=height,
            )
            self._climbing[player_id] = cur
        if hand == Hand.LEFT:
            cur.left_y = height
        else:
            cur.right_y = height
        cur.stamina += 1
        return True

    def release(
        self, *, player_id: str, hand: Hand,
    ) -> bool:
        cur = self._climbing.get(player_id)
        if cur is None:
            return False
        if hand == Hand.LEFT:
            if cur.left_y is None:
                return False
            cur.left_y = None
        else:
            if cur.right_y is None:
                return False
            cur.right_y = None
        # If both hands released, that's a FALL.
        if cur.left_y is None and cur.right_y is None:
            self._falls.append((
                player_id, cur.body_y,
                self._surfaces[cur.surface_id].bottom_y,
            ))
            del self._climbing[player_id]
        return True

    def move_body(
        self, *, player_id: str, new_height: float,
    ) -> bool:
        cur = self._climbing.get(player_id)
        if cur is None:
            return False
        # Need at least one hand anchored to move
        if cur.left_y is None and cur.right_y is None:
            return False
        surf = self._surfaces[cur.surface_id]
        if new_height < surf.bottom_y or new_height > surf.top_y:
            return False
        cur.body_y = new_height
        cur.stamina += 1
        return True

    def state(
        self, *, player_id: str,
    ) -> t.Optional[ClimbState]:
        cur = self._climbing.get(player_id)
        if cur is None:
            return None
        return ClimbState(
            player_id=player_id,
            surface_id=cur.surface_id,
            body_y=cur.body_y,
            left_hand_y=cur.left_y,
            right_hand_y=cur.right_y,
        )

    def stamina_consumed(
        self, *, player_id: str,
    ) -> int:
        cur = self._climbing.get(player_id)
        if cur is None:
            return 0
        return cur.stamina

    def fall_events(
        self, *, player_id: str,
    ) -> list[tuple[float, float]]:
        return [
            (height, ground)
            for pid, height, ground in self._falls
            if pid == player_id
        ]

    def reset(self, *, player_id: str) -> bool:
        touched = False
        if player_id in self._climbing:
            del self._climbing[player_id]
            touched = True
        before = len(self._falls)
        self._falls = [
            f for f in self._falls if f[0] != player_id
        ]
        if before != len(self._falls):
            touched = True
        return touched


__all__ = [
    "SurfaceKind", "Hand", "ClimbSurface",
    "ClimbState", "VrClimbing",
]
