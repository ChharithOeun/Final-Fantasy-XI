"""Tests for camera_zoom_curve."""
from __future__ import annotations

from server.camera_zoom_curve import (
    SNAP_DISTANCES, CameraZoomCurve,
)


def test_yalms_per_tick_fp_band():
    assert CameraZoomCurve.yalms_per_tick(0.0) == 0.5
    assert CameraZoomCurve.yalms_per_tick(3.0) == 0.5


def test_yalms_per_tick_mid_band():
    assert CameraZoomCurve.yalms_per_tick(10.0) == 2.0
    assert CameraZoomCurve.yalms_per_tick(20.0) == 2.0


def test_yalms_per_tick_top_band():
    assert CameraZoomCurve.yalms_per_tick(50.0) == 5.0
    assert CameraZoomCurve.yalms_per_tick(75.0) == 5.0


def test_snap_to_nearest_at_snap():
    assert CameraZoomCurve.snap_to_nearest(0.0) == 0.0
    assert CameraZoomCurve.snap_to_nearest(6.0) == 6.0
    assert CameraZoomCurve.snap_to_nearest(75.0) == 75.0


def test_snap_to_nearest_within_radius():
    # 5.5 is within 1.5 of 6.0
    assert CameraZoomCurve.snap_to_nearest(5.5) == 6.0
    # 24.0 within 1.5 of 25.0
    assert CameraZoomCurve.snap_to_nearest(24.0) == 25.0


def test_snap_to_nearest_outside_radius():
    # 10.0 is not within 1.5 of any snap
    assert CameraZoomCurve.snap_to_nearest(10.0) == 10.0


def test_apply_tick_zero_ticks_just_snaps():
    out = CameraZoomCurve.apply_tick(
        current_distance=5.7, ticks=0,
    )
    assert out == 6.0


def test_apply_tick_zoom_out_from_fp():
    # 1 tick at 0.0 (yalms_per_tick=0.5) → 0.5
    out = CameraZoomCurve.apply_tick(
        current_distance=0.0, ticks=1,
    )
    # 0.5 is within 1.5 of snap 0.0, snaps back
    assert out == 0.0


def test_apply_tick_zoom_out_far():
    # Start at 6.0; zoom out 4 ticks
    # At 6 → +2 = 8, +2=10, +2=12, +2=14
    # 14 is not near any snap; result 14
    out = CameraZoomCurve.apply_tick(
        current_distance=6.0, ticks=4,
    )
    assert out == 14.0


def test_apply_tick_zoom_in_from_top_down():
    # Start at 75.0; zoom in 1 tick (yalms_per_tick=5)
    # 75 → 70; not near snap; result 70
    out = CameraZoomCurve.apply_tick(
        current_distance=75.0, ticks=-1,
    )
    assert out == 70.0


def test_apply_tick_clamps_at_zero():
    out = CameraZoomCurve.apply_tick(
        current_distance=0.0, ticks=-10,
    )
    assert out == 0.0


def test_apply_tick_clamps_at_max():
    out = CameraZoomCurve.apply_tick(
        current_distance=80.0, ticks=10,
    )
    assert out == 80.0


def test_apply_tick_crosses_band():
    # Start at 5.0 (FP band, 0.5/tick), zoom out 4 ticks
    # 5.0 -> 5.5 -> 6.0 (mid band starts at 6) ->
    # at 6.0 next tick uses 2.0/tick: 6.0 -> 8.0
    # But we already used 3 ticks getting to 6.0, so
    # only 1 tick remains (we did 4 total).
    # Sequence: 5.0 +0.5=5.5, +0.5=6.0, +2.0=8.0,
    # +2.0=10.0
    out = CameraZoomCurve.apply_tick(
        current_distance=5.0, ticks=4,
    )
    assert out == 10.0


def test_apply_tick_into_snap_zone():
    # Start at 23.5; zoom out 1 tick (2.0/tick) → 25.5
    # 25.5 is within 1.5 of snap 25.0, snaps to 25.0
    out = CameraZoomCurve.apply_tick(
        current_distance=23.5, ticks=1,
    )
    assert out == 25.0


def test_apply_tick_zoom_all_the_way_out():
    # Start at 0.0, zoom out aggressively (50 ticks)
    out = CameraZoomCurve.apply_tick(
        current_distance=0.0, ticks=50,
    )
    # Should land somewhere high; shouldn't exceed 80
    assert 0.0 <= out <= 80.0


def test_five_snap_distances():
    assert len(SNAP_DISTANCES) == 5


def test_snap_distances_ascending():
    assert list(SNAP_DISTANCES) == sorted(SNAP_DISTANCES)
