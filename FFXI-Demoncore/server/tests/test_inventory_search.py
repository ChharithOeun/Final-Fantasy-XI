"""Tests for inventory search."""
from __future__ import annotations

from server.inventory_search import (
    InventorySearch,
    ItemType,
    StorageTab,
)


def _seed(s: InventorySearch):
    s.upsert_item(
        player_id="alice", tab=StorageTab.INVENTORY,
        item_id="moonbow", label="Moonbow",
        item_type=ItemType.WEAPON,
        level=75,
        stats={"STR": 5, "ATTACK": 30},
        qty=1,
    )
    s.upsert_item(
        player_id="alice", tab=StorageTab.SAFE,
        item_id="iron_helm", label="Iron Helm",
        item_type=ItemType.ARMOR,
        level=20,
        stats={"DEFENSE": 15},
        qty=1,
    )
    s.upsert_item(
        player_id="alice", tab=StorageTab.SATCHEL,
        item_id="hi_potion", label="Hi-Potion",
        item_type=ItemType.CONSUMABLE,
        level=1,
        stats={},
        qty=12,
    )
    s.upsert_item(
        player_id="bob", tab=StorageTab.INVENTORY,
        item_id="iron_helm", label="Iron Helm",
        item_type=ItemType.ARMOR,
        level=20,
        stats={"DEFENSE": 15},
        qty=1,
    )


def test_upsert_records_item():
    s = InventorySearch()
    _seed(s)
    assert s.total_holdings(player_id="alice") == 3


def test_upsert_zero_qty_rejected():
    s = InventorySearch()
    assert not s.upsert_item(
        player_id="alice", tab=StorageTab.INVENTORY,
        item_id="x", label="X",
        item_type=ItemType.OTHER,
        qty=0,
    )


def test_upsert_empty_id_rejected():
    s = InventorySearch()
    assert not s.upsert_item(
        player_id="alice", tab=StorageTab.INVENTORY,
        item_id="", label="X",
        item_type=ItemType.OTHER,
    )


def test_remove_item():
    s = InventorySearch()
    _seed(s)
    assert s.remove_item(
        player_id="alice", tab=StorageTab.INVENTORY,
        item_id="moonbow",
    )
    assert s.total_holdings(player_id="alice") == 2


def test_remove_unknown():
    s = InventorySearch()
    assert not s.remove_item(
        player_id="alice", tab=StorageTab.INVENTORY,
        item_id="ghost",
    )


def test_search_substring():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice", query="moon",
    )
    ids = {h.item_id for h in hits}
    assert "moonbow" in ids


def test_search_isolates_player():
    s = InventorySearch()
    _seed(s)
    hits = s.search(player_id="alice")
    assert all(h.player_id == "alice" for h in hits)


def test_search_filter_tab():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice",
        tabs=(StorageTab.SAFE,),
    )
    assert {h.item_id for h in hits} == {"iron_helm"}


def test_search_filter_type():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice",
        item_type=ItemType.CONSUMABLE,
    )
    assert {h.item_id for h in hits} == {"hi_potion"}


def test_search_min_level():
    s = InventorySearch()
    _seed(s)
    hits = s.search(player_id="alice", min_level=70)
    assert {h.item_id for h in hits} == {"moonbow"}


def test_search_max_level():
    s = InventorySearch()
    _seed(s)
    hits = s.search(player_id="alice", max_level=10)
    assert {h.item_id for h in hits} == {"hi_potion"}


def test_search_stat_threshold():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice",
        stat_threshold={"DEFENSE": 10},
    )
    assert {h.item_id for h in hits} == {"iron_helm"}


def test_search_stat_threshold_excludes_missing():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice",
        stat_threshold={"STR": 1},
    )
    assert {h.item_id for h in hits} == {"moonbow"}


def test_search_combined_filters():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice",
        item_type=ItemType.WEAPON,
        min_level=50,
        stat_threshold={"ATTACK": 20},
    )
    assert {h.item_id for h in hits} == {"moonbow"}


def test_search_max_results_cap():
    s = InventorySearch()
    for i in range(10):
        s.upsert_item(
            player_id="alice", tab=StorageTab.STORAGE,
            item_id=f"item_{i}", label=f"item {i}",
            item_type=ItemType.MATERIAL,
        )
    hits = s.search(
        player_id="alice", max_results=3,
    )
    assert len(hits) == 3


def test_clear_player():
    s = InventorySearch()
    _seed(s)
    n = s.clear_player(player_id="alice")
    assert n == 3
    assert s.total_holdings(player_id="alice") == 0


def test_search_empty_query_returns_filtered_all():
    s = InventorySearch()
    _seed(s)
    hits = s.search(player_id="alice")
    assert len(hits) == 3


def test_search_deterministic_order():
    s = InventorySearch()
    _seed(s)
    h1 = s.search(player_id="alice")
    h2 = s.search(player_id="alice")
    assert [h.item_id for h in h1] == [
        h.item_id for h in h2
    ]


def test_search_sorts_by_tab_then_item():
    s = InventorySearch()
    _seed(s)
    hits = s.search(player_id="alice")
    tabs = [h.tab.value for h in hits]
    # alphabetical-ish order by tab name; sorted increasing
    assert tabs == sorted(tabs)


def test_qty_preserved():
    s = InventorySearch()
    _seed(s)
    hits = s.search(
        player_id="alice", query="hi-potion",
    )
    assert hits[0].qty == 12


def test_total_holdings_empty():
    s = InventorySearch()
    assert s.total_holdings(player_id="ghost") == 0
