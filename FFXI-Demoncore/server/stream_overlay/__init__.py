"""Stream overlay — what data flows broadcaster → viewers.

The overlay is the "what does a spectator see" layer. As
the broadcaster plays, the in-game client emits events;
the overlay registry buffers a rolling window of recent
events that the viewer's UI renders as the live stream.

5 OverlayEventKinds:
    GEAR_CHANGE   broadcaster swapped a gear set —
                  viewers see the new piece highlighted
    SPELL_CAST    cast started/finished — show the
                  spell name + duration
    JA_USED       job ability popped — show the icon
    HP_TIER       broadcaster's HP crossed into a new
                  visible_health stage (we don't leak
                  exact HP — see visible_health module
                  for the 7-stage grammar)
    POSITION      broadcaster moved across a meaningful
                  threshold (zone change, named-mob
                  range, party room) — coarse, no fine
                  coordinates

The buffer is bounded (100 events per session) — older
events fall off as new ones arrive. New viewers joining
mid-stream see the last N events as backfill, so they're
not staring at a blank overlay until the next event fires.

Public surface
--------------
    OverlayEventKind enum
    OverlayEvent dataclass (frozen)
    StreamOverlay
        .record(session_id, kind, payload, timestamp)
            -> bool
        .recent(session_id, limit) -> list[OverlayEvent]
        .latest_by_kind(session_id, kind)
            -> Optional[OverlayEvent]
        .clear_session(session_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_BUFFER_CAP = 100


class OverlayEventKind(str, enum.Enum):
    GEAR_CHANGE = "gear_change"
    SPELL_CAST = "spell_cast"
    JA_USED = "ja_used"
    HP_TIER = "hp_tier"
    POSITION = "position"


@dataclasses.dataclass(frozen=True)
class OverlayEvent:
    session_id: str
    kind: OverlayEventKind
    payload: str           # opaque to this module; UI parses
    timestamp: int


@dataclasses.dataclass
class StreamOverlay:
    # session_id -> bounded list of events
    _buffer: dict[
        str, list[OverlayEvent],
    ] = dataclasses.field(default_factory=dict)

    def record(
        self, *, session_id: str,
        kind: OverlayEventKind, payload: str,
        timestamp: int,
    ) -> bool:
        if not session_id or not payload.strip():
            return False
        buf = self._buffer.setdefault(session_id, [])
        # Reject out-of-order events (clock skew protection)
        if buf and timestamp < buf[-1].timestamp:
            return False
        buf.append(OverlayEvent(
            session_id=session_id, kind=kind,
            payload=payload, timestamp=timestamp,
        ))
        # Trim to cap
        if len(buf) > _BUFFER_CAP:
            del buf[0:len(buf) - _BUFFER_CAP]
        return True

    def recent(
        self, *, session_id: str, limit: int = 50,
    ) -> list[OverlayEvent]:
        if limit <= 0:
            return []
        buf = self._buffer.get(session_id, [])
        return list(buf[-limit:])

    def latest_by_kind(
        self, *, session_id: str, kind: OverlayEventKind,
    ) -> t.Optional[OverlayEvent]:
        buf = self._buffer.get(session_id, [])
        for ev in reversed(buf):
            if ev.kind == kind:
                return ev
        return None

    def clear_session(self, *, session_id: str) -> int:
        buf = self._buffer.pop(session_id, [])
        return len(buf)

    def total_events(self) -> int:
        return sum(len(b) for b in self._buffer.values())


__all__ = [
    "OverlayEventKind", "OverlayEvent", "StreamOverlay",
]
