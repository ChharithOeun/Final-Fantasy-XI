"""Beastman mail runners — goblin courier delivery network.

Beastman cities don't run their own postal service — goblin
neutrals do. Players SEND PARCELS (item + optional gil + 70-char
note) to other beastman recipients via a GOBLIN MAIL RUNNER.

Each parcel has:
  - sender_id, recipient_id
  - cargo_item_id (optional, "" for letter-only)
  - gil_amount (optional, 0..1_000_000)
  - note_text (max 70 chars)
  - posted_at

Runners deliver after a configurable lag (default 1 hour) so
the system has the texture of physical couriers, not instant
mail. Each player has an INBOX cap of 8; recipient must claim
or reject before more mail arrives.

Public surface
--------------
    Parcel dataclass
    BeastmanMailRunners
        .send(sender_id, recipient_id, cargo_item_id,
              gil_amount, note_text, now_seconds)
        .arrive(parcel_id, now_seconds)
        .claim(parcel_id, recipient_id)
        .reject(parcel_id, recipient_id)
        .inbox(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_INBOX_CAP = 8
_DEFAULT_DELIVERY_SECONDS = 3600   # 1 hour
_GIL_HARD_CAP = 1_000_000
_NOTE_MAX = 70


class ParcelState(str, enum.Enum):
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CLAIMED = "claimed"
    REJECTED = "rejected"


@dataclasses.dataclass
class Parcel:
    parcel_id: int
    sender_id: str
    recipient_id: str
    cargo_item_id: str
    gil_amount: int
    note_text: str
    posted_at: int
    arrives_at: int
    state: ParcelState = ParcelState.IN_TRANSIT


@dataclasses.dataclass(frozen=True)
class SendResult:
    accepted: bool
    parcel_id: int = 0
    arrives_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClaimResult:
    accepted: bool
    parcel_id: int
    cargo_item_id: str = ""
    gil_amount: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanMailRunners:
    _parcels: dict[int, Parcel] = dataclasses.field(default_factory=dict)
    _next_id: int = 1
    _delivery_seconds: int = _DEFAULT_DELIVERY_SECONDS

    def set_delivery_lag(self, *, seconds: int) -> bool:
        if seconds < 0:
            return False
        self._delivery_seconds = seconds
        return True

    def _inbox_count(self, player_id: str) -> int:
        return sum(
            1 for p in self._parcels.values()
            if p.recipient_id == player_id
            and p.state in (
                ParcelState.IN_TRANSIT, ParcelState.DELIVERED,
            )
        )

    def send(
        self, *, sender_id: str,
        recipient_id: str,
        cargo_item_id: str = "",
        gil_amount: int = 0,
        note_text: str = "",
        now_seconds: int,
    ) -> SendResult:
        if not sender_id or not recipient_id:
            return SendResult(False, reason="missing endpoints")
        if sender_id == recipient_id:
            return SendResult(False, reason="cannot mail self")
        if gil_amount < 0 or gil_amount > _GIL_HARD_CAP:
            return SendResult(False, reason="gil out of range")
        if len(note_text) > _NOTE_MAX:
            return SendResult(False, reason="note too long")
        if not cargo_item_id and gil_amount == 0 and not note_text:
            return SendResult(False, reason="empty parcel")
        if self._inbox_count(recipient_id) >= _INBOX_CAP:
            return SendResult(False, reason="recipient inbox full")
        pid = self._next_id
        self._next_id += 1
        p = Parcel(
            parcel_id=pid,
            sender_id=sender_id,
            recipient_id=recipient_id,
            cargo_item_id=cargo_item_id,
            gil_amount=gil_amount,
            note_text=note_text,
            posted_at=now_seconds,
            arrives_at=now_seconds + self._delivery_seconds,
        )
        self._parcels[pid] = p
        return SendResult(
            accepted=True,
            parcel_id=pid, arrives_at=p.arrives_at,
        )

    def arrive(
        self, *, parcel_id: int, now_seconds: int,
    ) -> bool:
        p = self._parcels.get(parcel_id)
        if p is None or p.state != ParcelState.IN_TRANSIT:
            return False
        if now_seconds < p.arrives_at:
            return False
        p.state = ParcelState.DELIVERED
        return True

    def _auto_arrive(self, now_seconds: int) -> None:
        for p in self._parcels.values():
            if (
                p.state == ParcelState.IN_TRANSIT
                and now_seconds >= p.arrives_at
            ):
                p.state = ParcelState.DELIVERED

    def claim(
        self, *, parcel_id: int,
        recipient_id: str,
        now_seconds: int,
    ) -> ClaimResult:
        # First lazy-arrive anything overdue
        self._auto_arrive(now_seconds)
        p = self._parcels.get(parcel_id)
        if p is None:
            return ClaimResult(
                False, parcel_id, reason="unknown parcel",
            )
        if p.recipient_id != recipient_id:
            return ClaimResult(
                False, parcel_id, reason="not your parcel",
            )
        if p.state != ParcelState.DELIVERED:
            return ClaimResult(
                False, parcel_id, reason="not yet delivered",
            )
        p.state = ParcelState.CLAIMED
        return ClaimResult(
            accepted=True,
            parcel_id=parcel_id,
            cargo_item_id=p.cargo_item_id,
            gil_amount=p.gil_amount,
        )

    def reject(
        self, *, parcel_id: int,
        recipient_id: str,
    ) -> bool:
        p = self._parcels.get(parcel_id)
        if p is None or p.recipient_id != recipient_id:
            return False
        if p.state in (
            ParcelState.CLAIMED, ParcelState.REJECTED,
        ):
            return False
        p.state = ParcelState.REJECTED
        return True

    def inbox(
        self, *, player_id: str,
    ) -> tuple[Parcel, ...]:
        return tuple(
            p for p in self._parcels.values()
            if p.recipient_id == player_id
            and p.state in (
                ParcelState.IN_TRANSIT, ParcelState.DELIVERED,
            )
        )

    def total_parcels(self) -> int:
        return len(self._parcels)


__all__ = [
    "ParcelState", "Parcel",
    "SendResult", "ClaimResult",
    "BeastmanMailRunners",
]
