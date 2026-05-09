"""Card battle game — Triple-Triad-style 2-player.

Each player brings a 5-card deck. They take turns
placing cards on a 3x3 grid. Each card has 4 number
sides (NSEW). When a card is placed adjacent to an
opponent's card, the new card's edge facing the
opponent compares to the opponent's card edge facing
the new card. If new > opponent, the opponent's card
flips to the new player's color.

Game ends when the 9th card is placed. Whoever owns
the most cards wins.

Simplified rule set (no Same / Plus / Combo for now;
just direct edge compare).

Public surface
--------------
    Side enum (N / E / S / W)
    Color enum
    GameState enum
    Card dataclass (frozen)
    PlacedCard dataclass (frozen)
    Move dataclass (frozen)
    CardBattleGameSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Side(str, enum.Enum):
    N = "n"
    E = "e"
    S = "s"
    W = "w"


class Color(str, enum.Enum):
    RED = "red"
    BLUE = "blue"


class GameState(str, enum.Enum):
    AWAITING_DECKS = "awaiting_decks"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


_OPPOSITE = {
    Side.N: Side.S,
    Side.E: Side.W,
    Side.S: Side.N,
    Side.W: Side.E,
}


@dataclasses.dataclass(frozen=True)
class Card:
    card_id: str
    name: str
    n: int
    e: int
    s: int
    w: int


@dataclasses.dataclass(frozen=True)
class PlacedCard:
    card: Card
    color: Color
    cell: int  # 0..8 grid index


@dataclasses.dataclass(frozen=True)
class Move:
    move_id: str
    cell: int
    card_id: str
    color: Color


@dataclasses.dataclass
class _GState:
    game_id: str
    red_player: str
    blue_player: str
    red_deck: list[Card] = dataclasses.field(
        default_factory=list,
    )
    blue_deck: list[Card] = dataclasses.field(
        default_factory=list,
    )
    grid: dict[int, PlacedCard] = dataclasses.field(
        default_factory=dict,
    )
    state: GameState = GameState.AWAITING_DECKS
    next_to_move: Color = Color.RED
    moves: list[Move] = dataclasses.field(
        default_factory=list,
    )


def _validate_card(c: Card) -> bool:
    if not c.card_id or not c.name:
        return False
    for v in (c.n, c.e, c.s, c.w):
        if not 1 <= v <= 10:
            return False
    return True


def _adjacent(cell: int) -> dict[Side, int]:
    """Return {side: adjacent_cell_index or -1}."""
    row = cell // 3
    col = cell % 3
    out: dict[Side, int] = {}
    out[Side.N] = (
        (row - 1) * 3 + col if row > 0 else -1
    )
    out[Side.S] = (
        (row + 1) * 3 + col if row < 2 else -1
    )
    out[Side.W] = (
        row * 3 + (col - 1) if col > 0 else -1
    )
    out[Side.E] = (
        row * 3 + (col + 1) if col < 2 else -1
    )
    return out


def _side_value(card: Card, side: Side) -> int:
    return {
        Side.N: card.n, Side.E: card.e,
        Side.S: card.s, Side.W: card.w,
    }[side]


@dataclasses.dataclass
class CardBattleGameSystem:
    _games: dict[str, _GState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def start_game(
        self, *, red_player: str,
        blue_player: str,
    ) -> t.Optional[str]:
        if not red_player or not blue_player:
            return None
        if red_player == blue_player:
            return None
        gid = f"game_{self._next_id}"
        self._next_id += 1
        self._games[gid] = _GState(
            game_id=gid, red_player=red_player,
            blue_player=blue_player,
        )
        return gid

    def submit_deck(
        self, *, game_id: str, color: Color,
        deck: t.Sequence[Card],
    ) -> bool:
        if game_id not in self._games:
            return False
        g = self._games[game_id]
        if g.state != GameState.AWAITING_DECKS:
            return False
        if len(deck) != 5:
            return False
        if len(set(c.card_id for c in deck)) != 5:
            return False
        for c in deck:
            if not _validate_card(c):
                return False
        if color == Color.RED:
            if g.red_deck:
                return False
            g.red_deck = list(deck)
        else:
            if g.blue_deck:
                return False
            g.blue_deck = list(deck)
        if g.red_deck and g.blue_deck:
            g.state = GameState.IN_PROGRESS
        return True

    def play(
        self, *, game_id: str, color: Color,
        cell: int, card_id: str,
    ) -> t.Optional[int]:
        """Place a card. Returns # of flips
        triggered, or None on invalid move."""
        if game_id not in self._games:
            return None
        g = self._games[game_id]
        if g.state != GameState.IN_PROGRESS:
            return None
        if g.next_to_move != color:
            return None
        if not 0 <= cell <= 8:
            return None
        if cell in g.grid:
            return None
        deck = (
            g.red_deck if color == Color.RED
            else g.blue_deck
        )
        card = next(
            (c for c in deck
             if c.card_id == card_id),
            None,
        )
        if card is None:
            return None
        # Place
        g.grid[cell] = PlacedCard(
            card=card, color=color, cell=cell,
        )
        deck.remove(card)
        # Resolve flips
        flips = 0
        for side, adj_cell in _adjacent(cell).items():
            if adj_cell == -1:
                continue
            if adj_cell not in g.grid:
                continue
            adj = g.grid[adj_cell]
            if adj.color == color:
                continue
            my_edge = _side_value(card, side)
            their_edge = _side_value(
                adj.card, _OPPOSITE[side],
            )
            if my_edge > their_edge:
                g.grid[adj_cell] = (
                    dataclasses.replace(
                        adj, color=color,
                    )
                )
                flips += 1
        g.moves.append(Move(
            move_id=f"m{len(g.moves) + 1}",
            cell=cell, card_id=card_id,
            color=color,
        ))
        # Switch turn
        g.next_to_move = (
            Color.BLUE if color == Color.RED
            else Color.RED
        )
        # End-of-game check: 9 cells full
        if len(g.grid) == 9:
            g.state = GameState.COMPLETED
        return flips

    def score(
        self, *, game_id: str,
    ) -> t.Optional[tuple[int, int]]:
        if game_id not in self._games:
            return None
        g = self._games[game_id]
        red = sum(
            1 for p in g.grid.values()
            if p.color == Color.RED
        )
        blue = sum(
            1 for p in g.grid.values()
            if p.color == Color.BLUE
        )
        return (red, blue)

    def winner(
        self, *, game_id: str,
    ) -> t.Optional[Color]:
        sc = self.score(game_id=game_id)
        if sc is None:
            return None
        if self._games[game_id].state != (
            GameState.COMPLETED
        ):
            return None
        red, blue = sc
        if red == blue:
            return None
        return Color.RED if red > blue else Color.BLUE

    def state_of(
        self, *, game_id: str,
    ) -> t.Optional[GameState]:
        if game_id not in self._games:
            return None
        return self._games[game_id].state


__all__ = [
    "Side", "Color", "GameState", "Card",
    "PlacedCard", "Move",
    "CardBattleGameSystem",
]
