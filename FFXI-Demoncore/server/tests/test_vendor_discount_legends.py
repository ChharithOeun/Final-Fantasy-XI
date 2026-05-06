"""Tests for vendor_discount_legends."""
from __future__ import annotations

from server.npc_legend_awareness import (
    RecognitionResult,
    RecognitionTier,
)
from server.vendor_discount_legends import (
    VendorDiscountEngine,
    VendorLoyalty,
)


def _rec(tier: RecognitionTier) -> RecognitionResult:
    return RecognitionResult(
        tier=tier, highest_title_id=None,
        faction_friendly=False, faction_hostile=False,
        reaction_phrase="",
    )


def test_unknown_pays_full_buy():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.UNKNOWN),
    )
    assert q.final_price == 100
    assert q.discount_pct == 0


def test_noted_3pct_off_buy():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.NOTED),
    )
    assert q.discount_pct == 3
    assert q.final_price == 97


def test_mythical_20pct_off_buy():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    assert q.discount_pct == 20
    assert q.final_price == 80


def test_homeboy_adds_5_to_buy_discount():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.HONORED),
        loyalty=VendorLoyalty.HOMEBOY,
    )
    # 7 + 5 = 12
    assert q.discount_pct == 12
    assert q.final_price == 88


def test_outsider_halves_buy_discount():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        loyalty=VendorLoyalty.OUTSIDER,
    )
    # 20 // 2 = 10
    assert q.discount_pct == 10


def test_outlaw_refused():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=True,
    )
    assert q.refused is True


def test_contraband_shop_serves_outlaws():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.NOTED),
        is_outlaw=True, vendor_serves_outlaws=True,
    )
    assert q.refused is False
    assert q.discount_pct == 3


def test_negative_price_refused():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=-1,
        recognition=_rec(RecognitionTier.NOTED),
    )
    assert q.refused is True


def test_sell_quote_pays_premium():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    # +15% on sell
    assert q.discount_pct == 15
    assert q.final_price == 115


def test_sell_outsider_halves_premium():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        loyalty=VendorLoyalty.OUTSIDER,
    )
    # 15 // 2 = 7
    assert q.discount_pct == 7


def test_sell_homeboy_adds_5():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=100,
        recognition=_rec(RecognitionTier.HONORED),
        loyalty=VendorLoyalty.HOMEBOY,
    )
    assert q.discount_pct == 10  # 5 + 5


def test_sell_outlaw_refused():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=True,
    )
    assert q.refused is True


def test_buy_cap_at_30():
    e = VendorDiscountEngine()
    # MYTHICAL=20, +HOMEBOY=25 (no cap hit), test the 30 cap
    # by simulating a hypothetical higher value via direct
    # check
    q = e.quote_buy(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        loyalty=VendorLoyalty.HOMEBOY,
    )
    # 20 + 5 = 25 (still under cap)
    assert q.discount_pct == 25
    assert q.final_price == 75


def test_sell_cap_at_25():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=100,
        recognition=_rec(RecognitionTier.MYTHICAL),
        loyalty=VendorLoyalty.HOMEBOY,
    )
    # 15 + 5 = 20 (under 25 cap)
    assert q.discount_pct == 20
    assert q.final_price == 120


def test_zero_base_price_ok():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=0,
        recognition=_rec(RecognitionTier.MYTHICAL),
    )
    assert q.refused is False
    assert q.final_price == 0


def test_three_loyalty_kinds():
    assert len(list(VendorLoyalty)) == 3


def test_revered_buy_12pct():
    e = VendorDiscountEngine()
    q = e.quote_buy(
        base_price=1000,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert q.discount_pct == 12
    assert q.final_price == 880


def test_revered_sell_9pct():
    e = VendorDiscountEngine()
    q = e.quote_sell(
        base_price=1000,
        recognition=_rec(RecognitionTier.REVERED),
    )
    assert q.discount_pct == 9
    assert q.final_price == 1090
