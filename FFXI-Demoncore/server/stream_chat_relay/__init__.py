"""Stream chat relay — viewer side-channel chat.

A spectator's chat in the stream's side panel goes here,
not into the broadcaster's regular chat. The broadcaster
has moderation tools: mute_viewer (silence one viewer
for this stream), and ban_viewer (kick + block from
re-joining via spectator_pool callbacks).

Rate limit: 5 messages per viewer per 30s window. Anti-
spam without being too restrictive.

Message length capped at 200 chars; blank or whitespace-
only blocked.

The chat is per-session — when the stream ends, the chat
log can be cleared by the controller. We don't auto-clear;
the broadcaster might want to review the chat after.

Public surface
--------------
    SendResult dataclass (frozen)
    ChatMessage dataclass (frozen)
    StreamChatRelay
        .send(viewer_id, session_id, body, now)
            -> SendResult
        .recent(session_id, limit) -> list[ChatMessage]
        .mute(broadcaster_id, viewer_id, session_id)
            -> bool
        .ban(broadcaster_id, viewer_id, session_id)
            -> bool
        .is_muted(viewer_id, session_id) -> bool
        .is_banned(viewer_id, session_id) -> bool
        .clear_session(session_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


_MAX_BODY = 200
_RATE_WINDOW_SEC = 30
_RATE_LIMIT = 5


@dataclasses.dataclass(frozen=True)
class ChatMessage:
    msg_id: int
    session_id: str
    viewer_id: str
    body: str
    posted_at: int


@dataclasses.dataclass(frozen=True)
class SendResult:
    success: bool
    reason: str
    message: t.Optional[ChatMessage]


@dataclasses.dataclass
class StreamChatRelay:
    _messages: list[ChatMessage] = dataclasses.field(
        default_factory=list,
    )
    _muted: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    _banned: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    # session_id -> broadcaster_id (for moderation auth)
    _session_owner: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def register_session(
        self, *, session_id: str, broadcaster_id: str,
    ) -> bool:
        """Caller wires a session_id to its broadcaster
        when the streaming session starts. Required for
        moderation calls."""
        if not session_id or not broadcaster_id:
            return False
        self._session_owner[session_id] = broadcaster_id
        return True

    def send(
        self, *, viewer_id: str, session_id: str,
        body: str, now: int,
    ) -> SendResult:
        if not viewer_id or not session_id:
            return SendResult(
                success=False, reason="ids_required",
                message=None,
            )
        body = body.strip()
        if not body:
            return SendResult(
                success=False, reason="empty_body",
                message=None,
            )
        if len(body) > _MAX_BODY:
            return SendResult(
                success=False, reason="body_too_long",
                message=None,
            )
        if (viewer_id, session_id) in self._banned:
            return SendResult(
                success=False, reason="banned",
                message=None,
            )
        if (viewer_id, session_id) in self._muted:
            return SendResult(
                success=False, reason="muted",
                message=None,
            )
        # Rate limit
        cutoff = now - _RATE_WINDOW_SEC
        recent_count = sum(
            1 for m in self._messages
            if m.viewer_id == viewer_id
            and m.session_id == session_id
            and m.posted_at >= cutoff
        )
        if recent_count >= _RATE_LIMIT:
            return SendResult(
                success=False, reason="rate_limited",
                message=None,
            )
        msg = ChatMessage(
            msg_id=self._next_id,
            session_id=session_id, viewer_id=viewer_id,
            body=body, posted_at=now,
        )
        self._next_id += 1
        self._messages.append(msg)
        return SendResult(
            success=True, reason="", message=msg,
        )

    def recent(
        self, *, session_id: str, limit: int = 50,
    ) -> list[ChatMessage]:
        if limit <= 0:
            return []
        out = [
            m for m in self._messages
            if m.session_id == session_id
        ]
        return out[-limit:]

    def _broadcaster_check(
        self, broadcaster_id: str, session_id: str,
    ) -> bool:
        owner = self._session_owner.get(session_id)
        return owner is not None and owner == broadcaster_id

    def mute(
        self, *, broadcaster_id: str, viewer_id: str,
        session_id: str,
    ) -> bool:
        if not self._broadcaster_check(
            broadcaster_id, session_id,
        ):
            return False
        if not viewer_id:
            return False
        self._muted.add((viewer_id, session_id))
        return True

    def ban(
        self, *, broadcaster_id: str, viewer_id: str,
        session_id: str,
    ) -> bool:
        if not self._broadcaster_check(
            broadcaster_id, session_id,
        ):
            return False
        if not viewer_id:
            return False
        self._banned.add((viewer_id, session_id))
        return True

    def is_muted(
        self, *, viewer_id: str, session_id: str,
    ) -> bool:
        return (viewer_id, session_id) in self._muted

    def is_banned(
        self, *, viewer_id: str, session_id: str,
    ) -> bool:
        return (viewer_id, session_id) in self._banned

    def clear_session(self, *, session_id: str) -> int:
        before = len(self._messages)
        self._messages = [
            m for m in self._messages
            if m.session_id != session_id
        ]
        return before - len(self._messages)

    def total_messages(self) -> int:
        return len(self._messages)


__all__ = [
    "ChatMessage", "SendResult", "StreamChatRelay",
]
