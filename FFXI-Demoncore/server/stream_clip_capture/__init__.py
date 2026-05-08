"""Stream clip capture — save 30-second highlights.

A spectator (or the broadcaster themselves) can hit
"clip" and the system snapshots the last 30 seconds of
overlay events. The clip is owned by whoever clipped
it, has a title, and can be shared/posted later. The
typical use: a viewer captures Chharith's first-try
Maat win and shares it.

Each clip stores:
    - clip_id (unique)
    - session_id (where it came from)
    - clipped_by (player who hit clip)
    - title (≤ 80 chars; defaults to a stamp if blank)
    - events (the snapshot of overlay events from
      [now - 30s, now], frozen tuple)
    - clipped_at

Quotas (anti-spam):
    - one clip per (clipper, session) per minute (no
      machine-gunning the clip button)
    - per-player lifetime cap 500 clips (UI sanity;
      player can delete to free slots)

Public surface
--------------
    Clip dataclass (frozen)
    StreamClipCapture
        .capture(clipper_id, session_id, title,
                 events, now) -> Optional[Clip]
        .get(clip_id) -> Optional[Clip]
        .clips_by(clipper_id) -> list[Clip]
        .clips_for_session(session_id) -> list[Clip]
        .delete(clip_id, clipper_id) -> bool
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.stream_overlay import OverlayEvent


_CLIP_WINDOW_SEC = 30
_MIN_GAP_BETWEEN_CLIPS_SEC = 60
_MAX_TITLE_LEN = 80
_PER_PLAYER_CAP = 500


@dataclasses.dataclass(frozen=True)
class Clip:
    clip_id: str
    session_id: str
    clipped_by: str
    title: str
    events: tuple[OverlayEvent, ...]
    clipped_at: int


@dataclasses.dataclass
class StreamClipCapture:
    _clips: dict[str, Clip] = dataclasses.field(
        default_factory=dict,
    )
    # clipper_id -> set[clip_id]
    _by_clipper: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    _next_seq: int = 1

    def _last_clip_time(
        self, *, clipper_id: str, session_id: str,
    ) -> int:
        latest = 0
        for cid in self._by_clipper.get(clipper_id, set()):
            c = self._clips[cid]
            if c.session_id != session_id:
                continue
            if c.clipped_at > latest:
                latest = c.clipped_at
        return latest

    def capture(
        self, *, clipper_id: str, session_id: str,
        title: str, events: list[OverlayEvent], now: int,
    ) -> t.Optional[Clip]:
        if not clipper_id or not session_id:
            return None
        title = title.strip()
        if len(title) > _MAX_TITLE_LEN:
            return None
        if len(self._by_clipper.get(
            clipper_id, set(),
        )) >= _PER_PLAYER_CAP:
            return None
        last = self._last_clip_time(
            clipper_id=clipper_id, session_id=session_id,
        )
        if last and (now - last) < _MIN_GAP_BETWEEN_CLIPS_SEC:
            return None
        # Filter to the 30-second window
        cutoff = now - _CLIP_WINDOW_SEC
        windowed = tuple(
            e for e in events
            if e.session_id == session_id
            and cutoff <= e.timestamp <= now
        )
        clip_id = f"clip_{self._next_seq}"
        self._next_seq += 1
        c = Clip(
            clip_id=clip_id, session_id=session_id,
            clipped_by=clipper_id,
            title=title or f"clip {clip_id}",
            events=windowed, clipped_at=now,
        )
        self._clips[clip_id] = c
        self._by_clipper.setdefault(
            clipper_id, set(),
        ).add(clip_id)
        return c

    def get(
        self, *, clip_id: str,
    ) -> t.Optional[Clip]:
        return self._clips.get(clip_id)

    def clips_by(
        self, *, clipper_id: str,
    ) -> list[Clip]:
        out = [
            self._clips[cid]
            for cid in self._by_clipper.get(clipper_id, set())
        ]
        out.sort(key=lambda c: -c.clipped_at)
        return out

    def clips_for_session(
        self, *, session_id: str,
    ) -> list[Clip]:
        out = [
            c for c in self._clips.values()
            if c.session_id == session_id
        ]
        out.sort(key=lambda c: c.clipped_at)
        return out

    def delete(
        self, *, clip_id: str, clipper_id: str,
    ) -> bool:
        c = self._clips.get(clip_id)
        if c is None or c.clipped_by != clipper_id:
            return False
        del self._clips[clip_id]
        self._by_clipper.get(
            clipper_id, set(),
        ).discard(clip_id)
        return True

    def total_clips(self) -> int:
        return len(self._clips)


__all__ = ["Clip", "StreamClipCapture"]
