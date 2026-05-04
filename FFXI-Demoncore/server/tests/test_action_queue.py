"""Tests for the action queue."""
from __future__ import annotations

from server.action_queue import (
    ActionQueueSystem,
    MAX_QUEUE_AGE,
    QueueState,
)


def test_start_action_busy():
    a = ActionQueueSystem()
    res = a.start_action(
        player_id="alice", action_id="cure_iv",
        cast_time=2.5, gcd_time=0.5,
        now_seconds=0.0,
    )
    assert res.accepted
    assert res.state == QueueState.BUSY


def test_start_empty_action_rejected():
    a = ActionQueueSystem()
    res = a.start_action(
        player_id="alice", action_id="",
        cast_time=1.0, now_seconds=0.0,
    )
    assert not res.accepted


def test_start_when_busy_rejected():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    res = a.start_action(
        player_id="alice", action_id="banish",
        cast_time=2.0, now_seconds=0.5,
    )
    assert not res.accepted


def test_queue_next_while_busy():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    res = a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.5,
    )
    assert res.accepted
    assert res.state == QueueState.QUEUED
    assert res.queued_action_id == "banish"


def test_queue_next_when_idle_rejected():
    a = ActionQueueSystem()
    res = a.queue_next(
        player_id="alice", action_id="cure",
        queued_at_seconds=0.0,
    )
    assert not res.accepted
    assert "not busy" in res.reason


def test_queue_empty_action_rejected():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    res = a.queue_next(
        player_id="alice", action_id="",
        queued_at_seconds=1.0,
    )
    assert not res.accepted


def test_tick_fires_queued_when_active_ends():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.5,
    )
    fired = a.tick(player_id="alice", now_seconds=2.5)
    assert fired == "banish"
    assert a.state_for("alice") == QueueState.IDLE


def test_tick_no_queue_returns_none():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    fired = a.tick(player_id="alice", now_seconds=2.5)
    assert fired is None
    assert a.state_for("alice") == QueueState.IDLE


def test_tick_still_busy_returns_none():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.5,
    )
    fired = a.tick(player_id="alice", now_seconds=1.0)
    assert fired is None
    assert a.state_for("alice") == QueueState.QUEUED


def test_cancel_queued_works():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.5,
    )
    assert a.cancel_queued(player_id="alice")
    assert a.state_for("alice") == QueueState.BUSY
    fired = a.tick(player_id="alice", now_seconds=2.5)
    assert fired is None


def test_cancel_unknown_returns_false():
    a = ActionQueueSystem()
    assert not a.cancel_queued(player_id="alice")


def test_cancel_no_queue_returns_false():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    assert not a.cancel_queued(player_id="alice")


def test_stale_queue_drops():
    a = ActionQueueSystem(max_queue_age_seconds=1.0)
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=10.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=0.0,
    )
    # 10s elapses; queue is older than 1.0s max age → drops
    fired = a.tick(player_id="alice", now_seconds=10.0)
    assert fired is None


def test_overwrite_queued_action_keeps_latest():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.0,
    )
    a.queue_next(
        player_id="alice", action_id="dia_iv",
        queued_at_seconds=1.5,
    )
    fired = a.tick(player_id="alice", now_seconds=2.5)
    assert fired == "dia_iv"


def test_state_for_unknown():
    a = ActionQueueSystem()
    assert a.state_for("ghost") is None


def test_queued_action_id_lookup():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="cure",
        cast_time=2.0, now_seconds=0.0,
    )
    a.queue_next(
        player_id="alice", action_id="banish",
        queued_at_seconds=1.0,
    )
    assert a.queued_action_id(
        player_id="alice",
    ) == "banish"


def test_total_players():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="x",
        cast_time=1.0,
    )
    a.start_action(
        player_id="bob", action_id="x",
        cast_time=1.0,
    )
    assert a.total_players() == 2


def test_max_queue_age_constant():
    assert MAX_QUEUE_AGE == 4.0


def test_busy_window_zero_immediate_idle():
    a = ActionQueueSystem()
    a.start_action(
        player_id="alice", action_id="instant",
        cast_time=0.0, gcd_time=0.0,
        now_seconds=0.0,
    )
    fired = a.tick(player_id="alice", now_seconds=0.0)
    # No queued action, just becomes idle
    assert fired is None
    assert a.state_for("alice") == QueueState.IDLE
