"""Tests for cinematic_camera."""
from __future__ import annotations

import pytest

from server.cinematic_camera import (
    CameraProfile, CinematicCameraSystem, PROFILES,
    list_profiles, profile,
)


def test_profiles_seven_bodies():
    assert len(PROFILES) == 7


def test_profiles_have_known_names():
    expected = {
        "arri_alexa_35", "arri_alexa_mini_lf",
        "red_v_raptor_8k_vv", "sony_venice_2",
        "blackmagic_ursa_mini_pro_12k",
        "iphone_16_pro", "canon_c500_mk2",
    }
    assert set(PROFILES) == expected


def test_select_profile_happy():
    s = CinematicCameraSystem()
    p = s.select_profile("arri_alexa_35")
    assert isinstance(p, CameraProfile)
    assert s.profile is p


def test_select_profile_unknown_raises():
    s = CinematicCameraSystem()
    with pytest.raises(ValueError):
        s.select_profile("ghost_camera")


def test_default_shutter_180():
    s = CinematicCameraSystem()
    assert s.shutter_angle_deg == 180.0


def test_set_shutter_angle_happy():
    s = CinematicCameraSystem()
    s.set_shutter_angle(172.8)
    assert s.shutter_angle_deg == pytest.approx(172.8)


def test_set_shutter_angle_zero_blocked():
    s = CinematicCameraSystem()
    with pytest.raises(ValueError):
        s.set_shutter_angle(0)


def test_set_shutter_angle_over_360_blocked():
    s = CinematicCameraSystem()
    with pytest.raises(ValueError):
        s.set_shutter_angle(361)


def test_set_iso_happy():
    s = CinematicCameraSystem()
    s.select_profile("arri_alexa_35")
    s.set_iso(1600)
    assert s.iso == 1600


def test_set_iso_no_profile_raises():
    s = CinematicCameraSystem()
    with pytest.raises(RuntimeError):
        s.set_iso(1600)


def test_set_iso_out_of_range_raises():
    s = CinematicCameraSystem()
    s.select_profile("arri_alexa_35")  # iso_max=6400
    with pytest.raises(ValueError):
        s.set_iso(25600)


def test_select_profile_resnaps_iso_when_out_of_range():
    s = CinematicCameraSystem()
    s.select_profile("blackmagic_ursa_mini_pro_12k")
    s.set_iso(25000)
    s.select_profile("iphone_16_pro")  # iso_max=8000
    # snapped back to native
    assert s.iso == PROFILES["iphone_16_pro"].native_iso


def test_set_white_balance_happy():
    s = CinematicCameraSystem()
    s.set_white_balance(3200)
    assert s.white_balance_kelvin == 3200


def test_set_white_balance_out_of_range():
    s = CinematicCameraSystem()
    with pytest.raises(ValueError):
        s.set_white_balance(500)


def test_shutter_speed_seconds_180_at_24fps():
    s = CinematicCameraSystem()
    # 180 deg @ 24fps == 1/48 s
    assert s.shutter_speed_seconds(fps=24) == pytest.approx(
        1 / 48,
    )


def test_shutter_speed_seconds_zero_fps_raises():
    s = CinematicCameraSystem()
    with pytest.raises(ValueError):
        s.shutter_speed_seconds(fps=0)


def test_render_intent_contains_camera_id():
    s = CinematicCameraSystem()
    s.select_profile("sony_venice_2")
    intent = s.get_render_intent()
    assert intent["profile"] == "sony_venice_2"


def test_render_intent_carries_sensor_geometry():
    s = CinematicCameraSystem()
    s.select_profile("arri_alexa_35")
    intent = s.get_render_intent()
    assert intent["sensor_w_mm"] == pytest.approx(27.99)
    assert intent["sensor_h_mm"] == pytest.approx(19.22)


def test_render_intent_no_profile_raises():
    s = CinematicCameraSystem()
    with pytest.raises(RuntimeError):
        s.get_render_intent()


def test_iphone_high_pixel_density():
    # tiny sensor, small pixels
    p = profile("iphone_16_pro")
    assert p.pixel_pitch_um < 3.0


def test_alexa35_dr_at_least_17():
    p = profile("arri_alexa_35")
    assert p.dynamic_range_stops >= 17.0


def test_list_profiles_sorted():
    names = list_profiles()
    assert names == tuple(sorted(names))


def test_profile_unknown_raises():
    with pytest.raises(ValueError):
        profile("ghost")


def test_render_intent_includes_shutter_and_iso():
    s = CinematicCameraSystem()
    s.select_profile("canon_c500_mk2")
    s.set_shutter_angle(172.8)
    s.set_iso(1600)
    intent = s.get_render_intent()
    assert intent["shutter_angle_deg"] == pytest.approx(172.8)
    assert intent["iso"] == 1600
