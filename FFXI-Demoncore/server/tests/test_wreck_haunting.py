"""Tests for wreck haunting."""
from __future__ import annotations

from server.wreck_haunting import HauntLevel, WreckHaunting


def test_quiet_just_filed():
    h = WreckHaunting()
    s = h.observe(ship_id="x", filed_at=0, now_seconds=60)
    assert s.level == HauntLevel.QUIET


def test_stirring_after_one_hour():
    h = WreckHaunting()
    s = h.observe(ship_id="x", filed_at=0, now_seconds=3_600)
    assert s.level == HauntLevel.STIRRING


def test_restless_after_six_hours():
    h = WreckHaunting()
    s = h.observe(ship_id="x", filed_at=0, now_seconds=6 * 3_600)
    assert s.level == HauntLevel.RESTLESS


def test_ravenous_after_24_hours():
    h = WreckHaunting()
    s = h.observe(ship_id="x", filed_at=0, now_seconds=24 * 3_600)
    assert s.level == HauntLevel.RAVENOUS


def test_aggro_multiplier_progresses():
    h = WreckHaunting()
    quiet = h.observe(ship_id="x", filed_at=0, now_seconds=60)
    stirring = h.observe(ship_id="x", filed_at=0, now_seconds=3_600)
    restless = h.observe(ship_id="x", filed_at=0, now_seconds=6 * 3_600)
    ravenous = h.observe(ship_id="x", filed_at=0, now_seconds=24 * 3_600)
    assert (
        quiet.aggro_multiplier
        < stirring.aggro_multiplier
        < restless.aggro_multiplier
        < ravenous.aggro_multiplier
    )


def test_disturb_resets_to_quiet():
    h = WreckHaunting()
    # mature wreck (24h+) should be RAVENOUS — disturbed -> QUIET
    h.disturb(ship_id="x", now_seconds=24 * 3_600)
    s = h.observe(ship_id="x", filed_at=0, now_seconds=24 * 3_600 + 100)
    assert s.level == HauntLevel.QUIET


def test_disturb_window_expires():
    h = WreckHaunting()
    h.disturb(ship_id="x", now_seconds=0)
    # 30min cooldown
    s_during = h.observe(ship_id="x", filed_at=0, now_seconds=29 * 60)
    s_after = h.observe(
        ship_id="x", filed_at=0, now_seconds=24 * 3_600 + 31 * 60,
    )
    assert s_during.level == HauntLevel.QUIET
    assert s_after.level == HauntLevel.RAVENOUS


def test_disturb_blank_id_rejected():
    h = WreckHaunting()
    assert h.disturb(ship_id="", now_seconds=0) is False


def test_age_negative_clamps_to_quiet():
    h = WreckHaunting()
    # observe before wreck filed
    s = h.observe(ship_id="x", filed_at=1_000, now_seconds=0)
    assert s.level == HauntLevel.QUIET
    assert s.age_seconds == 0


def test_disturbed_until_returns_window():
    h = WreckHaunting()
    h.disturb(ship_id="x", now_seconds=100)
    end = h.disturbed_until(ship_id="x")
    assert end == 100 + 30 * 60


def test_aggro_multiplier_static_lookup():
    assert WreckHaunting.aggro_multiplier_for(
        level=HauntLevel.QUIET,
    ) == 0.5
    assert WreckHaunting.aggro_multiplier_for(
        level=HauntLevel.RAVENOUS,
    ) == 2.5
