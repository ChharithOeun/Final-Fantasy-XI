"""Tabletop chess — turn-based 2-player strategy game.

Played at Bastok pub tables on engraved wooden boards.
8x8 grid, 5 piece kinds (PAWN, KNIGHT, BISHOP, ROOK,
KING). Standard chess move rules with check, checkmate
and stalemate detection. No queen, castling, promotion
or en-passant in this variant — pub players preferred
the cleaner rule set.

Lifecycle
    SETUP        pieces being placed
    ACTIVE       moves being made
    CHECKMATE    a king has no escape
    STALEMATE    no legal move, king not in check
    RESIGNED     a player gave up
    DRAW         agreed draw

Public surface
--------------
    PieceKind enum
    Color enum
    GameState enum
    Square dataclass (frozen)
    Piece dataclass (frozen)
    Move dataclass (frozen)
    Game dataclass (frozen)
    TabletopChessSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_BOARD_SIZE = 8


class PieceKind(str, enum.Enum):
    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    KING = "king"


class Color(str, enum.Enum):
    WHITE = "white"
    BLACK = "black"


class GameState(str, enum.Enum):
    SETUP = "setup"
    ACTIVE = "active"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    RESIGNED = "resigned"
    DRAW = "draw"


@dataclasses.dataclass(frozen=True)
class Square:
    file: int
    rank: int


@dataclasses.dataclass(frozen=True)
class Piece:
    kind: PieceKind
    color: Color


@dataclasses.dataclass(frozen=True)
class Move:
    from_file: int
    from_rank: int
    to_file: int
    to_rank: int
    moved_kind: PieceKind
    captured: t.Optional[Piece]
    mover_color: Color


@dataclasses.dataclass(frozen=True)
class Game:
    game_id: str
    white_player: str
    black_player: str
    state: GameState
    turn: Color
    winner_color: t.Optional[Color]
    moves: tuple[Move, ...]


def _on_board(f: int, r: int) -> bool:
    return 0 <= f < _BOARD_SIZE and 0 <= r < _BOARD_SIZE


def _opp(c: Color) -> Color:
    if c == Color.WHITE:
        return Color.BLACK
    return Color.WHITE


def _piece_attacks(
    board: dict[tuple[int, int], Piece],
    f: int, r: int,
) -> set[tuple[int, int]]:
    p = board.get((f, r))
    if p is None:
        return set()
    out: set[tuple[int, int]] = set()
    if p.kind == PieceKind.PAWN:
        dr = 1 if p.color == Color.WHITE else -1
        for df in (-1, 1):
            nf, nr = f + df, r + dr
            if _on_board(nf, nr):
                out.add((nf, nr))
    elif p.kind == PieceKind.KNIGHT:
        for df, dr in [
            (1, 2), (2, 1), (-1, 2), (-2, 1),
            (1, -2), (2, -1), (-1, -2), (-2, -1),
        ]:
            nf, nr = f + df, r + dr
            if _on_board(nf, nr):
                out.add((nf, nr))
    elif p.kind == PieceKind.KING:
        for df in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if df == 0 and dr == 0:
                    continue
                nf, nr = f + df, r + dr
                if _on_board(nf, nr):
                    out.add((nf, nr))
    elif p.kind == PieceKind.BISHOP:
        for df, dr in [
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ]:
            nf, nr = f + df, r + dr
            while _on_board(nf, nr):
                out.add((nf, nr))
                if (nf, nr) in board:
                    break
                nf += df
                nr += dr
    elif p.kind == PieceKind.ROOK:
        for df, dr in [
            (1, 0), (-1, 0), (0, 1), (0, -1),
        ]:
            nf, nr = f + df, r + dr
            while _on_board(nf, nr):
                out.add((nf, nr))
                if (nf, nr) in board:
                    break
                nf += df
                nr += dr
    return out


def _attacked_by(
    board: dict[tuple[int, int], Piece], color: Color,
) -> set[tuple[int, int]]:
    out: set[tuple[int, int]] = set()
    for (f, r), p in board.items():
        if p.color == color:
            out |= _piece_attacks(board, f, r)
    return out


def _find_king(
    board: dict[tuple[int, int], Piece], color: Color,
) -> t.Optional[tuple[int, int]]:
    for sq, p in board.items():
        if (p.kind == PieceKind.KING
                and p.color == color):
            return sq
    return None


def _in_check(
    board: dict[tuple[int, int], Piece], color: Color,
) -> bool:
    king = _find_king(board, color)
    if king is None:
        return False
    return king in _attacked_by(board, _opp(color))


def _pseudo_moves(
    board: dict[tuple[int, int], Piece], color: Color,
) -> list[tuple[int, int, int, int]]:
    out: list[tuple[int, int, int, int]] = []
    for (f, r), p in list(board.items()):
        if p.color != color:
            continue
        if p.kind == PieceKind.PAWN:
            dr = 1 if p.color == Color.WHITE else -1
            nf, nr = f, r + dr
            if _on_board(nf, nr) and (nf, nr) not in board:
                out.append((f, r, nf, nr))
            for df in (-1, 1):
                nf, nr = f + df, r + dr
                if _on_board(nf, nr):
                    tgt = board.get((nf, nr))
                    if tgt is not None and tgt.color != color:
                        out.append((f, r, nf, nr))
        else:
            attacks = _piece_attacks(board, f, r)
            for (nf, nr) in attacks:
                tgt = board.get((nf, nr))
                if tgt is None or tgt.color != color:
                    out.append((f, r, nf, nr))
    return out


def _legal_moves(
    board: dict[tuple[int, int], Piece], color: Color,
) -> list[tuple[int, int, int, int]]:
    out = []
    for mv in _pseudo_moves(board, color):
        ff, fr, tf, tr = mv
        moved = board[(ff, fr)]
        captured = board.get((tf, tr))
        del board[(ff, fr)]
        board[(tf, tr)] = moved
        if not _in_check(board, color):
            out.append(mv)
        board[(ff, fr)] = moved
        if captured is None:
            del board[(tf, tr)]
        else:
            board[(tf, tr)] = captured
    return out


@dataclasses.dataclass
class _GState:
    spec: Game
    board: dict[tuple[int, int], Piece] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class TabletopChessSystem:
    _games: dict[str, _GState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def create_game(
        self, *, white_player: str, black_player: str,
    ) -> t.Optional[str]:
        if not white_player or not black_player:
            return None
        if white_player == black_player:
            return None
        gid = f"game_{self._next}"
        self._next += 1
        spec = Game(
            game_id=gid, white_player=white_player,
            black_player=black_player,
            state=GameState.SETUP, turn=Color.WHITE,
            winner_color=None, moves=(),
        )
        self._games[gid] = _GState(spec=spec)
        return gid

    def place_piece(
        self, *, game_id: str, file: int, rank: int,
        kind: PieceKind, color: Color,
    ) -> bool:
        if game_id not in self._games:
            return False
        st = self._games[game_id]
        if st.spec.state != GameState.SETUP:
            return False
        if not _on_board(file, rank):
            return False
        st.board[(file, rank)] = Piece(kind, color)
        return True

    def start_game(self, *, game_id: str) -> bool:
        if game_id not in self._games:
            return False
        st = self._games[game_id]
        if st.spec.state != GameState.SETUP:
            return False
        if _find_king(st.board, Color.WHITE) is None:
            return False
        if _find_king(st.board, Color.BLACK) is None:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=GameState.ACTIVE,
        )
        return True

    def move(
        self, *, game_id: str, from_file: int,
        from_rank: int, to_file: int, to_rank: int,
    ) -> bool:
        if game_id not in self._games:
            return False
        st = self._games[game_id]
        if st.spec.state != GameState.ACTIVE:
            return False
        if not _on_board(from_file, from_rank):
            return False
        if not _on_board(to_file, to_rank):
            return False
        p = st.board.get((from_file, from_rank))
        if p is None or p.color != st.spec.turn:
            return False
        legal = _legal_moves(st.board, st.spec.turn)
        key = (from_file, from_rank, to_file, to_rank)
        if key not in legal:
            return False
        captured = st.board.get((to_file, to_rank))
        del st.board[(from_file, from_rank)]
        st.board[(to_file, to_rank)] = p
        new_move = Move(
            from_file=from_file, from_rank=from_rank,
            to_file=to_file, to_rank=to_rank,
            moved_kind=p.kind, captured=captured,
            mover_color=st.spec.turn,
        )
        next_turn = _opp(st.spec.turn)
        next_legal = _legal_moves(st.board, next_turn)
        new_state = GameState.ACTIVE
        winner: t.Optional[Color] = None
        if not next_legal:
            if _in_check(st.board, next_turn):
                new_state = GameState.CHECKMATE
                winner = st.spec.turn
            else:
                new_state = GameState.STALEMATE
        st.spec = dataclasses.replace(
            st.spec, turn=next_turn, state=new_state,
            winner_color=winner,
            moves=st.spec.moves + (new_move,),
        )
        return True

    def resign(
        self, *, game_id: str, color: Color,
    ) -> bool:
        if game_id not in self._games:
            return False
        st = self._games[game_id]
        if st.spec.state != GameState.ACTIVE:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=GameState.RESIGNED,
            winner_color=_opp(color),
        )
        return True

    def offer_draw(self, *, game_id: str) -> bool:
        if game_id not in self._games:
            return False
        st = self._games[game_id]
        if st.spec.state != GameState.ACTIVE:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=GameState.DRAW,
        )
        return True

    def is_in_check(
        self, *, game_id: str, color: Color,
    ) -> bool:
        if game_id not in self._games:
            return False
        return _in_check(
            self._games[game_id].board, color,
        )

    def piece_at(
        self, *, game_id: str, file: int, rank: int,
    ) -> t.Optional[Piece]:
        if game_id not in self._games:
            return None
        return self._games[game_id].board.get(
            (file, rank),
        )

    def game(
        self, *, game_id: str,
    ) -> t.Optional[Game]:
        if game_id not in self._games:
            return None
        return self._games[game_id].spec

    def legal_moves_count(
        self, *, game_id: str,
    ) -> int:
        if game_id not in self._games:
            return 0
        st = self._games[game_id]
        return len(
            _legal_moves(st.board, st.spec.turn),
        )


__all__ = [
    "PieceKind", "Color", "GameState", "Square",
    "Piece", "Move", "Game", "TabletopChessSystem",
]
