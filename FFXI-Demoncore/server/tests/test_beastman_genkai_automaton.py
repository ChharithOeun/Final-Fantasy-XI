"""Tests for the beastman genkai automaton."""
from __future__ import annotations

from server.beastman_genkai_automaton import (
    BeastmanGenkaiAutomaton,
    GenkaiStage,
    StageStatus,
)


def _clear(g, player_id, stages, current_level):
    for s in stages:
        g.start_stage(
            player_id=player_id, stage=s,
            current_level=current_level,
        )
        g.complete_stage(
            player_id=player_id, stage=s,
        )


def test_start_50_at_level_50():
    g = BeastmanGenkaiAutomaton()
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    assert res.accepted


def test_start_50_below_level_rejected():
    g = BeastmanGenkaiAutomaton()
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=49,
    )
    assert not res.accepted


def test_start_55_before_50_rejected():
    g = BeastmanGenkaiAutomaton()
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_55,
        current_level=99,
    )
    assert not res.accepted


def test_start_55_after_50_clear():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (GenkaiStage.LEVEL_50,),
        current_level=99,
    )
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_55,
        current_level=55,
    )
    assert res.accepted


def test_complete_stage():
    g = BeastmanGenkaiAutomaton()
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    res = g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    assert res.accepted


def test_complete_unstarted_rejected():
    g = BeastmanGenkaiAutomaton()
    res = g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    assert not res.accepted


def test_complete_double_rejected():
    g = BeastmanGenkaiAutomaton()
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    res = g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    assert not res.accepted


def test_double_start_rejected():
    g = BeastmanGenkaiAutomaton()
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    assert not res.accepted


def test_can_proceed_past_50_blocked():
    g = BeastmanGenkaiAutomaton()
    assert not g.can_proceed_past(
        player_id="alice", target_level=51,
    )


def test_can_proceed_past_50_after_clear():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (GenkaiStage.LEVEL_50,),
        current_level=99,
    )
    assert g.can_proceed_past(
        player_id="alice", target_level=51,
    )


def test_can_proceed_past_75_requires_all():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (
            GenkaiStage.LEVEL_50,
            GenkaiStage.LEVEL_55,
            GenkaiStage.LEVEL_60,
            GenkaiStage.LEVEL_65,
            GenkaiStage.LEVEL_70,
        ),
        current_level=99,
    )
    assert not g.can_proceed_past(
        player_id="alice", target_level=76,
    )
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_75,
        current_level=99,
    )
    g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_75,
    )
    assert g.can_proceed_past(
        player_id="alice", target_level=76,
    )


def test_grand_proof_requires_75_done():
    g = BeastmanGenkaiAutomaton()
    res = g.start_stage(
        player_id="alice",
        stage=GenkaiStage.GRAND_PROOF,
        current_level=99,
    )
    assert not res.accepted


def test_grand_proof_unlocks_2nd_sub():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (
            GenkaiStage.LEVEL_50,
            GenkaiStage.LEVEL_55,
            GenkaiStage.LEVEL_60,
            GenkaiStage.LEVEL_65,
            GenkaiStage.LEVEL_70,
            GenkaiStage.LEVEL_75,
        ),
        current_level=99,
    )
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.GRAND_PROOF,
        current_level=99,
    )
    g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.GRAND_PROOF,
    )
    assert g.has_second_subjob_slot(player_id="alice")


def test_no_2nd_sub_until_grand_proof():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (
            GenkaiStage.LEVEL_50,
            GenkaiStage.LEVEL_55,
            GenkaiStage.LEVEL_60,
        ),
        current_level=99,
    )
    assert not g.has_second_subjob_slot(
        player_id="alice",
    )


def test_progress_for_sorted():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (
            GenkaiStage.LEVEL_50,
            GenkaiStage.LEVEL_55,
        ),
        current_level=99,
    )
    rows = g.progress_for(player_id="alice")
    assert [r.stage for r in rows] == [
        GenkaiStage.LEVEL_50,
        GenkaiStage.LEVEL_55,
    ]


def test_has_completed_stage_lookup():
    g = BeastmanGenkaiAutomaton()
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    assert not g.has_completed_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    g.complete_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )
    assert g.has_completed_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
    )


def test_status_in_progress_after_start():
    g = BeastmanGenkaiAutomaton()
    g.start_stage(
        player_id="alice",
        stage=GenkaiStage.LEVEL_50,
        current_level=50,
    )
    rows = g.progress_for(player_id="alice")
    assert rows[0].status == StageStatus.IN_PROGRESS


def test_per_player_isolation():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (GenkaiStage.LEVEL_50,),
        current_level=99,
    )
    assert not g.has_completed_stage(
        player_id="bob",
        stage=GenkaiStage.LEVEL_50,
    )


def test_total_progress():
    g = BeastmanGenkaiAutomaton()
    _clear(
        g, "alice",
        (GenkaiStage.LEVEL_50,),
        current_level=99,
    )
    assert g.total_progress() == 1
