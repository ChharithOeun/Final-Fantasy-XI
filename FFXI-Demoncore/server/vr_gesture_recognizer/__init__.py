"""VR gesture recognizer — turn controller motion into action intent.

In VR, players don't just press buttons — they wave,
point, throw, and trace shapes with their hands. This
module recognizes a small canonical set of gestures
from a stream of controller pose samples.

GestureKind:
    POINT       quick directional hand stab (target a mob)
    THROW       overhand throwing motion (item or pact)
    SLASH       horizontal sweep (melee accent / weapon
                skill flair)
    DRAW_RUNE   tracing a closed shape on a vertical
                plane (RUN runes, GEO traces)
    SEAL_FORM   two-handed pose (NIN hand seals)
    PUNCH       quick forward jab (MNK attack flair)

The recognizer is a state machine fed PoseSamples
(timestamped 3D position + handedness). It outputs
RecognizedGesture records: kind + confidence (0..1) +
duration_ms + start/end times.

Recognition is fuzzy. We accept gestures with confidence
≥ 0.6 by default. The caller can ask for a stricter
threshold via min_confidence param.

Sliding window: only gestures completed within the
last 1500ms are considered "live". Older recognitions
are aged out so the recognizer doesn't keep firing the
same wave from 10 seconds ago.

Public surface
--------------
    GestureKind enum
    Hand enum
    PoseSample dataclass (frozen)
    RecognizedGesture dataclass (frozen)
    VrGestureRecognizer
        .ingest(player_id, sample) -> bool
        .recent(player_id, now,
                min_confidence=0.6) -> list[RecognizedGesture]
        .reset(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


_LIVE_WINDOW_MS = 1500
_MIN_SAMPLES_FOR_GESTURE = 6
_DEFAULT_MIN_CONFIDENCE = 0.6


class GestureKind(str, enum.Enum):
    POINT = "point"
    THROW = "throw"
    SLASH = "slash"
    DRAW_RUNE = "draw_rune"
    SEAL_FORM = "seal_form"
    PUNCH = "punch"


class Hand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclasses.dataclass(frozen=True)
class PoseSample:
    player_id: str
    hand: Hand
    x: float
    y: float
    z: float
    timestamp_ms: int


@dataclasses.dataclass(frozen=True)
class RecognizedGesture:
    player_id: str
    kind: GestureKind
    confidence: float
    duration_ms: int
    start_ms: int
    end_ms: int
    hand: Hand


def _dist3(
    a: PoseSample, b: PoseSample,
) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)


@dataclasses.dataclass
class VrGestureRecognizer:
    # player_id -> rolling buffer per hand
    _buffer: dict[
        tuple[str, Hand], list[PoseSample],
    ] = dataclasses.field(default_factory=dict)
    _recognized: list[RecognizedGesture] = dataclasses.field(
        default_factory=list,
    )

    def ingest(
        self, *, player_id: str, sample: PoseSample,
    ) -> bool:
        if not player_id or sample.player_id != player_id:
            return False
        key = (player_id, sample.hand)
        buf = self._buffer.setdefault(key, [])
        # Reject out-of-order samples
        if buf and sample.timestamp_ms < buf[-1].timestamp_ms:
            return False
        buf.append(sample)
        # Keep buffer bounded
        if len(buf) > 60:
            del buf[0:len(buf) - 60]
        # Try to recognize a gesture from the recent
        # window. We trigger on each sample; recognizer
        # picks the strongest match if any.
        self._maybe_recognize(player_id, sample.hand, buf)
        return True

    def _maybe_recognize(
        self, player_id: str, hand: Hand,
        buf: list[PoseSample],
    ) -> None:
        if len(buf) < _MIN_SAMPLES_FOR_GESTURE:
            return
        recent = buf[-_MIN_SAMPLES_FOR_GESTURE:]
        start = recent[0]
        end = recent[-1]
        duration = end.timestamp_ms - start.timestamp_ms
        if duration <= 0 or duration > 1200:
            return
        net = _dist3(start, end)
        # Path length sums consecutive distances; ratio
        # to net gives "straightness" (1.0 = straight)
        path = 0.0
        for i in range(1, len(recent)):
            path += _dist3(recent[i - 1], recent[i])
        # SEAL_FORM is a stillness gesture — both hands
        # stationary AND close together. Check this BEFORE
        # the path-too-small filter, since SEAL_FORM
        # PRECISELY requires path < 0.2.
        if path < 0.2:
            other_hand = (
                Hand.LEFT if hand == Hand.RIGHT
                else Hand.RIGHT
            )
            other_buf = self._buffer.get(
                (player_id, other_hand), [],
            )
            if other_buf:
                other_recent = other_buf[
                    -_MIN_SAMPLES_FOR_GESTURE:
                ]
                if len(other_recent) >= _MIN_SAMPLES_FOR_GESTURE:
                    other_path = 0.0
                    for i in range(1, len(other_recent)):
                        other_path += _dist3(
                            other_recent[i - 1],
                            other_recent[i],
                        )
                    if other_path < 0.2:
                        cross_dist = _dist3(
                            recent[-1], other_recent[-1],
                        )
                        if cross_dist < 0.4:
                            self._fire(
                                player_id=player_id,
                                kind=GestureKind.SEAL_FORM,
                                confidence=0.7,
                                duration_ms=duration,
                                start_ms=start.timestamp_ms,
                                end_ms=end.timestamp_ms,
                                hand=hand,
                            )
                            return
            return  # nothing else triggers on stillness
        straightness = net / path if path > 0 else 0.0
        # Forward Z velocity (positive forward in our convention)
        dz_total = end.z - start.z
        # Vertical drop (POINT/PUNCH typically flat;
        # THROW arcs up then forward; SLASH flat horizontal)
        dy_total = end.y - start.y
        # Horizontal sweep (X)
        dx_total = end.x - start.x
        kind: t.Optional[GestureKind] = None
        confidence = 0.0
        if straightness > 0.85 and net > 0.25:
            # Quick straight motion
            if abs(dz_total) > abs(dx_total) and abs(dz_total) > abs(dy_total):
                # Forward jab
                if duration < 400 and net < 0.6:
                    kind = GestureKind.PUNCH
                    confidence = min(
                        1.0, 0.6 + straightness * 0.3,
                    )
                else:
                    kind = GestureKind.POINT
                    confidence = min(
                        1.0, 0.55 + straightness * 0.4,
                    )
            elif abs(dx_total) > abs(dz_total):
                # Horizontal sweep
                kind = GestureKind.SLASH
                confidence = min(
                    1.0, 0.55 + straightness * 0.4,
                )
        elif straightness < 0.75 and path > 0.4 and net < path * 0.75:
            # Curved path — rune-drawing. Note we only
            # see a sliding window of samples, so a full
            # closed loop won't necessarily appear in
            # one frame; the curving signal is enough.
            kind = GestureKind.DRAW_RUNE
            confidence = min(
                1.0, 0.5 + (path - net) * 0.5,
            )
        elif (dy_total > 0.15 and dz_total > 0.15
              and 0.5 < straightness < 0.85):
            # Up-and-forward = throw arc
            kind = GestureKind.THROW
            confidence = min(
                1.0, 0.6 + straightness * 0.3,
            )
        if kind is None or confidence < 0.5:
            return
        self._fire(
            player_id=player_id, kind=kind,
            confidence=confidence, duration_ms=duration,
            start_ms=start.timestamp_ms,
            end_ms=end.timestamp_ms, hand=hand,
        )

    def _fire(
        self, *, player_id: str, kind: GestureKind,
        confidence: float, duration_ms: int,
        start_ms: int, end_ms: int, hand: Hand,
    ) -> None:
        # De-dupe: same kind from same hand within 300ms
        for prev in reversed(self._recognized):
            if (prev.player_id == player_id
                    and prev.hand == hand
                    and prev.kind == kind
                    and end_ms - prev.end_ms < 300):
                return
        self._recognized.append(RecognizedGesture(
            player_id=player_id, kind=kind,
            confidence=round(confidence, 3),
            duration_ms=duration_ms,
            start_ms=start_ms, end_ms=end_ms, hand=hand,
        ))

    def recent(
        self, *, player_id: str, now: int,
        min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
    ) -> list[RecognizedGesture]:
        cutoff = now - _LIVE_WINDOW_MS
        out = [
            r for r in self._recognized
            if r.player_id == player_id
            and r.end_ms >= cutoff
            and r.confidence >= min_confidence
        ]
        out.sort(key=lambda r: -r.end_ms)
        return out

    def reset(self, *, player_id: str) -> bool:
        keys = [k for k in self._buffer if k[0] == player_id]
        for k in keys:
            del self._buffer[k]
        before = len(self._recognized)
        self._recognized = [
            r for r in self._recognized
            if r.player_id != player_id
        ]
        return before != len(self._recognized) or bool(keys)


__all__ = [
    "GestureKind", "Hand", "PoseSample",
    "RecognizedGesture", "VrGestureRecognizer",
]
