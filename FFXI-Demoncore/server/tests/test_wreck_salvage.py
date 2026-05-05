"""Tests for wreck salvage."""
from __future__ import annotations

from server.wreck_salvage import (
    DECAY_SECONDS,
    SALVAGE_RATE_UNITS_PER_SECOND,
    WreckSalvage,
)


def test_register_wreck_happy():
    w = WreckSalvage()
    assert w.register_wreck(wreck_id="wr1", cargo_units=100) is True


def test_register_wreck_blank():
    w = WreckSalvage()
    assert w.register_wreck(wreck_id="", cargo_units=10) is False


def test_register_wreck_zero_cargo():
    w = WreckSalvage()
    assert w.register_wreck(wreck_id="wr1", cargo_units=0) is False


def test_register_wreck_double_blocked():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    assert w.register_wreck(wreck_id="wr1", cargo_units=50) is False


def test_begin_salvage_happy():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    assert w.begin_salvage(
        crew_id="c1", wreck_id="wr1", now_seconds=0,
    ) is True


def test_begin_salvage_unknown_wreck():
    w = WreckSalvage()
    assert w.begin_salvage(
        crew_id="c1", wreck_id="ghost", now_seconds=0,
    ) is False


def test_begin_salvage_double_blocked():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    assert w.begin_salvage(
        crew_id="c1", wreck_id="wr1", now_seconds=10,
    ) is False


def test_tick_solo_pulls_cargo():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    r = w.tick(crew_id="c1", wreck_id="wr1", now_seconds=10)
    assert r.accepted is True
    expected = 10 * SALVAGE_RATE_UNITS_PER_SECOND
    assert abs(r.units_pulled - expected) < 0.01


def test_tick_split_between_two_crews():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    w.begin_salvage(crew_id="c2", wreck_id="wr1", now_seconds=0)
    r1 = w.tick(crew_id="c1", wreck_id="wr1", now_seconds=10)
    r2 = w.tick(crew_id="c2", wreck_id="wr1", now_seconds=10)
    # rate is split: each gets half
    expected_each = 10 * SALVAGE_RATE_UNITS_PER_SECOND / 2
    assert abs(r1.units_pulled - expected_each) < 0.01
    assert abs(r2.units_pulled - expected_each) < 0.01


def test_tick_unknown_wreck():
    w = WreckSalvage()
    r = w.tick(crew_id="c1", wreck_id="ghost", now_seconds=0)
    assert r.accepted is False


def test_tick_not_salvaging():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    r = w.tick(crew_id="c1", wreck_id="wr1", now_seconds=10)
    assert r.accepted is False
    assert r.reason == "not salvaging"


def test_tick_caps_at_cargo_remaining():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=5)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    # 5 cargo / 0.1 per sec = 50 sec to drain — well within decay
    r = w.tick(crew_id="c1", wreck_id="wr1", now_seconds=120)
    assert r.units_pulled <= 5
    assert r.cargo_remaining == 0


def test_decay_blocks_new_salvage():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=1000)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    # second crew shows up after decay window
    ok = w.begin_salvage(
        crew_id="c2", wreck_id="wr1",
        now_seconds=DECAY_SECONDS + 10,
    )
    assert ok is False


def test_decay_makes_tick_fail():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=1000)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    r = w.tick(
        crew_id="c1", wreck_id="wr1",
        now_seconds=DECAY_SECONDS + 10,
    )
    assert r.accepted is False
    assert r.wreck_decayed is True


def test_stop_salvage():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    assert w.stop_salvage(crew_id="c1", wreck_id="wr1") is True
    assert w.active_crews(wreck_id="wr1") == ()


def test_stop_unknown():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    assert w.stop_salvage(crew_id="c1", wreck_id="wr1") is False


def test_units_remaining_unknown_zero():
    w = WreckSalvage()
    assert w.units_remaining(wreck_id="ghost") == 0


def test_active_crews_listed():
    w = WreckSalvage()
    w.register_wreck(wreck_id="wr1", cargo_units=100)
    w.begin_salvage(crew_id="c1", wreck_id="wr1", now_seconds=0)
    w.begin_salvage(crew_id="c2", wreck_id="wr1", now_seconds=0)
    crews = w.active_crews(wreck_id="wr1")
    assert "c1" in crews
    assert "c2" in crews
