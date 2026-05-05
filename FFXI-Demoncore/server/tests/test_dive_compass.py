"""Tests for dive compass."""
from __future__ import annotations

from server.dive_compass import (
    BAND_DEPTH_M,
    DiveCompass,
    MAX_SAFE_ASCENT_RATE_M_PER_S,
)


def test_pin_target_happy():
    c = DiveCompass()
    ok = c.pin_target(player_id="p1", x=10, y=20, band=2)
    assert ok is True


def test_pin_blank_player():
    c = DiveCompass()
    ok = c.pin_target(player_id="", x=0, y=0, band=2)
    assert ok is False


def test_pin_invalid_band():
    c = DiveCompass()
    ok = c.pin_target(player_id="p1", x=0, y=0, band=99)
    assert ok is False


def test_bearing_no_pin():
    c = DiveCompass()
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert b is None


def test_bearing_north():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=0, y=100, band=2)
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert b is not None
    assert abs(b.bearing_degrees - 0.0) < 0.01
    assert abs(b.horizontal_distance - 100.0) < 0.01


def test_bearing_east():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=100, y=0, band=2)
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert abs(b.bearing_degrees - 90.0) < 0.01


def test_bearing_south():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=0, y=-50, band=2)
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert abs(b.bearing_degrees - 180.0) < 0.01


def test_bearing_west():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=-50, y=0, band=2)
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert abs(b.bearing_degrees - 270.0) < 0.01


def test_depth_delta_target_below():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=0, y=0, band=3)  # DEEP = 300
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )  # MID = 100
    # target is 200m deeper
    assert abs(b.depth_delta_meters - 200.0) < 0.01


def test_depth_delta_target_above():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=0, y=0, band=1)  # SHALLOW = 30
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=3,
    )  # DEEP = 300
    # target is 270m above
    assert abs(b.depth_delta_meters + 270.0) < 0.01


def test_clear_pin():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=0, y=0, band=2)
    ok = c.clear_pin(player_id="p1")
    assert ok is True
    assert c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    ) is None


def test_clear_unknown_pin():
    c = DiveCompass()
    assert c.clear_pin(player_id="ghost") is False


def test_ascent_warning_threshold():
    c = DiveCompass()
    warn = c.report_ascent(
        player_id="p1",
        ascent_rate_m_per_s=MAX_SAFE_ASCENT_RATE_M_PER_S + 0.5,
    )
    assert warn is True
    assert c.ascent_warning_for(player_id="p1") is True


def test_ascent_below_threshold_no_warning():
    c = DiveCompass()
    warn = c.report_ascent(
        player_id="p1",
        ascent_rate_m_per_s=MAX_SAFE_ASCENT_RATE_M_PER_S - 1.0,
    )
    assert warn is False


def test_warning_propagates_to_bearing():
    c = DiveCompass()
    c.pin_target(player_id="p1", x=10, y=10, band=2)
    c.report_ascent(
        player_id="p1",
        ascent_rate_m_per_s=MAX_SAFE_ASCENT_RATE_M_PER_S + 1.0,
    )
    b = c.bearing_for(
        player_id="p1", current_x=0, current_y=0, current_band=2,
    )
    assert b.ascent_warning is True


def test_band_depth_canonical():
    assert BAND_DEPTH_M[0] == 0.0
    assert BAND_DEPTH_M[4] == 800.0
