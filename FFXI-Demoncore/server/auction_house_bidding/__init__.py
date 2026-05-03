"""Auction-house bidding wars.

Extends the basic auction_house listing model (buyout-only) with
a true BIDDING auction. A seller posts a lot with:

* Reserve price (minimum acceptable)
* Auction window (game-seconds until close)
* Optional buyout price (instant-buy ends auction)

Bidders place bids; bid increments enforce a minimum step over
the current high bid. At expiry the highest bidder wins; if
no bid >= reserve, the lot closes UNSOLD.

Outbid players get a delivery_box message; their bid amount is
returned to escrow.

Public surface
--------------
    LotState enum
    LotKind enum (RESERVE_AUCTION / BUYOUT_ONLY)
    Bid dataclass
    AuctionLot dataclass
    BidResult enum
    PlaceBidResult dataclass
    AuctionBiddingRegistry
        .post_lot(seller_id, item_id, reserve, ...)
        .place_bid(player_id, lot_id, amount, now)
        .buyout(player_id, lot_id, now)
        .close_expired(now) -> tuple[lot_id]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default minimum bid increment as percentage of current high bid.
MIN_BID_INCREMENT_PCT = 5
DEFAULT_AUCTION_WINDOW_SECONDS = 60 * 60 * 24


class LotState(str, enum.Enum):
    OPEN = "open"
    SOLD = "sold"
    UNSOLD = "unsold"
    CANCELLED = "cancelled"


class LotKind(str, enum.Enum):
    RESERVE_AUCTION = "reserve_auction"
    BUYOUT_ONLY = "buyout_only"        # no bidding, instant buy


class BidOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    OUTBID = "outbid"                  # informational
    REJECTED_LOW = "rejected_low"
    REJECTED_CLOSED = "rejected_closed"
    REJECTED_SELLER = "rejected_seller"


@dataclasses.dataclass(frozen=True)
class Bid:
    bidder_id: str
    amount: int
    placed_at_seconds: float


@dataclasses.dataclass
class AuctionLot:
    lot_id: str
    seller_id: str
    item_id: str
    quantity: int
    reserve_price: int
    buyout_price: t.Optional[int] = None
    posted_at_seconds: float = 0.0
    closes_at_seconds: float = 0.0
    state: LotState = LotState.OPEN
    kind: LotKind = LotKind.RESERVE_AUCTION
    bids: list[Bid] = dataclasses.field(default_factory=list)
    winner_id: t.Optional[str] = None
    final_price: t.Optional[int] = None
    outbid_pending: list[str] = dataclasses.field(
        default_factory=list,
    )

    @property
    def current_high(self) -> int:
        if not self.bids:
            return 0
        return max(b.amount for b in self.bids)

    @property
    def current_high_bidder(self) -> t.Optional[str]:
        if not self.bids:
            return None
        return max(self.bids, key=lambda b: b.amount).bidder_id

    def is_active(self, *, now_seconds: float) -> bool:
        return (
            self.state == LotState.OPEN
            and now_seconds < self.closes_at_seconds
        )


@dataclasses.dataclass(frozen=True)
class PlaceBidResult:
    outcome: BidOutcome
    lot_id: str
    new_high: int = 0
    outbid_player_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BuyoutResult:
    accepted: bool
    lot_id: str
    final_price: int = 0
    refunded_bidders: tuple[str, ...] = ()
    reason: t.Optional[str] = None


def _min_acceptable_bid(*, current_high: int, reserve: int) -> int:
    if current_high == 0:
        return reserve
    increment = max(1, current_high * MIN_BID_INCREMENT_PCT // 100)
    return current_high + increment


@dataclasses.dataclass
class AuctionBiddingRegistry:
    min_bid_increment_pct: int = MIN_BID_INCREMENT_PCT
    _lots: dict[str, AuctionLot] = dataclasses.field(
        default_factory=dict,
    )
    _next_lot_id: int = 0

    def post_lot(
        self, *, seller_id: str, item_id: str,
        quantity: int = 1, reserve_price: int = 0,
        buyout_price: t.Optional[int] = None,
        kind: LotKind = LotKind.RESERVE_AUCTION,
        now_seconds: float = 0.0,
        window_seconds: float = DEFAULT_AUCTION_WINDOW_SECONDS,
    ) -> t.Optional[AuctionLot]:
        if reserve_price < 0 or quantity <= 0:
            return None
        if (
            kind == LotKind.BUYOUT_ONLY
            and (buyout_price is None or buyout_price <= 0)
        ):
            return None
        lid = f"lot_{self._next_lot_id}"
        self._next_lot_id += 1
        lot = AuctionLot(
            lot_id=lid, seller_id=seller_id,
            item_id=item_id, quantity=quantity,
            reserve_price=reserve_price,
            buyout_price=buyout_price,
            posted_at_seconds=now_seconds,
            closes_at_seconds=now_seconds + window_seconds,
            kind=kind,
        )
        self._lots[lid] = lot
        return lot

    def lot(self, lot_id: str) -> t.Optional[AuctionLot]:
        return self._lots.get(lot_id)

    def lots_for_item(
        self, item_id: str,
    ) -> tuple[AuctionLot, ...]:
        return tuple(
            l for l in self._lots.values()
            if l.item_id == item_id
        )

    def place_bid(
        self, *, player_id: str, lot_id: str,
        amount: int, now_seconds: float,
    ) -> PlaceBidResult:
        lot = self._lots.get(lot_id)
        if lot is None:
            return PlaceBidResult(
                outcome=BidOutcome.REJECTED_CLOSED,
                lot_id=lot_id,
                reason="no such lot",
            )
        if lot.kind == LotKind.BUYOUT_ONLY:
            return PlaceBidResult(
                outcome=BidOutcome.REJECTED_CLOSED,
                lot_id=lot_id,
                reason="buyout-only lot",
            )
        if not lot.is_active(now_seconds=now_seconds):
            return PlaceBidResult(
                outcome=BidOutcome.REJECTED_CLOSED,
                lot_id=lot_id,
                reason="auction closed",
            )
        if player_id == lot.seller_id:
            return PlaceBidResult(
                outcome=BidOutcome.REJECTED_SELLER,
                lot_id=lot_id,
                reason="seller cannot bid on own lot",
            )
        min_bid = _min_acceptable_bid(
            current_high=lot.current_high,
            reserve=lot.reserve_price,
        )
        if amount < min_bid:
            return PlaceBidResult(
                outcome=BidOutcome.REJECTED_LOW,
                lot_id=lot_id,
                new_high=lot.current_high,
                reason=f"need at least {min_bid}",
            )
        prev_high_bidder = lot.current_high_bidder
        lot.bids.append(Bid(
            bidder_id=player_id, amount=amount,
            placed_at_seconds=now_seconds,
        ))
        if (
            prev_high_bidder is not None
            and prev_high_bidder != player_id
        ):
            lot.outbid_pending.append(prev_high_bidder)
        return PlaceBidResult(
            outcome=BidOutcome.ACCEPTED,
            lot_id=lot_id,
            new_high=amount,
            outbid_player_id=prev_high_bidder,
        )

    def buyout(
        self, *, player_id: str, lot_id: str,
        now_seconds: float,
    ) -> BuyoutResult:
        lot = self._lots.get(lot_id)
        if lot is None:
            return BuyoutResult(
                accepted=False, lot_id=lot_id,
                reason="no such lot",
            )
        if not lot.is_active(now_seconds=now_seconds):
            return BuyoutResult(
                accepted=False, lot_id=lot_id,
                reason="lot closed",
            )
        if lot.buyout_price is None:
            return BuyoutResult(
                accepted=False, lot_id=lot_id,
                reason="lot has no buyout price",
            )
        if player_id == lot.seller_id:
            return BuyoutResult(
                accepted=False, lot_id=lot_id,
                reason="seller cannot buyout own lot",
            )
        # Refund all losing bidders
        refunded = tuple({b.bidder_id for b in lot.bids})
        lot.state = LotState.SOLD
        lot.winner_id = player_id
        lot.final_price = lot.buyout_price
        lot.outbid_pending.extend(refunded)
        return BuyoutResult(
            accepted=True, lot_id=lot_id,
            final_price=lot.buyout_price,
            refunded_bidders=refunded,
        )

    def close_expired(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        closed: list[str] = []
        for lot in self._lots.values():
            if lot.state != LotState.OPEN:
                continue
            if now_seconds < lot.closes_at_seconds:
                continue
            if lot.current_high >= lot.reserve_price and lot.bids:
                lot.state = LotState.SOLD
                lot.winner_id = lot.current_high_bidder
                lot.final_price = lot.current_high
            else:
                lot.state = LotState.UNSOLD
            closed.append(lot.lot_id)
        return tuple(closed)

    def cancel(
        self, *, lot_id: str, seller_id: str,
        now_seconds: float,
    ) -> bool:
        lot = self._lots.get(lot_id)
        if lot is None or lot.seller_id != seller_id:
            return False
        if lot.state != LotState.OPEN:
            return False
        # Refund any current bidder
        if lot.current_high_bidder:
            lot.outbid_pending.extend({
                b.bidder_id for b in lot.bids
            })
        lot.state = LotState.CANCELLED
        return True

    def total_lots(self) -> int:
        return len(self._lots)


__all__ = [
    "MIN_BID_INCREMENT_PCT", "DEFAULT_AUCTION_WINDOW_SECONDS",
    "LotState", "LotKind", "BidOutcome",
    "Bid", "AuctionLot",
    "PlaceBidResult", "BuyoutResult",
    "AuctionBiddingRegistry",
]
