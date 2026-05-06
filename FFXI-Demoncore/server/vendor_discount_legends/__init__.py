"""Vendor discounts for legends — pricing varies by reputation.

Vendors give discounts to title-holders. The discount
scales with the highest title tier the player carries:

    UNKNOWN   no discount (paying full price)
    NOTED      -3% buy / +2% sell
    HONORED   -7% buy / +5% sell
    REVERED  -12% buy / +9% sell
    MYTHICAL -20% buy / +15% sell

The discount is also conditioned on per-vendor *vendor_loyalty*:
    NEUTRAL    full discount applies as listed
    HOMEBOY    full discount + extra 5% (vendor is from this
               player's home nation)
    OUTSIDER   discount halved (vendor is foreign — politer
               but not as generous)

Outlaw flag causes vendors to refuse service entirely
(except the OUTLAW_PIT contraband shop, which always serves
anyone).

Public surface
--------------
    VendorLoyalty enum
    PriceQuote dataclass (frozen)
    VendorDiscountEngine
        .quote_buy(base_price, recognition, loyalty,
                   is_outlaw, vendor_serves_outlaws)
            -> PriceQuote
        .quote_sell(base_price, recognition, loyalty,
                    is_outlaw, vendor_serves_outlaws)
            -> PriceQuote
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.npc_legend_awareness import (
    RecognitionResult,
    RecognitionTier,
)


class VendorLoyalty(str, enum.Enum):
    NEUTRAL = "neutral"
    HOMEBOY = "homeboy"
    OUTSIDER = "outsider"


_BUY_PCT = {
    RecognitionTier.UNKNOWN: 0,
    RecognitionTier.NOTED: 3,
    RecognitionTier.HONORED: 7,
    RecognitionTier.REVERED: 12,
    RecognitionTier.MYTHICAL: 20,
}

_SELL_PCT = {
    RecognitionTier.UNKNOWN: 0,
    RecognitionTier.NOTED: 2,
    RecognitionTier.HONORED: 5,
    RecognitionTier.REVERED: 9,
    RecognitionTier.MYTHICAL: 15,
}


@dataclasses.dataclass(frozen=True)
class PriceQuote:
    final_price: int
    discount_pct: int        # 0-30 typical (positive number)
    refused: bool            # True when outlaw or invalid
    refusal_reason: str = ""


def _apply_loyalty(pct: int, loyalty: VendorLoyalty) -> int:
    if loyalty == VendorLoyalty.HOMEBOY:
        return pct + 5
    if loyalty == VendorLoyalty.OUTSIDER:
        return pct // 2
    return pct


@dataclasses.dataclass
class VendorDiscountEngine:

    def quote_buy(
        self, *, base_price: int,
        recognition: RecognitionResult,
        loyalty: VendorLoyalty = VendorLoyalty.NEUTRAL,
        is_outlaw: bool = False,
        vendor_serves_outlaws: bool = False,
    ) -> PriceQuote:
        if base_price < 0:
            return PriceQuote(
                final_price=0, discount_pct=0,
                refused=True, refusal_reason="invalid price",
            )
        if is_outlaw and not vendor_serves_outlaws:
            return PriceQuote(
                final_price=0, discount_pct=0,
                refused=True,
                refusal_reason="vendor refuses outlaws",
            )
        pct = _BUY_PCT[recognition.tier]
        pct = _apply_loyalty(pct, loyalty)
        # pct cap at 30% for sanity
        if pct > 30:
            pct = 30
        if pct < 0:
            pct = 0
        final = base_price - (base_price * pct) // 100
        return PriceQuote(
            final_price=final, discount_pct=pct, refused=False,
        )

    def quote_sell(
        self, *, base_price: int,
        recognition: RecognitionResult,
        loyalty: VendorLoyalty = VendorLoyalty.NEUTRAL,
        is_outlaw: bool = False,
        vendor_serves_outlaws: bool = False,
    ) -> PriceQuote:
        if base_price < 0:
            return PriceQuote(
                final_price=0, discount_pct=0,
                refused=True, refusal_reason="invalid price",
            )
        if is_outlaw and not vendor_serves_outlaws:
            return PriceQuote(
                final_price=0, discount_pct=0,
                refused=True,
                refusal_reason="vendor refuses outlaws",
            )
        pct = _SELL_PCT[recognition.tier]
        pct = _apply_loyalty(pct, loyalty)
        if pct > 25:
            pct = 25
        if pct < 0:
            pct = 0
        # sell-side: vendor pays MORE for items
        final = base_price + (base_price * pct) // 100
        return PriceQuote(
            final_price=final, discount_pct=pct, refused=False,
        )


__all__ = [
    "VendorLoyalty", "PriceQuote", "VendorDiscountEngine",
]
