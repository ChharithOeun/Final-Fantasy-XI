"""Chat channels — say/shout/yell/tell/party/linkshell routing.

FFXI canonical channels with scopes:
    SAY    - proximity (~25 yalms)
    SHOUT  - whole zone
    YELL   - global (jeuno-only originally)
    TELL   - DM to one player
    PARTY  - to current party
    LINKSHELL - all members of equipped LS

Public surface
--------------
    Channel enum
    ChatMessage immutable record
    ChatRouter facade
        .send(channel, sender, recipient, body)
        .recipients_for(channel, sender, ctx) -> set[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


SAY_RADIUS_YALMS = 25
SHOUT_SCOPE = "zone"
YELL_SCOPE = "global"


class Channel(str, enum.Enum):
    SAY = "say"
    SHOUT = "shout"
    YELL = "yell"
    TELL = "tell"
    PARTY = "party"
    LINKSHELL = "linkshell"
    LINKSHELL_2 = "linkshell_2"


@dataclasses.dataclass(frozen=True)
class ChatMessage:
    sender_id: str
    channel: Channel
    body: str
    recipient_id: t.Optional[str] = None    # tell only
    timestamp: int = 0


@dataclasses.dataclass(frozen=True)
class ChatContext:
    """What the router needs to know about the world."""
    sender_zone_id: str = ""
    proximity_player_ids: tuple[str, ...] = ()
    zone_player_ids: tuple[str, ...] = ()
    global_player_ids: tuple[str, ...] = ()
    party_member_ids: tuple[str, ...] = ()
    linkshell_member_ids: tuple[str, ...] = ()
    linkshell_2_member_ids: tuple[str, ...] = ()
    blocked_by_recipient: frozenset[str] = frozenset()


@dataclasses.dataclass(frozen=True)
class SendResult:
    accepted: bool
    delivered_to: tuple[str, ...] = ()
    reason: t.Optional[str] = None


def _filter_blocked(
    recipients: t.Iterable[str],
    sender_id: str,
    blocked_by: t.Iterable[str],
) -> tuple[str, ...]:
    blocked_set = set(blocked_by)
    return tuple(
        r for r in recipients
        if r != sender_id and r not in blocked_set
    )


class ChatRouter:
    """Stateless facade. Caller passes ChatContext per send call."""

    def send(
        self, *,
        message: ChatMessage,
        ctx: ChatContext,
    ) -> SendResult:
        if not message.body.strip():
            return SendResult(False, reason="empty body")
        ch = message.channel
        if ch == Channel.SAY:
            recips = _filter_blocked(
                ctx.proximity_player_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        if ch == Channel.SHOUT:
            recips = _filter_blocked(
                ctx.zone_player_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        if ch == Channel.YELL:
            recips = _filter_blocked(
                ctx.global_player_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        if ch == Channel.TELL:
            if message.recipient_id is None:
                return SendResult(
                    False, reason="tell needs recipient",
                )
            if message.recipient_id in ctx.blocked_by_recipient:
                return SendResult(
                    False, reason="recipient blocked you",
                )
            return SendResult(
                True, delivered_to=(message.recipient_id,),
            )
        if ch == Channel.PARTY:
            recips = _filter_blocked(
                ctx.party_member_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        if ch == Channel.LINKSHELL:
            recips = _filter_blocked(
                ctx.linkshell_member_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        if ch == Channel.LINKSHELL_2:
            recips = _filter_blocked(
                ctx.linkshell_2_member_ids,
                message.sender_id,
                ctx.blocked_by_recipient,
            )
            return SendResult(True, delivered_to=recips)
        return SendResult(False, reason="unknown channel")


__all__ = [
    "SAY_RADIUS_YALMS", "SHOUT_SCOPE", "YELL_SCOPE",
    "Channel", "ChatMessage", "ChatContext",
    "SendResult", "ChatRouter",
]
