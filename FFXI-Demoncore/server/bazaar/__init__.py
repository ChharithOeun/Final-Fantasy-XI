"""Bazaar — player shop using inventory slots.

Each item slot in a player's inventory can be tagged with a bazaar
price. When a buyer browses the bazaar, they see all priced slots.
On purchase, item moves from seller to buyer; gil moves the other way.

Different from auction_house: bazaar is direct (no AH fee, no
expiration), but only works while seller is online + targetable
in the world.

Public surface
--------------
    Bazaar per-player
        .price(slot_index, item_id, qty, price_gil)
        .unprice(slot_index)
        .browse() -> tuple[BazaarEntry, ...]
        .buy(buyer_id, slot_index, buyer_gil) -> BuyResult
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class BazaarEntry:
    slot_index: int
    item_id: str
    quantity: int
    price_gil: int


@dataclasses.dataclass(frozen=True)
class BuyResult:
    accepted: bool
    item_id: t.Optional[str] = None
    quantity: int = 0
    gil_paid: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class Bazaar:
    seller_id: str
    is_online: bool = True
    _priced: dict[int, BazaarEntry] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def price(
        self, *,
        slot_index: int, item_id: str,
        quantity: int, price_gil: int,
    ) -> bool:
        if quantity <= 0 or price_gil <= 0:
            return False
        self._priced[slot_index] = BazaarEntry(
            slot_index=slot_index, item_id=item_id,
            quantity=quantity, price_gil=price_gil,
        )
        return True

    def unprice(self, *, slot_index: int) -> bool:
        if slot_index not in self._priced:
            return False
        del self._priced[slot_index]
        return True

    def browse(self) -> tuple[BazaarEntry, ...]:
        if not self.is_online:
            return ()
        return tuple(self._priced.values())

    def buy(
        self, *,
        buyer_id: str,
        slot_index: int,
        buyer_gil_balance: int,
    ) -> BuyResult:
        if not self.is_online:
            return BuyResult(False, reason="seller offline")
        if buyer_id == self.seller_id:
            return BuyResult(False, reason="cannot buy own bazaar")
        entry = self._priced.get(slot_index)
        if entry is None:
            return BuyResult(False, reason="slot not priced")
        if buyer_gil_balance < entry.price_gil:
            return BuyResult(False, reason="insufficient gil")
        # Sell: remove from priced + return result.
        del self._priced[slot_index]
        return BuyResult(
            accepted=True,
            item_id=entry.item_id,
            quantity=entry.quantity,
            gil_paid=entry.price_gil,
        )

    def go_offline(self) -> None:
        self.is_online = False

    def go_online(self) -> None:
        self.is_online = True


__all__ = ["BazaarEntry", "BuyResult", "Bazaar"]
