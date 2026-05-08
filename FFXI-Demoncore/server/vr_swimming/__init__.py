"""VR swimming — arm strokes propel you through water.

Step into a lake or off a ferry pier and you're in the
water. In flat-screen FFXI movement is identical
above/below water. In VR, you swim by stroking your
arms through the water — like an actual swimmer.

Each ArmStroke is a backward-and-down sweep of one hand.
We detect strokes from the same hand-pose stream that
feeds vr_gesture_recognizer, but we look for a different
signature: large backward-Z motion (>0.4m), modest
downward-Y motion (>0.05m), within a short time window
(<800ms).

Per-stroke propulsion:
    each stroke imparts ~0.8m of forward velocity-impulse
    in the direction the head is facing. Sustained
    stroking (alternating arms within 1.2s) keeps the
    player moving forward smoothly. Stop stroking -> the
    player decelerates and hangs in the water.

Buoyancy (off by default — many zones don't simulate
water depth):
    if the player is in water, head Y < surface_y means
    you're underwater. We expose that as a boolean for
    the lighting pipeline to dim/colorize.

Stroke types:
    BREASTSTROKE    both arms simultaneously, slow,
                    powerful — 1.2x propulsion
    FREESTYLE       alternating arms, faster — base
                    propulsion
    DOG_PADDLE      shorter, less efficient — 0.6x

Public surface
--------------
    StrokeKind enum
    Hand enum
    HandSweep dataclass (frozen)
    SwimState dataclass (frozen)
    VrSwimming
        .enter_water(player_id, surface_y) -> bool
        .exit_water(player_id) -> bool
        .ingest_sweep(player_id, hand, sweep) -> bool
        .state(player_id) -> Optional[SwimState]
        .tick(player_id, now_ms) -> None
        .reset(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_BACKWARD_Z_THRESHOLD = 0.4
_DOWNWARD_Y_THRESHOLD = 0.05
_STROKE_MAX_DURATION_MS = 800
_BREASTSTROKE_WINDOW_MS = 250  # both hands within this
_ALTERNATING_WINDOW_MS = 1200  # for FREESTYLE
_BASE_FORWARD_IMPULSE = 0.8
_DECAY_PER_SECOND = 0.6


class StrokeKind(str, enum.Enum):
    BREASTSTROKE = "breaststroke"
    FREESTYLE = "freestyle"
    DOG_PADDLE = "dog_paddle"


class Hand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class HandSweep:
    backward_z_m: float
    downward_y_m: float
    duration_ms: int
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class SwimState:
    player_id: str
    in_water: bool
    underwater: bool
    head_y: float
    surface_y: float
    forward_velocity_mps: float
    last_stroke_ms: t.Optional[int]
    last_stroke_kind: t.Optional[StrokeKind]


@dataclasses.dataclass
class _Player:
    surface_y: float
    head_y: float = 0.0
    velocity: float = 0.0
    last_stroke_ms: t.Optional[int] = None
    last_stroke_kind: t.Optional[StrokeKind] = None
    last_left_ms: t.Optional[int] = None
    last_right_ms: t.Optional[int] = None
    in_water: bool = True


@dataclasses.dataclass
class VrSwimming:
    _players: dict[str, _Player] = dataclasses.field(
        default_factory=dict,
    )

    def enter_water(
        self, *, player_id: str, surface_y: float,
    ) -> bool:
        if not player_id:
            return False
        self._players[player_id] = _Player(
            surface_y=surface_y, head_y=surface_y,
        )
        return True

    def exit_water(self, *, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        del self._players[player_id]
        return True

    def update_head(
        self, *, player_id: str, head_y: float,
    ) -> bool:
        if player_id not in self._players:
            return False
        self._players[player_id].head_y = head_y
        return True

    def ingest_sweep(
        self, *, player_id: str, hand: Hand,
        sweep: HandSweep,
    ) -> bool:
        if player_id not in self._players:
            return False
        # Reject sweeps that aren't recognizable strokes
        if sweep.backward_z_m < _BACKWARD_Z_THRESHOLD:
            return False
        if sweep.downward_y_m < _DOWNWARD_Y_THRESHOLD:
            return False
        if sweep.duration_ms > _STROKE_MAX_DURATION_MS:
            return False
        p = self._players[player_id]
        # Update last-hand-time
        if hand == Hand.LEFT:
            p.last_left_ms = sweep.timestamp_ms
        else:
            p.last_right_ms = sweep.timestamp_ms
        # Detect stroke kind
        kind: StrokeKind
        if (p.last_left_ms is not None
                and p.last_right_ms is not None
                and abs(p.last_left_ms - p.last_right_ms)
                <= _BREASTSTROKE_WINDOW_MS):
            kind = StrokeKind.BREASTSTROKE
            multiplier = 1.2
        elif (p.last_stroke_ms is not None
              and sweep.timestamp_ms - p.last_stroke_ms
              <= _ALTERNATING_WINDOW_MS
              and p.last_stroke_kind != kind_other(hand)
              if False else False):
            # placeholder branch — handled below
            kind = StrokeKind.FREESTYLE
            multiplier = 1.0
        else:
            # Decide: alternating freestyle or solo paddle
            if (p.last_stroke_ms is not None
                    and sweep.timestamp_ms - p.last_stroke_ms
                    <= _ALTERNATING_WINDOW_MS):
                kind = StrokeKind.FREESTYLE
                multiplier = 1.0
            else:
                kind = StrokeKind.DOG_PADDLE
                multiplier = 0.6
        p.velocity += _BASE_FORWARD_IMPULSE * multiplier
        p.last_stroke_ms = sweep.timestamp_ms
        p.last_stroke_kind = kind
        return True

    def tick(
        self, *, player_id: str, elapsed_ms: int,
    ) -> bool:
        if player_id not in self._players:
            return False
        p = self._players[player_id]
        if elapsed_ms <= 0:
            return True
        decay = _DECAY_PER_SECOND * (elapsed_ms / 1000.0)
        p.velocity = max(0.0, p.velocity - decay)
        return True

    def state(
        self, *, player_id: str,
    ) -> t.Optional[SwimState]:
        if player_id not in self._players:
            return None
        p = self._players[player_id]
        return SwimState(
            player_id=player_id,
            in_water=p.in_water,
            underwater=p.head_y < p.surface_y,
            head_y=p.head_y,
            surface_y=p.surface_y,
            forward_velocity_mps=round(p.velocity, 3),
            last_stroke_ms=p.last_stroke_ms,
            last_stroke_kind=p.last_stroke_kind,
        )

    def reset(self, *, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        del self._players[player_id]
        return True


def kind_other(hand: Hand) -> Hand:
    return Hand.RIGHT if hand == Hand.LEFT else Hand.LEFT


__all__ = [
    "StrokeKind", "Hand", "HandSweep", "SwimState",
    "VrSwimming",
]
