"""Tests for the beastman bonanza."""
from __future__ import annotations

from server.beastman_bonanza import (
    BeastmanBonanza,
    BonanzaState,
)


def _seed(b):
    b.open_round(
        round_id="r1", marble_cost=1000, max_per_player=8,
    )


def test_open_round():
    b = BeastmanBonanza()
    assert _seed(b) is None  # returns True but our seed returns None
    assert b.total_rounds() == 1


def test_open_round_duplicate():
    b = BeastmanBonanza()
    _seed(b)
    res = b.open_round(
        round_id="r1", marble_cost=500, max_per_player=4,
    )
    assert not res


def test_open_round_zero_cost():
    b = BeastmanBonanza()
    res = b.open_round(
        round_id="bad", marble_cost=0, max_per_player=1,
    )
    assert not res


def test_open_round_zero_cap():
    b = BeastmanBonanza()
    res = b.open_round(
        round_id="bad", marble_cost=100, max_per_player=0,
    )
    assert not res


def test_buy_basic():
    b = BeastmanBonanza()
    _seed(b)
    res = b.buy(
        player_id="kraw", round_id="r1", number="12345",
    )
    assert res.accepted
    assert res.cost == 1000


def test_buy_invalid_number():
    b = BeastmanBonanza()
    _seed(b)
    res = b.buy(
        player_id="kraw", round_id="r1", number="abc12",
    )
    assert not res.accepted


def test_buy_short_number():
    b = BeastmanBonanza()
    _seed(b)
    res = b.buy(
        player_id="kraw", round_id="r1", number="123",
    )
    assert not res.accepted


def test_buy_cap_enforced():
    b = BeastmanBonanza()
    _seed(b)
    for i in range(8):
        b.buy(
            player_id="kraw", round_id="r1", number=f"1234{i}",
        )
    res = b.buy(
        player_id="kraw", round_id="r1", number="11111",
    )
    assert not res.accepted


def test_buy_unknown_round():
    b = BeastmanBonanza()
    res = b.buy(
        player_id="kraw", round_id="ghost", number="12345",
    )
    assert not res.accepted


def test_draw_basic():
    b = BeastmanBonanza()
    _seed(b)
    assert b.draw(round_id="r1", winning_number="12345")


def test_draw_invalid_number():
    b = BeastmanBonanza()
    _seed(b)
    assert not b.draw(round_id="r1", winning_number="bad")


def test_draw_unknown_round():
    b = BeastmanBonanza()
    assert not b.draw(round_id="ghost", winning_number="12345")


def test_buy_after_draw_blocked():
    b = BeastmanBonanza()
    _seed(b)
    b.draw(round_id="r1", winning_number="12345")
    res = b.buy(
        player_id="kraw", round_id="r1", number="11111",
    )
    assert not res.accepted


def test_check_5_match():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="12345")
    b.draw(round_id="r1", winning_number="12345")
    res = b.check(player_id="kraw", round_id="r1")
    assert res.matches_5 == 1


def test_check_4_match():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="12340")
    b.draw(round_id="r1", winning_number="12345")
    res = b.check(player_id="kraw", round_id="r1")
    assert res.matches_4 == 1


def test_check_3_match():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="12300")
    b.draw(round_id="r1", winning_number="12345")
    res = b.check(player_id="kraw", round_id="r1")
    assert res.matches_3 == 1


def test_check_no_match_below_3():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="00000")
    b.draw(round_id="r1", winning_number="12345")
    res = b.check(player_id="kraw", round_id="r1")
    assert res.matches_5 == 0
    assert res.matches_4 == 0
    assert res.matches_3 == 0


def test_check_before_draw():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="12345")
    res = b.check(player_id="kraw", round_id="r1")
    assert not res.accepted


def test_close_round():
    b = BeastmanBonanza()
    _seed(b)
    assert b.close_round(round_id="r1")


def test_close_round_double_blocked():
    b = BeastmanBonanza()
    _seed(b)
    b.close_round(round_id="r1")
    assert not b.close_round(round_id="r1")


def test_state_for():
    b = BeastmanBonanza()
    _seed(b)
    assert b.state_for(round_id="r1") == BonanzaState.OPEN
    b.draw(round_id="r1", winning_number="12345")
    assert b.state_for(round_id="r1") == BonanzaState.DRAWN
    b.close_round(round_id="r1")
    assert b.state_for(round_id="r1") == BonanzaState.CLOSED


def test_per_player_isolation():
    b = BeastmanBonanza()
    _seed(b)
    b.buy(player_id="kraw", round_id="r1", number="12345")
    b.buy(player_id="zlar", round_id="r1", number="00000")
    b.draw(round_id="r1", winning_number="12345")
    res = b.check(player_id="zlar", round_id="r1")
    assert res.matches_5 == 0
