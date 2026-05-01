"""Auction house — listings, buy-now, expiration, sale history.

The Vana'diel auction house is buy-now, not bid-up: a seller posts
at a price, the first buyer to click takes it. No haggling, no top-
bid escalation — the in-game social negotiation happens in bazaar
windows on the side. This module models the buy-now AH plus a
recent_history queue for price discovery.

Public surface
--------------
    Listing                  active listing
    SaleRecord               completed sale entry
    AuctionHouse             container per-shard
        .post(...)
        .buy(listing_id, buyer_id, now_tick) -> BuyResult
        .cancel(listing_id, seller_id) -> CancelResult
        .tick_expirations(now_tick) -> tuple[Listing, ...]
        .listings_for(item_id, now_tick) -> tuple[Listing, ...]
        .recent_sales(item_id, limit) -> tuple[SaleRecord, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


DEFAULT_LISTING_LIFETIME_SECONDS = 7 * 24 * 60 * 60   # 7 days


class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclasses.dataclass
class Listing:
    listing_id: int
    item_id: str
    seller_id: str
    price_gil: int
    posted_at_tick: int
    expires_at_tick: int
    status: ListingStatus = ListingStatus.ACTIVE


@dataclasses.dataclass(frozen=True)
class SaleRecord:
    item_id: str
    seller_id: str
    buyer_id: str
    price_gil: int
    sold_at_tick: int


@dataclasses.dataclass(frozen=True)
class BuyResult:
    accepted: bool
    listing_id: int
    sale: t.Optional[SaleRecord] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CancelResult:
    accepted: bool
    listing_id: int
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AuctionHouse:
    shard_id: str
    lifetime_seconds: int = DEFAULT_LISTING_LIFETIME_SECONDS
    _next_listing_id: int = 1
    _listings: dict[int, Listing] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    _history: list[SaleRecord] = dataclasses.field(
        default_factory=list, repr=False,
    )

    def post(
        self, *, item_id: str, seller_id: str,
        price_gil: int, now_tick: int,
    ) -> Listing:
        if price_gil <= 0:
            raise ValueError("price_gil must be > 0")
        if not item_id or not seller_id:
            raise ValueError("item_id and seller_id required")
        listing = Listing(
            listing_id=self._next_listing_id,
            item_id=item_id, seller_id=seller_id,
            price_gil=price_gil,
            posted_at_tick=now_tick,
            expires_at_tick=now_tick + self.lifetime_seconds,
        )
        self._listings[listing.listing_id] = listing
        self._next_listing_id += 1
        return listing

    def buy(
        self, *, listing_id: int, buyer_id: str, now_tick: int,
    ) -> BuyResult:
        listing = self._listings.get(listing_id)
        if listing is None:
            return BuyResult(False, listing_id, reason="unknown")
        if listing.status != ListingStatus.ACTIVE:
            return BuyResult(
                False, listing_id,
                reason=f"listing not active ({listing.status.value})",
            )
        if now_tick >= listing.expires_at_tick:
            listing.status = ListingStatus.EXPIRED
            return BuyResult(False, listing_id, reason="expired")
        if buyer_id == listing.seller_id:
            return BuyResult(
                False, listing_id, reason="cannot buy own listing",
            )
        listing.status = ListingStatus.SOLD
        sale = SaleRecord(
            item_id=listing.item_id,
            seller_id=listing.seller_id,
            buyer_id=buyer_id,
            price_gil=listing.price_gil,
            sold_at_tick=now_tick,
        )
        self._history.append(sale)
        return BuyResult(True, listing_id, sale=sale)

    def cancel(
        self, *, listing_id: int, seller_id: str,
    ) -> CancelResult:
        listing = self._listings.get(listing_id)
        if listing is None:
            return CancelResult(False, listing_id, "unknown")
        if listing.seller_id != seller_id:
            return CancelResult(
                False, listing_id, "not seller's listing",
            )
        if listing.status != ListingStatus.ACTIVE:
            return CancelResult(
                False, listing_id,
                f"already {listing.status.value}",
            )
        listing.status = ListingStatus.CANCELLED
        return CancelResult(True, listing_id)

    def tick_expirations(
        self, *, now_tick: int,
    ) -> tuple[Listing, ...]:
        out: list[Listing] = []
        for listing in self._listings.values():
            if (
                listing.status == ListingStatus.ACTIVE
                and now_tick >= listing.expires_at_tick
            ):
                listing.status = ListingStatus.EXPIRED
                out.append(listing)
        return tuple(out)

    def listings_for(
        self, *, item_id: str, now_tick: int,
    ) -> tuple[Listing, ...]:
        out = [
            L for L in self._listings.values()
            if L.item_id == item_id
            and L.status == ListingStatus.ACTIVE
            and now_tick < L.expires_at_tick
        ]
        out.sort(key=lambda L: (L.price_gil, L.posted_at_tick))
        return tuple(out)

    def recent_sales(
        self, *, item_id: str, limit: int = 10,
    ) -> tuple[SaleRecord, ...]:
        matches = [s for s in self._history if s.item_id == item_id]
        return tuple(matches[-limit:])

    def median_recent_price(
        self, *, item_id: str, limit: int = 10,
    ) -> t.Optional[int]:
        sales = self.recent_sales(item_id=item_id, limit=limit)
        if not sales:
            return None
        prices = sorted(s.price_gil for s in sales)
        mid = len(prices) // 2
        if len(prices) % 2 == 1:
            return prices[mid]
        return (prices[mid - 1] + prices[mid]) // 2

    def open_listing_count(self) -> int:
        return sum(
            1 for L in self._listings.values()
            if L.status == ListingStatus.ACTIVE
        )


__all__ = [
    "DEFAULT_LISTING_LIFETIME_SECONDS",
    "ListingStatus", "Listing", "SaleRecord",
    "BuyResult", "CancelResult",
    "AuctionHouse",
]
