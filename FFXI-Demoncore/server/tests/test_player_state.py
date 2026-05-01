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
    INSTANCE_EVICT_SECONDS,
    PERMADEATH_THRESHOLD_LEVEL,
    PERMADEATH_TIMER_SECONDS,
    _compute_penalty,
)


# ----------------------------------------------------------------------
# _compute_penalty (per-tier death penalty table)
# ----------------------------------------------------------------------

def test_low_level_no_permadeath():
    """Levels 1-29: standard knockout, no permadeath."""
    p = _compute_penalty(level=15)
    assert p.durability_pct_lost == 0.10
    assert p.levels_lost == 1
    assert p.permadeath_timer_seconds == 0
    assert p.reraise_lockout_seconds == 0


def test_lvl_29_still_no_permadeath():
    """Boundary: level 29 is the last sub-permadeath level."""
    p = _compute_penalty(level=29)
    assert p.permadeath_timer_seconds == 0


def test_lvl_30_first_permadeath():
    """Permadeath kicks in at level 30."""
    p = _compute_penalty(level=30)
    assert p.permadeath_timer_seconds == PERMADEATH_TIMER_SECONDS
    assert p.durability_pct_lost == 0.25
    assert p.levels_lost == 1


def test_mid_level_permadeath():
    p = _compute_penalty(level=50)
    assert p.permadeath_timer_seconds == PERMADEATH_TIMER_SECONDS
    assert p.durability_pct_lost == 0.25


def test_high_level_permadeath_at_90():
    """Lvl 90+ adds the 2-day Reraise lockout."""
    p = _compute_penalty(level=90)
    assert p.durability_pct_lost == 0.40
    assert p.permadeath_timer_seconds == PERMADEATH_TIMER_SECONDS
    assert p.reraise_lockout_seconds == 2 * 86400


def test_lvl_99_apex_penalty():
    """Lvl 99: full durability loss, no level loss, permadeath timer."""
    p = _compute_penalty(level=99)
    assert p.durability_pct_lost == 1.0
    assert p.levels_lost == 0
    assert p.permadeath_timer_seconds == PERMADEATH_TIMER_SECONDS


# ----------------------------------------------------------------------
# Standard death (lvl 1-29) — no permadeath
# ----------------------------------------------------------------------

def test_lvl_15_death_standard_ko():
    snap = PlayerSnapshot(player_id="alice", level=15)
    sm = PlayerStateMachine(snap)
    penalty = sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert snap.lifecycle == PlayerLifecycle.KO
    assert snap.level == 14
    assert penalty.durability_pct_lost == 0.10
    assert sm.is_in_permadeath_timer() is False


def test_lvl_15_raise_no_lockout():
    snap = PlayerSnapshot(player_id="alice", level=15)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    raised = sm.notify_raised(now=15)
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE


# ----------------------------------------------------------------------
# Lvl 30+ permadeath — the apex difficulty pillar
# ----------------------------------------------------------------------

def test_lvl_30_death_starts_permadeath_timer():
    """First level where permadeath applies."""
    snap = PlayerSnapshot(player_id="alice", level=30)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    assert snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER
    assert snap.permadeath_started_at == 1000
    assert sm.is_in_permadeath_timer() is True


def test_lvl_50_death_starts_permadeath_timer():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    assert snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER


def test_lvl_30_raise_within_timer_succeeds():
    snap = PlayerSnapshot(player_id="alice", level=30)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    raised = sm.notify_raised(now=1000 + 1800)   # 30 min in
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE
    assert snap.permadeath_started_at is None


def test_lvl_30_permadeath_timer_expires_to_fomor():
    """Lvl 30+ transitions to FOMOR after 1 hour."""
    snap = PlayerSnapshot(player_id="alice", level=30)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))

    # 30 min — not yet
    assert sm.notify_permadeath_timer_expired(now=1000 + 1800) is False
    assert snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER

    # 65 min — past
    assert sm.notify_permadeath_timer_expired(now=1000 + 3900) is True
    assert snap.lifecycle == PlayerLifecycle.FOMOR


def test_lvl_92_reraise_lockout_2_days():
    snap = PlayerSnapshot(player_id="alice", level=92)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=100))
    assert snap.reraise_locked_until == 100 + 2 * 86400


def test_lvl_92_raise_during_lockout_fails():
    snap = PlayerSnapshot(player_id="alice", level=92)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=100))
    raised = sm.notify_raised(now=100 + 86400)
    assert raised is False


# ----------------------------------------------------------------------
# Instance KO — 3-min in-instance window
# ----------------------------------------------------------------------

def test_instance_death_starts_3min_window():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(
        DeathEvent(cause="killed_by_boss", in_instance=True, timestamp=2000),
        instance_id="bcnm_maat_genkai_1",
    )
    assert snap.lifecycle == PlayerLifecycle.KO_INSTANCE
    assert snap.instance_evict_at == 2000 + INSTANCE_EVICT_SECONDS
    assert snap.instance_id == "bcnm_maat_genkai_1"
    assert snap.permadeath_started_at is None


def test_instance_raise_within_3min_succeeds():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", in_instance=True, timestamp=2000))
    # Raised at 2 min — within 3-min window
    raised = sm.notify_raised(now=2000 + 120)
    assert raised is True
    assert snap.lifecycle == PlayerLifecycle.ALIVE
    assert snap.instance_evict_at is None
    assert snap.instance_id is None


def test_instance_evict_after_3min_starts_permadeath():
    """3 min elapsed without raise → warp out + permadeath countdown."""
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", in_instance=True, timestamp=2000))

    # 2 min elapsed — not yet
    assert sm.notify_instance_evict_timer_expired(now=2000 + 120) is False
    assert snap.lifecycle == PlayerLifecycle.KO_INSTANCE

    # 3 min elapsed — evict + permadeath kicks in (lvl 50 ≥ 30)
    assert sm.notify_instance_evict_timer_expired(now=2000 + 180) is True
    assert snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER
    assert snap.permadeath_started_at == 2000 + 180
    assert snap.instance_evict_at is None


def test_instance_evict_at_low_level_goes_to_ko_not_permadeath():
    """A lvl-15 player evicted from instance just transitions to KO,
    not the permadeath timer."""
    snap = PlayerSnapshot(player_id="alice", level=15)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", in_instance=True, timestamp=2000))
    sm.notify_instance_evict_timer_expired(now=2000 + 200)
    assert snap.lifecycle == PlayerLifecycle.KO
    assert sm.is_in_permadeath_timer() is False


def test_instance_full_permadeath_chain():
    """Full chain: instance death → 3min → evict → 1hr → FOMOR."""
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", in_instance=True, timestamp=0))

    # 3 min → evict
    sm.notify_instance_evict_timer_expired(now=180)
    assert snap.lifecycle == PlayerLifecycle.KO_PERMADEATH_TIMER

    # +1 hr → FOMOR
    transitioned = sm.notify_permadeath_timer_expired(now=180 + 3700)
    assert transitioned is True
    assert snap.lifecycle == PlayerLifecycle.FOMOR


def test_time_until_instance_evict_query():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", in_instance=True, timestamp=2000))
    remaining = sm.time_until_instance_evict(now=2000 + 60)
    assert remaining == pytest.approx(120.0)   # 2 min remaining


# ----------------------------------------------------------------------
# Cumulative tracking + edge cases
# ----------------------------------------------------------------------

def test_repeated_death_increments_count():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    for i in range(3):
        sm.notify_death(DeathEvent(cause="x", timestamp=i * 100))
        sm.notify_raised(now=i * 100 + 30)
    assert snap.death_count == 3
    assert snap.total_levels_lost_to_death == 3
    assert snap.total_durability_lost_to_death_pct == pytest.approx(0.75)


def test_floor_at_level_1():
    snap = PlayerSnapshot(player_id="alice", level=1)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert snap.level == 1


def test_fomor_cannot_be_raised():
    snap = PlayerSnapshot(player_id="alice", level=99,
                            lifecycle=PlayerLifecycle.FOMOR,
                            fomor_at=2000)
    sm = PlayerStateMachine(snap)
    raised = sm.notify_raised(now=3000)
    assert raised is False
    assert snap.lifecycle == PlayerLifecycle.FOMOR


def test_fomor_cannot_die_again():
    snap = PlayerSnapshot(player_id="alice", level=99,
                            lifecycle=PlayerLifecycle.FOMOR)
    sm = PlayerStateMachine(snap)
    with pytest.raises(ValueError, match="FOMOR"):
        sm.notify_death(DeathEvent(cause="x", timestamp=3000))


def test_state_query_helpers():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    assert sm.is_alive() is True
    assert sm.is_in_permadeath_timer() is False
    assert sm.is_in_instance_ko() is False

    sm.notify_death(DeathEvent(cause="x", timestamp=10))
    assert sm.is_alive() is False
    assert sm.is_in_permadeath_timer() is True


def test_time_until_permadeath_zero_when_expired():
    snap = PlayerSnapshot(player_id="alice", level=50)
    sm = PlayerStateMachine(snap)
    sm.notify_death(DeathEvent(cause="x", timestamp=1000))
    remaining = sm.time_until_permadeath(now=1000 + 5000)
    assert remaining == 0.0
