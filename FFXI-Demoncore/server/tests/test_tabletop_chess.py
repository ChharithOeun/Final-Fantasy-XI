"""Tests for tabletop_chess."""
from __future__ import annotations

from server.tabletop_chess import (
    TabletopChessSystem, PieceKind, Color, GameState,
)


def _bare_game(s: TabletopChessSystem) -> str:
    """Create a game with only the two kings."""
    gid = s.create_game(
        white_player="alice", black_player="bob",
    )
    s.place_piece(
        game_id=gid, file=4, rank=0,
        kind=PieceKind.KING, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=4, rank=7,
        kind=PieceKind.KING, color=Color.BLACK,
    )
    return gid


def test_create_happy():
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="alice", black_player="bob",
    )
    assert gid is not None


def test_create_empty_player():
    s = TabletopChessSystem()
    assert s.create_game(
        white_player="", black_player="bob",
    ) is None


def test_create_same_player():
    s = TabletopChessSystem()
    assert s.create_game(
        white_player="alice", black_player="alice",
    ) is None


def test_place_piece_happy():
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="a", black_player="b",
    )
    assert s.place_piece(
        game_id=gid, file=0, rank=0,
        kind=PieceKind.ROOK, color=Color.WHITE,
    ) is True


def test_place_piece_off_board():
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="a", black_player="b",
    )
    assert s.place_piece(
        game_id=gid, file=8, rank=0,
        kind=PieceKind.ROOK, color=Color.WHITE,
    ) is False


def test_place_piece_after_start_blocked():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    assert s.place_piece(
        game_id=gid, file=0, rank=0,
        kind=PieceKind.ROOK, color=Color.WHITE,
    ) is False


def test_start_requires_both_kings():
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="a", black_player="b",
    )
    s.place_piece(
        game_id=gid, file=4, rank=0,
        kind=PieceKind.KING, color=Color.WHITE,
    )
    assert s.start_game(game_id=gid) is False


def test_start_happy():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    assert s.start_game(game_id=gid) is True


def test_move_before_start_blocked():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    assert s.move(
        game_id=gid, from_file=4, from_rank=0,
        to_file=4, to_rank=1,
    ) is False


def test_move_wrong_turn_blocked():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    # White's turn; black king moving is wrong turn.
    assert s.move(
        game_id=gid, from_file=4, from_rank=7,
        to_file=4, to_rank=6,
    ) is False


def test_pawn_forward():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=0, rank=1,
        kind=PieceKind.PAWN, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=0, from_rank=1,
        to_file=0, to_rank=2,
    ) is True


def test_pawn_capture_diagonal():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=3, rank=3,
        kind=PieceKind.PAWN, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=4, rank=4,
        kind=PieceKind.PAWN, color=Color.BLACK,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=3, from_rank=3,
        to_file=4, to_rank=4,
    ) is True
    assert s.piece_at(
        game_id=gid, file=4, rank=4,
    ).color == Color.WHITE


def test_pawn_no_forward_capture():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=3, rank=3,
        kind=PieceKind.PAWN, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=3, rank=4,
        kind=PieceKind.PAWN, color=Color.BLACK,
    )
    s.start_game(game_id=gid)
    # blocked forward capture
    assert s.move(
        game_id=gid, from_file=3, from_rank=3,
        to_file=3, to_rank=4,
    ) is False


def test_knight_l_shape():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=1, rank=0,
        kind=PieceKind.KNIGHT, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=1, from_rank=0,
        to_file=2, to_rank=2,
    ) is True


def test_bishop_diagonal():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=2, rank=0,
        kind=PieceKind.BISHOP, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=2, from_rank=0,
        to_file=5, to_rank=3,
    ) is True


def test_bishop_blocked_by_friendly():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=2, rank=0,
        kind=PieceKind.BISHOP, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=4, rank=2,
        kind=PieceKind.PAWN, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=2, from_rank=0,
        to_file=5, to_rank=3,
    ) is False


def test_rook_orthogonal():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=0, rank=0,
        kind=PieceKind.ROOK, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=0, from_rank=0,
        to_file=0, to_rank=5,
    ) is True


def test_king_one_square():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    assert s.move(
        game_id=gid, from_file=4, from_rank=0,
        to_file=4, to_rank=1,
    ) is True


def test_king_cannot_move_into_check():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    # Black rook attacks rank 1
    s.place_piece(
        game_id=gid, file=0, rank=1,
        kind=PieceKind.ROOK, color=Color.BLACK,
    )
    s.start_game(game_id=gid)
    # King can't step into rank 1
    assert s.move(
        game_id=gid, from_file=4, from_rank=0,
        to_file=4, to_rank=1,
    ) is False


def test_resign_sets_winner_to_opponent():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    assert s.resign(
        game_id=gid, color=Color.WHITE,
    ) is True
    g = s.game(game_id=gid)
    assert g.state == GameState.RESIGNED
    assert g.winner_color == Color.BLACK


def test_offer_draw():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    assert s.offer_draw(game_id=gid) is True
    assert s.game(game_id=gid).state == GameState.DRAW


def test_checkmate_detected():
    """Back-rank mate: white K at e1, black K at e8,
    black rooks on a8 & b8 — white plays Ra1-a8#?
    Actually let's set up a simpler mate: black king
    on h8, white rook on a8 (gives check), white rook
    on b7 (covers escape squares g7/h7). White just
    moved that — but we need black to be in mate
    after white's move, so we set up the position
    with black to move into mate territory.

    Cleanest: white moves second rook to b7 to seal
    mate. Setup: white K e1, black K h8, white rook
    a8 (already giving check), white rook somewhere
    that on next move goes to b7. Easier: just
    pre-place rooks on a8 + b7 with white to move,
    then white plays Ke1-e2 (a tempo move). That
    doesn't deliver mate.

    Simplest reliable mate: place all attackers
    pre-mate, with one move available that delivers
    it. White K on a1, black K on h8, white rook
    on a7 (cuts off rank 7), white rook on b1.
    White moves Rb1-b8 — checkmate.
    """
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="a", black_player="b",
    )
    s.place_piece(
        game_id=gid, file=0, rank=0,
        kind=PieceKind.KING, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=7, rank=7,
        kind=PieceKind.KING, color=Color.BLACK,
    )
    # White rook on a7 (file 0, rank 6) cuts off rank 7
    s.place_piece(
        game_id=gid, file=0, rank=6,
        kind=PieceKind.ROOK, color=Color.WHITE,
    )
    # White rook on b1 (file 1, rank 0) — moves to b8
    s.place_piece(
        game_id=gid, file=1, rank=0,
        kind=PieceKind.ROOK, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    # Rb1-b8: file 1, rank 0 -> file 1, rank 7
    assert s.move(
        game_id=gid, from_file=1, from_rank=0,
        to_file=1, to_rank=7,
    ) is True
    g = s.game(game_id=gid)
    assert g.state == GameState.CHECKMATE
    assert g.winner_color == Color.WHITE


def test_stalemate_clean():
    """Classic stalemate: black king h8, white king
    e7 moves to f7, white bishop on b1 covers h7 via
    long diagonal. After Ke7-f7, black king on h8 has
    no legal move (g7+g8 attacked by Kf7, h7 attacked
    by Bb1) and is NOT in check.
    """
    s = TabletopChessSystem()
    gid = s.create_game(
        white_player="a", black_player="b",
    )
    s.place_piece(
        game_id=gid, file=7, rank=7,
        kind=PieceKind.KING, color=Color.BLACK,
    )
    s.place_piece(
        game_id=gid, file=4, rank=6,
        kind=PieceKind.KING, color=Color.WHITE,
    )
    s.place_piece(
        game_id=gid, file=1, rank=0,
        kind=PieceKind.BISHOP, color=Color.WHITE,
    )
    s.start_game(game_id=gid)
    # Ke7-f7
    assert s.move(
        game_id=gid, from_file=4, from_rank=6,
        to_file=5, to_rank=6,
    ) is True
    g = s.game(game_id=gid)
    assert g.state == GameState.STALEMATE
    assert g.winner_color is None

def test_is_in_check_query():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.place_piece(
        game_id=gid, file=4, rank=4,
        kind=PieceKind.ROOK, color=Color.BLACK,
    )
    s.start_game(game_id=gid)
    assert s.is_in_check(
        game_id=gid, color=Color.WHITE,
    ) is True


def test_legal_moves_count_initial():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    # Only white king on e1, can move to 5 legal
    # squares (d1,d2,e2,f1,f2) — black king far away.
    assert s.legal_moves_count(game_id=gid) == 5


def test_move_records_history():
    s = TabletopChessSystem()
    gid = _bare_game(s)
    s.start_game(game_id=gid)
    s.move(
        game_id=gid, from_file=4, from_rank=0,
        to_file=4, to_rank=1,
    )
    g = s.game(game_id=gid)
    assert len(g.moves) == 1
    assert g.moves[0].mover_color == Color.WHITE


def test_unknown_game():
    s = TabletopChessSystem()
    assert s.game(game_id="ghost") is None
    assert s.move(
        game_id="ghost", from_file=0, from_rank=0,
        to_file=1, to_rank=1,
    ) is False
