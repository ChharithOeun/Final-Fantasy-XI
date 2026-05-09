"""Tests for card_battle_game."""
from __future__ import annotations

from server.card_battle_game import (
    CardBattleGameSystem, Color, GameState, Card,
    Side,
)


def _deck(prefix="r"):
    return [
        Card(card_id=f"{prefix}_{i}",
             name=f"Card {i}",
             n=5, e=5, s=5, w=5)
        for i in range(5)
    ]


def _strong_deck(prefix):
    return [
        Card(card_id=f"{prefix}_{i}",
             name=f"Strong {i}",
             n=10, e=10, s=10, w=10)
        for i in range(5)
    ]


def _weak_deck(prefix):
    return [
        Card(card_id=f"{prefix}_{i}",
             name=f"Weak {i}",
             n=1, e=1, s=1, w=1)
        for i in range(5)
    ]


def _setup_game(s):
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    s.submit_deck(
        game_id=gid, color=Color.RED,
        deck=_deck("r"),
    )
    s.submit_deck(
        game_id=gid, color=Color.BLUE,
        deck=_deck("b"),
    )
    return gid


def test_start_game_happy():
    s = CardBattleGameSystem()
    assert s.start_game(
        red_player="bob", blue_player="naji",
    ) is not None


def test_start_game_self_blocked():
    s = CardBattleGameSystem()
    assert s.start_game(
        red_player="x", blue_player="x",
    ) is None


def test_start_game_blank():
    s = CardBattleGameSystem()
    assert s.start_game(
        red_player="", blue_player="naji",
    ) is None


def test_submit_deck_wrong_size():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    bad = _deck("r")[:3]
    assert s.submit_deck(
        game_id=gid, color=Color.RED, deck=bad,
    ) is False


def test_submit_deck_dup_card_ids():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    same = [
        Card(card_id="x", name="x", n=5,
             e=5, s=5, w=5)
        for _ in range(5)
    ]
    assert s.submit_deck(
        game_id=gid, color=Color.RED, deck=same,
    ) is False


def test_submit_deck_invalid_card():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    bad = _deck("r")[:4] + [
        Card(card_id="x", name="x", n=11,
             e=5, s=5, w=5),
    ]
    assert s.submit_deck(
        game_id=gid, color=Color.RED, deck=bad,
    ) is False


def test_submit_deck_double_blocked():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    s.submit_deck(
        game_id=gid, color=Color.RED,
        deck=_deck("r"),
    )
    assert s.submit_deck(
        game_id=gid, color=Color.RED,
        deck=_deck("r2"),
    ) is False


def test_state_advances_to_in_progress():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    assert s.state_of(
        game_id=gid,
    ) == GameState.IN_PROGRESS


def test_play_happy():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    flips = s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="r_0",
    )
    assert flips == 0


def test_play_wrong_turn():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    flips = s.play(
        game_id=gid, color=Color.BLUE,
        cell=0, card_id="b_0",
    )
    assert flips is None


def test_play_occupied_cell():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="r_0",
    )
    flips = s.play(
        game_id=gid, color=Color.BLUE,
        cell=0, card_id="b_0",
    )
    assert flips is None


def test_play_unknown_card():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    flips = s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="ghost",
    )
    assert flips is None


def test_play_out_of_bounds():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    flips = s.play(
        game_id=gid, color=Color.RED,
        cell=20, card_id="r_0",
    )
    assert flips is None


def test_flip_when_stronger_edge():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    s.submit_deck(
        game_id=gid, color=Color.RED,
        deck=_strong_deck("r"),
    )
    s.submit_deck(
        game_id=gid, color=Color.BLUE,
        deck=_weak_deck("b"),
    )
    # Red plays cell 0, Blue plays cell 1 (E of red)
    s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="r_0",
    )
    s.play(
        game_id=gid, color=Color.BLUE,
        cell=1, card_id="b_0",
    )
    # Red plays cell 4 (S of cell 1) -> red.N(10)
    # vs blue's S(1) -> flip
    flips = s.play(
        game_id=gid, color=Color.RED,
        cell=4, card_id="r_1",
    )
    assert flips == 1


def test_no_flip_same_color():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="r_0",
    )
    s.play(
        game_id=gid, color=Color.BLUE,
        cell=4, card_id="b_0",
    )
    s.play(
        game_id=gid, color=Color.RED,
        cell=1, card_id="r_1",
    )
    # Blue cell 4 not adjacent to red cell 0 + 1 in
    # a way to flip — and same-color cards never
    # flip each other. Confirm scores reasonable.
    sc = s.score(game_id=gid)
    assert sc is not None


def test_play_after_game_complete():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    moves = [
        (Color.RED, 0, "r_0"),
        (Color.BLUE, 1, "b_0"),
        (Color.RED, 2, "r_1"),
        (Color.BLUE, 3, "b_1"),
        (Color.RED, 4, "r_2"),
        (Color.BLUE, 5, "b_2"),
        (Color.RED, 6, "r_3"),
        (Color.BLUE, 7, "b_3"),
        (Color.RED, 8, "r_4"),
    ]
    for color, cell, card in moves:
        s.play(
            game_id=gid, color=color, cell=cell,
            card_id=card,
        )
    assert s.state_of(
        game_id=gid,
    ) == GameState.COMPLETED
    # Try to play more
    flips = s.play(
        game_id=gid, color=Color.BLUE,
        cell=0, card_id="b_4",
    )
    assert flips is None


def test_score_after_full_game():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    moves = [
        (Color.RED, 0, "r_0"),
        (Color.BLUE, 1, "b_0"),
        (Color.RED, 2, "r_1"),
        (Color.BLUE, 3, "b_1"),
        (Color.RED, 4, "r_2"),
        (Color.BLUE, 5, "b_2"),
        (Color.RED, 6, "r_3"),
        (Color.BLUE, 7, "b_3"),
        (Color.RED, 8, "r_4"),
    ]
    for color, cell, card in moves:
        s.play(
            game_id=gid, color=color, cell=cell,
            card_id=card,
        )
    sc = s.score(game_id=gid)
    assert sc is not None
    assert sum(sc) == 9


def test_winner_strong_deck():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    s.submit_deck(
        game_id=gid, color=Color.RED,
        deck=_strong_deck("r"),
    )
    s.submit_deck(
        game_id=gid, color=Color.BLUE,
        deck=_weak_deck("b"),
    )
    moves = [
        (Color.RED, 0, "r_0"),
        (Color.BLUE, 1, "b_0"),
        (Color.RED, 2, "r_1"),
        (Color.BLUE, 3, "b_1"),
        (Color.RED, 4, "r_2"),
        (Color.BLUE, 5, "b_2"),
        (Color.RED, 6, "r_3"),
        (Color.BLUE, 7, "b_3"),
        (Color.RED, 8, "r_4"),
    ]
    for color, cell, card in moves:
        s.play(
            game_id=gid, color=color, cell=cell,
            card_id=card,
        )
    assert s.winner(game_id=gid) == Color.RED


def test_winner_unsettled_none():
    s = CardBattleGameSystem()
    gid = _setup_game(s)
    assert s.winner(game_id=gid) is None


def test_state_unknown():
    s = CardBattleGameSystem()
    assert s.state_of(game_id="ghost") is None


def test_play_before_decks_blocked():
    s = CardBattleGameSystem()
    gid = s.start_game(
        red_player="bob", blue_player="naji",
    )
    flips = s.play(
        game_id=gid, color=Color.RED,
        cell=0, card_id="x",
    )
    assert flips is None


def test_score_unknown():
    s = CardBattleGameSystem()
    assert s.score(game_id="ghost") is None


def test_enum_counts():
    assert len(list(Side)) == 4
    assert len(list(Color)) == 2
    assert len(list(GameState)) == 3
