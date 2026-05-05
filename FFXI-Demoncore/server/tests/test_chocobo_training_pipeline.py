"""Tests for the chocobo training pipeline."""
from __future__ import annotations

from server.chocobo_training_pipeline import (
    ChocoboTrainingPipeline,
    Phase,
    PhaseStatus,
)


_MONTH = 30 * 86_400


def test_start_ability_basic():
    p = ChocoboTrainingPipeline()
    res = p.start_phase(
        player_id="kraw",
        chick_id="c1",
        phase=Phase.ABILITY,
        now_seconds=0,
        resources_paid=True,
    )
    assert res.accepted
    assert res.deadline_at == _MONTH


def test_start_no_resources():
    p = ChocoboTrainingPipeline()
    res = p.start_phase(
        player_id="kraw",
        chick_id="c1",
        phase=Phase.ABILITY,
        now_seconds=0,
        resources_paid=False,
    )
    assert not res.accepted


def test_start_mount_before_ability_blocked():
    p = ChocoboTrainingPipeline()
    res = p.start_phase(
        player_id="kraw",
        chick_id="c1",
        phase=Phase.MOUNT,
        now_seconds=0,
        resources_paid=True,
    )
    assert not res.accepted


def test_start_combat_before_mount_blocked():
    p = ChocoboTrainingPipeline()
    res = p.start_phase(
        player_id="kraw",
        chick_id="c1",
        phase=Phase.COMBAT,
        now_seconds=0,
        resources_paid=True,
    )
    assert not res.accepted


def test_progress_basic():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    res = p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=10,
    )
    assert res.accepted
    assert res.sessions_done == 10


def test_progress_clamps():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    res = p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=999,
    )
    assert res.sessions_done == 30


def test_progress_phase_not_started():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    res = p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, sessions_done=5,
    )
    assert not res.accepted


def test_progress_zero_sessions():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    res = p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=0,
    )
    assert not res.accepted


def test_complete_too_early_duration():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=30,
    )
    res = p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=86_400,
    )
    assert not res.accepted


def test_complete_sessions_incomplete():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=10,
    )
    res = p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=_MONTH,
    )
    assert not res.accepted


def test_complete_basic():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=30,
    )
    res = p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=_MONTH,
    )
    assert res.accepted
    assert res.status == PhaseStatus.COMPLETED


def test_full_pipeline_to_combat():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=_MONTH,
    )
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=_MONTH,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=2 * _MONTH,
    )
    res = p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.COMBAT, now_seconds=2 * _MONTH,
        resources_paid=True,
    )
    assert res.accepted


def test_combat_phase_optional_can_skip():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=_MONTH,
    )
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=_MONTH,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=2 * _MONTH,
    )
    snap = p.status_for(player_id="kraw", chick_id="c1")
    assert snap.statuses[Phase.MOUNT] == PhaseStatus.COMPLETED
    assert snap.statuses[Phase.COMBAT] == PhaseStatus.NOT_STARTED


def test_combat_phase_can_start_anytime_after_mount():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=_MONTH,
    )
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=_MONTH,
        resources_paid=True,
    )
    p.progress(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, sessions_done=30,
    )
    p.complete_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.MOUNT, now_seconds=2 * _MONTH,
    )
    # Wait many months before starting combat training
    res = p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.COMBAT, now_seconds=12 * _MONTH,
        resources_paid=True,
    )
    assert res.accepted


def test_status_for_unknown_chick():
    p = ChocoboTrainingPipeline()
    snap = p.status_for(player_id="ghost", chick_id="c1")
    assert snap.statuses[Phase.ABILITY] == PhaseStatus.NOT_STARTED


def test_start_phase_already_started():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    res = p.start_phase(
        player_id="kraw", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=10,
        resources_paid=True,
    )
    assert not res.accepted


def test_per_player_per_chick_isolation():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="alice", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    snap = p.status_for(player_id="bob", chick_id="c1")
    assert snap.statuses[Phase.ABILITY] == PhaseStatus.NOT_STARTED


def test_total_pipelines():
    p = ChocoboTrainingPipeline()
    p.start_phase(
        player_id="alice", chick_id="c1",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    p.start_phase(
        player_id="bob", chick_id="c2",
        phase=Phase.ABILITY, now_seconds=0,
        resources_paid=True,
    )
    assert p.total_pipelines() == 2
