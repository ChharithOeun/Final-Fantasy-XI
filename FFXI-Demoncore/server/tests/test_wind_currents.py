"""Tests for wind currents."""
from __future__ import annotations

from server.wind_currents import (
    JET_STREAM_BAND,
    Wind,
    WindCurrents,
)


def test_register_zone_happy():
    w = WindCurrents()
    assert w.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    ) is True


def test_register_zone_blank():
    w = WindCurrents()
    assert w.register_zone(zone_id="", wind_by_band={}) is False


def test_wind_at_unknown():
    w = WindCurrents()
    assert w.wind_at(zone_id="ghost", band=2) is None


def test_wind_at_returns():
    w = WindCurrents()
    wnd = Wind(dx=1, dy=0, speed=1)
    w.register_zone(zone_id="bay", wind_by_band={2: wnd})
    assert w.wind_at(zone_id="bay", band=2) == wnd


def test_aligned_with_wind_boosts():
    w = WindCurrents()
    w.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    )
    # ship heading east, wind blowing east -> boost
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e.boost_pct > 0
    assert e.effective_speed > e.base_speed


def test_against_wind_penalizes():
    w = WindCurrents()
    w.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    )
    # ship heading west, wind blowing east -> penalty
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=-1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e.boost_pct < 0
    assert e.effective_speed < e.base_speed


def test_perpendicular_no_effect():
    w = WindCurrents()
    w.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    )
    # ship heading north, wind blowing east -> ~0
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=0, ship_dir_y=1, ship_base_speed=10.0,
    )
    assert e.boost_pct == 0


def test_no_wind_no_effect():
    w = WindCurrents()
    w.register_zone(zone_id="bay", wind_by_band={})
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e.boost_pct == 0
    assert e.effective_speed == 10.0


def test_register_jet_stream():
    w = WindCurrents()
    ok = w.register_jet_stream(
        jet_id="js1", zone_id="bay",
        dx=1, dy=0, speed=2.0,
    )
    assert ok is True
    js = w.jet_streams_in(zone_id="bay")
    assert len(js) == 1
    assert js[0].band == JET_STREAM_BAND


def test_register_jet_stream_blank():
    w = WindCurrents()
    assert w.register_jet_stream(
        jet_id="", zone_id="bay", dx=1, dy=0, speed=1,
    ) is False


def test_jet_stream_only_at_stratosphere():
    w = WindCurrents()
    w.register_jet_stream(
        jet_id="js1", zone_id="bay",
        dx=1, dy=0, speed=1,
    )
    # at MID band there's no jet stream, even though one exists in zone
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e.in_jet_stream is False


def test_jet_stream_multiplier_applied():
    w = WindCurrents()
    w.register_zone(
        zone_id="bay",
        wind_by_band={JET_STREAM_BAND: Wind(dx=1, dy=0, speed=1)},
    )
    # WITH a jet stream
    w.register_jet_stream(
        jet_id="js1", zone_id="bay",
        dx=1, dy=0, speed=1.0,
    )
    e_jet = w.effect_on(
        zone_id="bay", band=JET_STREAM_BAND,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e_jet.in_jet_stream is True
    # comparison without jet
    w_nojet = WindCurrents()
    w_nojet.register_zone(
        zone_id="bay",
        wind_by_band={JET_STREAM_BAND: Wind(dx=1, dy=0, speed=1)},
    )
    e_nojet = w_nojet.effect_on(
        zone_id="bay", band=JET_STREAM_BAND,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e_jet.boost_pct > e_nojet.boost_pct


def test_unknown_zone_no_effect():
    w = WindCurrents()
    e = w.effect_on(
        zone_id="ghost", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e.effective_speed == 10.0
    assert e.boost_pct == 0


def test_zero_ship_dir_safe():
    w = WindCurrents()
    w.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    )
    e = w.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=0, ship_dir_y=0, ship_base_speed=10.0,
    )
    # no division by zero; result is 0 alignment
    assert e.boost_pct == 0


def test_weak_wind_smaller_effect():
    strong = WindCurrents()
    strong.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=1)},
    )
    weak = WindCurrents()
    weak.register_zone(
        zone_id="bay",
        wind_by_band={2: Wind(dx=1, dy=0, speed=0.3)},
    )
    e_strong = strong.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    e_weak = weak.effect_on(
        zone_id="bay", band=2,
        ship_dir_x=1, ship_dir_y=0, ship_base_speed=10.0,
    )
    assert e_strong.boost_pct > e_weak.boost_pct
