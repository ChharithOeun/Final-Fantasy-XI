"""Bounty payout — split + mail rewards for bounty kills.

When a bounty kill resolves (an outlaw's head is taken, a
hostile-PvP target is hunted down, etc.), this module splits the
bounty pool evenly among the participating killers and queues a
mailbox parcel per share.

Composes on top of:
* outlaw_linkshell — source of LS bounty pools
* delivery_box     — destination for the gil + token mail
* permadeath_broadcast — caller can chain a server announcement
                          after the payout settles

Public surface
--------------
    BountyParticipant dataclass (player_id + role)
    BountyParcel dataclass — what gets mailed
    settle_bounty(participants, total_bounty, ...) -> SettlementResult
    deliver_to_inboxes(settlement, inboxes, now_tick) -> int
        delivered count
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.delivery_box import DeliveryBox


# Bounty Office is the default sender on outgoing parcels.
BOUNTY_OFFICE_SENDER_ID = "bounty_office"
DEFAULT_TOKEN_ITEM_ID = "bounty_certificate"


@dataclasses.dataclass(frozen=True)
class BountyParticipant:
    player_id: str
    role: str = "killer"        # "killer" / "support" / "tracker"


@dataclasses.dataclass(frozen=True)
class BountyParcel:
    """One mail item destined for one participant."""
    recipient_id: str
    gil: int
    token_quantity: int = 1
    token_item_id: str = DEFAULT_TOKEN_ITEM_ID


@dataclasses.dataclass(frozen=True)
class SettlementResult:
    accepted: bool
    parcels: tuple[BountyParcel, ...] = ()
    per_share_gil: int = 0
    leftover_gil: int = 0
    reason: t.Optional[str] = None


def settle_bounty(
    *, participants: t.Iterable[BountyParticipant],
    total_bounty: int, token_item_id: str = DEFAULT_TOKEN_ITEM_ID,
) -> SettlementResult:
    """Split a bounty evenly across participants. Each one gets the
    same share (rounded down) plus a single bounty token. The
    rounding leftover stays with the bounty office."""
    p_list = list(participants)
    if not p_list:
        return SettlementResult(False, reason="no participants")
    if total_bounty < 0:
        return SettlementResult(False, reason="negative bounty")
    if total_bounty == 0:
        # Tokens-only payout (no gil to split).
        parcels = tuple(
            BountyParcel(
                recipient_id=p.player_id, gil=0,
                token_quantity=1, token_item_id=token_item_id,
            ) for p in p_list
        )
        return SettlementResult(
            accepted=True, parcels=parcels,
            per_share_gil=0, leftover_gil=0,
        )
    n = len(p_list)
    per_share = total_bounty // n
    leftover = total_bounty - per_share * n
    parcels = tuple(
        BountyParcel(
            recipient_id=p.player_id, gil=per_share,
            token_quantity=1, token_item_id=token_item_id,
        ) for p in p_list
    )
    return SettlementResult(
        accepted=True, parcels=parcels,
        per_share_gil=per_share, leftover_gil=leftover,
    )


def deliver_to_inboxes(
    *, settlement: SettlementResult,
    inboxes: dict[str, DeliveryBox],
    now_tick: int,
    sender_id: str = BOUNTY_OFFICE_SENDER_ID,
) -> int:
    """Push every parcel from a SettlementResult into the matching
    recipient's DeliveryBox. Returns the count successfully
    delivered. If a recipient has no inbox or their inbox is full,
    the parcel is dropped (caller can decide retry policy)."""
    if not settlement.accepted:
        return 0
    delivered = 0
    for parcel in settlement.parcels:
        inbox = inboxes.get(parcel.recipient_id)
        if inbox is None:
            continue
        res = inbox.receive(
            sender_id=sender_id,
            item_id=parcel.token_item_id,
            quantity=parcel.token_quantity,
            gil_attached=parcel.gil,
            now_tick=now_tick,
        )
        if res.accepted:
            delivered += 1
    return delivered


__all__ = [
    "BOUNTY_OFFICE_SENDER_ID", "DEFAULT_TOKEN_ITEM_ID",
    "BountyParticipant", "BountyParcel",
    "SettlementResult",
    "settle_bounty", "deliver_to_inboxes",
]
