"""Tests for auction-house bidding."""
from __future__ import annotations

from server.auction_house_bidding import (
    AuctionBiddingRegistry,
    BidOutcome,
    DEFAULT_AUCTION_WINDOW_SECONDS,
    LotKind,
    LotState,
)


def test_post_lot_basic():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, now_seconds=0.0,
    )
    assert lot is not None
    assert lot.state == LotState.OPEN
    assert lot.reserve_price == 1000


def test_post_lot_zero_quantity_rejected():
    reg = AuctionBiddingRegistry()
    assert reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        quantity=0, reserve_price=1000,
    ) is None


def test_post_buyout_only_requires_price():
    reg = AuctionBiddingRegistry()
    assert reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        kind=LotKind.BUYOUT_ONLY,
        reserve_price=0,
    ) is None
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        kind=LotKind.BUYOUT_ONLY,
        reserve_price=0, buyout_price=5000,
    )
    assert lot is not None


def test_seller_cannot_bid_on_own_lot():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=100,
    )
    res = reg.place_bid(
        player_id="alice", lot_id=lot.lot_id,
        amount=200, now_seconds=10.0,
    )
    assert res.outcome == BidOutcome.REJECTED_SELLER


def test_first_bid_must_meet_reserve():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
    )
    low = reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=500, now_seconds=10.0,
    )
    assert low.outcome == BidOutcome.REJECTED_LOW
    fine = reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1000, now_seconds=20.0,
    )
    assert fine.outcome == BidOutcome.ACCEPTED


def test_subsequent_bid_needs_5pct_increment():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
    )
    reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1000, now_seconds=10.0,
    )
    # 5% of 1000 = 50; need at least 1050
    low = reg.place_bid(
        player_id="charlie", lot_id=lot.lot_id,
        amount=1010, now_seconds=20.0,
    )
    assert low.outcome == BidOutcome.REJECTED_LOW
    enough = reg.place_bid(
        player_id="charlie", lot_id=lot.lot_id,
        amount=1100, now_seconds=30.0,
    )
    assert enough.outcome == BidOutcome.ACCEPTED


def test_outbid_player_recorded():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
    )
    reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1000, now_seconds=10.0,
    )
    res = reg.place_bid(
        player_id="charlie", lot_id=lot.lot_id,
        amount=1500, now_seconds=20.0,
    )
    assert res.outbid_player_id == "bob"
    assert "bob" in lot.outbid_pending


def test_bid_after_close_rejected():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, now_seconds=0.0,
        window_seconds=100.0,
    )
    res = reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1000, now_seconds=200.0,
    )
    assert res.outcome == BidOutcome.REJECTED_CLOSED


def test_bid_unknown_lot_rejected():
    reg = AuctionBiddingRegistry()
    res = reg.place_bid(
        player_id="bob", lot_id="ghost",
        amount=1000, now_seconds=0.0,
    )
    assert res.outcome == BidOutcome.REJECTED_CLOSED


def test_bid_on_buyout_only_rejected():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        kind=LotKind.BUYOUT_ONLY,
        reserve_price=0, buyout_price=5000,
    )
    res = reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=5000, now_seconds=10.0,
    )
    assert res.outcome == BidOutcome.REJECTED_CLOSED


def test_buyout_ends_auction():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, buyout_price=5000,
    )
    res = reg.buyout(
        player_id="bob", lot_id=lot.lot_id,
        now_seconds=10.0,
    )
    assert res.accepted
    assert res.final_price == 5000
    assert reg.lot(lot.lot_id).state == LotState.SOLD


def test_buyout_refunds_existing_bidders():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, buyout_price=5000,
    )
    reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1500, now_seconds=10.0,
    )
    res = reg.buyout(
        player_id="charlie", lot_id=lot.lot_id,
        now_seconds=20.0,
    )
    assert "bob" in res.refunded_bidders


def test_buyout_seller_blocked():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, buyout_price=5000,
    )
    res = reg.buyout(
        player_id="alice", lot_id=lot.lot_id,
        now_seconds=10.0,
    )
    assert not res.accepted


def test_close_expired_sells_to_high_bidder():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
        window_seconds=100.0,
    )
    reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=2000, now_seconds=10.0,
    )
    closed = reg.close_expired(now_seconds=200.0)
    assert lot.lot_id in closed
    assert reg.lot(lot.lot_id).state == LotState.SOLD
    assert reg.lot(lot.lot_id).winner_id == "bob"
    assert reg.lot(lot.lot_id).final_price == 2000


def test_close_expired_unsold_when_no_bids():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000, window_seconds=100.0,
    )
    reg.close_expired(now_seconds=200.0)
    assert reg.lot(lot.lot_id).state == LotState.UNSOLD


def test_cancel_returns_bidders():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
    )
    reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=1500, now_seconds=10.0,
    )
    assert reg.cancel(
        lot_id=lot.lot_id, seller_id="alice",
        now_seconds=20.0,
    )
    assert reg.lot(lot.lot_id).state == LotState.CANCELLED


def test_cancel_wrong_seller_rejected():
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="iron_sword",
        reserve_price=1000,
    )
    assert not reg.cancel(
        lot_id=lot.lot_id, seller_id="bob",
        now_seconds=10.0,
    )


def test_full_lifecycle_bidding_war_then_buyout():
    """Three bidders escalate; one buyouts to end it."""
    reg = AuctionBiddingRegistry()
    lot = reg.post_lot(
        seller_id="alice", item_id="legendary_sword",
        reserve_price=10000, buyout_price=100000,
        now_seconds=0.0,
    )
    r1 = reg.place_bid(
        player_id="bob", lot_id=lot.lot_id,
        amount=10000, now_seconds=10.0,
    )
    assert r1.outcome == BidOutcome.ACCEPTED
    r2 = reg.place_bid(
        player_id="charlie", lot_id=lot.lot_id,
        amount=15000, now_seconds=20.0,
    )
    assert r2.outcome == BidOutcome.ACCEPTED
    r3 = reg.place_bid(
        player_id="dave", lot_id=lot.lot_id,
        amount=20000, now_seconds=30.0,
    )
    assert r3.outcome == BidOutcome.ACCEPTED
    # Bob impatient, buys it out
    out = reg.buyout(
        player_id="bob", lot_id=lot.lot_id,
        now_seconds=40.0,
    )
    assert out.accepted
    assert reg.lot(lot.lot_id).winner_id == "bob"
    assert reg.lot(lot.lot_id).final_price == 100000
