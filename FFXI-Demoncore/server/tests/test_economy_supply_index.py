"""Tests for the economy supply index."""
from __future__ import annotations

import pytest

from server.economy_supply_index import (
    DEFAULT_HISTORY_SECONDS,
    EconomySupplyIndex,
    SupplySource,
)


def test_publish_and_total():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.AH_LISTING,
        count=50, now_seconds=0.0,
    )
    assert idx.total("iron_ore") == 150


def test_negative_count_rejected():
    idx = EconomySupplyIndex()
    with pytest.raises(ValueError):
        idx.publish(
            item_id="iron_ore",
            source=SupplySource.PLAYER_INVENTORY,
            count=-5, now_seconds=0.0,
        )


def test_publish_overwrites_same_source():
    """Re-publishing for (item, source) replaces, doesn't add."""
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=80, now_seconds=10.0,
    )
    assert idx.total("iron_ore") == 80


def test_by_source_breaks_down_total():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.AH_LISTING,
        count=50, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.NPC_VENDOR_STOCK,
        count=25, now_seconds=0.0,
    )
    breakdown = idx.by_source("iron_ore")
    assert breakdown[SupplySource.PLAYER_INVENTORY] == 100
    assert breakdown[SupplySource.AH_LISTING] == 50
    assert breakdown[SupplySource.NPC_VENDOR_STOCK] == 25


def test_trend_pct_positive_when_growing():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=3600.0,
    )
    trend = idx.trend_pct(item_id="iron_ore", now_seconds=3600.0)
    assert trend == pytest.approx(100.0, abs=0.01)


def test_trend_pct_negative_when_shrinking():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=3600.0,
    )
    trend = idx.trend_pct(item_id="iron_ore", now_seconds=3600.0)
    assert trend == pytest.approx(-50.0, abs=0.01)


def test_trend_pct_zero_when_insufficient_data():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    assert idx.trend_pct(
        item_id="iron_ore", now_seconds=0.0,
    ) == 0.0


def test_trend_pct_handles_zero_baseline():
    """When the oldest snapshot was 0 supply, trend reports 100%
    growth if current is positive."""
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=0, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=50, now_seconds=3600.0,
    )
    assert idx.trend_pct(
        item_id="iron_ore", now_seconds=3600.0,
    ) == 100.0


def test_history_window_drops_old_points():
    idx = EconomySupplyIndex(history_seconds=100)
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=200.0,
    )
    snap = idx.snapshot_at(
        item_id="iron_ore", now_seconds=200.0,
    )
    # First snapshot at t=0 should have been pruned (older than 100s)
    assert snap.sample_count == 1


def test_snapshot_packages_full_state():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="iron_ore", source=SupplySource.AH_LISTING,
        count=50, now_seconds=0.0,
    )
    snap = idx.snapshot_at(item_id="iron_ore", now_seconds=0.0)
    assert snap.total_count == 150
    assert snap.by_source[SupplySource.PLAYER_INVENTORY] == 100


def test_all_items_lists_published():
    idx = EconomySupplyIndex()
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=100, now_seconds=0.0,
    )
    idx.publish(
        item_id="cotton", source=SupplySource.PLAYER_INVENTORY,
        count=50, now_seconds=0.0,
    )
    items = set(idx.all_items())
    assert items == {"iron_ore", "cotton"}


def test_compact_old_drops_history():
    idx = EconomySupplyIndex(history_seconds=10000)
    for i in range(5):
        idx.publish(
            item_id="iron_ore",
            source=SupplySource.PLAYER_INVENTORY,
            count=100 + i, now_seconds=float(i * 100),
        )
    dropped = idx.compact_old(
        now_seconds=10000, max_age_seconds=300,
    )
    # First two points are older than 300s ago
    assert dropped >= 1


def test_default_history_is_one_day():
    assert DEFAULT_HISTORY_SECONDS == 60 * 60 * 24


def test_full_lifecycle_iron_ore_demand_spike():
    """Iron ore supply ramps up, then collapses as demand hits.
    Trend reflects the drop."""
    idx = EconomySupplyIndex()
    # Day 1: 200 ore in player inventories
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=200, now_seconds=0.0,
    )
    # Day 2: another caravan adds 50
    idx.publish(
        item_id="iron_ore", source=SupplySource.CARAVAN_IN_TRANSIT,
        count=50, now_seconds=3600.0,
    )
    # Day 3: crafting consumed 150
    idx.publish(
        item_id="iron_ore", source=SupplySource.PLAYER_INVENTORY,
        count=50, now_seconds=7200.0,
    )
    snap = idx.snapshot_at(
        item_id="iron_ore", now_seconds=7200.0,
    )
    assert snap.total_count == 100   # 50 inventory + 50 caravan
    assert snap.trend_pct < 0       # supply collapsed from peak
