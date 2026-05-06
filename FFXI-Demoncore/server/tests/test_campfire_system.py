"""Tests for campfire_system."""
from __future__ import annotations

from server.campfire_system import CampfireSystem


def test_build_fire_happy():
    s = CampfireSystem()
    ok = s.build_fire(
        fire_id="cf1", zone_id="ronfaure",
        position=(0.0, 0.0, 0.0),
        initial_fuel=300, started_at=0,
    )
    assert ok is True
    assert s.is_lit(fire_id="cf1", now_seconds=10) is True


def test_blank_id_blocked():
    s = CampfireSystem()
    out = s.build_fire(
        fire_id="", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert out is False


def test_zero_fuel_blocked():
    s = CampfireSystem()
    out = s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=0, started_at=0,
    )
    assert out is False


def test_duplicate_fire_blocked():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    again = s.build_fire(
        fire_id="x", zone_id="z2", position=(0, 0, 0),
        initial_fuel=200, started_at=0,
    )
    assert again is False


def test_tick_consumes_fuel():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    fuel = s.tick(fire_id="x", dt_seconds=60, now_seconds=60)
    assert fuel == 240


def test_fire_dies_at_zero():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    fuel = s.tick(fire_id="x", dt_seconds=400, now_seconds=400)
    assert fuel == 0
    assert s.is_lit(fire_id="x", now_seconds=400) is False


def test_add_wood_extends():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=100, started_at=0,
    )
    s.tick(fire_id="x", dt_seconds=50, now_seconds=50)
    fuel = s.add_wood(fire_id="x", fuel_added=200)
    assert fuel == 250


def test_add_wood_negative_no_op():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    fuel = s.add_wood(fire_id="x", fuel_added=-5)
    assert fuel == 300


def test_add_wood_unknown_fire():
    s = CampfireSystem()
    out = s.add_wood(fire_id="ghost", fuel_added=100)
    assert out == 0


def test_extinguish_happy():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.extinguish(fire_id="x") is True
    assert s.is_lit(fire_id="x", now_seconds=10) is False


def test_extinguish_unknown():
    s = CampfireSystem()
    assert s.extinguish(fire_id="ghost") is False


def test_warmth_offset_at_fire():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    # at distance 0 → full warmth
    assert s.warmth_offset(
        fire_id="x", distance_yalms=0,
    ) == 30


def test_warmth_offset_falloff():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    # at distance 4 (half radius) → 50% warmth
    out = s.warmth_offset(fire_id="x", distance_yalms=4)
    assert out == 15


def test_warmth_offset_outside_radius():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.warmth_offset(
        fire_id="x", distance_yalms=20,
    ) == 0


def test_warmth_offset_unknown_fire():
    s = CampfireSystem()
    assert s.warmth_offset(
        fire_id="ghost", distance_yalms=0,
    ) == 0


def test_light_radius_when_lit():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.light_radius(fire_id="x") == 8


def test_cook_raw_food():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.cook(fire_id="x", food_kind="raw_meat") == "cooked_meat"


def test_cook_blank_food():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.cook(fire_id="x", food_kind="") == ""


def test_cook_already_cooked_passthrough():
    s = CampfireSystem()
    s.build_fire(
        fire_id="x", zone_id="z", position=(0, 0, 0),
        initial_fuel=300, started_at=0,
    )
    assert s.cook(
        fire_id="x", food_kind="cooked_meat",
    ) == "cooked_meat"


def test_cook_unknown_fire():
    s = CampfireSystem()
    assert s.cook(fire_id="ghost", food_kind="raw_meat") == ""
