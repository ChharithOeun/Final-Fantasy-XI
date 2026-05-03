"""Tests for NPC economy / merchant pricing."""
from __future__ import annotations

from server.faction_reputation import ReputationBand
from server.npc_economy import (
    MerchantRegistry,
    QuoteOutcome,
)


def _stocked_merchant() -> MerchantRegistry:
    reg = MerchantRegistry()
    inv = reg.register_merchant(
        npc_id="dabihook", home_settlement_id="bastok",
        feeder_route_ids=("bastok_jeuno_caravan",),
    )
    inv.add_item(
        item_id="potion", base_price=100,
        desired_stock=100, initial_stock=50,
    )
    return reg


def test_register_and_stock_merchant():
    reg = _stocked_merchant()
    assert reg.total_merchants() == 1
    assert reg.merchant("dabihook").total_items() == 1


def test_unknown_merchant_quote_refused():
    reg = MerchantRegistry()
    res = reg.quote_buy(
        npc_id="ghost", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    assert res.outcome == QuoteOutcome.REFUSED


def test_unknown_item_quote_refused():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="phantom_item",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    assert res.outcome == QuoteOutcome.REFUSED


def test_hostile_band_refused():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.HOSTILE,
    )
    assert res.outcome == QuoteOutcome.REFUSED
    assert "refuse" in res.reason


def test_kos_band_refused():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.KILL_ON_SIGHT,
    )
    assert res.outcome == QuoteOutcome.REFUSED


def test_neutral_buy_at_base_price():
    """Stock = 50, desired = 100 -> 50% ratio (normal). No raid
    pressure. Neutral rep. Should be exactly base price."""
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    assert res.outcome == QuoteOutcome.ACCEPTED
    assert res.quote.final_price == 100


def test_friendly_discount():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.FRIENDLY,
    )
    # 100 * 0.9 = 90
    assert res.quote.final_price == 90


def test_hero_band_steepest_discount():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.HERO_OF_THE_FACTION,
    )
    # 100 * 0.7 = 70
    assert res.quote.final_price == 70


def test_unfriendly_pays_extra():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.UNFRIENDLY,
    )
    # 100 * 1.25 = 125
    assert res.quote.final_price == 125


def test_low_stock_surcharge():
    reg = _stocked_merchant()
    # Drop stock to 10/100 (< 25%)
    reg.merchant("dabihook").ledger("potion").stock_count = 10
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    # 100 * 1.5 (scarcity) = 150
    assert res.quote.final_price == 150
    assert res.quote.supply_multiplier == 1.5


def test_overstock_discount():
    reg = _stocked_merchant()
    # Bump stock to 90/100 (> 75%)
    reg.merchant("dabihook").ledger("potion").stock_count = 90
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    # 100 * 0.85 = 85
    assert res.quote.final_price == 85


def test_raid_pressure_high_marks_up():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
        route_pressure=80,
    )
    # 100 * 1.0 (supply) * 1.0 (rep) * 1.3 (raid) = 130
    assert res.quote.final_price == 130


def test_raid_pressure_medium_marks_up_modestly():
    reg = _stocked_merchant()
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
        route_pressure=45,
    )
    # 100 * 1.15 = 115
    assert res.quote.final_price == 115


def test_out_of_stock_refused():
    reg = _stocked_merchant()
    reg.merchant("dabihook").ledger("potion").stock_count = 0
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    assert res.outcome == QuoteOutcome.REFUSED
    assert "out of stock" in res.reason


def test_record_sale_decrements_stock():
    reg = _stocked_merchant()
    assert reg.record_sale(
        npc_id="dabihook", item_id="potion", units=3,
    )
    led = reg.merchant("dabihook").ledger("potion")
    assert led.stock_count == 47
    assert led.units_sold == 3


def test_record_sale_more_than_stock_rejected():
    reg = _stocked_merchant()
    reg.merchant("dabihook").ledger("potion").stock_count = 5
    assert not reg.record_sale(
        npc_id="dabihook", item_id="potion", units=10,
    )


def test_stock_from_caravan_increments_inventory():
    reg = _stocked_merchant()
    assert reg.stock(
        npc_id="dabihook", item_id="potion", count=30,
    )
    led = reg.merchant("dabihook").ledger("potion")
    assert led.stock_count == 80


def test_quote_sell_basic():
    reg = _stocked_merchant()
    res = reg.quote_sell(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    assert res.outcome == QuoteOutcome.ACCEPTED
    # Neutral rep: 0.5 + (1.0 - 1.0) * 0.4 = 0.5 -> 50 gil
    assert res.quote.final_price == 50


def test_quote_sell_better_for_high_rep():
    reg = _stocked_merchant()
    neutral = reg.quote_sell(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.NEUTRAL,
    )
    hero = reg.quote_sell(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.HERO_OF_THE_FACTION,
    )
    # Hero band: 0.5 + (1.0 - 0.7) * 0.4 = 0.62 -> 62 gil
    assert hero.quote.final_price > neutral.quote.final_price


def test_full_lifecycle_supply_rep_raid_compound():
    """A nation hero buying a potion from an overstocked merchant
    on a raided trade route. Overstock discount * hero discount *
    raid surcharge."""
    reg = _stocked_merchant()
    reg.merchant("dabihook").ledger("potion").stock_count = 95
    res = reg.quote_buy(
        npc_id="dabihook", item_id="potion",
        player_rep_band=ReputationBand.HERO_OF_THE_FACTION,
        route_pressure=80,
    )
    # 100 * 0.85 (overstock) * 0.7 (hero) * 1.3 (raid) = 77.35 -> 77
    assert res.quote.final_price == 77
    # All multipliers reflected in quote
    assert res.quote.supply_multiplier == 0.85
    assert res.quote.rep_multiplier == 0.7
    assert res.quote.raid_multiplier == 1.3
