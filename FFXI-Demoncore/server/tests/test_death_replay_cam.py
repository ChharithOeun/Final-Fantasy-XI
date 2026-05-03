"""Tests for the death replay cam."""
from __future__ import annotations

from server.death_replay_cam import (
    DEFAULT_BUFFER_WINDOW_SECONDS,
    DeathReplayCam,
    FrameKind,
)


def test_capture_frame_creates_buffer():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    assert cam.total_active_buffers() == 1


def test_capture_frame_clamps_hp():
    cam = DeathReplayCam()
    f = cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=999,
    )
    assert f.player_hp_pct == 100
    f2 = cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=-5,
    )
    assert f2.player_hp_pct == 0


def test_buffer_prunes_old_frames():
    cam = DeathReplayCam(buffer_window_seconds=10)
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.capture_frame(
        player_id="alice", kind=FrameKind.AUTO_ATTACK,
        timestamp_seconds=20.0, player_hp_pct=80,
    )
    buf = cam._buffers["alice"]
    # First frame at t=0 should be pruned
    timestamps = [f.timestamp_seconds for f in buf]
    assert 0.0 not in timestamps


def test_buffer_max_frames_cap():
    cam = DeathReplayCam(max_frames=3)
    for i in range(5):
        cam.capture_frame(
            player_id="alice", kind=FrameKind.IDLE,
            timestamp_seconds=float(i),
            player_hp_pct=100,
        )
    assert len(cam._buffers["alice"]) == 3


def test_freeze_on_death_creates_clip():
    cam = DeathReplayCam()
    for i in range(5):
        cam.capture_frame(
            player_id="alice", kind=FrameKind.AUTO_ATTACK,
            timestamp_seconds=float(i),
            player_hp_pct=100 - i * 10,
        )
    cam.capture_frame(
        player_id="alice", kind=FrameKind.KO_HIT,
        timestamp_seconds=5.0, player_hp_pct=0,
        actor_id="orc_chief",
    )
    clip = cam.freeze_on_death(
        player_id="alice",
        captured_at_seconds=5.0,
        cause_of_death="overwhelmed by orc raid",
    )
    assert clip is not None
    assert len(clip.frames) == 6
    assert clip.cause_of_death == "overwhelmed by orc raid"
    # KO_HIT frame should be present
    assert any(
        f.kind == FrameKind.KO_HIT for f in clip.frames
    )


def test_freeze_unknown_player_returns_none():
    cam = DeathReplayCam()
    assert cam.freeze_on_death(
        player_id="ghost", captured_at_seconds=0.0,
    ) is None


def test_freeze_empty_buffer_returns_none():
    """A captured-then-pruned-empty buffer should still yield
    None. The simplest test: no captures at all."""
    cam = DeathReplayCam()
    assert cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    ) is None


def test_freeze_clears_live_buffer():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    assert "alice" not in cam._buffers
    assert cam.total_active_buffers() == 0


def test_clip_for_lookup():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    clip = cam.clip_for("alice")
    assert clip is not None
    assert clip.player_id == "alice"


def test_clip_for_unknown_returns_none():
    cam = DeathReplayCam()
    assert cam.clip_for("ghost") is None


def test_per_player_buffers_isolated():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.capture_frame(
        player_id="bob", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    # Bob's buffer should still be active
    assert "bob" in cam._buffers


def test_party_hp_pcts_preserved():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.AUTO_ATTACK,
        timestamp_seconds=0.0, player_hp_pct=100,
        party_hp_pcts=(("bob", 80), ("carol", 95)),
    )
    clip = cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    frame = clip.frames[0]
    assert ("bob", 80) in frame.party_hp_pcts


def test_reset_buffer():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    assert cam.reset_buffer(player_id="alice")
    assert cam.total_active_buffers() == 0


def test_reset_unknown_returns_false():
    cam = DeathReplayCam()
    assert not cam.reset_buffer(player_id="ghost")


def test_window_seconds_in_clip():
    cam = DeathReplayCam(buffer_window_seconds=15)
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    clip = cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    assert clip.window_seconds == 15


def test_total_frozen_clips():
    cam = DeathReplayCam()
    cam.capture_frame(
        player_id="alice", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.freeze_on_death(
        player_id="alice", captured_at_seconds=0.0,
    )
    cam.capture_frame(
        player_id="bob", kind=FrameKind.IDLE,
        timestamp_seconds=0.0, player_hp_pct=100,
    )
    cam.freeze_on_death(
        player_id="bob", captured_at_seconds=0.0,
    )
    assert cam.total_frozen_clips() == 2


def test_default_window_constant():
    assert DEFAULT_BUFFER_WINDOW_SECONDS == 30
