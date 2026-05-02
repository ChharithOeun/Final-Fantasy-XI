"""Mog Wardrobe — equipment-only inventory tabs.

Wardrobe slots only accept gear (weapons/armor/accessories). They
hold equipped items live and can be drawn from anywhere — unlike
Mog Safe / Storage which require returning to Mog House.

Default size: 30 slots per tab. Up to 4 wardrobe tabs unlock via
quests (each successive tab requires a higher level/title).

Public surface
--------------
    WardrobeId enum (WARDROBE_1 ... WARDROBE_4)
    Wardrobe (single tab)
    PlayerWardrobes
        .unlock(wardrobe_id, main_level) -> bool
        .deposit(wardrobe_id, item) -> bool
        .withdraw(wardrobe_id, item_id) -> Optional[Item]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


WARDROBE_TAB_SIZE = 30


class WardrobeId(str, enum.Enum):
    WARDROBE_1 = "wardrobe_1"
    WARDROBE_2 = "wardrobe_2"
    WARDROBE_3 = "wardrobe_3"
    WARDROBE_4 = "wardrobe_4"


# Unlock requirements per tab (canonical FFXI: tab 1 free,
# higher tabs gated by quests requiring main-job level).
_UNLOCK_MIN_LEVEL: dict[WardrobeId, int] = {
    WardrobeId.WARDROBE_1: 1,
    WardrobeId.WARDROBE_2: 30,
    WardrobeId.WARDROBE_3: 60,
    WardrobeId.WARDROBE_4: 90,
}


# Equipment categories the wardrobe will accept.
EQUIPMENT_CATEGORIES = frozenset({
    "weapon", "shield", "ammo", "head", "neck", "earring",
    "body", "hands", "ring", "back", "waist", "legs", "feet",
})


@dataclasses.dataclass(frozen=True)
class Item:
    item_id: str
    category: str   # one of EQUIPMENT_CATEGORIES (or other for safe)
    name: str = ""


@dataclasses.dataclass
class Wardrobe:
    wardrobe_id: WardrobeId
    unlocked: bool = False
    _slots: list[Item] = dataclasses.field(default_factory=list)

    @property
    def free_slots(self) -> int:
        return WARDROBE_TAB_SIZE - len(self._slots)

    @property
    def items(self) -> tuple[Item, ...]:
        return tuple(self._slots)

    def deposit(self, item: Item) -> bool:
        if not self.unlocked:
            return False
        if item.category not in EQUIPMENT_CATEGORIES:
            return False
        if self.free_slots <= 0:
            return False
        self._slots.append(item)
        return True

    def withdraw(self, item_id: str) -> t.Optional[Item]:
        for it in list(self._slots):
            if it.item_id == item_id:
                self._slots.remove(it)
                return it
        return None


@dataclasses.dataclass
class PlayerWardrobes:
    player_id: str
    _tabs: dict[WardrobeId, Wardrobe] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        for wid in WardrobeId:
            self._tabs[wid] = Wardrobe(wardrobe_id=wid)
        # Wardrobe 1 is unlocked by default.
        self._tabs[WardrobeId.WARDROBE_1].unlocked = True

    def unlock(self, *, wardrobe_id: WardrobeId, main_level: int) -> bool:
        tab = self._tabs[wardrobe_id]
        if tab.unlocked:
            return False
        required = _UNLOCK_MIN_LEVEL[wardrobe_id]
        if main_level < required:
            return False
        tab.unlocked = True
        return True

    def is_unlocked(self, wardrobe_id: WardrobeId) -> bool:
        return self._tabs[wardrobe_id].unlocked

    def deposit(self, *, wardrobe_id: WardrobeId, item: Item) -> bool:
        return self._tabs[wardrobe_id].deposit(item)

    def withdraw(self, *, wardrobe_id: WardrobeId,
                 item_id: str) -> t.Optional[Item]:
        return self._tabs[wardrobe_id].withdraw(item_id)

    def total_unlocked_capacity(self) -> int:
        return sum(
            WARDROBE_TAB_SIZE
            for tab in self._tabs.values()
            if tab.unlocked
        )

    def total_used_slots(self) -> int:
        return sum(
            len(tab.items)
            for tab in self._tabs.values()
        )


__all__ = [
    "WARDROBE_TAB_SIZE",
    "WardrobeId",
    "EQUIPMENT_CATEGORIES",
    "Item",
    "Wardrobe",
    "PlayerWardrobes",
]
