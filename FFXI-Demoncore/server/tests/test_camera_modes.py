"""Tests for camera_modes."""
from __future__ import annotations

from server.camera_modes import CameraMode, CameraModes


def test_canonical_first_person():
    assert CameraModes.canonical_mode_for_distance(
        0.0,
    ) == CameraMode.FIRST_PERSON


def test_canonical_over_shoulder():
    assert CameraModes.canonical_mode_for_distance(
        6.0,
    ) == CameraMode.OVER_SHOULDER


def test_canonical_tactical():
    assert CameraModes.canonical_mode_for_distance(
        25.0,
    ) == CameraMode.TACTICAL


def test_canonical_top_down():
    assert CameraModes.canonical_mode_for_distance(
        70.0,
    ) == CameraMode.TOP_DOWN


def test_canonical_above_max_clamps_to_top_down():
    assert CameraModes.canonical_mode_for_distance(
        200.0,
    ) == CameraMode.TOP_DOWN


def test_canonical_band_boundaries():
    # 0.5 should still be first-person
    assert CameraModes.canonical_mode_for_distance(
        0.5,
    ) == CameraMode.FIRST_PERSON
    # 12.0 over-shoulder boundary
    assert CameraModes.canonical_mode_for_distance(
        12.0,
    ) == CameraMode.OVER_SHOULDER
    # 12.01 → tactical
    assert CameraModes.canonical_mode_for_distance(
        12.01,
    ) == CameraMode.TACTICAL


def test_set_state_happy():
    c = CameraModes()
    out = c.set_state(
        player_id="bob",
        mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=-15.0, yaw_deg=45.0,
    )
    assert out is True


def test_set_state_blank_player_blocked():
    c = CameraModes()
    out = c.set_state(
        player_id="", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=-15.0, yaw_deg=45.0,
    )
    assert out is False


def test_set_state_negative_distance_blocked():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=-1.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    assert out is False


def test_set_state_excessive_distance_blocked():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.TOP_DOWN,
        distance=200.0, pitch_deg=-90.0, yaw_deg=0.0,
    )
    assert out is False


def test_set_state_pitch_out_of_range():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=120.0, yaw_deg=0.0,
    )
    assert out is False


def test_set_state_yaw_normalizes():
    c = CameraModes()
    c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=0.0, yaw_deg=720.0,
    )
    s = c.state_for(player_id="bob")
    assert s.yaw_deg == 0.0


def test_set_state_vr_requires_zero_distance():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.VR_FIRST_PERSON,
        distance=10.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    assert out is False


def test_set_state_vr_at_zero_ok():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.VR_FIRST_PERSON,
        distance=0.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    assert out is True


def test_set_state_top_down_requires_pitch_down():
    c = CameraModes()
    # Pitch up while in TOP_DOWN doesn't make sense
    out = c.set_state(
        player_id="bob", mode=CameraMode.TOP_DOWN,
        distance=60.0, pitch_deg=30.0, yaw_deg=0.0,
    )
    assert out is False


def test_set_state_top_down_pitch_steep_ok():
    c = CameraModes()
    out = c.set_state(
        player_id="bob", mode=CameraMode.TOP_DOWN,
        distance=60.0, pitch_deg=-80.0, yaw_deg=0.0,
    )
    assert out is True


def test_state_for_unknown_none():
    c = CameraModes()
    assert c.state_for(player_id="ghost") is None


def test_state_for_returns_record():
    c = CameraModes()
    c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=-10.0, yaw_deg=90.0,
    )
    s = c.state_for(player_id="bob")
    assert s.distance == 6.0
    assert s.yaw_deg == 90.0


def test_set_state_overwrites_prior():
    c = CameraModes()
    c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    c.set_state(
        player_id="bob", mode=CameraMode.TACTICAL,
        distance=20.0, pitch_deg=-30.0, yaw_deg=180.0,
    )
    s = c.state_for(player_id="bob")
    assert s.mode == CameraMode.TACTICAL


def test_total_states():
    c = CameraModes()
    c.set_state(
        player_id="bob", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    c.set_state(
        player_id="cara", mode=CameraMode.OVER_SHOULDER,
        distance=6.0, pitch_deg=0.0, yaw_deg=0.0,
    )
    assert c.total_states() == 2


def test_five_camera_modes():
    assert len(list(CameraMode)) == 5
