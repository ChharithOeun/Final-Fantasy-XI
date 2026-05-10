"""Tests for photo_mode."""
from __future__ import annotations

import pytest

from server.photo_mode import (
    ExportTarget,
    Filter,
    MAX_FOCAL_MM,
    MAX_FOCUS_M,
    MAX_T_STOP,
    MIN_FOCAL_MM,
    MIN_FOCUS_M,
    MIN_T_STOP,
    PhotoCamera,
    PhotoCapture,
    PhotoModeSystem,
    PhotoState,
)


def _sys() -> PhotoModeSystem:
    return PhotoModeSystem()


def _activate(sys_, player="p1"):
    sys_.enter_photo_mode(player)
    sys_.set_camera(
        player,
        "arri_alexa_35",
        "cooke_s7i_50mm",
        50.0,
        2.8,
        3.0,
        (0.0, 0.0, 1.6),
        (1.0, 0.0, 1.6),
    )


# ---- enum coverage ----

def test_state_count():
    assert len(list(PhotoState)) == 4


def test_state_inactive_present():
    assert PhotoState.INACTIVE in list(PhotoState)


def test_state_pose_lock_present():
    assert PhotoState.ACTIVE_POSE_LOCK in list(PhotoState)


def test_export_target_count():
    assert len(list(ExportTarget)) == 5


def test_export_target_has_exr():
    assert ExportTarget.EXR_HDR in list(ExportTarget)


def test_filter_count():
    assert len(list(Filter)) == 8


def test_filter_has_trailer_master():
    assert Filter.DEMONCORE_TRAILER_MASTER in list(Filter)


# ---- enter / exit ----

def test_enter_photo_mode_from_inactive():
    s = _sys()
    state = s.enter_photo_mode("p1")
    assert state == PhotoState.ACTIVE_FREEROAM


def test_enter_photo_mode_idempotent():
    s = _sys()
    s.enter_photo_mode("p1")
    state = s.enter_photo_mode("p1")
    assert state == PhotoState.ACTIVE_FREEROAM


def test_exit_photo_mode():
    s = _sys()
    s.enter_photo_mode("p1")
    state = s.exit_photo_mode("p1")
    assert state == PhotoState.INACTIVE


def test_exit_clears_camera():
    s = _sys()
    _activate(s)
    s.exit_photo_mode("p1")
    assert s.camera_for("p1") is None


def test_state_for_default_inactive():
    s = _sys()
    assert s.state_for("p1") == PhotoState.INACTIVE


def test_is_active_default_false():
    s = _sys()
    assert s.is_active("p1") is False


def test_is_active_after_enter():
    s = _sys()
    s.enter_photo_mode("p1")
    assert s.is_active("p1") is True


def test_enter_empty_player_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.enter_photo_mode("")


# ---- camera ----

def test_set_camera_when_inactive_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.set_camera(
            "p1", "arri_alexa_35", "cooke_s7i_50mm",
            50.0, 2.8, 3.0,
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
        )


def test_set_camera_focal_out_of_range_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_camera(
            "p1", "arri_alexa_35", "cooke_s7i_50mm",
            MAX_FOCAL_MM + 1, 2.8, 3.0,
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
        )


def test_set_camera_t_stop_out_of_range_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_camera(
            "p1", "arri_alexa_35", "cooke_s7i_50mm",
            50.0, MAX_T_STOP + 1.0, 3.0,
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
        )


def test_set_camera_focus_out_of_range_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_camera(
            "p1", "arri_alexa_35", "cooke_s7i_50mm",
            50.0, 2.8, MIN_FOCUS_M / 2,
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
        )


def test_set_camera_returns_camera():
    s = _sys()
    s.enter_photo_mode("p1")
    cam = s.set_camera(
        "p1", "arri_alexa_35", "cooke_s7i_50mm",
        50.0, 2.8, 3.0,
        (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
    )
    assert isinstance(cam, PhotoCamera)
    assert cam.focal_length_mm == 50.0


def test_set_dolly_path_attaches_keyframes():
    s = _sys()
    _activate(s)
    cam = s.set_dolly_path(
        "p1",
        [(0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (2.0, 1.0, 1.0)],
    )
    assert len(cam.dolly_path) == 3


def test_set_dolly_path_without_camera_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_dolly_path("p1", [(0.0, 0.0, 0.0)])


# ---- pose lock ----

def test_pose_lock_changes_state():
    s = _sys()
    _activate(s)
    state = s.pose_lock("p1", "subject")
    assert state == PhotoState.ACTIVE_POSE_LOCK
    assert s.pose_lock_target("p1") == "subject"


def test_pose_lock_when_inactive_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.pose_lock("p1", "subject")


def test_pose_lock_empty_target_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.pose_lock("p1", "")


def test_release_pose_lock():
    s = _sys()
    _activate(s)
    s.pose_lock("p1", "subject")
    state = s.release_pose_lock("p1")
    assert state == PhotoState.ACTIVE_FREEROAM
    assert s.pose_lock_target("p1") == ""


# ---- TOD / weather / LUT ----

def test_scrub_time_of_day():
    s = _sys()
    s.enter_photo_mode("p1")
    hour = s.scrub_time_of_day("p1", 6.5)
    assert hour == 6.5
    assert s.time_of_day("p1") == 6.5


def test_scrub_tod_out_of_range_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.scrub_time_of_day("p1", 24.0)


def test_set_weather_override():
    s = _sys()
    s.enter_photo_mode("p1")
    w = s.set_weather_override("p1", "aurora")
    assert w == "aurora"


def test_set_weather_unknown_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_weather_override("p1", "tornado")


def test_set_film_grade():
    s = _sys()
    s.enter_photo_mode("p1")
    lut = s.set_film_grade("p1", "kodak_vision3_250d")
    assert lut == "kodak_vision3_250d"
    assert s.film_grade_for("p1") == "kodak_vision3_250d"


def test_set_film_grade_empty_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.set_film_grade("p1", "")


# ---- HUD toggles ----

def test_set_hide_hud():
    s = _sys()
    s.enter_photo_mode("p1")
    h = s.set_hide_hud("p1", True)
    assert h is True


def test_set_hide_other_players():
    s = _sys()
    s.enter_photo_mode("p1")
    h = s.set_hide_other_players("p1", True)
    assert h is True


# ---- filters ----

def test_apply_filter_appends():
    s = _sys()
    s.enter_photo_mode("p1")
    chain = s.apply_filter("p1", Filter.VIGNETTE, 0.5)
    assert (Filter.VIGNETTE, 0.5) in chain


def test_apply_filter_replaces_existing():
    s = _sys()
    s.enter_photo_mode("p1")
    s.apply_filter("p1", Filter.VIGNETTE, 0.5)
    chain = s.apply_filter("p1", Filter.VIGNETTE, 0.8)
    assert len(chain) == 1
    assert chain[0] == (Filter.VIGNETTE, 0.8)


def test_apply_filter_zero_intensity_removes():
    s = _sys()
    s.enter_photo_mode("p1")
    s.apply_filter("p1", Filter.VIGNETTE, 0.5)
    chain = s.apply_filter("p1", Filter.VIGNETTE, 0.0)
    assert chain == ()


def test_apply_filter_invalid_intensity_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.apply_filter("p1", Filter.BLOOM, 1.5)


# ---- recommended ----

def test_recommended_for_bastok_markets():
    s = _sys()
    cam, lens, focal = s.recommended_camera_for(
        "bastok_markets",
    )
    assert cam == "arri_alexa_35"
    assert "cooke" in lens.lower()


def test_recommended_for_unknown_falls_back():
    s = _sys()
    cam, lens, focal = s.recommended_camera_for(
        "nonexistent_zone",
    )
    assert cam  # non-empty
    assert lens
    assert focal > 0


def test_has_recommended_known_zone():
    s = _sys()
    assert s.has_recommended_for("bastok_markets")


def test_has_recommended_unknown_zone():
    s = _sys()
    assert not s.has_recommended_for("nonexistent")


# ---- capture ----

def test_capture_when_inactive_raises():
    s = _sys()
    with pytest.raises(ValueError):
        s.capture("p1", ExportTarget.PNG_4K)


def test_capture_without_camera_raises():
    s = _sys()
    s.enter_photo_mode("p1")
    with pytest.raises(ValueError):
        s.capture("p1", ExportTarget.PNG_4K)


def test_capture_returns_photo_capture():
    s = _sys()
    _activate(s)
    cap = s.capture(
        "p1", ExportTarget.PNG_4K,
        zone_id="bastok_markets",
        character_name="Aragorn",
        now_ms=42,
    )
    assert isinstance(cap, PhotoCapture)
    assert cap.target == ExportTarget.PNG_4K
    assert "bastok_markets" in cap.sticker_overlay
    assert "Aragorn" in cap.sticker_overlay
    assert cap.captured_at_ms == 42


def test_capture_increments_counter():
    s = _sys()
    _activate(s)
    s.capture("p1", ExportTarget.PNG_4K)
    s.capture("p1", ExportTarget.PNG_4K)
    assert s.capture_count("p1") == 2


def test_capture_id_unique():
    s = _sys()
    _activate(s)
    c1 = s.capture("p1", ExportTarget.PNG_4K)
    c2 = s.capture("p1", ExportTarget.PNG_4K)
    assert c1.capture_id != c2.capture_id


def test_capture_extension_matches_target():
    s = _sys()
    _activate(s)
    c = s.capture("p1", ExportTarget.EXR_HDR)
    assert c.file_path_stub.endswith(".exr")
    c2 = s.capture("p1", ExportTarget.MP4_60S_4K)
    assert c2.file_path_stub.endswith(".mp4")
    c3 = s.capture("p1", ExportTarget.GIF_5S)
    assert c3.file_path_stub.endswith(".gif")


def test_capture_returns_to_freeroam():
    s = _sys()
    _activate(s)
    s.capture("p1", ExportTarget.PNG_4K)
    assert s.state_for("p1") == PhotoState.ACTIVE_FREEROAM


def test_capture_returns_to_pose_lock():
    s = _sys()
    _activate(s)
    s.pose_lock("p1", "subject")
    s.capture("p1", ExportTarget.PNG_4K)
    assert s.state_for("p1") == PhotoState.ACTIVE_POSE_LOCK


def test_capture_carries_filter_chain():
    s = _sys()
    _activate(s)
    s.apply_filter("p1", Filter.SEPIA, 0.7)
    s.apply_filter("p1", Filter.VIGNETTE, 0.3)
    c = s.capture("p1", ExportTarget.PNG_4K)
    assert (Filter.SEPIA, 0.7) in c.filter_chain
    assert (Filter.VIGNETTE, 0.3) in c.filter_chain


def test_capture_carries_film_grade():
    s = _sys()
    _activate(s)
    s.set_film_grade("p1", "demoncore_standard")
    c = s.capture("p1", ExportTarget.PNG_4K)
    assert c.film_grade_lut == "demoncore_standard"


def test_capture_carries_time_of_day():
    s = _sys()
    _activate(s)
    s.scrub_time_of_day("p1", 18.0)
    c = s.capture("p1", ExportTarget.PNG_4K)
    assert c.time_of_day_hour == 18.0


# ---- constants ----

def test_min_focal_constant():
    assert MIN_FOCAL_MM > 0


def test_max_focal_greater_than_min():
    assert MAX_FOCAL_MM > MIN_FOCAL_MM


def test_t_stop_range_constants():
    assert MIN_T_STOP < MAX_T_STOP


def test_focus_range_constants():
    assert MIN_FOCUS_M < MAX_FOCUS_M
