"""Delivery box — mail items + gil between players.

Each player has an 8-slot inbox. Senders ship items with optional
gil; recipient retrieves. Unretrieved deliveries auto-return to
sender after 30 days.

Public surface
--------------
    DeliveryItem
    DeliveryBox per recipient
        .receive(parcel)
        .retrieve(slot)
        .reject(slot)
        .tick(now_tick) -> auto-return parcels past expiry
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


INBOX_CAPACITY = 8
DELIVERY_LIFETIME_SECONDS = 30 * 24 * 60 * 60


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    RETRIEVED = "retrieved"
    REJECTED = "rejected"
    AUTO_RETURNED = "auto_returned"


@dataclasses.dataclass
class DeliveryItem:
    parcel_id: int
    sender_id: str
    recipient_id: str
    item_id: str
    quantity: int
    gil_attached: int
    sent_at_tick: int
    expires_at_tick: int
    status: DeliveryStatus = DeliveryStatus.PENDING


@dataclasses.dataclass(frozen=True)
class ReceiveResult:
    accepted: bool
    parcel_id: t.Optional[int] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class DeliveryBox:
    recipient_id: str
    _next_parcel_id: int = 1
    _slots: list[DeliveryItem] = dataclasses.field(
        default_factory=list, repr=False,
    )

    def free_slots(self) -> int:
        return INBOX_CAPACITY - len(self._slots)

    def receive(
        self, *,
        sender_id: str, item_id: str, quantity: int,
        gil_attached: int, now_tick: int,
    ) -> ReceiveResult:
        if quantity <= 0 or gil_attached < 0:
            return ReceiveResult(False, reason="invalid amounts")
        if self.free_slots() <= 0:
            return ReceiveResult(False, reason="inbox full")
        parcel = DeliveryItem(
            parcel_id=self._next_parcel_id,
            sender_id=sender_id,
            recipient_id=self.recipient_id,
            item_id=item_id, quantity=quantity,
            gil_attached=gil_attached,
            sent_at_tick=now_tick,
            expires_at_tick=now_tick + DELIVERY_LIFETIME_SECONDS,
        )
        self._slots.append(parcel)
        self._next_parcel_id += 1
        return ReceiveResult(True, parcel_id=parcel.parcel_id)

    def retrieve(
        self, *, parcel_id: int,
    ) -> t.Optional[DeliveryItem]:
        for i, p in enumerate(self._slots):
            if p.parcel_id == parcel_id and \
               p.status == DeliveryStatus.PENDING:
                p.status = DeliveryStatus.RETRIEVED
                return self._slots.pop(i)
        return None

    def reject(
        self, *, parcel_id: int,
    ) -> t.Optional[DeliveryItem]:
        for i, p in enumerate(self._slots):
            if p.parcel_id == parcel_id and \
               p.status == DeliveryStatus.PENDING:
                p.status = DeliveryStatus.REJECTED
                return self._slots.pop(i)
        return None

    def pending(self) -> tuple[DeliveryItem, ...]:
        return tuple(
            p for p in self._slots
            if p.status == DeliveryStatus.PENDING
        )

    def tick(self, *, now_tick: int) -> tuple[DeliveryItem, ...]:
        """Auto-return expired parcels. Returns the returned set."""
        returned: list[DeliveryItem] = []
        kept: list[DeliveryItem] = []
        for p in self._slots:
            if (p.status == DeliveryStatus.PENDING
                    and now_tick >= p.expires_at_tick):
                p.status = DeliveryStatus.AUTO_RETURNED
                returned.append(p)
            else:
                kept.append(p)
        self._slots = kept
        return tuple(returned)


__all__ = [
    "INBOX_CAPACITY", "DELIVERY_LIFETIME_SECONDS",
    "DeliveryStatus", "DeliveryItem",
    "ReceiveResult", "DeliveryBox",
]
