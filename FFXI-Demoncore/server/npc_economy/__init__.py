"""NPC economy — merchant pricing AI.

NPC merchants in Demoncore are AI agents running shops. They:

* Restock from incoming caravans (trade_routes)
* Set prices based on local supply/demand
* Discount for friendly customers (faction_reputation)
* Mark up when their supply lines are under raid pressure
* Refuse service entirely to hostile customers

This module owns the pricing decision. The shop's actual UI
(npc_vendor) consumes a quote from here. The merchant's AI agent
can override on a case-by-case basis (special discount, "I don't
sell to your kind") but the registry is the floor.

Pricing model
-------------
Each merchant maintains a per-item ledger:
* base_price (the canonical FFXI shop price)
* stock_count (current units in stock)
* desired_stock (the merchant's target inventory level)
* turnover_rate (units sold per game-day; tunes restock urgency)

Final quote =
    base_price
    * supply_multiplier(stock_count, desired_stock)
    * raid_pressure_multiplier(route_pressure)
    * rep_band_multiplier(player_rep_band)

Supply multiplier:
    < 25% of desired -> 1.5x   (scarcity surcharge)
    25-75%           -> 1.0x   (normal)
    > 75%            -> 0.85x  (overstock discount)

Raid pressure multiplier (route feeding this shop):
    > 60   -> 1.3x
    30-60  -> 1.15x
    < 30   -> 1.0x

Rep band multiplier:
    HERO_OF_THE_FACTION -> 0.7x
    ALLIED              -> 0.8x
    FRIENDLY            -> 0.9x
    NEUTRAL             -> 1.0x
    UNFRIENDLY          -> 1.25x  (pay extra to get served)
    HOSTILE / KILL_ON_SIGHT -> service refused

Public surface
--------------
    PriceQuote dataclass
    QuoteResult dataclass — accepted vs. refused
    MerchantInventory dataclass
    MerchantRegistry
        .register_merchant(npc_id, ...)
        .stock(npc_id, item_id, count) — restock from caravan
        .quote_buy(npc_id, item_id, player_rep_band, route_pressure)
        .quote_sell(npc_id, item_id, player_rep_band)
        .record_sale(npc_id, item_id, units)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.faction_reputation import ReputationBand


class QuoteOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    REFUSED = "refused"


@dataclasses.dataclass(frozen=True)
class PriceQuote:
    item_id: str
    base_price: int
    final_price: int
    supply_multiplier: float
    rep_multiplier: float
    raid_multiplier: float
    units_in_stock: int


@dataclasses.dataclass(frozen=True)
class QuoteResult:
    outcome: QuoteOutcome
    quote: t.Optional[PriceQuote] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MerchantItemLedger:
    item_id: str
    base_price: int
    stock_count: int = 0
    desired_stock: int = 100
    units_sold: int = 0


@dataclasses.dataclass
class MerchantInventory:
    npc_id: str
    home_settlement_id: str           # which town this shop is in
    feeder_route_ids: tuple[str, ...] = ()  # routes that supply us
    _items: dict[str, MerchantItemLedger] = dataclasses.field(
        default_factory=dict,
    )

    def add_item(
        self, *, item_id: str, base_price: int,
        desired_stock: int = 100, initial_stock: int = 0,
    ) -> MerchantItemLedger:
        ledger = MerchantItemLedger(
            item_id=item_id, base_price=base_price,
            stock_count=initial_stock,
            desired_stock=desired_stock,
        )
        self._items[item_id] = ledger
        return ledger

    def ledger(
        self, item_id: str,
    ) -> t.Optional[MerchantItemLedger]:
        return self._items.get(item_id)

    def total_items(self) -> int:
        return len(self._items)


# --------------------------------------------------------------------
# Multiplier tables
# --------------------------------------------------------------------
_REP_MULTIPLIER: dict[ReputationBand, float] = {
    ReputationBand.HERO_OF_THE_FACTION: 0.7,
    ReputationBand.ALLIED: 0.8,
    ReputationBand.FRIENDLY: 0.9,
    ReputationBand.NEUTRAL: 1.0,
    ReputationBand.UNFRIENDLY: 1.25,
}

# Bands at which the shop will not serve at all.
_REFUSED_BANDS: frozenset[ReputationBand] = frozenset({
    ReputationBand.HOSTILE,
    ReputationBand.KILL_ON_SIGHT,
})


def _supply_multiplier(stock: int, desired: int) -> float:
    if desired <= 0:
        return 1.0
    ratio = stock / desired
    if ratio < 0.25:
        return 1.5
    if ratio > 0.75:
        return 0.85
    return 1.0


def _raid_multiplier(route_pressure: int) -> float:
    if route_pressure > 60:
        return 1.3
    if route_pressure >= 30:
        return 1.15
    return 1.0


@dataclasses.dataclass
class MerchantRegistry:
    _merchants: dict[str, MerchantInventory] = dataclasses.field(
        default_factory=dict,
    )

    def register_merchant(
        self, *, npc_id: str, home_settlement_id: str,
        feeder_route_ids: tuple[str, ...] = (),
    ) -> MerchantInventory:
        inv = MerchantInventory(
            npc_id=npc_id,
            home_settlement_id=home_settlement_id,
            feeder_route_ids=feeder_route_ids,
        )
        self._merchants[npc_id] = inv
        return inv

    def merchant(
        self, npc_id: str,
    ) -> t.Optional[MerchantInventory]:
        return self._merchants.get(npc_id)

    def stock(
        self, *, npc_id: str, item_id: str, count: int,
    ) -> bool:
        """Push goods into the shop (e.g. on caravan arrival)."""
        inv = self._merchants.get(npc_id)
        if inv is None:
            return False
        ledger = inv.ledger(item_id)
        if ledger is None:
            return False
        ledger.stock_count += count
        return True

    def quote_buy(
        self, *, npc_id: str, item_id: str,
        player_rep_band: ReputationBand,
        route_pressure: int = 0,
    ) -> QuoteResult:
        """Player buying FROM the merchant."""
        inv = self._merchants.get(npc_id)
        if inv is None:
            return QuoteResult(
                QuoteOutcome.REFUSED, reason="unknown merchant",
            )
        ledger = inv.ledger(item_id)
        if ledger is None:
            return QuoteResult(
                QuoteOutcome.REFUSED, reason="merchant doesn't carry that",
            )
        if player_rep_band in _REFUSED_BANDS:
            return QuoteResult(
                QuoteOutcome.REFUSED, reason="merchant refuses service",
            )
        if ledger.stock_count <= 0:
            return QuoteResult(
                QuoteOutcome.REFUSED, reason="out of stock",
            )
        sup = _supply_multiplier(
            ledger.stock_count, ledger.desired_stock,
        )
        rep = _REP_MULTIPLIER[player_rep_band]
        raid = _raid_multiplier(route_pressure)
        final = int(round(
            ledger.base_price * sup * rep * raid,
        ))
        return QuoteResult(
            QuoteOutcome.ACCEPTED,
            quote=PriceQuote(
                item_id=item_id, base_price=ledger.base_price,
                final_price=final,
                supply_multiplier=sup, rep_multiplier=rep,
                raid_multiplier=raid,
                units_in_stock=ledger.stock_count,
            ),
        )

    def quote_sell(
        self, *, npc_id: str, item_id: str,
        player_rep_band: ReputationBand,
    ) -> QuoteResult:
        """Player selling TO the merchant. Sell price is base * 0.5
        unmultiplied by raid pressure, but rep matters (higher rep =
        merchant offers better trade-in)."""
        inv = self._merchants.get(npc_id)
        if inv is None:
            return QuoteResult(
                QuoteOutcome.REFUSED, reason="unknown merchant",
            )
        ledger = inv.ledger(item_id)
        if ledger is None:
            return QuoteResult(
                QuoteOutcome.REFUSED,
                reason="merchant doesn't accept that",
            )
        if player_rep_band in _REFUSED_BANDS:
            return QuoteResult(
                QuoteOutcome.REFUSED,
                reason="merchant refuses service",
            )
        rep = _REP_MULTIPLIER[player_rep_band]
        # Inverse rep curve for sell — higher rep -> better offer
        # 1.0 -> 0.5x base; 0.7 (HERO) -> 0.7x base
        sell_factor = 0.5 + (1.0 - rep) * 0.4
        final = max(1, int(round(ledger.base_price * sell_factor)))
        return QuoteResult(
            QuoteOutcome.ACCEPTED,
            quote=PriceQuote(
                item_id=item_id, base_price=ledger.base_price,
                final_price=final,
                supply_multiplier=1.0, rep_multiplier=rep,
                raid_multiplier=1.0,
                units_in_stock=ledger.stock_count,
            ),
        )

    def record_sale(
        self, *, npc_id: str, item_id: str, units: int = 1,
    ) -> bool:
        inv = self._merchants.get(npc_id)
        if inv is None:
            return False
        ledger = inv.ledger(item_id)
        if ledger is None or ledger.stock_count < units:
            return False
        ledger.stock_count -= units
        ledger.units_sold += units
        return True

    def total_merchants(self) -> int:
        return len(self._merchants)


__all__ = [
    "QuoteOutcome", "PriceQuote", "QuoteResult",
    "MerchantItemLedger", "MerchantInventory",
    "MerchantRegistry",
]
