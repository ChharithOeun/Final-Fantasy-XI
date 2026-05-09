"""Tests for atmospheric_render."""
from __future__ import annotations

import pytest

from server.atmospheric_render import (
    AtmosphericProfile, AtmosphericRenderSystem,
    TimeOfDay, Weather,
)


def _make(zone: str = "buburimu") -> AtmosphericProfile:
    return AtmosphericProfile(
        zone=zone, density=0.3, god_ray_count=8,
        distance_haze_km=12.0, dust_mote_density=500.0,
        led_wall_ambient_color=(0.6, 0.5, 0.4),
        scatter_anisotropy=0.4,
    )


def test_set_zone_atmosphere_happy():
    s = AtmosphericRenderSystem()
    p = _make()
    s.set_zone_atmosphere("buburimu", p)
    assert s.get_profile("buburimu") is p


def test_set_zone_mismatched_zone_raises():
    s = AtmosphericRenderSystem()
    p = _make("buburimu")
    with pytest.raises(ValueError):
        s.set_zone_atmosphere("davoi", p)


def test_set_zone_empty_zone_raises():
    s = AtmosphericRenderSystem()
    with pytest.raises(ValueError):
        s.set_zone_atmosphere("", _make(""))


def test_set_zone_density_oob_raises():
    s = AtmosphericRenderSystem()
    bad = AtmosphericProfile(
        zone="x", density=2.0, god_ray_count=1,
        distance_haze_km=1, dust_mote_density=1,
        led_wall_ambient_color=(0, 0, 0),
        scatter_anisotropy=0,
    )
    with pytest.raises(ValueError):
        s.set_zone_atmosphere("x", bad)


def test_set_zone_anisotropy_oob_raises():
    s = AtmosphericRenderSystem()
    bad = AtmosphericProfile(
        zone="x", density=0.5, god_ray_count=1,
        distance_haze_km=1, dust_mote_density=1,
        led_wall_ambient_color=(0, 0, 0),
        scatter_anisotropy=2.0,
    )
    with pytest.raises(ValueError):
        s.set_zone_atmosphere("x", bad)


def test_set_zone_negative_godrays_raises():
    s = AtmosphericRenderSystem()
    bad = AtmosphericProfile(
        zone="x", density=0.5, god_ray_count=-1,
        distance_haze_km=1, dust_mote_density=1,
        led_wall_ambient_color=(0, 0, 0),
        scatter_anisotropy=0,
    )
    with pytest.raises(ValueError):
        s.set_zone_atmosphere("x", bad)


def test_get_profile_unknown_returns_none():
    s = AtmosphericRenderSystem()
    assert s.get_profile("ghost") is None


def test_god_ray_count_dawn_max():
    s = AtmosphericRenderSystem()
    s.set_zone_atmosphere("buburimu", _make())
    dawn = s.god_ray_count_for("buburimu", 6)
    day = s.god_ray_count_for("buburimu", 12)
    night = s.god_ray_count_for("buburimu", 22)
    assert dawn > day > night


def test_god_ray_count_unknown_zone_uses_default_base():
    s = AtmosphericRenderSystem()
    # default base 4, dawn = 1.0x => 4
    assert s.god_ray_count_for("unset", 6) == 4


def test_god_ray_count_invalid_hour_raises():
    s = AtmosphericRenderSystem()
    with pytest.raises(ValueError):
        s.god_ray_count_for("x", 24)


def test_distance_haze_proportional_to_visibility():
    s = AtmosphericRenderSystem()
    near = s.distance_haze_km(4.0)
    far = s.distance_haze_km(40.0)
    assert far > near
    assert near == pytest.approx(1.0)


def test_distance_haze_zero_raises():
    s = AtmosphericRenderSystem()
    with pytest.raises(ValueError):
        s.distance_haze_km(0)


def test_led_wall_default_grey():
    s = AtmosphericRenderSystem()
    assert s.led_wall_color("ghost") == (0.5, 0.5, 0.5)


def test_led_wall_returns_zone_color():
    s = AtmosphericRenderSystem()
    s.set_zone_atmosphere("buburimu", _make())
    assert s.led_wall_color("buburimu") == (0.6, 0.5, 0.4)


def test_apply_weather_clear_low_density():
    s = AtmosphericRenderSystem()
    p = s.apply_weather("davoi", Weather.CLEAR)
    assert p.density < 0.1


def test_apply_weather_sandstorm_high_density():
    s = AtmosphericRenderSystem()
    p = s.apply_weather("altepa", Weather.SANDSTORM)
    assert p.density > 0.8


def test_apply_weather_rain_back_scatter():
    s = AtmosphericRenderSystem()
    p = s.apply_weather("ronfaure", Weather.RAIN)
    assert p.scatter_anisotropy < 0


def test_apply_weather_aurora_forward_scatter():
    s = AtmosphericRenderSystem()
    p = s.apply_weather("uleguerand", Weather.AURORA)
    assert p.scatter_anisotropy > 0.5


def test_apply_weather_preserves_other_fields():
    s = AtmosphericRenderSystem()
    s.set_zone_atmosphere("buburimu", _make())
    s.apply_weather("buburimu", Weather.OVERCAST)
    p = s.get_profile("buburimu")
    # god_ray_count survives — it was 8, weather doesn't
    # touch that field
    assert p.god_ray_count == 8


def test_render_intent_unknown_zone_default():
    s = AtmosphericRenderSystem()
    intent = s.get_render_intent("ghost", 12)
    assert intent["zone"] == "ghost"
    assert intent["density"] == pytest.approx(0.05)


def test_render_intent_carries_tod():
    s = AtmosphericRenderSystem()
    intent = s.get_render_intent("x", 18)
    assert intent["tod"] == "dusk"


def test_render_intent_known_zone():
    s = AtmosphericRenderSystem()
    s.set_zone_atmosphere("buburimu", _make())
    intent = s.get_render_intent("buburimu", 6)
    assert intent["density"] == pytest.approx(0.3)
    assert intent["led_wall_color"] == (0.6, 0.5, 0.4)


def test_weather_enum_count():
    assert len(list(Weather)) == 5


def test_tod_enum_count():
    assert len(list(TimeOfDay)) == 4
