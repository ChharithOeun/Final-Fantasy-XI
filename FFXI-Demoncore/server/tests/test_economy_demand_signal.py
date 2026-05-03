"""Tests for the economy demand signal."""
from __future__ import annotations

import pytest

from server.economy_demand_signal import (
    DEFAULT_WINDOW_SECONDS,
    DemandKind,
    EconomyDemandTracker,
)


def test_default_window_is_one_hour():
    assert DEFAULT_WINDOW_SECONDS == 3600.0


def test_record_zero_or_negative_rejected():
    t = EconomyDemandTracker()
    with pytest.raises(ValueError):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            count=0, now_seconds=0.0,
        )
    with pytest.raises(ValueError):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            count=-3, now_seconds=0.0,
        )


def test_signal_for_unknown_item_zero():
    t = EconomyDemandTracker()
    sig = t.signal_for(item_id="ghost", now_seconds=0.0)
    assert sig.rate_per_hour == 0.0
    assert sig.sample_event_count == 0


def test_signal_rate_per_hour_within_window():
    t = EconomyDemandTracker(window_seconds=3600.0)
    # 10 purchases within last hour
    for i in range(10):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            count=1, now_seconds=float(i * 60),
        )
    sig = t.signal_for(item_id="iron_ore", now_seconds=3600.0)
    assert sig.rate_per_hour == 10.0


def test_signal_count_aggregates():
    t = EconomyDemandTracker(window_seconds=3600.0)
    t.record(
        item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
        count=5, now_seconds=100.0,
    )
    t.record(
        item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
        count=15, now_seconds=200.0,
    )
    sig = t.signal_for(item_id="iron_ore", now_seconds=3600.0)
    assert sig.rate_per_hour == 20.0


def test_signal_trend_growing():
    t = EconomyDemandTracker(window_seconds=3600.0)
    # Previous window: 5 events
    for i in range(5):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(i * 60),   # 0..240
        )
    # Current window: 15 events
    for i in range(15):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(3700 + i * 60),  # well into 2nd hour
        )
    sig = t.signal_for(item_id="iron_ore", now_seconds=7200.0)
    assert sig.rate_per_hour == 15.0
    # +200% trend (5 -> 15)
    assert sig.trend_pct == pytest.approx(200.0, abs=0.01)


def test_signal_trend_shrinking():
    t = EconomyDemandTracker(window_seconds=3600.0)
    # Previous window: 20 events
    for i in range(20):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(i * 60),
        )
    # Current window: 5 events
    for i in range(5):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(3700 + i * 60),
        )
    sig = t.signal_for(item_id="iron_ore", now_seconds=7200.0)
    # -75% trend (20 -> 5)
    assert sig.trend_pct == pytest.approx(-75.0, abs=0.01)


def test_signal_trend_zero_when_no_prior_data():
    """First-time demand spike — no prior events, rate is positive,
    trend reports 100% (came from nothing)."""
    t = EconomyDemandTracker()
    t.record(
        item_id="new_item", kind=DemandKind.PURCHASE_NPC,
        count=10, now_seconds=0.0,
    )
    sig = t.signal_for(item_id="new_item", now_seconds=0.0)
    assert sig.trend_pct == 100.0


def test_signal_by_kind_breaks_down_demand():
    t = EconomyDemandTracker()
    t.record(
        item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
        count=10, now_seconds=0.0,
    )
    t.record(
        item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
        count=20, now_seconds=0.0,
    )
    t.record(
        item_id="iron_ore", kind=DemandKind.QUEST_TURN_IN,
        count=5, now_seconds=0.0,
    )
    sig = t.signal_for(item_id="iron_ore", now_seconds=0.0)
    assert sig.by_kind[DemandKind.PURCHASE_NPC] == 10
    assert sig.by_kind[DemandKind.CRAFT_CONSUMED] == 20
    assert sig.by_kind[DemandKind.QUEST_TURN_IN] == 5


def test_old_events_drop_out_of_window():
    t = EconomyDemandTracker(window_seconds=3600.0)
    # Way old event
    t.record(
        item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
        now_seconds=0.0,
    )
    # Now ask 3 hours later
    sig = t.signal_for(item_id="iron_ore", now_seconds=10800.0)
    # Old event was outside even the 2x window so it was trimmed
    # OR it's outside both current and previous windows
    assert sig.rate_per_hour == 0.0


def test_top_demanded_ranks_by_rate():
    t = EconomyDemandTracker()
    for _ in range(5):
        t.record(
            item_id="cotton", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    for _ in range(20):
        t.record(
            item_id="iron_ore", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    for _ in range(10):
        t.record(
            item_id="oak_lumber", kind=DemandKind.CRAFT_CONSUMED,
            now_seconds=100.0,
        )
    top = t.top_demanded(top_n=3, now_seconds=200.0)
    ids_in_order = [s.item_id for s in top]
    assert ids_in_order == ["iron_ore", "oak_lumber", "cotton"]


def test_top_demanded_top_n_caps():
    t = EconomyDemandTracker()
    for i in range(5):
        t.record(
            item_id=f"item_{i}",
            kind=DemandKind.PURCHASE_NPC, now_seconds=100.0,
        )
    top = t.top_demanded(top_n=2, now_seconds=200.0)
    assert len(top) == 2


def test_compact_old_drops_events():
    t = EconomyDemandTracker(window_seconds=100.0)
    for i in range(10):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(i * 50),
        )
    dropped = t.compact_old(
        now_seconds=10000.0, max_age_seconds=100.0,
    )
    assert dropped >= 5


def test_full_lifecycle_iron_ore_demand_explodes():
    """Iron ore demand starts low, then explodes with a big AH
    rush. The trend signal flags the spike."""
    t = EconomyDemandTracker(window_seconds=3600.0)
    # Slow first hour
    for i in range(5):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_NPC,
            now_seconds=float(i * 600),
        )
    # Big spike second hour
    for i in range(50):
        t.record(
            item_id="iron_ore", kind=DemandKind.PURCHASE_AH,
            now_seconds=float(3700 + i * 60),
        )
    sig = t.signal_for(item_id="iron_ore", now_seconds=7200.0)
    assert sig.rate_per_hour == 50.0
    assert sig.trend_pct >= 500.0  # ~10x growth
    assert sig.by_kind[DemandKind.PURCHASE_AH] == 50
