"""Gear slot filter — what items can go in what slot.

The 16 canonical FFXI equipment slots:

    main, sub, ranged, ammo,
    head, neck, ear1, ear2,
    body, hands, ring1, ring2,
    back, waist, legs, feet

Plus the per-item bag binding (wardrobe1..wardrobe8 +
mog satchel/sack/case/inventory). The filter answers
"which items in the player's gear pool can legally go
in slot X?" — feeding the autocomplete dropdown a
correctly-restricted candidate list.

Each item declares its slot_compatibility (set of slots
it fits) and bag_id (where the item lives in storage).
A two-handed weapon fits 'main' but locks 'sub' to empty;
a shield fits 'sub' only when not dual-wielding; etc.

The Edge Case Tax is real here, so the filter is data-
driven: callers register items with their compatibility
declared, and the filter just looks them up.

Public surface
--------------
    Slot enum (the 16 canonical slots)
    GearItem dataclass (frozen)
    GearSlotFilter
        .register_item(item) -> bool
        .candidates_for_slot(slot, owned_only,
                              owner_id) -> list[GearItem]
        .can_equip(item_id, slot) -> bool
        .item_lookup(item_id) -> Optional[GearItem]
        .grant_to_owner(owner_id, item_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Slot(str, enum.Enum):
    MAIN = "main"
    SUB = "sub"
    RANGED = "ranged"
    AMMO = "ammo"
    HEAD = "head"
    NECK = "neck"
    EAR1 = "ear1"
    EAR2 = "ear2"
    BODY = "body"
    HANDS = "hands"
    RING1 = "ring1"
    RING2 = "ring2"
    BACK = "back"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"


@dataclasses.dataclass(frozen=True)
class GearItem:
    item_id: str
    display_name: str
    slot_compatibility: tuple[Slot, ...]
    is_two_handed: bool = False
    default_bag: str = "wardrobe1"


@dataclasses.dataclass
class GearSlotFilter:
    _items: dict[str, GearItem] = dataclasses.field(
        default_factory=dict,
    )
    # owner_id → set of item_ids the owner has
    _ownership: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_item(self, *, item: GearItem) -> bool:
        if not item.item_id or not item.display_name:
            return False
        if item.item_id in self._items:
            return False
        if not item.slot_compatibility:
            # an item that fits no slot is meaningless
            return False
        self._items[item.item_id] = item
        return True

    def can_equip(
        self, *, item_id: str, slot: Slot,
    ) -> bool:
        item = self._items.get(item_id)
        if item is None:
            return False
        return slot in item.slot_compatibility

    def item_lookup(
        self, *, item_id: str,
    ) -> t.Optional[GearItem]:
        return self._items.get(item_id)

    def grant_to_owner(
        self, *, owner_id: str, item_id: str,
    ) -> bool:
        if not owner_id or item_id not in self._items:
            return False
        s = self._ownership.setdefault(owner_id, set())
        if item_id in s:
            return False
        s.add(item_id)
        return True

    def revoke_from_owner(
        self, *, owner_id: str, item_id: str,
    ) -> bool:
        s = self._ownership.get(owner_id)
        if s is None or item_id not in s:
            return False
        s.discard(item_id)
        return True

    def candidates_for_slot(
        self, *, slot: Slot,
        owned_only: bool = False,
        owner_id: str = "",
    ) -> list[GearItem]:
        """Items that fit a slot.

        If owned_only=True, restrict to items granted to
        owner_id. The autocomplete dropdown shows EVERY
        candidate when the player is filling a hypothetical
        spec, but flips to owned_only when previewing
        what's actually wearable right now.
        """
        out: list[GearItem] = []
        if owned_only:
            owned = self._ownership.get(owner_id, set())
            for item_id in owned:
                item = self._items.get(item_id)
                if item is None:
                    continue
                if slot in item.slot_compatibility:
                    out.append(item)
        else:
            for item in self._items.values():
                if slot in item.slot_compatibility:
                    out.append(item)
        # stable ordering by display_name for UI
        out.sort(key=lambda i: i.display_name)
        return out

    def total_items(self) -> int:
        return len(self._items)

    def total_owned(self, *, owner_id: str) -> int:
        return len(self._ownership.get(owner_id, set()))


__all__ = [
    "Slot", "GearItem", "GearSlotFilter",
]
