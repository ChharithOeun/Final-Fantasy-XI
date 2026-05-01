"""Tests for the player state machine.

Run:  python -m pytest server/tests/test_player_state.py -v
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from player_state import (
    DeathEvent,
    DeathPenalty,
    PlayerLifecycle,
    PlayerSnapshot,
    PlayerStateMachine,
)
from player_state.machine import (
    PERMADEATH_TIMER_SECONDS,
    _compute_penalty,
)


# ----------------------------------------------------------------------
# _compute_penalty (the per-level death penalty table)
# ----------------------------------------------------------------------

def test_low_level_penalty():
    p = _compute_penalty(level=15)
    assert p.durability_pct_lost == 0.25
    assert p.levels_lost == 1
    assert p.reraise_lockout_seconds == 0
    assert p.permadeath_timer_seconds == 0


def test_high_level_penalty_at_90():
    p = _compute_penalty(level=90)
    assert p.durability_pct_lost == 0.40
    assert p.levels_lost == 1
    assert p.reraise_lockout_seconds == 2 * 86400
    assert p.permadeath_timer_seconds == 0


def test_high_level_penalty_at_98():
    p = _compute_penalty(level=98)
    assert p.durability_pct_lost == 0.40
    assert p.reraise_lockout_seconds == 2 * 86400


def test_lvl_99_penalty_full_durability_loss():
    p = _compute_penalty(level=99)
    assert p.durability_pct_lost == 1.0
    assert p.levels_lost == 0
    assert p.permadeath_timer_seconds == PERMADEATH_TIMER_SECONDS


# ----------------------------------------------------------------------
# Standard-tier death (lvl 1-89)
# ----------------------------------------------------------------------

def test_standard_death_loses_one_level():
    snap = PlayerSnapshot(player_id="alice", level=20)
    sm = PlayerStateMachine(snap)
    penalty = sm.notify_death(DeathEvent(cause="killed_by:goblin", timestamp=10))
    assert snap.lifecycle == PlayerLifecycle.KO
    assert snap.level == 19
    assert snap.death_count == 1
    assert snap.last_death_cause == "killed_by:goblin"
    assert penalty.durability_pct_lost == 0.25


def test_raise_returns_to_alive():
    snap = PlayerSnapshot(player_id="alice", level=20)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert snap.lifecycle == PlayerLifecycle.KO

    raised = sm.notify_raised(raise_tier=1, now=15)
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE


def test_repeated_death_increments_count():
    snap = PlayerSnapshot(player_id="alice", level=30)
    sm = PlayerStateMachine(snap)
    for i in range(3):
        sm.notify_death(DeathEvent(cause="x", timestamp=i * 100))
        sm.notify_raised(now=i * 100 + 10)
    assert snap.death_count == 3
    assert snap.level == 30 - 3
    assert snap.total_levels_lost_to_death == 3
    assert snap.total_durability_lost_to_death_pct == pytest.approx(0.75)


def test_floor_at_level_1():
    """Levels lost can't push the player below level 1."""
    snap = PlayerSnapshot(player_id="alice", level=1)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert snap.level == 1


# ----------------------------------------------------------------------
# Mid-tier death (lvl 90-98) with Reraise lockout
# ----------------------------------------------------------------------

def test_lvl_92_death_locks_reraise_for_2_days():
    snap = PlayerSnapshot(player_id="alice", level=92)
    sm = PlayerStateMachine(snap)
    penalty = sm.notify_death(DeathEvent(cause="x", timestamp=100))
    assert penalty.reraise_lockout_seconds == 2 * 86400
    assert snap.reraise_locked_until == 100 + 2 * 86400
    assert snap.lifecycle == PlayerLifecycle.KO


def test_raise_during_reraise_lockout_fails():
    snap = PlayerSnapshot(player_id="alice", level=92)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=100))
    raised = sm.notify_raised(now=100 + 86400)   # 1 day later, still locked
    assert raised is False
    assert snap.lifecycle == PlayerLifecycle.KO


def test_raise_after_reraise_lockout_succeeds():
    snap = PlayerSnapshot(player_id="alice", level=92)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=100))
    raised = sm.notify_raised(now=100 + 3 * 86400)   # 3 days later, unlocked
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE


# ----------------------------------------------------------------------
# Lvl 99 death — permadeath timer + Fomor transition
# ----------------------------------------------------------------------

def test_lvl_99_death_starts_permadeath_timer():
    snap = PlayerSnapshot(player_id="alice", level=99)
    sm = PlayerStateMachine(snap)
    penalty = sm.notify_death(DeathEvent(cause="killed_by_quadav", timestamp=1000))
    assert snap.lifecycle == PlayerLifecycle.KO_LVL_99
    assert snap.permadeath_started_at == 1000
    assert penalty.permadeath_timer_seconds == 3600
    assert penalty.durability_pct_lost == 1.0


def test_lvl_99_raise_within_timer_succeeds():
    """If the party Raises the player before the 1-hour timer expires,
    the player returns to ALIVE."""
    snap = PlayerSnapshot(player_id="alice", level=99)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    raised = sm.notify_raised(now=1000 + 1800)   # 30 minutes later
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE
    assert snap.permadeath_started_at is None


def test_lvl_99_permadeath_timer_expires_to_fomor():
    """If 1 hour passes without raise, player becomes Fomor."""
    snap = PlayerSnapshot(player_id="alice", level=99)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))

    # 30 minutes — timer hasn't expired
    transitioned = sm.notify_permadeath_timer_expired(now=1000 + 1800)
    assert transitioned is False
    assert snap.lifecycle == PlayerLifecycle.KO_LVL_99

    # 65 minutes — timer expired
    transitioned = sm.notify_permadeath_timer_expired(now=1000 + 3900)
    assert transitioned is True
    assert snap.lifecycle == PlayerLifecycle.FOMOR
    assert snap.fomor_at == 1000 + 3900


def test_fomor_cannot_be_raised():
    """Once Fomor, no Raise spell brings the player back."""
    snap = PlayerSnapshot(player_id="alice", level=99,
                            lifecycle=PlayerLifecycle.FOMOR,
                            fomor_at=2000)
    sm = PlayerStateMachine(snap)
    raised = sm.notify_raised(now=3000)
    assert raised is False
    assert snap.lifecycle == PlayerLifecycle.FOMOR


def test_fomor_cannot_die_again():
    """Fomor characters don't go through the normal death pipeline."""
    snap = PlayerSnapshot(player_id="alice", level=99,
                            lifecycle=PlayerLifecycle.FOMOR,
                            fomor_at=2000)
    sm = PlayerStateMachine(snap)
    with pytest.raises(ValueError, match="FOMOR"):
        sm.notify_death(DeathEvent(cause="x", timestamp=3000))


# ----------------------------------------------------------------------
# Time-until-permadeath query
# ----------------------------------------------------------------------

def test_time_until_permadeath_correct():
    snap = PlayerSnapshot(player_id="alice", level=99)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    # 30 minutes after death
    remaining = sm.time_until_permadeath(now=1000 + 1800)
    assert remaining == pytest.approx(1800.0)


def test_time_until_permadeath_none_when_alive():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    assert sm.time_until_permadeath() is None


def test_time_until_permadeath_zero_when_expired():
    snap = PlayerSnapshot(player_id="alice", level=99)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    remaining = sm.time_until_permadeath(now=1000 + 5000)   # past 1hr
    assert remaining == 0.0


# ----------------------------------------------------------------------
# State queries
# ----------------------------------------------------------------------

def test_state_queries():
    snap = PlayerSnapshot(player_id="alice", level=20)
    sm = PlayerStateMachine(snap)
    assert sm.is_alive() is True
    assert sm.is_fomor() is False
    assert sm.is_in_permadeath_timer() is False

    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert sm.is_alive() is False
    assert sm.is_fomor() is False

    snap.level = 99
    sm.snap.lifecycle = PlayerLifecycle.ALIVE   # reset for next death
    sm.notify_death(DeathEvent(cause="x", timestamp=100))
    assert sm.is_in_permadeath_timer() is True
