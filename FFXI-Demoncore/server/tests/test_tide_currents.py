"""Tests for tide & currents."""
from __future__ import annotations

from server.tide_currents import (
    Current,
    HOURS_PER_LONG_PHASE,
    HOURS_PER_TIDE_PHASE,
    LongPhase,
    TideCurrents,
    TidePhase,
)


def test_phase_high_at_zero():
    t = TideCurrents()
    assert t.phase_at(now_game_hours=0) == TidePhase.HIGH


def test_phase_progression():
    t = TideCurrents()
    assert t.phase_at(
        now_game_hours=HOURS_PER_TIDE_PHASE,
    ) == TidePhase.MID_FALLING
    assert t.phase_at(
        now_game_hours=HOURS_PER_TIDE_PHASE * 2,
    ) == TidePhase.LOW
    assert t.phase_at(
        now_game_hours=HOURS_PER_TIDE_PHASE * 3,
    ) == TidePhase.MID_RISING
    # wraps back
    assert t.phase_at(
        now_game_hours=HOURS_PER_TIDE_PHASE * 4,
    ) == TidePhase.HIGH


def test_long_phase_spring_at_zero():
    t = TideCurrents()
    assert t.long_phase_at(now_game_hours=0) == LongPhase.SPRING


def test_long_phase_alternates():
    t = TideCurrents()
    assert t.long_phase_at(
        now_game_hours=HOURS_PER_LONG_PHASE,
    ) == LongPhase.NEAP
    assert t.long_phase_at(
        now_game_hours=HOURS_PER_LONG_PHASE * 2,
    ) == LongPhase.SPRING


def test_tide_modifier_spring_high():
    t = TideCurrents()
    # hour 0 = SPRING + HIGH
    m = t.tide_modifier(now_game_hours=0)
    assert m == 1.5


def test_tide_modifier_spring_low():
    t = TideCurrents()
    # SPRING + LOW
    m = t.tide_modifier(now_game_hours=HOURS_PER_TIDE_PHASE * 2)
    assert m == 0.5


def test_tide_modifier_neap_high_flatter():
    t = TideCurrents()
    # NEAP starts at HOURS_PER_LONG_PHASE; HIGH at offset 0
    m = t.tide_modifier(now_game_hours=HOURS_PER_LONG_PHASE)
    assert m == 1.2


def test_tide_modifier_mid_phases_unity():
    t = TideCurrents()
    m = t.tide_modifier(now_game_hours=HOURS_PER_TIDE_PHASE)
    assert m == 1.0


def test_register_zone_happy():
    t = TideCurrents()
    ok = t.register_zone(
        zone_id="trench",
        current_by_band={3: Current(dx=1, dy=0, dz=0)},
    )
    assert ok is True


def test_register_zone_blank():
    t = TideCurrents()
    ok = t.register_zone(zone_id="", current_by_band={})
    assert ok is False


def test_current_at_returns_value():
    t = TideCurrents()
    c = Current(dx=2, dy=-1, dz=0)
    t.register_zone(zone_id="trench", current_by_band={3: c})
    out = t.current_at(zone_id="trench", band=3)
    assert out == c


def test_current_at_unknown_zone():
    t = TideCurrents()
    assert t.current_at(zone_id="ghost", band=2) is None


def test_current_at_unknown_band():
    t = TideCurrents()
    t.register_zone(
        zone_id="trench",
        current_by_band={3: Current(0, 0, 0)},
    )
    assert t.current_at(zone_id="trench", band=99) is None


def test_is_spring_low():
    t = TideCurrents()
    # SPRING + LOW
    assert t.is_spring_low(
        now_game_hours=HOURS_PER_TIDE_PHASE * 2,
    ) is True


def test_is_spring_low_false_for_neap_low():
    t = TideCurrents()
    # NEAP + LOW
    assert t.is_spring_low(
        now_game_hours=HOURS_PER_LONG_PHASE + HOURS_PER_TIDE_PHASE * 2,
    ) is False


def test_is_spring_low_false_for_high():
    t = TideCurrents()
    # SPRING + HIGH
    assert t.is_spring_low(now_game_hours=0) is False
