"""Tests for abyssal trial gauntlet."""
from __future__ import annotations

from server.abyssal_trial_gauntlet import (
    AbyssalTrialGauntlet,
    DURATION_PER_STAGE,
    GauntletStage,
)


def test_start_run_happy():
    g = AbyssalTrialGauntlet()
    assert g.start_run(player_id="p1", now_seconds=0) is True


def test_start_run_blank():
    g = AbyssalTrialGauntlet()
    assert g.start_run(player_id="", now_seconds=0) is False


def test_clear_first_stage():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    ok = g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=120, now_seconds=120,
    )
    assert ok is True


def test_clear_skip_blocked():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    ok = g.clear_stage(
        player_id="p1", stage=GauntletStage.SAHUAGIN_GAUNTLET,
        cleared_in_seconds=200, now_seconds=200,
    )
    assert ok is False


def test_clear_over_timer_fails_run():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    over = DURATION_PER_STAGE[GauntletStage.SHALLOW_TIDE] + 60
    ok = g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=over, now_seconds=over,
    )
    assert ok is False
    # subsequent clear should also fail (run is dead)
    ok2 = g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=10, now_seconds=10,
    )
    assert ok2 is False


def test_unknown_player_clear():
    g = AbyssalTrialGauntlet()
    ok = g.clear_stage(
        player_id="ghost", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=10, now_seconds=10,
    )
    assert ok is False


def test_full_run_completion():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    elapsed = 0
    for stage in GauntletStage:
        cleared_in = DURATION_PER_STAGE[stage] - 30
        elapsed += cleared_in
        g.clear_stage(
            player_id="p1", stage=stage,
            cleared_in_seconds=cleared_in,
            now_seconds=elapsed,
        )
    assert g.full_run_completed(player_id="p1") is True


def test_partial_run_no_full_credit():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=100, now_seconds=100,
    )
    assert g.full_run_completed(player_id="p1") is False


def test_tokens_held():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=100, now_seconds=100,
    )
    g.clear_stage(
        player_id="p1", stage=GauntletStage.KELP_LABYRINTH,
        cleared_in_seconds=100, now_seconds=200,
    )
    tokens = g.tokens_held(player_id="p1")
    assert tokens == (
        GauntletStage.SHALLOW_TIDE,
        GauntletStage.KELP_LABYRINTH,
    )


def test_tokens_held_empty():
    g = AbyssalTrialGauntlet()
    assert g.tokens_held(player_id="ghost") == ()


def test_current_stage_progression():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    assert g.current_stage(player_id="p1") == GauntletStage.SHALLOW_TIDE
    g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=100, now_seconds=100,
    )
    assert g.current_stage(player_id="p1") == GauntletStage.KELP_LABYRINTH


def test_current_stage_after_failure():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    g.fail_run(player_id="p1", reason="dead", now_seconds=10)
    assert g.current_stage(player_id="p1") is None


def test_current_stage_unknown():
    g = AbyssalTrialGauntlet()
    assert g.current_stage(player_id="ghost") is None


def test_fail_run_unknown():
    g = AbyssalTrialGauntlet()
    assert g.fail_run(
        player_id="ghost", reason="x", now_seconds=0,
    ) is False


def test_restart_wipes_progress():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=100, now_seconds=100,
    )
    g.start_run(player_id="p1", now_seconds=200)
    assert g.tokens_held(player_id="p1") == ()
    assert g.current_stage(player_id="p1") == GauntletStage.SHALLOW_TIDE


def test_clear_after_failure_blocked():
    g = AbyssalTrialGauntlet()
    g.start_run(player_id="p1", now_seconds=0)
    g.fail_run(player_id="p1", reason="x", now_seconds=10)
    ok = g.clear_stage(
        player_id="p1", stage=GauntletStage.SHALLOW_TIDE,
        cleared_in_seconds=100, now_seconds=100,
    )
    assert ok is False
