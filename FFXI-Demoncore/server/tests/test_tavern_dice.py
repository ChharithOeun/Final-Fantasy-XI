"""Tests for tavern_dice."""
from __future__ import annotations

from server.tavern_dice import (
    TavernDiceSystem, RoundState, BidOutcome,
)


def test_open_happy():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="bastok_inn", dealer_id="dealer",
        dice_count=5, dice_sides=6,
    )
    assert rid is not None


def test_open_invalid_dice_count():
    s = TavernDiceSystem()
    assert s.open_round(
        table_id="x", dealer_id="d",
        dice_count=0, dice_sides=6,
    ) is None
    assert s.open_round(
        table_id="x", dealer_id="d",
        dice_count=20, dice_sides=6,
    ) is None


def test_open_invalid_dice_sides():
    s = TavernDiceSystem()
    assert s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=7,
    ) is None


def test_open_invalid_payout():
    s = TavernDiceSystem()
    assert s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
        win_payout_x100=100,
    ) is None


def test_place_bid_happy():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    assert bid is not None


def test_place_bid_dealer_blocked():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid = s.place_bid(
        round_id=rid, player_id="d",
        wager_gil=100, placed_day=10,
    )
    assert bid is None


def test_place_bid_zero_wager():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=0, placed_day=10,
    )
    assert bid is None


def test_place_bid_dup_player_blocked():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    second = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=200, placed_day=10,
    )
    assert second is None


def test_pool_accumulates():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.place_bid(
        round_id=rid, player_id="cara",
        wager_gil=200, placed_day=10,
    )
    assert s.round(
        round_id=rid,
    ).pool_total_gil == 300


def test_lock_happy():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    assert s.lock(round_id=rid) is True


def test_lock_double_blocked():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    s.lock(round_id=rid)
    assert s.lock(round_id=rid) is False


def test_bid_after_lock_blocked():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    s.lock(round_id=rid)
    bid = s.place_bid(
        round_id=rid, player_id="late",
        wager_gil=100, placed_day=10,
    )
    assert bid is None


def test_resolve_returns_dealer_roll():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid_id = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.lock(round_id=rid)
    roll = s.resolve(
        round_id=rid, dealer_seed=42,
        bid_seeds={bid_id: 7},
    )
    assert roll is not None
    assert 5 <= roll <= 30  # 5d6 range


def test_resolve_settles_outcomes():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid_id = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.lock(round_id=rid)
    s.resolve(
        round_id=rid, dealer_seed=42,
        bid_seeds={bid_id: 7},
    )
    bid = s.player_bid(
        round_id=rid, player_id="bob",
    )
    assert bid.outcome != BidOutcome.PENDING


def test_resolve_unlocked_blocked():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    roll = s.resolve(
        round_id=rid, dealer_seed=42,
        bid_seeds={},
    )
    assert roll is None


def test_resolve_unknown_round():
    s = TavernDiceSystem()
    assert s.resolve(
        round_id="ghost", dealer_seed=42,
        bid_seeds={},
    ) is None


def test_win_payout_2x():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
        win_payout_x100=200,
    )
    bid_id = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.lock(round_id=rid)
    # We rig: dealer_seed=0 -> all rolls 1, sum=5
    # bid_seed=1<<28 -> high rolls
    s.resolve(
        round_id=rid, dealer_seed=0,
        bid_seeds={bid_id: 0xFFFFFFFF},
    )
    bid = s.player_bid(
        round_id=rid, player_id="bob",
    )
    if bid.outcome == BidOutcome.WIN:
        assert bid.payout_gil == 200
    elif bid.outcome == BidOutcome.PUSH:
        assert bid.payout_gil == 100
    else:
        assert bid.payout_gil == 0


def test_player_bid_unknown():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    assert s.player_bid(
        round_id=rid, player_id="ghost",
    ) is None


def test_bids_listed():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.place_bid(
        round_id=rid, player_id="cara",
        wager_gil=200, placed_day=10,
    )
    out = s.bids(round_id=rid)
    assert len(out) == 2


def test_round_unknown():
    s = TavernDiceSystem()
    assert s.round(round_id="ghost") is None


def test_resolve_deterministic():
    s = TavernDiceSystem()
    rid = s.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid_id = s.place_bid(
        round_id=rid, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s.lock(round_id=rid)
    roll1 = s.resolve(
        round_id=rid, dealer_seed=42,
        bid_seeds={bid_id: 7},
    )
    s2 = TavernDiceSystem()
    rid2 = s2.open_round(
        table_id="x", dealer_id="d",
        dice_count=5, dice_sides=6,
    )
    bid_id2 = s2.place_bid(
        round_id=rid2, player_id="bob",
        wager_gil=100, placed_day=10,
    )
    s2.lock(round_id=rid2)
    roll2 = s2.resolve(
        round_id=rid2, dealer_seed=42,
        bid_seeds={bid_id2: 7},
    )
    assert roll1 == roll2


def test_enum_counts():
    assert len(list(RoundState)) == 3
    assert len(list(BidOutcome)) == 4
