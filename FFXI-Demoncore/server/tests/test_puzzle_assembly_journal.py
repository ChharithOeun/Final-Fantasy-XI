"""Tests for puzzle_assembly_journal."""
from __future__ import annotations

from server.puzzle_assembly_journal import PuzzleAssemblyJournal


def test_define_piece_happy():
    j = PuzzleAssemblyJournal()
    assert j.define_piece(
        piece_id="p_kill_alpha", label="Alpha kill order",
    ) is True


def test_define_piece_blank_id_blocked():
    j = PuzzleAssemblyJournal()
    assert j.define_piece(piece_id="", label="x") is False


def test_define_piece_dup_blocked():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    assert j.define_piece(piece_id="p1", label="y") is False


def test_define_solution_happy():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    j.define_piece(piece_id="p2", label="y")
    assert j.define_solution(
        solution_id="s1", label="solution",
        piece_ids=["p1", "p2"],
    ) is True


def test_define_solution_unknown_piece_blocked():
    j = PuzzleAssemblyJournal()
    assert j.define_solution(
        solution_id="s1", label="x", piece_ids=["ghost"],
    ) is False


def test_observe_hint_records():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    assert j.observe_hint(
        player_id="alice", hint_id="h1", piece_id="p1",
    ) is True


def test_observe_hint_dup_blocked():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    assert j.observe_hint(
        player_id="alice", hint_id="h1", piece_id="p1",
    ) is False


def test_observe_unknown_piece_blocked():
    j = PuzzleAssemblyJournal()
    assert j.observe_hint(
        player_id="alice", hint_id="h1", piece_id="ghost",
    ) is False


def test_piece_confirmed_after_one_hint_default():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    assert j.piece_confirmed(player_id="alice", piece_id="p1") is True


def test_piece_not_confirmed_below_threshold():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x", hints_needed=3)
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    j.observe_hint(player_id="alice", hint_id="h2", piece_id="p1")
    assert j.piece_confirmed(player_id="alice", piece_id="p1") is False


def test_piece_confirmed_at_threshold():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x", hints_needed=3)
    for hid in ["h1", "h2", "h3"]:
        j.observe_hint(player_id="alice", hint_id=hid, piece_id="p1")
    assert j.piece_confirmed(player_id="alice", piece_id="p1") is True


def test_pieces_for_lists_only_confirmed():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x", hints_needed=1)
    j.define_piece(piece_id="p2", label="y", hints_needed=2)
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p2")
    out = j.pieces_for(player_id="alice")
    assert len(out) == 1
    assert out[0].piece_id == "p1"


def test_solution_unlocks_when_all_pieces_confirmed():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    j.define_piece(piece_id="p2", label="y")
    j.define_solution(
        solution_id="s1", label="winning",
        piece_ids=["p1", "p2"],
    )
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    assert j.solutions_unlocked(player_id="alice") == ()
    j.observe_hint(player_id="alice", hint_id="h2", piece_id="p2")
    out = j.solutions_unlocked(player_id="alice")
    assert len(out) == 1
    assert out[0].solution_id == "s1"


def test_unknown_player_safe():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    assert j.piece_confirmed(player_id="ghost", piece_id="p1") is False
    assert j.pieces_for(player_id="ghost") == ()
    assert j.solutions_unlocked(player_id="ghost") == ()


def test_hints_observed_count():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x", hints_needed=3)
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    j.observe_hint(player_id="alice", hint_id="h2", piece_id="p1")
    assert j.hints_observed_count(
        player_id="alice", piece_id="p1",
    ) == 2


def test_per_player_isolation():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p1", label="x")
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p1")
    assert j.piece_confirmed(player_id="alice", piece_id="p1") is True
    assert j.piece_confirmed(player_id="bob", piece_id="p1") is False
