"""Tests for strategy_walkthrough_log."""
from __future__ import annotations

from server.strategy_walkthrough_log import (
    RunResult, StrategyWalkthroughLog,
)


def test_record_run_happy():
    log = StrategyWalkthroughLog()
    out = log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    assert out is not None
    assert out.result == RunResult.WIN


def test_record_run_blank_player_blocked():
    log = StrategyWalkthroughLog()
    out = log.record_run(
        player_id="", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    assert out is None


def test_record_run_blank_guide_blocked():
    log = StrategyWalkthroughLog()
    out = log.record_run(
        player_id="bob", guide_id="",
        result=RunResult.WIN, ran_at=1000,
    )
    assert out is None


def test_stats_for_empty_zero():
    log = StrategyWalkthroughLog()
    s = log.stats_for(guide_id="g1")
    assert s.runs_total == 0
    assert s.win_rate == 0.0


def test_stats_for_counts_results():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=2000,
    )
    log.record_run(
        player_id="cara", guide_id="g1",
        result=RunResult.WIPE, ran_at=3000,
    )
    log.record_run(
        player_id="dan", guide_id="g1",
        result=RunResult.BAILED, ran_at=4000,
    )
    s = log.stats_for(guide_id="g1")
    assert s.wins == 2
    assert s.wipes == 1
    assert s.bailed == 1
    assert s.runs_total == 4


def test_win_rate_bailed_excluded():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="cara", guide_id="g1",
        result=RunResult.WIPE, ran_at=2000,
    )
    log.record_run(
        player_id="dan", guide_id="g1",
        result=RunResult.BAILED, ran_at=3000,
    )
    s = log.stats_for(guide_id="g1")
    # 1 win, 1 wipe → 50% (bailed excluded)
    assert s.win_rate == 0.5


def test_win_rate_zero_decisive_runs():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.BAILED, ran_at=1000,
    )
    s = log.stats_for(guide_id="g1")
    assert s.win_rate == 0.0


def test_stats_for_isolates_per_guide():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="bob", guide_id="g2",
        result=RunResult.WIPE, ran_at=2000,
    )
    s1 = log.stats_for(guide_id="g1")
    s2 = log.stats_for(guide_id="g2")
    assert s1.wins == 1
    assert s2.wipes == 1
    assert s1.wipes == 0
    assert s2.wins == 0


def test_stats_for_window_filters_old():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIPE, ran_at=2_000_000,
    )
    s = log.stats_for_window(
        guide_id="g1", now=2_000_100, day_window=7,
    )
    assert s.wins == 0
    assert s.wipes == 1


def test_stats_for_window_zero_window():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    s = log.stats_for_window(
        guide_id="g1", now=2000, day_window=0,
    )
    assert s.runs_total == 0


def test_runs_for_player_sorted():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=3000,
    )
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIPE, ran_at=1000,
    )
    out = log.runs_for_player(
        player_id="bob", guide_id="g1",
    )
    assert out[0].ran_at == 1000


def test_runs_for_player_isolates():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="cara", guide_id="g1",
        result=RunResult.WIPE, ran_at=2000,
    )
    out = log.runs_for_player(
        player_id="bob", guide_id="g1",
    )
    assert len(out) == 1


def test_runs_for_player_other_guide_excluded():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="bob", guide_id="g2",
        result=RunResult.WIPE, ran_at=2000,
    )
    out = log.runs_for_player(
        player_id="bob", guide_id="g1",
    )
    assert len(out) == 1


def test_total_runs():
    log = StrategyWalkthroughLog()
    log.record_run(
        player_id="bob", guide_id="g1",
        result=RunResult.WIN, ran_at=1000,
    )
    log.record_run(
        player_id="cara", guide_id="g2",
        result=RunResult.WIPE, ran_at=2000,
    )
    assert log.total_runs() == 2


def test_three_run_results():
    assert len(list(RunResult)) == 3
