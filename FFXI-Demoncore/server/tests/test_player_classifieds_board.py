"""Tests for player_classifieds_board."""
from __future__ import annotations

from server.player_classifieds_board import (
    PlayerClassifiedsBoardSystem,
    ListingKind, ListingState,
)


def _board(s: PlayerClassifiedsBoardSystem) -> str:
    return s.found_board(
        operator_id="naji", name="Bastok Bulletin",
    )


def _post(
    s: PlayerClassifiedsBoardSystem,
    bid: str, kind: ListingKind = ListingKind.OFFER,
    poster: str = "bob",
    fee: int = 100, post_day: int = 10,
    expiry_day: int = 20,
) -> str:
    return s.post_listing(
        board_id=bid, poster_id=poster, kind=kind,
        headline="Selling Mythril", body="50k each",
        listing_fee_gil=fee, post_day=post_day,
        expiry_day=expiry_day,
    )


def test_found_board_happy():
    s = PlayerClassifiedsBoardSystem()
    assert _board(s) is not None


def test_post_listing_happy():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert _post(s, bid) is not None


def test_post_empty_headline_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert s.post_listing(
        board_id=bid, poster_id="bob",
        kind=ListingKind.OFFER, headline="",
        body="x", listing_fee_gil=100,
        post_day=10, expiry_day=20,
    ) is None


def test_post_zero_fee_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert s.post_listing(
        board_id=bid, poster_id="bob",
        kind=ListingKind.OFFER, headline="x",
        body="y", listing_fee_gil=0,
        post_day=10, expiry_day=20,
    ) is None


def test_post_same_day_expiry_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert s.post_listing(
        board_id=bid, poster_id="bob",
        kind=ListingKind.OFFER, headline="x",
        body="y", listing_fee_gil=100,
        post_day=10, expiry_day=10,
    ) is None


def test_post_past_expiry_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert s.post_listing(
        board_id=bid, poster_id="bob",
        kind=ListingKind.OFFER, headline="x",
        body="y", listing_fee_gil=100,
        post_day=10, expiry_day=5,
    ) is None


def test_listing_fee_accumulates_to_operator():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    _post(s, bid, fee=100)
    _post(s, bid, fee=200)
    assert s.board(
        board_id=bid,
    ).revenue_gil == 300


def test_expire_listings_moves_state():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(
        s, bid, post_day=10, expiry_day=20,
    )
    moved = s.expire_listings(
        board_id=bid, current_day=25,
    )
    assert moved == 1
    assert s.listing(
        board_id=bid, listing_id=lid,
    ).state == ListingState.EXPIRED


def test_mark_resolved_returns_refund():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(
        s, bid, fee=200, post_day=10, expiry_day=20,
    )
    # 5 days remaining of 10 total — 50% pro-rated
    # half = 200 * 5 / (2*10) = 50
    refund = s.mark_resolved(
        board_id=bid, listing_id=lid,
        poster_id="bob", current_day=15,
    )
    assert refund == 50


def test_mark_resolved_wrong_poster_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(s, bid)
    assert s.mark_resolved(
        board_id=bid, listing_id=lid,
        poster_id="cara", current_day=15,
    ) is None


def test_mark_resolved_already_resolved_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(s, bid)
    s.mark_resolved(
        board_id=bid, listing_id=lid,
        poster_id="bob", current_day=15,
    )
    assert s.mark_resolved(
        board_id=bid, listing_id=lid,
        poster_id="bob", current_day=16,
    ) is None


def test_mark_resolved_after_expiry_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(
        s, bid, post_day=10, expiry_day=20,
    )
    assert s.mark_resolved(
        board_id=bid, listing_id=lid,
        poster_id="bob", current_day=25,
    ) is None


def test_cancel_listing_happy():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(s, bid)
    assert s.cancel_listing(
        board_id=bid, listing_id=lid,
        poster_id="bob",
    ) is True
    assert s.listing(
        board_id=bid, listing_id=lid,
    ).state == ListingState.CANCELED


def test_cancel_listing_no_refund():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(s, bid, fee=300)
    s.cancel_listing(
        board_id=bid, listing_id=lid,
        poster_id="bob",
    )
    # Operator keeps the full fee
    assert s.board(
        board_id=bid,
    ).revenue_gil == 300


def test_cancel_listing_wrong_poster_blocked():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    lid = _post(s, bid)
    assert s.cancel_listing(
        board_id=bid, listing_id=lid,
        poster_id="cara",
    ) is False


def test_listings_by_kind_filter():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    _post(s, bid, kind=ListingKind.OFFER)
    _post(s, bid, kind=ListingKind.OFFER)
    _post(s, bid, kind=ListingKind.WANT)
    assert len(s.listings_by_kind(
        board_id=bid, kind=ListingKind.OFFER,
    )) == 2


def test_listings_by_poster_filter():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    _post(s, bid, poster="bob")
    _post(s, bid, poster="bob")
    _post(s, bid, poster="cara")
    assert len(s.listings_by_poster(
        board_id=bid, poster_id="bob",
    )) == 2


def test_active_listings_only():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    l1 = _post(s, bid)
    _post(s, bid)
    s.cancel_listing(
        board_id=bid, listing_id=l1, poster_id="bob",
    )
    assert len(s.active_listings(
        board_id=bid,
    )) == 1


def test_unknown_listing():
    s = PlayerClassifiedsBoardSystem()
    bid = _board(s)
    assert s.listing(
        board_id=bid, listing_id="ghost",
    ) is None


def test_unknown_board():
    s = PlayerClassifiedsBoardSystem()
    assert s.board(board_id="ghost") is None


def test_kind_count():
    assert len(list(ListingKind)) == 4


def test_state_count():
    assert len(list(ListingState)) == 4
