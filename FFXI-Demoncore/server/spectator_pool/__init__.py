"""Spectator pool — viewers attached to a stream.

While a streaming session is ACTIVE, viewers can join
and leave. This module owns the per-stream viewer set
and enforces caps.

Caps:
    PUBLIC streams       max 100 concurrent viewers
    FRIENDS_ONLY         max 30 (intimate)
    LINKSHELL_ONLY       max 50

Joining is consensual: the join() entry validates
privacy access via a caller-supplied predicate (the
controller knows who's friends with whom and which LS
each player is in). The module just enforces the cap.

A viewer can only watch ONE stream at a time. Joining
a second stream auto-leaves the first.

Public surface
--------------
    JoinResult dataclass (frozen)
    SpectatorPool
        .join(viewer_id, session, can_view_predicate,
              joined_at) -> JoinResult
        .leave(viewer_id) -> bool
        .viewers_of(session_id) -> list[str]
        .viewer_count(session_id) -> int
        .watching_what(viewer_id) -> Optional[str]   # session_id
        .clear_session(session_id) -> int  # n viewers ejected
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.streaming_session import (
    Privacy, SessionStatus, StreamingSession,
)


_CAP_PUBLIC = 100
_CAP_FRIENDS = 30
_CAP_LINKSHELL = 50


@dataclasses.dataclass(frozen=True)
class JoinResult:
    success: bool
    reason: str
    session_id: str


def _cap_for(privacy: Privacy) -> int:
    if privacy == Privacy.PUBLIC:
        return _CAP_PUBLIC
    if privacy == Privacy.FRIENDS_ONLY:
        return _CAP_FRIENDS
    return _CAP_LINKSHELL


@dataclasses.dataclass
class SpectatorPool:
    # session_id → set[viewer_id]
    _by_session: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # viewer_id → session_id (one stream at a time)
    _viewer_at: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def join(
        self, *, viewer_id: str,
        session: StreamingSession,
        can_view_predicate: t.Callable[[], bool],
        joined_at: int,
    ) -> JoinResult:
        if not viewer_id:
            return JoinResult(
                success=False, reason="viewer_id_required",
                session_id="",
            )
        if session.broadcaster_id == viewer_id:
            return JoinResult(
                success=False, reason="self_view",
                session_id=session.session_id,
            )
        if session.status != SessionStatus.ACTIVE:
            return JoinResult(
                success=False, reason="session_not_active",
                session_id=session.session_id,
            )
        if not can_view_predicate():
            return JoinResult(
                success=False,
                reason="privacy_blocked",
                session_id=session.session_id,
            )
        viewers = self._by_session.setdefault(
            session.session_id, set(),
        )
        if viewer_id in viewers:
            return JoinResult(
                success=True, reason="",
                session_id=session.session_id,
            )
        cap = _cap_for(session.privacy)
        if len(viewers) >= cap:
            return JoinResult(
                success=False, reason="at_capacity",
                session_id=session.session_id,
            )
        # Auto-leave any prior stream
        prior = self._viewer_at.get(viewer_id)
        if prior and prior != session.session_id:
            self._by_session.get(
                prior, set(),
            ).discard(viewer_id)
        viewers.add(viewer_id)
        self._viewer_at[viewer_id] = session.session_id
        return JoinResult(
            success=True, reason="",
            session_id=session.session_id,
        )

    def leave(self, *, viewer_id: str) -> bool:
        sid = self._viewer_at.pop(viewer_id, None)
        if not sid:
            return False
        self._by_session.get(sid, set()).discard(viewer_id)
        return True

    def viewers_of(
        self, *, session_id: str,
    ) -> list[str]:
        return sorted(self._by_session.get(session_id, set()))

    def viewer_count(self, *, session_id: str) -> int:
        return len(self._by_session.get(session_id, set()))

    def watching_what(
        self, *, viewer_id: str,
    ) -> t.Optional[str]:
        return self._viewer_at.get(viewer_id)

    def clear_session(self, *, session_id: str) -> int:
        viewers = self._by_session.pop(
            session_id, set(),
        )
        for v in viewers:
            self._viewer_at.pop(v, None)
        return len(viewers)

    def total_viewers(self) -> int:
        return len(self._viewer_at)


__all__ = [
    "JoinResult", "SpectatorPool",
]
