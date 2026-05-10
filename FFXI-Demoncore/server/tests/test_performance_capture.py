"""Tests for performance_capture."""
from __future__ import annotations

import pytest

from server.performance_capture import (
    CaptureDevice, DeviceKind, DEVICES,
    PerformanceCaptureSystem, SessionState,
    best_device_for, device, list_devices,
)


def test_devices_five_supported():
    assert len(DEVICES) == 5


def test_devices_have_known_names():
    expected = {
        "live_link_face", "rokoko_smartsuit_pro_ii",
        "optitrack_prime_41", "faceware_mark_iv",
        "metahuman_animator",
    }
    assert set(DEVICES) == expected


def test_live_link_face_is_facial_arkit_52():
    d = device("live_link_face")
    assert d.kind == DeviceKind.FACIAL
    assert d.tracker_count == 52
    assert d.sample_rate_hz == 60


def test_rokoko_is_body_19_imu():
    d = device("rokoko_smartsuit_pro_ii")
    assert d.kind == DeviceKind.BODY
    assert d.tracker_count == 19


def test_optitrack_is_body_high_rate():
    d = device("optitrack_prime_41")
    assert d.kind == DeviceKind.BODY
    assert d.sample_rate_hz == 240
    assert d.lighting_required is True


def test_metahuman_animator_offline_zero_latency():
    d = device("metahuman_animator")
    assert d.latency_ms == 0.0


def test_device_unknown_raises():
    with pytest.raises(ValueError):
        device("kinect_v2")


def test_list_devices_sorted():
    names = list_devices()
    assert names == tuple(sorted(names))


def test_register_device_happy():
    s = PerformanceCaptureSystem()
    d = s.register_device("live_link_face")
    assert isinstance(d, CaptureDevice)
    assert s.is_registered("live_link_face")


def test_register_unknown_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(ValueError):
        s.register_device("ghost_rig")


def test_calibrate_happy():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    assert s.is_calibrated("live_link_face")


def test_calibrate_without_register_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(RuntimeError):
        s.calibrate("live_link_face")


def test_start_session_happy_multidevice():
    s = PerformanceCaptureSystem()
    for n in ("live_link_face", "rokoko_smartsuit_pro_ii"):
        s.register_device(n)
        s.calibrate(n)
    rec = s.start_session(
        actor_id="curilla",
        devices=("live_link_face", "rokoko_smartsuit_pro_ii"),
    )
    assert rec.actor_id == "curilla"
    assert rec.state == SessionState.CAPTURING
    assert "live_link_face" in rec.devices
    assert "rokoko_smartsuit_pro_ii" in rec.devices
    assert s.active_take == rec.take_id


def test_start_session_no_devices_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(ValueError):
        s.start_session(actor_id="a", devices=())


def test_start_session_no_actor_raises():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    with pytest.raises(ValueError):
        s.start_session(actor_id="", devices=("live_link_face",))


def test_start_session_uncalibrated_raises():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    with pytest.raises(RuntimeError):
        s.start_session(
            actor_id="a", devices=("live_link_face",),
        )


def test_start_session_unregistered_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(RuntimeError):
        s.start_session(
            actor_id="a", devices=("optitrack_prime_41",),
        )


def test_only_one_active_take_at_a_time():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    s.start_session(
        actor_id="a", devices=("live_link_face",),
    )
    with pytest.raises(RuntimeError):
        s.start_session(
            actor_id="b", devices=("live_link_face",),
        )


def test_end_session_moves_to_post():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    s.start_session(
        actor_id="a", devices=("live_link_face",),
    )
    rec = s.end_session()
    assert rec.state == SessionState.POST
    assert s.active_take is None


def test_end_session_without_active_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(RuntimeError):
        s.end_session()


def test_archive_happy():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    rec = s.start_session(
        actor_id="a", devices=("live_link_face",),
    )
    s.end_session()
    archived = s.archive(rec.take_id)
    assert archived.state == SessionState.ARCHIVED


def test_archive_unknown_raises():
    s = PerformanceCaptureSystem()
    with pytest.raises(ValueError):
        s.archive("take_99")


def test_archive_without_post_raises():
    s = PerformanceCaptureSystem()
    s.register_device("live_link_face")
    s.calibrate("live_link_face")
    rec = s.start_session(
        actor_id="a", devices=("live_link_face",),
    )
    with pytest.raises(RuntimeError):
        s.archive(rec.take_id)


def test_best_device_for_known_scene_kinds():
    assert best_device_for("dialogue") == "live_link_face"
    assert best_device_for("combat") == "optitrack_prime_41"
    assert (
        best_device_for("field")
        == "rokoko_smartsuit_pro_ii"
    )
    assert best_device_for("pickup") == "metahuman_animator"


def test_best_device_for_unknown_falls_back():
    # default falls to LLF — cheapest hero facial
    assert best_device_for("__nope__") == "live_link_face"


def test_lifecycle_round_trip():
    s = PerformanceCaptureSystem()
    for n in ("live_link_face", "rokoko_smartsuit_pro_ii"):
        s.register_device(n)
        s.calibrate(n)
    rec = s.start_session(
        actor_id="volker",
        devices=("live_link_face", "rokoko_smartsuit_pro_ii"),
    )
    assert rec.state == SessionState.CAPTURING
    posted = s.end_session()
    assert posted.state == SessionState.POST
    archived = s.archive(rec.take_id)
    assert archived.state == SessionState.ARCHIVED
    # should appear in takes() list
    assert any(
        t.take_id == rec.take_id for t in s.takes()
    )
