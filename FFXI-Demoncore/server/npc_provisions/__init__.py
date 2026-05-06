"""NPC provisions — the unspoiling vendor pantry.

Inn cooks and tavern keepers stock food and drink that
players can buy. The anti-monopoly rule is simple: NPC
stock does NOT decay until a player buys it. The moment
a sale happens, the item flips into normal leftover_storage
aging (7-day food / 3-month drink defaults).

Without this, a single player-cook could buy out the
NPC's stock, sit on it through the spoil window, and
force everyone to buy player-made food at inflated AH
prices. Anti-cornering by design.

Restock cycles refill the pantry on a schedule (e.g. each
game-day). A pantry has per-item max_stock; restocks top
the inventory back up but never overflow.

Public surface
--------------
    PantryEntry dataclass (mutable)
    NpcPantry
        .define_item(item_id, dish, payload, kind,
                     max_stock, gil_price) -> bool
        .restock_cycle() -> int  (count restocked)
        .available(item_id) -> int
        .purchase(item_id, buyer_id, leftover_storage,
                  leftover_id, now) -> Optional[str]
            (returns leftover_id of the now-aging item;
             None if out of stock or unknown)
        .price(item_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.cookpot_recipes import BuffPayload, DishKind
from server.leftover_storage import (
    LeftoverStorage, Provenance, ProvisionKind,
)


@dataclasses.dataclass
class PantryEntry:
    item_id: str
    dish: DishKind
    payload: BuffPayload
    kind: ProvisionKind
    max_stock: int
    gil_price: int
    current_stock: int


@dataclasses.dataclass
class NpcPantry:
    npc_id: str = "vendor"
    _items: dict[str, PantryEntry] = dataclasses.field(
        default_factory=dict,
    )

    def define_item(
        self, *, item_id: str, dish: DishKind,
        payload: BuffPayload, kind: ProvisionKind,
        max_stock: int, gil_price: int,
    ) -> bool:
        if not item_id:
            return False
        if item_id in self._items:
            return False
        if max_stock <= 0 or gil_price < 0:
            return False
        self._items[item_id] = PantryEntry(
            item_id=item_id, dish=dish, payload=payload,
            kind=kind, max_stock=max_stock,
            gil_price=gil_price,
            current_stock=max_stock,
        )
        return True

    def restock_cycle(self) -> int:
        """Top each item back to max_stock.

        Returns the total units restocked across all items.
        """
        restocked = 0
        for entry in self._items.values():
            if entry.current_stock < entry.max_stock:
                restocked += entry.max_stock - entry.current_stock
                entry.current_stock = entry.max_stock
        return restocked

    def available(self, *, item_id: str) -> int:
        e = self._items.get(item_id)
        if e is None:
            return 0
        return e.current_stock

    def price(self, *, item_id: str) -> int:
        e = self._items.get(item_id)
        if e is None:
            return 0
        return e.gil_price

    def purchase(
        self, *, item_id: str, buyer_id: str,
        leftover_storage: LeftoverStorage,
        leftover_id: str, now: int,
    ) -> t.Optional[str]:
        e = self._items.get(item_id)
        if e is None:
            return None
        if not buyer_id or not leftover_id:
            return None
        if e.current_stock <= 0:
            return None
        # Stash into the player's leftover storage as
        # NPC_STOCKED first, then immediately transfer
        # to the buyer to flip provenance to PLAYER_MADE
        # so aging starts now. This keeps the "no decay
        # while NPC-held" rule intact even if the same
        # storage instance houses both.
        ok = leftover_storage.stash(
            leftover_id=leftover_id,
            owner_id=self.npc_id, dish=e.dish,
            payload=e.payload, stashed_at=now,
            kind=e.kind, provenance=Provenance.NPC_STOCKED,
        )
        if not ok:
            return None
        leftover_storage.transfer_to_player(
            leftover_id=leftover_id, new_owner_id=buyer_id,
        )
        e.current_stock -= 1
        return leftover_id

    def total_items_defined(self) -> int:
        return len(self._items)


__all__ = [
    "PantryEntry", "NpcPantry",
]
