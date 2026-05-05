"""Tests for kraken ink market."""
from __future__ import annotations

from server.kraken_ink_market import (
    InkGear,
    InkLoot,
    KrakenInkMarket,
)


def test_first_restock_succeeds():
    m = KrakenInkMarket()
    assert m.restock(now_seconds=0) is True
    assert m.stock_remaining(gear=InkGear.INKBLOT_BAND) == 5


def test_double_restock_blocked_within_window():
    m = KrakenInkMarket()
    m.restock(now_seconds=0)
    # 1h later — still within 24h window
    assert m.restock(now_seconds=3_600) is False


def test_restock_after_window_succeeds():
    m = KrakenInkMarket()
    m.restock(now_seconds=0)
    # buy 1 to reduce stock
    m.purchase(
        player_id="p", gear=InkGear.INKBLOT_BAND,
        loot_inventory={
            InkLoot.ABYSSAL_FRAGMENT: 5,
            InkLoot.KRAKEN_INK: 5,
            InkLoot.HOLLOW_PEARL: 5,
        },
        gil_paid=15_000, now_seconds=10,
    )
    assert m.stock_remaining(gear=InkGear.INKBLOT_BAND) == 4
    # 25h later -> restock should reset to base
    assert m.restock(now_seconds=25 * 3_600) is True
    assert m.stock_remaining(gear=InkGear.INKBLOT_BAND) == 5


def test_purchase_happy():
    m = KrakenInkMarket()
    r = m.purchase(
        player_id="p",
        gear=InkGear.INKBLOT_BAND,
        loot_inventory={
            InkLoot.ABYSSAL_FRAGMENT: 5,
            InkLoot.KRAKEN_INK: 5,
            InkLoot.HOLLOW_PEARL: 5,
        },
        gil_paid=15_000,
        now_seconds=0,
    )
    assert r.accepted is True
    assert r.gear == InkGear.INKBLOT_BAND
    assert r.gil_consumed == 15_000
    assert r.loot_consumed[InkLoot.ABYSSAL_FRAGMENT] == 3


def test_purchase_insufficient_gil():
    m = KrakenInkMarket()
    r = m.purchase(
        player_id="p",
        gear=InkGear.INKBLOT_BAND,
        loot_inventory={
            InkLoot.ABYSSAL_FRAGMENT: 5,
            InkLoot.KRAKEN_INK: 5,
            InkLoot.HOLLOW_PEARL: 5,
        },
        gil_paid=10_000,
        now_seconds=0,
    )
    assert r.accepted is False
    assert r.reason == "insufficient gil"


def test_purchase_insufficient_loot():
    m = KrakenInkMarket()
    r = m.purchase(
        player_id="p",
        gear=InkGear.HOLLOW_TRIDENT,  # needs 10/4/2
        loot_inventory={
            InkLoot.ABYSSAL_FRAGMENT: 5,
            InkLoot.KRAKEN_INK: 1,
            InkLoot.HOLLOW_PEARL: 0,
        },
        gil_paid=300_000,
        now_seconds=0,
    )
    assert r.accepted is False
    assert r.reason == "insufficient loot"


def test_purchase_blank_player():
    m = KrakenInkMarket()
    r = m.purchase(
        player_id="",
        gear=InkGear.INKBLOT_BAND,
        loot_inventory={},
        gil_paid=15_000, now_seconds=0,
    )
    assert r.accepted is False


def test_purchase_decrements_stock():
    m = KrakenInkMarket()
    inv = {
        InkLoot.ABYSSAL_FRAGMENT: 100,
        InkLoot.KRAKEN_INK: 100,
        InkLoot.HOLLOW_PEARL: 100,
    }
    for _ in range(5):
        r = m.purchase(
            player_id="p", gear=InkGear.INKBLOT_BAND,
            loot_inventory=inv, gil_paid=15_000,
            now_seconds=0,
        )
        assert r.accepted is True
    # 6th fails — out of stock
    r = m.purchase(
        player_id="p", gear=InkGear.INKBLOT_BAND,
        loot_inventory=inv, gil_paid=15_000,
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "out of stock"


def test_recipe_for_lookup():
    r = KrakenInkMarket.recipe_for(gear=InkGear.HOLLOW_TRIDENT)
    assert r is not None
    assert r.gil_cost == 300_000
    assert r.pearls == 2


def test_auto_restock_on_purchase():
    m = KrakenInkMarket()
    # no manual restock — purchase at time 0 should trigger one
    r = m.purchase(
        player_id="p",
        gear=InkGear.INKBLOT_BAND,
        loot_inventory={
            InkLoot.ABYSSAL_FRAGMENT: 5,
            InkLoot.KRAKEN_INK: 5,
            InkLoot.HOLLOW_PEARL: 5,
        },
        gil_paid=15_000, now_seconds=0,
    )
    assert r.accepted is True


def test_stock_remaining_unknown_gear_zero():
    m = KrakenInkMarket()
    # before restock, no stock
    assert m.stock_remaining(gear=InkGear.HOLLOW_TRIDENT) == 0
