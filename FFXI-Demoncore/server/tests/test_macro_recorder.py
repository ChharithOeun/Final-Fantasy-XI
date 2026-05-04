"""Tests for the macro recorder."""
from __future__ import annotations

from server.macro_recorder import (
    ActionKind,
    MacroRecorder,
    MAX_ACTIONS_PER_RECORDING,
    MAX_INTER_ACTION_DELAY,
    MIN_INTER_ACTION_DELAY,
)


def test_start_creates_recording():
    r = MacroRecorder()
    rec = r.start(
        player_id="alice", recording_id="cure_combo",
        label="Cure Combo",
        now_seconds=0.0,
    )
    assert rec is not None
    assert rec.is_recording


def test_start_when_already_recording_rejected():
    r = MacroRecorder()
    r.start(
        player_id="alice", recording_id="a",
    )
    res = r.start(
        player_id="alice", recording_id="b",
    )
    assert res is None


def test_start_double_id_rejected():
    r = MacroRecorder()
    r.start(
        player_id="alice", recording_id="a",
    )
    r.stop(player_id="alice")
    res = r.start(
        player_id="alice", recording_id="a",
    )
    assert res is None


def test_capture_succeeds():
    r = MacroRecorder()
    r.start(
        player_id="alice", recording_id="m",
    )
    res = r.capture(
        player_id="alice",
        kind=ActionKind.SPELL,
        payload="cure_iv",
        at_seconds=0.0,
    )
    assert res.accepted


def test_capture_without_active_rejected():
    r = MacroRecorder()
    res = r.capture(
        player_id="alice",
        kind=ActionKind.SPELL,
        payload="cure",
        at_seconds=0.0,
    )
    assert not res.accepted


def test_capture_empty_payload_rejected():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    res = r.capture(
        player_id="alice",
        kind=ActionKind.SPELL,
        payload="",
        at_seconds=0.0,
    )
    assert not res.accepted


def test_capture_full_recording_rejected():
    r = MacroRecorder(max_actions=2)
    r.start(player_id="alice", recording_id="m")
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="a", at_seconds=0.0,
    )
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="b", at_seconds=1.0,
    )
    res = r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="c", at_seconds=2.0,
    )
    assert not res.accepted


def test_inter_action_delay_clamped_min():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="a", at_seconds=0.0,
    )
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="b", at_seconds=0.1,    # too fast
    )
    rec = r.recording(
        player_id="alice", recording_id="m",
    )
    assert (
        rec.actions[0].delay_after_seconds
        == MIN_INTER_ACTION_DELAY
    )


def test_inter_action_delay_clamped_max():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="a", at_seconds=0.0,
    )
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="b", at_seconds=999.0,
    )
    rec = r.recording(
        player_id="alice", recording_id="m",
    )
    assert (
        rec.actions[0].delay_after_seconds
        == MAX_INTER_ACTION_DELAY
    )


def test_stop_finalizes():
    r = MacroRecorder()
    r.start(
        player_id="alice", recording_id="m",
        now_seconds=0.0,
    )
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="cure", at_seconds=0.0,
    )
    rec = r.stop(player_id="alice", now_seconds=10.0)
    assert rec is not None
    assert not rec.is_recording
    assert rec.stopped_at_seconds == 10.0


def test_stop_without_active_returns_none():
    r = MacroRecorder()
    assert r.stop(player_id="alice") is None


def test_capture_after_stop_rejected():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.stop(player_id="alice")
    res = r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="cure", at_seconds=0.0,
    )
    assert not res.accepted


def test_replay_lines_renders_actions():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="cure_iv", at_seconds=0.0,
    )
    r.capture(
        player_id="alice", kind=ActionKind.JOB_ABILITY,
        payload="convert", at_seconds=2.0,
    )
    r.stop(player_id="alice")
    lines = r.replay_lines(
        player_id="alice", recording_id="m",
    )
    assert any("/spell cure_iv" in l for l in lines)
    assert any("/job_ability convert" in l for l in lines)
    assert any(l.startswith("/wait") for l in lines)


def test_replay_active_returns_empty():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.capture(
        player_id="alice", kind=ActionKind.SPELL,
        payload="cure", at_seconds=0.0,
    )
    assert r.replay_lines(
        player_id="alice", recording_id="m",
    ) == ()


def test_delete_finalized_recording():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    r.stop(player_id="alice")
    assert r.delete(
        player_id="alice", recording_id="m",
    )


def test_delete_active_rejected():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="m")
    assert not r.delete(
        player_id="alice", recording_id="m",
    )


def test_delete_unknown():
    r = MacroRecorder()
    assert not r.delete(
        player_id="alice", recording_id="ghost",
    )


def test_is_recording_flag():
    r = MacroRecorder()
    assert not r.is_recording(player_id="alice")
    r.start(player_id="alice", recording_id="m")
    assert r.is_recording(player_id="alice")
    r.stop(player_id="alice")
    assert not r.is_recording(player_id="alice")


def test_total_recordings_per_player():
    r = MacroRecorder()
    r.start(player_id="alice", recording_id="a")
    r.stop(player_id="alice")
    r.start(player_id="alice", recording_id="b")
    r.stop(player_id="alice")
    assert r.total_recordings(player_id="alice") == 2


def test_recording_unknown_returns_none():
    r = MacroRecorder()
    assert r.recording(
        player_id="alice", recording_id="ghost",
    ) is None


def test_max_actions_constant():
    assert MAX_ACTIONS_PER_RECORDING == 64
