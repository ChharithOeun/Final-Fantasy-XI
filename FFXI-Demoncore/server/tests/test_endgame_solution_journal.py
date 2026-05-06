"""Tests for endgame_solution_journal."""
from __future__ import annotations

from server.endgame_solution_journal import (
    EndgameSolutionJournal,
    StrategyEntry,
    StrategyKey,
)
from server.puzzle_assembly_journal import PuzzleAssemblyJournal


def _setup_pieced_journal():
    j = PuzzleAssemblyJournal()
    j.define_piece(piece_id="p_alpha", label="alpha kill")
    j.define_piece(piece_id="p_dmb", label="double mb")
    j.define_solution(
        solution_id="sol_alpha", label="alpha order",
        piece_ids=["p_alpha"],
    )
    j.define_solution(
        solution_id="sol_dmb", label="double-mb",
        piece_ids=["p_dmb"],
    )
    return j


def test_define_entry_happy():
    e = EndgameSolutionJournal()
    assert e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha",
        body="Marauder → Captain → Witch.",
    ) is True


def test_define_entry_blank_solution():
    e = EndgameSolutionJournal()
    assert e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="", body="x",
    ) is False


def test_define_entry_dup_solution_blocked():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    assert e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_BRAVO,
        solution_id="sol_alpha", body="y",
    ) is False


def test_define_entry_dup_strategy_key_blocked():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    assert e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha2", body="y",
    ) is False


def test_sync_from_unlocks_entries():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="Marauder first.",
    )
    e.define_entry(
        strategy_key=StrategyKey.QUEEN_DOUBLE_MB,
        solution_id="sol_dmb", body="Two bursts on guards.",
    )
    j = _setup_pieced_journal()
    # only alpha is solved
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    new = e.sync_from(player_id="alice", journal=j)
    assert len(new) == 1
    assert new[0].strategy_key == StrategyKey.KILL_ORDER_ALPHA


def test_sync_from_idempotent():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    j = _setup_pieced_journal()
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    first = e.sync_from(player_id="alice", journal=j)
    second = e.sync_from(player_id="alice", journal=j)
    assert len(first) == 1
    assert second == ()


def test_entries_for_after_sync():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    j = _setup_pieced_journal()
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    e.sync_from(player_id="alice", journal=j)
    out = e.entries_for(player_id="alice")
    assert len(out) == 1


def test_completion_pct_partial():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    e.define_entry(
        strategy_key=StrategyKey.QUEEN_DOUBLE_MB,
        solution_id="sol_dmb", body="y",
    )
    j = _setup_pieced_journal()
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    e.sync_from(player_id="alice", journal=j)
    pct = e.completion_pct(player_id="alice")
    assert 0.49 < pct < 0.51


def test_has_full_strategy():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    e.define_entry(
        strategy_key=StrategyKey.QUEEN_DOUBLE_MB,
        solution_id="sol_dmb", body="y",
    )
    j = _setup_pieced_journal()
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    j.observe_hint(player_id="alice", hint_id="h2", piece_id="p_dmb")
    e.sync_from(player_id="alice", journal=j)
    assert e.has_full_strategy(player_id="alice") is True


def test_no_strategy_with_no_pieces():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    j = _setup_pieced_journal()
    new = e.sync_from(player_id="alice", journal=j)
    assert new == ()
    assert e.completion_pct(player_id="alice") == 0.0


def test_unknown_player_safe():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    assert e.entries_for(player_id="ghost") == ()
    assert e.completion_pct(player_id="ghost") == 0.0
    assert e.has_full_strategy(player_id="ghost") is False


def test_blank_player_returns_empty():
    e = EndgameSolutionJournal()
    j = _setup_pieced_journal()
    out = e.sync_from(player_id="", journal=j)
    assert out == ()


def test_total_entries():
    e = EndgameSolutionJournal()
    assert e.total_entries() == 0
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    e.define_entry(
        strategy_key=StrategyKey.QUEEN_DOUBLE_MB,
        solution_id="sol_dmb", body="y",
    )
    assert e.total_entries() == 2


def test_full_strategy_keys_count():
    """All 8 canonical strategy keys define-able."""
    e = EndgameSolutionJournal()
    keys = list(StrategyKey)
    for i, k in enumerate(keys):
        ok = e.define_entry(
            strategy_key=k,
            solution_id=f"sol_{i}", body=f"strategy for {k.value}",
        )
        assert ok is True
    assert e.total_entries() == 8


def test_sync_from_partial_then_full():
    e = EndgameSolutionJournal()
    e.define_entry(
        strategy_key=StrategyKey.KILL_ORDER_ALPHA,
        solution_id="sol_alpha", body="x",
    )
    e.define_entry(
        strategy_key=StrategyKey.QUEEN_DOUBLE_MB,
        solution_id="sol_dmb", body="y",
    )
    j = _setup_pieced_journal()
    j.observe_hint(player_id="alice", hint_id="h1", piece_id="p_alpha")
    first = e.sync_from(player_id="alice", journal=j)
    assert len(first) == 1
    j.observe_hint(player_id="alice", hint_id="h2", piece_id="p_dmb")
    second = e.sync_from(player_id="alice", journal=j)
    assert len(second) == 1
    assert second[0].strategy_key == StrategyKey.QUEEN_DOUBLE_MB
