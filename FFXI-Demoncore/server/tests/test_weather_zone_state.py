"""Tests for weather_zone_state."""
from __future__ import annotations

from server.weather_zone_state import (
    WeatherKind,
    WeatherZoneState,
)


def test_set_weather_happy():
    w = WeatherZoneState()
    ok = w.set_weather(
        zone_id="ronfaure", kind=WeatherKind.RAIN,
        intensity=50, set_at=10,
    )
    assert ok is True
    assert w.current(zone_id="ronfaure") is not None


def test_blank_zone_blocked():
    w = WeatherZoneState()
    out = w.set_weather(
        zone_id="", kind=WeatherKind.RAIN,
        intensity=50, set_at=10,
    )
    assert out is False


def test_intensity_out_of_range_blocked():
    w = WeatherZoneState()
    assert w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=-1, set_at=10,
    ) is False
    assert w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=101, set_at=10,
    ) is False


def test_intensity_in_unknown_zone_zero():
    w = WeatherZoneState()
    assert w.intensity_in(zone_id="ghost") == 0


def test_re_set_overwrites():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=20, set_at=10,
    )
    w.set_weather(
        zone_id="z", kind=WeatherKind.SNOW,
        intensity=80, set_at=20,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.kind == WeatherKind.SNOW
    assert out.intensity == 80


def test_is_kind():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.THUNDERSTORM,
        intensity=70, set_at=10,
    )
    assert w.is_kind(
        zone_id="z", kind=WeatherKind.THUNDERSTORM,
    ) is True
    assert w.is_kind(zone_id="z", kind=WeatherKind.RAIN) is False


def test_is_kind_unknown_zone():
    w = WeatherZoneState()
    assert w.is_kind(zone_id="ghost", kind=WeatherKind.RAIN) is False


def test_all_zones_with():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="a", kind=WeatherKind.RAIN, intensity=10, set_at=1,
    )
    w.set_weather(
        zone_id="b", kind=WeatherKind.RAIN, intensity=20, set_at=1,
    )
    w.set_weather(
        zone_id="c", kind=WeatherKind.CLEAR, intensity=0, set_at=1,
    )
    rain = w.all_zones_with(kind=WeatherKind.RAIN)
    assert rain == ("a", "b")


def test_advance_unknown_zone():
    w = WeatherZoneState()
    out = w.advance_tick(
        zone_id="ghost", dt_seconds=10, now_seconds=10,
    )
    assert out is False


def test_advance_ramps_up_active_weather():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=20, set_at=0,
    )
    w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        transition_speed=10,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.intensity == 30


def test_advance_caps_at_100():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=95, set_at=0,
    )
    w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        transition_speed=20,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.intensity == 100


def test_advance_ramps_clear_to_zero():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.CLEAR,
        intensity=50, set_at=0,
    )
    w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        transition_speed=20,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.intensity == 30


def test_advance_to_target_kind_drops_first():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=50, set_at=0,
    )
    # try to switch to SNOW; rain intensity should drop first
    w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        target_kind=WeatherKind.SNOW, transition_speed=10,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.kind == WeatherKind.RAIN
    assert out.intensity == 40


def test_advance_switches_kind_at_zero():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=0, set_at=0,
    )
    w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        target_kind=WeatherKind.SNOW, transition_speed=10,
    )
    out = w.current(zone_id="z")
    assert out is not None
    assert out.kind == WeatherKind.SNOW
    assert out.intensity == 0


def test_negative_speed_blocked():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.RAIN,
        intensity=50, set_at=0,
    )
    out = w.advance_tick(
        zone_id="z", dt_seconds=1, now_seconds=10,
        transition_speed=-1,
    )
    assert out is False


def test_total_zones():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="a", kind=WeatherKind.RAIN, intensity=10, set_at=1,
    )
    w.set_weather(
        zone_id="b", kind=WeatherKind.SNOW, intensity=10, set_at=1,
    )
    assert w.total_zones() == 2


def test_eight_weather_kinds():
    assert len(list(WeatherKind)) == 8


def test_intensity_at_full():
    w = WeatherZoneState()
    w.set_weather(
        zone_id="z", kind=WeatherKind.THUNDERSTORM,
        intensity=100, set_at=0,
    )
    assert w.intensity_in(zone_id="z") == 100
