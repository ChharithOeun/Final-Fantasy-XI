"""Tests for spectator_mode."""
from __future__ import annotations

import pytest

from server.spectator_mode import (
    DEFAULT_ZOOM_MAX_M,
    DEFAULT_ZOOM_MIN_M,
    ROLLING_BUFFER_SECONDS,
    ReplayClip,
    ReplayEvent,
    SceneSwitchSuggestion,
    SpectatorMode,
    SpectatorSession,
    SpectatorSystem,
)


def _sys() -> SpectatorSystem:
    return SpectatorSystem()


# ---- enum coverage ----

def test_mode_count():
    assert len(list(SpectatorMode)) == 6


def test_mode_has_director_cam():
    assert SpectatorMode.DIRECTOR_CAM in list(SpectatorMode)


def test_mode_has_replay_playback():
    assert SpectatorMode.REPLAY_PLAYBACK in list(SpectatorMode)


def test_mode_has_broadcast_overlay():
    assert SpectatorMode.BROADCAST_OVERLAY in list(
        SpectatorMode,
    )


def test_replay_event_count():
    assert len(list(ReplayEvent)) == 4


def test_replay_event_has_critical_kill():
    assert ReplayEvent.CRITICAL_KILL in list(ReplayEvent)


def test_replay_event_has_world_first_nm():
    assert ReplayEvent.WORLD_FIRST_NM in list(ReplayEvent)


# ---- session lifecycle ----

def test_start_spectator_returns_session():
    s = _sys()
    sess = s.start_spectator(
        "spec1", "playerA", SpectatorMode.FREE_CAM,
    )
    assert isinstance(sess, SpectatorSession)
    assert sess.spec_id == "spec1"
    assert sess.watched_player_id == "playerA"
    assert sess.mode == SpectatorMode.FREE_CAM


def test_start_empty_spec_id_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.start_spectator("", "p1", SpectatorMode.FREE_CAM)


def test_start_empty_watched_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.start_spectator("spec1", "", SpectatorMode.FREE_CAM)


def test_start_duplicate_spec_id_raises():
    s = _sys()
    s.start_spectator(
        "spec1", "playerA", SpectatorMode.FREE_CAM,
    )
    with pytest.raises(ValueError):
        s.start_spectator(
            "spec1", "playerB", SpectatorMode.FREE_CAM,
        )


def test_end_spectator_removes_session():
    s = _sys()
    s.start_spectator(
        "spec1", "playerA", SpectatorMode.FREE_CAM,
    )
    s.end_spectator("spec1")
    assert not s.has_session("spec1")


def test_end_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.end_spectator("ghost")


def test_get_session_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_session("ghost")


def test_session_count():
    s = _sys()
    s.start_spectator(
        "spec1", "playerA", SpectatorMode.FREE_CAM,
    )
    s.start_spectator(
        "spec2", "playerB", SpectatorMode.FREE_CAM,
    )
    assert s.session_count() == 2


def test_broadcast_overlay_visible_for_broadcast_mode():
    s = _sys()
    sess = s.start_spectator(
        "spec1", "p1", SpectatorMode.BROADCAST_OVERLAY,
    )
    assert sess.broadcast_overlay_visible is True
    assert sess.dps_visible is True


def test_overlay_invisible_for_free_cam():
    s = _sys()
    sess = s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    assert sess.broadcast_overlay_visible is False


def test_default_zoom_range():
    s = _sys()
    sess = s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    assert sess.allowed_zoom_range_m == (
        DEFAULT_ZOOM_MIN_M, DEFAULT_ZOOM_MAX_M,
    )


# ---- set_mode ----

def test_set_mode_changes_mode():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_mode(
        "spec1", SpectatorMode.DIRECTOR_CAM,
    )
    assert sess.mode == SpectatorMode.DIRECTOR_CAM


def test_set_mode_enables_overlay_for_broadcast():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_mode(
        "spec1", SpectatorMode.BROADCAST_OVERLAY,
    )
    assert sess.broadcast_overlay_visible is True
    assert sess.dps_visible is True


def test_set_mode_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.set_mode("ghost", SpectatorMode.FREE_CAM)


# ---- overlay visibility ----

def test_set_overlay_friendly_names():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_overlay_visibility(
        "spec1", friendly_names=False,
    )
    assert sess.friendly_names_visible is False


def test_set_overlay_hp_bars():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_overlay_visibility(
        "spec1", hp_bars=False,
    )
    assert sess.hp_bars_visible is False


def test_set_overlay_dps():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_overlay_visibility("spec1", dps=True)
    assert sess.dps_visible is True


def test_set_overlay_preserves_others():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_overlay_visibility(
        "spec1", friendly_names=False,
    )
    assert sess.hp_bars_visible is True


# ---- zoom range ----

def test_set_zoom_range():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    sess = s.set_zoom_range("spec1", 5.0, 50.0)
    assert sess.allowed_zoom_range_m == (5.0, 50.0)


def test_set_zoom_negative_raises():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    with pytest.raises(ValueError):
        s.set_zoom_range("spec1", -1.0, 10.0)


def test_set_zoom_min_greater_than_max_raises():
    s = _sys()
    s.start_spectator(
        "spec1", "p1", SpectatorMode.FREE_CAM,
    )
    with pytest.raises(ValueError):
        s.set_zoom_range("spec1", 50.0, 10.0)


# ---- buffer ----

def test_push_snapshot_grows_buffer():
    s = _sys()
    n = s.push_snapshot("p1", 1000, {"hp": 100})
    assert n == 1
    n2 = s.push_snapshot("p1", 2000, {"hp": 90})
    assert n2 == 2


def test_buffer_size_default_zero():
    s = _sys()
    assert s.buffer_size("p1") == 0


def test_buffer_evicts_old_entries():
    s = _sys()
    s.push_snapshot("p1", 0, {"hp": 100})
    s.push_snapshot("p1", 10_000, {"hp": 95})
    # 80 seconds later, the early entry should evict
    # because the buffer window is 60 seconds.
    s.push_snapshot("p1", 80_000, {"hp": 50})
    buf = s.replay_buffer_for("p1")
    # Only entries within 80_000 - 60_000 = 20_000 onwards.
    assert all(t_ >= 20_000 for t_, _ in buf)


def test_push_empty_player_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.push_snapshot("", 1000, {})


def test_replay_buffer_for_unknown_empty():
    s = _sys()
    assert s.replay_buffer_for("ghost") == ()


# ---- save replay ----

def test_save_replay_creates_clip():
    s = _sys()
    s.push_snapshot("p1", 1000, {"hp": 100})
    s.push_snapshot("p1", 2000, {"hp": 90})
    clip = s.save_replay(
        "p1", ReplayEvent.CRITICAL_KILL, 2000,
    )
    assert isinstance(clip, ReplayClip)
    assert clip.event_kind == ReplayEvent.CRITICAL_KILL


def test_save_replay_increments_counter():
    s = _sys()
    s.push_snapshot("p1", 1000, {"hp": 100})
    c1 = s.save_replay(
        "p1", ReplayEvent.CRITICAL_KILL, 1000,
    )
    c2 = s.save_replay(
        "p1", ReplayEvent.DEATH, 2000,
    )
    assert c1.clip_id != c2.clip_id
    assert s.clip_count() == 2


def test_save_replay_empty_buffer_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.save_replay(
            "p1", ReplayEvent.CRITICAL_KILL, 1000,
        )


def test_save_replay_empty_player_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.save_replay(
            "", ReplayEvent.CRITICAL_KILL, 1000,
        )


def test_get_clip_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.get_clip("ghost")


def test_clip_file_path_stub():
    s = _sys()
    s.push_snapshot("p1", 1000, {})
    clip = s.save_replay(
        "p1", ReplayEvent.MAGIC_BURST_BOSS_KILL, 1000,
    )
    assert clip.file_path_stub.endswith(".mp4")
    assert "p1" in clip.file_path_stub


# ---- broadcast metadata ----

def test_broadcast_metadata_basic():
    s = _sys()
    s.start_spectator(
        "spec1", "playerA", SpectatorMode.BROADCAST_OVERLAY,
    )
    md = s.broadcast_metadata_for("spec1")
    assert "ndi_source_name" in md
    assert "rtmp_stream_key" in md
    assert md["mode"] == "broadcast_overlay"
    assert md["overlay_visible"] is True
    assert md["elements"]["dps_chart_bottom"] is True


def test_broadcast_metadata_free_cam_minimal():
    s = _sys()
    s.start_spectator(
        "spec1", "playerA", SpectatorMode.FREE_CAM,
    )
    md = s.broadcast_metadata_for("spec1")
    assert md["mode"] == "free_cam"
    assert md["overlay_visible"] is False


def test_broadcast_metadata_unknown_raises():
    s = _sys()
    with pytest.raises(KeyError):
        s.broadcast_metadata_for("ghost")


# ---- scene switch ----

def test_suggest_scene_for_boss_phase_change():
    s = _sys()
    sug = s.suggest_scene_switch("boss_phase_changed")
    assert isinstance(sug, SceneSwitchSuggestion)
    assert sug.target_scene == "wide_combat"


def test_suggest_scene_for_critical_kill():
    s = _sys()
    sug = s.suggest_scene_switch("critical_kill")
    assert sug.target_scene == "subject_close"


def test_suggest_scene_for_unknown():
    s = _sys()
    sug = s.suggest_scene_switch("nonexistent_cue")
    assert sug.target_scene == "default"


# ---- director cam ----

def test_director_cam_combat_fast_picks_handheld():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "combat_close",
        "tempo": "fast",
        "focus_targets": 2,
    })
    assert out == "handheld"


def test_director_cam_dialogue_one_picks_close_up():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "dialogue",
        "tempo": "medium",
        "focus_targets": 1,
    })
    assert out == "close_up"


def test_director_cam_dialogue_two_picks_ots():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "dialogue",
        "tempo": "medium",
        "focus_targets": 2,
    })
    assert out == "over_the_shoulder"


def test_director_cam_reveal_picks_wide():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "reveal",
        "tempo": "slow",
        "focus_targets": 0,
    })
    assert out == "wide_establishing"


def test_director_cam_default_medium():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "exploration",
        "tempo": "medium",
        "focus_targets": 0,
    })
    assert out == "medium"


def test_director_cam_action_set_piece_overhead():
    s = _sys()
    out = s.director_cam_pick({
        "scene_kind": "action_set_piece",
        "tempo": "fast",
        "focus_targets": 0,
    })
    assert out == "overhead"


# ---- constants ----

def test_rolling_buffer_seconds_constant():
    assert ROLLING_BUFFER_SECONDS == 60


def test_default_zoom_constants():
    assert DEFAULT_ZOOM_MIN_M < DEFAULT_ZOOM_MAX_M
