"""Inventory search — search & filter across all storage tabs.

Players carry items across many tabs in retail FFXI: INVENTORY,
SAFE, SAFE2, STORAGE, LOCKER, SATCHEL, SACK, CASE, WARDROBE,
WARDROBE2..8. Searching across all of them was historically a
chore. This module indexes a player's holdings across every tab
and answers structured queries:

  * substring on item label
  * filter by tab
  * filter by item type (WEAPON / ARMOR / CONSUMABLE / MATERIAL /
    KEYITEM / GIL_BAG)
  * filter by min_level
  * filter by stat threshold (e.g. STR >= 10)

Public surface
--------------
    StorageTab enum
    ItemType enum
    StackedItem dataclass
    SearchHit dataclass
    InventorySearch
        .upsert_item(player_id, tab, item_id, label, type, level,
                     stats, qty)
        .remove_item(player_id, tab, item_id)
        .search(player_id, query, ...) -> tuple[SearchHit]
        .clear_player(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class StorageTab(str, enum.Enum):
    INVENTORY = "inventory"
    SAFE = "safe"
    SAFE2 = "safe2"
    STORAGE = "storage"
    LOCKER = "locker"
    SATCHEL = "satchel"
    SACK = "sack"
    CASE = "case"
    WARDROBE = "wardrobe"
    WARDROBE2 = "wardrobe2"
    WARDROBE3 = "wardrobe3"
    WARDROBE4 = "wardrobe4"


class ItemType(str, enum.Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    KEYITEM = "keyitem"
    GIL_BAG = "gil_bag"
    OTHER = "other"


@dataclasses.dataclass
class StackedItem:
    item_id: str
    label: str
    item_type: ItemType
    level: int
    stats: dict[str, int]
    qty: int


@dataclasses.dataclass(frozen=True)
class SearchHit:
    player_id: str
    tab: StorageTab
    item_id: str
    label: str
    item_type: ItemType
    level: int
    qty: int
    stats: dict[str, int]


@dataclasses.dataclass
class InventorySearch:
    # (player_id, tab, item_id) -> StackedItem
    _items: dict[
        tuple[str, StorageTab, str], StackedItem,
    ] = dataclasses.field(default_factory=dict)

    def upsert_item(
        self, *, player_id: str, tab: StorageTab,
        item_id: str, label: str,
        item_type: ItemType,
        level: int = 1,
        stats: t.Mapping[str, int] = (),
        qty: int = 1,
    ) -> bool:
        if not item_id or qty <= 0:
            return False
        key = (player_id, tab, item_id)
        self._items[key] = StackedItem(
            item_id=item_id, label=label,
            item_type=item_type, level=level,
            stats=dict(stats), qty=qty,
        )
        return True

    def remove_item(
        self, *, player_id: str, tab: StorageTab,
        item_id: str,
    ) -> bool:
        return self._items.pop(
            (player_id, tab, item_id), None,
        ) is not None

    def search(
        self, *, player_id: str,
        query: str = "",
        tabs: t.Optional[tuple[StorageTab, ...]] = None,
        item_type: t.Optional[ItemType] = None,
        min_level: t.Optional[int] = None,
        max_level: t.Optional[int] = None,
        stat_threshold: t.Optional[
            t.Mapping[str, int]
        ] = None,
        max_results: int = 200,
    ) -> tuple[SearchHit, ...]:
        q = query.lower() if query else ""
        out: list[SearchHit] = []
        for (pid, tab, item_id), item in self._items.items():
            if pid != player_id:
                continue
            if tabs is not None and tab not in tabs:
                continue
            if item_type is not None and item.item_type != item_type:
                continue
            if (
                min_level is not None
                and item.level < min_level
            ):
                continue
            if (
                max_level is not None
                and item.level > max_level
            ):
                continue
            if (
                stat_threshold is not None
                and not _stat_threshold_passes(
                    item.stats, stat_threshold,
                )
            ):
                continue
            if q and q not in item.label.lower():
                continue
            out.append(SearchHit(
                player_id=player_id, tab=tab,
                item_id=item.item_id, label=item.label,
                item_type=item.item_type,
                level=item.level, qty=item.qty,
                stats=dict(item.stats),
            ))
        # Deterministic order: tab, then item_id
        out.sort(
            key=lambda h: (h.tab.value, h.item_id),
        )
        return tuple(out[:max_results])

    def clear_player(
        self, *, player_id: str,
    ) -> int:
        keys = [
            k for k in self._items
            if k[0] == player_id
        ]
        for k in keys:
            del self._items[k]
        return len(keys)

    def total_holdings(
        self, *, player_id: str,
    ) -> int:
        return sum(
            1 for k in self._items
            if k[0] == player_id
        )


def _stat_threshold_passes(
    item_stats: dict[str, int],
    threshold: t.Mapping[str, int],
) -> bool:
    for k, v in threshold.items():
        if item_stats.get(k, 0) < v:
            return False
    return True


__all__ = [
    "StorageTab", "ItemType",
    "StackedItem", "SearchHit",
    "InventorySearch",
]
