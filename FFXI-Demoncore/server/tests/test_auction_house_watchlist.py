"""Tests for the auction house watchlist."""
from __future__ import annotations

from server.auction_house_watchlist import (
    AlertKind,
    AuctionHouseWatchlist,
    WatchKind,
)


def test_add_item_rule():
    w = AuctionHouseWatchlist()
    rule = w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    assert rule is not None


def test_add_invalid_item_rule_no_item_id():
    w = AuctionHouseWatchlist()
    assert w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id=None,
    ) is None


def test_add_seller_rule():
    w = AuctionHouseWatchlist()
    rule = w.add_rule(
        player_id="alice",
        kind=WatchKind.SELLER_ID,
        seller_id="bob",
    )
    assert rule is not None


def test_add_invalid_seller_rule():
    w = AuctionHouseWatchlist()
    assert w.add_rule(
        player_id="alice",
        kind=WatchKind.SELLER_ID,
        seller_id=None,
    ) is None


def test_add_combined_rule_requires_both():
    w = AuctionHouseWatchlist()
    assert w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_AND_SELLER,
        item_id="moonbow",
        seller_id=None,
    ) is None


def test_remove_rule():
    w = AuctionHouseWatchlist()
    rule = w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    assert w.remove_rule(
        player_id="alice", rule_id=rule.rule_id,
    )


def test_remove_unknown_rule():
    w = AuctionHouseWatchlist()
    assert not w.remove_rule(
        player_id="alice", rule_id="ghost",
    )


def test_remove_other_player_rule_rejected():
    w = AuctionHouseWatchlist()
    rule = w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    assert not w.remove_rule(
        player_id="bob", rule_id=rule.rule_id,
    )


def test_listing_alerts_matching_item():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    alerts = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="seller_a", price=10000,
    )
    assert len(alerts) == 1
    assert alerts[0].kind == AlertKind.NEW_LISTING


def test_listing_no_match_no_alert():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    alerts = w.post_listing(
        listing_id="L1", item_id="iron_sword",
        seller_id="seller_a", price=100,
    )
    assert alerts == ()


def test_max_price_filter():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
        max_price=5000,
    )
    over = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="seller_a", price=10000,
    )
    assert over == ()
    under = w.post_listing(
        listing_id="L2", item_id="moonbow",
        seller_id="seller_a", price=4000,
    )
    assert len(under) == 1


def test_seller_match():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.SELLER_ID,
        seller_id="bob",
    )
    alerts = w.post_listing(
        listing_id="L1", item_id="anything",
        seller_id="bob", price=100,
    )
    assert len(alerts) == 1


def test_combined_rule_match():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_AND_SELLER,
        item_id="moonbow",
        seller_id="bob",
    )
    no_match = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="carol", price=100,
    )
    assert no_match == ()
    match = w.post_listing(
        listing_id="L2", item_id="moonbow",
        seller_id="bob", price=100,
    )
    assert len(match) == 1


def test_dedup_alert_per_listing():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    again = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    # Same (player, rule, listing) → no second alert
    assert again == ()


def test_delist_fires_alert_to_seen_watchers():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    delists = w.delist(listing_id="L1")
    assert len(delists) == 1
    assert delists[0].kind == AlertKind.DELISTED


def test_delist_unseen_no_alerts():
    w = AuctionHouseWatchlist()
    w.post_listing(
        listing_id="L1", item_id="x",
        seller_id="y", price=10,
    )
    assert w.delist(listing_id="L1") == ()


def test_delist_unknown_listing():
    w = AuctionHouseWatchlist()
    assert w.delist(listing_id="ghost") == ()


def test_pending_alerts_filters_acked():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    alerts = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    w.ack(
        player_id="alice",
        alert_id=alerts[0].alert_id,
    )
    pending = w.pending_alerts(player_id="alice")
    assert pending == ()


def test_ack_other_player_rejected():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    alerts = w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    assert not w.ack(
        player_id="bob",
        alert_id=alerts[0].alert_id,
    )


def test_total_rules_and_alerts():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    w.post_listing(
        listing_id="L1", item_id="moonbow",
        seller_id="bob", price=100,
    )
    assert w.total_rules() == 1
    assert w.total_alerts() == 1


def test_invalid_listing_data_no_alerts():
    w = AuctionHouseWatchlist()
    w.add_rule(
        player_id="alice",
        kind=WatchKind.ITEM_ID,
        item_id="moonbow",
    )
    res = w.post_listing(
        listing_id="L1", item_id="",
        seller_id="bob", price=100,
    )
    assert res == ()
    res2 = w.post_listing(
        listing_id="L2", item_id="moonbow",
        seller_id="", price=100,
    )
    assert res2 == ()
    res3 = w.post_listing(
        listing_id="L3", item_id="moonbow",
        seller_id="bob", price=-1,
    )
    assert res3 == ()
