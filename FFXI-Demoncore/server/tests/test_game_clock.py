"""Tests for the Vana'diel game clock.

Run:  python -m pytest server/tests/test_game_clock.py -v
"""
import datetime as dt
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator.game_clock import (
    WALL_SECONDS_PER_VANADIEL_DAY,
    WALL_SECONDS_PER_VANADIEL_HOUR,
    VanadielTime,
    parse_schedule_time,
    schedule_index_at,
    vanadiel_at,
)


# -------------------------- ratio sanity ---------------------------

def test_canonical_ratio():
    """One Vana'diel day = 3456 wall-seconds = 57m36s."""
    assert WALL_SECONDS_PER_VANADIEL_DAY == 3456.0
    assert WALL_SECONDS_PER_VANADIEL_HOUR == 144.0
    # 25× faster than wall time
    assert 86400 / WALL_SECONDS_PER_VANADIEL_DAY == 25.0


# -------------------------- vanadiel_at ----------------------------

def test_origin_anchor():
    v = vanadiel_at(0.0)
    assert v.hour == 0
    assert v.minute == 0
    assert v.second == 0
    assert v.day_of_month == 1
    assert v.month == 1


def test_one_vanadiel_hour_later():
    v = vanadiel_at(WALL_SECONDS_PER_VANADIEL_HOUR)  # 144 wall-seconds
    assert v.hour == 1
    assert v.minute == 0


def test_six_vanadiel_hours():
    v = vanadiel_at(6 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert v.hour == 6


def test_one_vanadiel_day():
    v = vanadiel_at(WALL_SECONDS_PER_VANADIEL_DAY)
    assert v.hour == 0
    assert v.day_of_year == 1
    assert v.day_of_month == 2


def test_one_vanadiel_month():
    v = vanadiel_at(30 * WALL_SECONDS_PER_VANADIEL_DAY)
    assert v.month == 2
    assert v.day_of_month == 1


def test_one_vanadiel_year():
    v = vanadiel_at(360 * WALL_SECONDS_PER_VANADIEL_DAY)
    assert v.year == 888  # default reference is 887


def test_weekday_cycles_8():
    """Weekday cycles every 8 days."""
    seen = set()
    for d in range(8):
        v = vanadiel_at(d * WALL_SECONDS_PER_VANADIEL_DAY)
        seen.add(v.weekday)
    assert len(seen) == 8


def test_is_night_at_midnight():
    v = vanadiel_at(0.0)  # 00:00
    assert v.is_night is True
    assert v.is_day is False


def test_is_day_at_noon():
    v = vanadiel_at(12 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert v.is_day is True
    assert v.is_night is False


def test_str_format():
    v = vanadiel_at(8 * WALL_SECONDS_PER_VANADIEL_HOUR + 90)
    # 8 hours + 90 vana-seconds (which is 90 vanadiel-seconds because
    # we already converted). Actually wait — vana_seconds = wall_seconds * 25
    # So 90 wall-seconds = 2250 vana-seconds = ~37 vana-min
    # Let's use a cleaner test
    v = vanadiel_at(8 * WALL_SECONDS_PER_VANADIEL_HOUR)
    s = str(v)
    assert "08:00:00" in s


# -------------------------- parse_schedule_time ----------------------

def test_parse_string_hhmm():
    assert parse_schedule_time("06:00") == (6, 0)
    assert parse_schedule_time("18:30") == (18, 30)


def test_parse_int_hours():
    assert parse_schedule_time(6) == (6, 0)
    assert parse_schedule_time(18) == (18, 0)


def test_parse_yaml_sexagesimal_minutes():
    """YAML 1.1 parses unquoted '09:00' as int 540 (= 9*60)."""
    assert parse_schedule_time(540) == (9, 0)
    assert parse_schedule_time(600) == (10, 0)   # YAML "10:00"
    assert parse_schedule_time(1080) == (18, 0)  # YAML "18:00"
    assert parse_schedule_time(810) == (13, 30)  # YAML "13:30"
    assert parse_schedule_time(0) == (0, 0)


def test_parse_int_hhmm_explicit():
    """Values >= 1440 are unambiguously HHMM."""
    assert parse_schedule_time(1830) == (18, 30)
    assert parse_schedule_time(2200) == (22, 0)


def test_parse_datetime_time():
    assert parse_schedule_time(dt.time(6, 0)) == (6, 0)
    assert parse_schedule_time(dt.time(22, 45)) == (22, 45)


def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        parse_schedule_time("not a time")


# -------------------------- schedule_index_at ------------------------

def test_schedule_index_morning():
    schedule = [
        ["06:00", "stall_setup",   "morning_idle"],
        ["12:00", "tavern",        "lunch"],
        ["19:00", "stall_pack_up", "evening_pack_up"],
    ]
    # at 07:00 -> index 0
    v = vanadiel_at(7 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert schedule_index_at(schedule, v) == 0


def test_schedule_index_afternoon():
    schedule = [
        ["06:00", "stall_setup",   "morning_idle"],
        ["12:00", "tavern",        "lunch"],
        ["19:00", "stall_pack_up", "evening_pack_up"],
    ]
    v = vanadiel_at(15 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert schedule_index_at(schedule, v) == 1


def test_schedule_index_pre_dawn_wraps():
    """At 03:00, no entry has fired yet today, so use the last entry."""
    schedule = [
        ["06:00", "stall_setup",  "morning_idle"],
        ["12:00", "tavern",       "lunch"],
        ["19:00", "stall_pack_up","evening_pack_up"],
    ]
    v = vanadiel_at(3 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert schedule_index_at(schedule, v) == 2  # yesterday's last entry


def test_schedule_index_empty():
    v = vanadiel_at(12 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert schedule_index_at([], v) == -1


def test_schedule_unparseable_entry_skipped():
    schedule = [
        ["06:00", "ok",           "ok"],
        ["bad",   "broken_entry", "broken_anim"],  # malformed
        ["18:00", "evening",      "evening_anim"],
    ]
    v = vanadiel_at(20 * WALL_SECONDS_PER_VANADIEL_HOUR)
    # Should still find the 18:00 entry
    assert schedule_index_at(schedule, v) == 2
