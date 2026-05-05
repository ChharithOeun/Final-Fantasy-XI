"""Tests for aerial wreck salvage."""
from __future__ import annotations

from server.aerial_wreck_salvage import (
    ADJACENT_BAND_PENALTY,
    AerialWreckSalvage,
    DECAY_SECONDS,
    SALVAGE_RATE_UNITS_PER_SECOND,
)


def test_register_happy():
    s = AerialWreckSalvage()
    assert s.register_wreck(
        wreck_id="w1", cargo_units=100, crash_band=2,
    ) is True


def test_register_blank():
    s = AerialWreckSalvage()
    assert s.register_wreck(
        wreck_id="", cargo_units=100, crash_band=2,
    ) is False


def test_register_zero_cargo():
    s = AerialWreckSalvage()
    assert s.register_wreck(
        wreck_id="w1", cargo_units=0, crash_band=2,
    ) is False


def test_register_double_blocked():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    assert s.register_wreck(
        wreck_id="w1", cargo_units=50, crash_band=2,
    ) is False


def test_begin_salvage_same_band():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    assert s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    ) is True


def test_begin_salvage_adjacent_band_ok():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    assert s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=3, now_seconds=0,
    ) is True


def test_begin_salvage_far_band_blocked():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    assert s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=4, now_seconds=0,
    ) is False


def test_begin_salvage_unknown_wreck():
    s = AerialWreckSalvage()
    assert s.begin_salvage(
        crew_id="c1", wreck_id="ghost", crew_band=2, now_seconds=0,
    ) is False


def test_begin_salvage_double_blocked():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    assert s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=10,
    ) is False


def test_tick_solo_pulls_full_rate_at_crash_band():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    r = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=10,
    )
    assert r.accepted is True
    expected = 10 * SALVAGE_RATE_UNITS_PER_SECOND
    assert abs(r.units_pulled - expected) < 0.01


def test_tick_adjacent_band_slower():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=3, now_seconds=0,
    )
    r = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=3, now_seconds=10,
    )
    expected = 10 * SALVAGE_RATE_UNITS_PER_SECOND * ADJACENT_BAND_PENALTY
    assert abs(r.units_pulled - expected) < 0.01


def test_tick_split_between_crews():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    s.begin_salvage(
        crew_id="c2", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    r1 = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=10,
    )
    expected = 10 * SALVAGE_RATE_UNITS_PER_SECOND / 2
    assert abs(r1.units_pulled - expected) < 0.01


def test_tick_decay():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=1000, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    r = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=2,
        now_seconds=DECAY_SECONDS + 10,
    )
    assert r.accepted is False
    assert r.wreck_decayed is True


def test_scavenger_pressure_drains_cargo():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.set_scavenger_pressure(
        wreck_id="w1", units_per_second=1.0, now_seconds=0,
    )
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=10,
    )
    # 10s of scavenger pressure already drained 10 units
    remaining = s.units_remaining(wreck_id="w1")
    assert remaining < 100


def test_scavenger_pressure_unknown_wreck():
    s = AerialWreckSalvage()
    assert s.set_scavenger_pressure(
        wreck_id="ghost", units_per_second=1.0,
    ) is False


def test_stop_salvage():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    assert s.stop_salvage(crew_id="c1", wreck_id="w1") is True


def test_stop_unknown():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    assert s.stop_salvage(crew_id="ghost", wreck_id="w1") is False


def test_units_remaining_unknown():
    s = AerialWreckSalvage()
    assert s.units_remaining(wreck_id="ghost") == 0


def test_tick_caps_at_remaining():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=3, crash_band=2)
    s.begin_salvage(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=0,
    )
    r = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=120,
    )
    assert r.cargo_remaining == 0


def test_tick_not_salvaging():
    s = AerialWreckSalvage()
    s.register_wreck(wreck_id="w1", cargo_units=100, crash_band=2)
    r = s.tick(
        crew_id="c1", wreck_id="w1", crew_band=2, now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "not salvaging"
