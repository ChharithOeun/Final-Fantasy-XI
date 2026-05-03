"""Mog House furnishings — decoration with stat bonuses.

Players install furniture in their Mog House. Each piece:
* takes one floor or wall slot (per-room limits)
* provides a stat bonus that activates when the player is logged
  in (canonical FFXI behavior — leaving the area expires the
  passive)
* grants a small chance of moogle assistance (e.g. discounted
  vendor prices, faster home-point recall)

Furniture types (sample):
    storage      — extra Mog Safe slots
    mp_regen     — passive MP/tick while in Mog House
    status_res   — random status-resist bonus
    crafting     — bonus to a specific craft skill
    cosmetic     — pure decoration, no stat

Public surface
--------------
    FurnitureKind enum
    FurnitureItem dataclass / FURNITURE_CATALOG
    MogRoom (player's Mog House)
        .install(item_id) / .remove(slot)
        .aggregate_bonuses() -> dict[str, int]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Slot caps per Mog House room (canonical FFXI: 70 floor, 30 wall)
FLOOR_SLOTS = 70
WALL_SLOTS = 30


class FurnitureKind(str, enum.Enum):
    STORAGE = "storage"
    MP_REGEN = "mp_regen"
    STATUS_RES = "status_res"
    CRAFTING = "crafting"
    COSMETIC = "cosmetic"


class SlotKind(str, enum.Enum):
    FLOOR = "floor"
    WALL = "wall"


@dataclasses.dataclass(frozen=True)
class FurnitureItem:
    item_id: str
    label: str
    kind: FurnitureKind
    slot_kind: SlotKind
    stat_bonuses: tuple[tuple[str, int], ...]  # ("storage_slots", 5)
    moogle_assist: bool = False


FURNITURE_CATALOG: dict[str, FurnitureItem] = {
    # Storage furniture
    "mog_chest": FurnitureItem(
        "mog_chest", "Mog Chest", FurnitureKind.STORAGE,
        SlotKind.FLOOR, stat_bonuses=(("storage_slots", 5),),
    ),
    "mog_armoire": FurnitureItem(
        "mog_armoire", "Mog Armoire", FurnitureKind.STORAGE,
        SlotKind.FLOOR, stat_bonuses=(("storage_slots", 8),),
    ),
    # MP regen furniture (canonical FFXI bookshelf etc.)
    "tarutaru_bookshelf": FurnitureItem(
        "tarutaru_bookshelf", "Tarutaru Bookshelf",
        FurnitureKind.MP_REGEN, SlotKind.FLOOR,
        stat_bonuses=(("mp_per_tick", 1),),
    ),
    "ornate_bookshelf": FurnitureItem(
        "ornate_bookshelf", "Ornate Bookshelf",
        FurnitureKind.MP_REGEN, SlotKind.FLOOR,
        stat_bonuses=(("mp_per_tick", 2),),
        moogle_assist=True,
    ),
    # Status-resist
    "anti_silence_charm": FurnitureItem(
        "anti_silence_charm", "Anti-Silence Wall Charm",
        FurnitureKind.STATUS_RES, SlotKind.WALL,
        stat_bonuses=(("silence_resist", 5),),
    ),
    "anti_petrify_statue": FurnitureItem(
        "anti_petrify_statue", "Anti-Petrify Statue",
        FurnitureKind.STATUS_RES, SlotKind.FLOOR,
        stat_bonuses=(("petrify_resist", 5),),
    ),
    # Crafting bonuses
    "smithing_bench": FurnitureItem(
        "smithing_bench", "Smithing Bench", FurnitureKind.CRAFTING,
        SlotKind.FLOOR, stat_bonuses=(("smithing_skill", 3),),
    ),
    "alchemy_lab": FurnitureItem(
        "alchemy_lab", "Alchemy Lab", FurnitureKind.CRAFTING,
        SlotKind.FLOOR, stat_bonuses=(("alchemy_skill", 3),),
        moogle_assist=True,
    ),
    # Cosmetic (no stats)
    "wedding_cake_diorama": FurnitureItem(
        "wedding_cake_diorama", "Wedding Cake Diorama",
        FurnitureKind.COSMETIC, SlotKind.FLOOR, stat_bonuses=(),
    ),
    "festival_banner": FurnitureItem(
        "festival_banner", "Festival Banner",
        FurnitureKind.COSMETIC, SlotKind.WALL, stat_bonuses=(),
    ),
}


@dataclasses.dataclass(frozen=True)
class InstallResult:
    accepted: bool
    slot_index: int = -1
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MogRoom:
    player_id: str
    floor_items: list[str] = dataclasses.field(default_factory=list)
    wall_items: list[str] = dataclasses.field(default_factory=list)

    def install(self, *, item_id: str) -> InstallResult:
        item = FURNITURE_CATALOG.get(item_id)
        if item is None:
            return InstallResult(False, reason="unknown furniture")
        if item.slot_kind == SlotKind.FLOOR:
            if len(self.floor_items) >= FLOOR_SLOTS:
                return InstallResult(False, reason="floor full")
            self.floor_items.append(item_id)
            return InstallResult(True, slot_index=len(self.floor_items) - 1)
        # WALL
        if len(self.wall_items) >= WALL_SLOTS:
            return InstallResult(False, reason="wall full")
        self.wall_items.append(item_id)
        return InstallResult(True, slot_index=len(self.wall_items) - 1)

    def remove(self, *, slot_kind: SlotKind, slot_index: int) -> bool:
        target = self.floor_items if slot_kind == SlotKind.FLOOR \
            else self.wall_items
        if slot_index < 0 or slot_index >= len(target):
            return False
        target.pop(slot_index)
        return True

    def aggregate_bonuses(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for item_id in self.floor_items + self.wall_items:
            item = FURNITURE_CATALOG.get(item_id)
            if item is None:
                continue
            for stat, val in item.stat_bonuses:
                out[stat] = out.get(stat, 0) + val
        return out

    def has_moogle_assist(self) -> bool:
        for item_id in self.floor_items + self.wall_items:
            item = FURNITURE_CATALOG.get(item_id)
            if item is not None and item.moogle_assist:
                return True
        return False


__all__ = [
    "FLOOR_SLOTS", "WALL_SLOTS",
    "FurnitureKind", "SlotKind",
    "FurnitureItem", "FURNITURE_CATALOG",
    "InstallResult", "MogRoom",
]
