"""Streaming session — broadcaster lifecycle.

A famous player toggles "I'm broadcasting" and the world
can watch them play. This module owns the per-broadcaster
session state: who's live, when they started, what their
visibility settings are, when they ended.

Privacy levels:
    PUBLIC          anyone can watch
    FRIENDS_ONLY    only the broadcaster's friends list
                    can see + join
    LINKSHELL_ONLY  only members of a designated LS

Session lifecycle:
    start_session() → ACTIVE
    end_session()   → ENDED  (terminal; new session
                              gets a new ID)

A broadcaster can have at most one active session at a
time. Re-calling start_session() while one is already
active returns the existing session_id (idempotent).

Sessions auto-end if they go untouched for an idle
window (default 30 min). The caller calls heartbeat()
on activity (any in-game action by the broadcaster).

Public surface
--------------
    Privacy enum
    SessionStatus enum
    StreamingSession dataclass (frozen)
    StreamingSessionRegistry
        .start(broadcaster_id, privacy, started_at,
               linkshell_id) -> Optional[StreamingSession]
        .end(broadcaster_id, ended_at) -> bool
        .heartbeat(broadcaster_id, now) -> bool
        .session_for(broadcaster_id)
            -> Optional[StreamingSession]
        .live_sessions() -> list[StreamingSession]
        .reap_idle(now) -> int  # n sessions auto-ended
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_IDLE_TIMEOUT_SEC = 30 * 60   # 30 minutes


class Privacy(str, enum.Enum):
    PUBLIC = "public"
    FRIENDS_ONLY = "friends_only"
    LINKSHELL_ONLY = "linkshell_only"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"


@dataclasses.dataclass(frozen=True)
class StreamingSession:
    session_id: str
    broadcaster_id: str
    privacy: Privacy
    linkshell_id: str           # empty unless LINKSHELL_ONLY
    started_at: int
    ended_at: int               # 0 while ACTIVE
    last_activity_at: int
    status: SessionStatus


@dataclasses.dataclass
class StreamingSessionRegistry:
    _sessions: dict[str, StreamingSession] = dataclasses.field(
        default_factory=dict,
    )
    # broadcaster_id → active session_id (only when ACTIVE)
    _active_by_broadcaster: dict[
        str, str,
    ] = dataclasses.field(default_factory=dict)
    _next_seq: int = 1

    def start(
        self, *, broadcaster_id: str, privacy: Privacy,
        started_at: int, linkshell_id: str = "",
    ) -> t.Optional[StreamingSession]:
        if not broadcaster_id:
            return None
        if (privacy == Privacy.LINKSHELL_ONLY
                and not linkshell_id):
            return None
        existing = self._active_by_broadcaster.get(
            broadcaster_id,
        )
        if existing:
            return self._sessions[existing]
        sid = f"stream_{self._next_seq}"
        self._next_seq += 1
        s = StreamingSession(
            session_id=sid,
            broadcaster_id=broadcaster_id,
            privacy=privacy,
            linkshell_id=(
                linkshell_id
                if privacy == Privacy.LINKSHELL_ONLY else ""
            ),
            started_at=started_at, ended_at=0,
            last_activity_at=started_at,
            status=SessionStatus.ACTIVE,
        )
        self._sessions[sid] = s
        self._active_by_broadcaster[broadcaster_id] = sid
        return s

    def end(
        self, *, broadcaster_id: str, ended_at: int,
    ) -> bool:
        sid = self._active_by_broadcaster.get(
            broadcaster_id,
        )
        if not sid:
            return False
        s = self._sessions[sid]
        self._sessions[sid] = dataclasses.replace(
            s, status=SessionStatus.ENDED,
            ended_at=ended_at,
        )
        del self._active_by_broadcaster[broadcaster_id]
        return True

    def heartbeat(
        self, *, broadcaster_id: str, now: int,
    ) -> bool:
        sid = self._active_by_broadcaster.get(
            broadcaster_id,
        )
        if not sid:
            return False
        s = self._sessions[sid]
        if now < s.last_activity_at:
            return False  # clock skew; refuse
        self._sessions[sid] = dataclasses.replace(
            s, last_activity_at=now,
        )
        return True

    def session_for(
        self, *, broadcaster_id: str,
    ) -> t.Optional[StreamingSession]:
        sid = self._active_by_broadcaster.get(
            broadcaster_id,
        )
        return self._sessions.get(sid) if sid else None

    def live_sessions(self) -> list[StreamingSession]:
        out = [
            self._sessions[sid]
            for sid in self._active_by_broadcaster.values()
        ]
        out.sort(key=lambda s: -s.started_at)
        return out

    def reap_idle(self, *, now: int) -> int:
        cutoff = now - _IDLE_TIMEOUT_SEC
        to_end: list[str] = []
        for bid, sid in self._active_by_broadcaster.items():
            s = self._sessions[sid]
            if s.last_activity_at < cutoff:
                to_end.append(bid)
        for bid in to_end:
            self.end(broadcaster_id=bid, ended_at=now)
        return len(to_end)

    def total_sessions(self) -> int:
        return len(self._sessions)


__all__ = [
    "Privacy", "SessionStatus", "StreamingSession",
    "StreamingSessionRegistry",
]
