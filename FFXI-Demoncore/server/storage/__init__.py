"""Storage — Mog House inventory containers.

Per-character storage is split across multiple containers, each
with a slot cap. Items live in slots 1..N within their container.
Moving items requires a free destination slot. Some containers are
"home only" (Storage Slip): they can't be accessed in the field.

Public surface
--------------
    Container enum
    ITEM_SLOT_LIMITS dict
    StorageSlot dataclass
    PlayerStorage container facade
        .add(item_id, qty=1, container=Inventory) -> SlotRef|None
        .move(from_ref, to_container) -> bool
        .remove(slot_ref, qty=1) -> bool
        .total_count(item_id) -> int
        .free_slots(container) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Container(str, enum.Enum):
    INVENTORY = "inventory"           # always available; 80 slots
    MOG_SATCHEL = "mog_satchel"       # always available; 80 slots
    MOG_SACK = "mog_sack"             # always available; 80 slots
    MOG_CASE = "mog_case"             # always available; 80 slots
    MOG_WARDROBE = "mog_wardrobe"     # equipment-only; 80 slots
    MOG_LOCKER = "mog_locker"         # home only; 80 slots
    MOG_SAFE = "mog_safe"             # home only; 80 slots
    STORAGE_SLIP = "storage_slip"     # home only; unbounded


# How many slots each container holds.
SLOT_LIMITS: dict[Container, int] = {
    Container.INVENTORY: 80,
    Container.MOG_SATCHEL: 80,
    Container.MOG_SACK: 80,
    Container.MOG_CASE: 80,
    Container.MOG_WARDROBE: 80,
    Container.MOG_LOCKER: 80,
    Container.MOG_SAFE: 80,
    Container.STORAGE_SLIP: 999,
}


HOME_ONLY = frozenset({
    Container.MOG_LOCKER, Container.MOG_SAFE,
    Container.STORAGE_SLIP,
})


@dataclasses.dataclass
class StorageSlot:
    container: Container
    slot_index: int
    item_id: str
    quantity: int


@dataclasses.dataclass(frozen=True)
class SlotRef:
    container: Container
    slot_index: int


@dataclasses.dataclass
class PlayerStorage:
    player_id: str
    at_home: bool = True
    _slots: dict[tuple[Container, int], StorageSlot] = (
        dataclasses.field(default_factory=dict, repr=False)
    )

    def _can_use(self, container: Container) -> bool:
        if container in HOME_ONLY and not self.at_home:
            return False
        return True

    def add(
        self, *,
        item_id: str, quantity: int = 1,
        container: Container = Container.INVENTORY,
    ) -> t.Optional[SlotRef]:
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if not self._can_use(container):
            return None
        cap = SLOT_LIMITS[container]
        for i in range(1, cap + 1):
            key = (container, i)
            if key not in self._slots:
                slot = StorageSlot(
                    container=container, slot_index=i,
                    item_id=item_id, quantity=quantity,
                )
                self._slots[key] = slot
                return SlotRef(container=container, slot_index=i)
        return None

    def move(
        self, *,
        from_ref: SlotRef,
        to_container: Container,
    ) -> bool:
        if not self._can_use(to_container):
            return False
        src = self._slots.get((from_ref.container, from_ref.slot_index))
        if src is None:
            return False
        cap = SLOT_LIMITS[to_container]
        # Find first free dest slot
        for i in range(1, cap + 1):
            key = (to_container, i)
            if key not in self._slots:
                src.container = to_container
                src.slot_index = i
                # Re-key
                del self._slots[
                    (from_ref.container, from_ref.slot_index)
                ]
                self._slots[key] = src
                return True
        return False

    def remove(
        self, *, slot_ref: SlotRef, quantity: int = 1,
    ) -> bool:
        slot = self._slots.get(
            (slot_ref.container, slot_ref.slot_index),
        )
        if slot is None:
            return False
        if quantity > slot.quantity:
            return False
        slot.quantity -= quantity
        if slot.quantity == 0:
            del self._slots[
                (slot_ref.container, slot_ref.slot_index)
            ]
        return True

    def total_count(self, item_id: str) -> int:
        return sum(
            s.quantity for s in self._slots.values()
            if s.item_id == item_id
        )

    def free_slots(self, container: Container) -> int:
        cap = SLOT_LIMITS[container]
        used = sum(
            1 for k in self._slots
            if k[0] == container
        )
        return cap - used

    def slots_in(self, container: Container) -> tuple[StorageSlot, ...]:
        return tuple(
            s for k, s in self._slots.items() if k[0] == container
        )


__all__ = [
    "Container", "SLOT_LIMITS", "HOME_ONLY",
    "StorageSlot", "SlotRef", "PlayerStorage",
]
