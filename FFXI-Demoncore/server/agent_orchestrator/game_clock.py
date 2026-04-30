"""Vana'diel game clock — wall-time → in-game-time conversion.

FFXI's canonical ratio: one Vana'diel day = 57 minutes 36 seconds of
wall time. So one Vana'diel hour = 2 minutes 24 seconds of wall time.

We use this for agent schedules. A Tier-2 NPC with a schedule entry
"06:00 stall_setup" fires that event when Vana'diel time hits 06:00 —
which happens once every 57m 36s wall-clock (with a 24h cycle inside
that window).

This module is pure functions. No state. No I/O. Tested with explicit
clocks so no real time is ever needed.
"""
from __future__ import annotations

import dataclasses
import time as _time


# Canonical FFXI ratio: 1 Vana'diel day = 3456 wall seconds.
WALL_SECONDS_PER_VANADIEL_DAY = 3456.0
WALL_SECONDS_PER_VANADIEL_HOUR = WALL_SECONDS_PER_VANADIEL_DAY / 24.0  # = 144s
VANADIEL_DAYS_PER_VANADIEL_YEAR = 360
VANADIEL_DAYS_PER_VANADIEL_MONTH = 30  # 12 months × 30 days = 360 — matches FFXI

# Days of the Vana'diel week (8 days). FFXI canonical ordering.
VANADIEL_WEEKDAYS = [
    "Firesday", "Earthsday", "Watersday", "Windsday",
    "Iceday",   "Lightningday", "Lightsday", "Darksday",
]

# Reference epoch — wall time 0.0 corresponds to Vana'diel
# year 887, month 1, day 1, 00:00:00 (Lightsday, by canonical mapping
# you can override below if your server uses a different anchor).
DEFAULT_REFERENCE_WALL_TIME = 0.0
DEFAULT_REFERENCE_VANADIEL_YEAR = 887
DEFAULT_REFERENCE_VANADIEL_DAY_OF_YEAR = 0
DEFAULT_REFERENCE_WEEKDAY_INDEX = 6  # Lightsday


@dataclasses.dataclass(frozen=True)
class VanadielTime:
    """A single moment in Vana'diel.

    Year is open-ended. Month is 1-12. Day-of-month is 1-30. Hour is
    0-23. Minute is 0-59. Second is 0-59. Day-of-week is 0-7 indexing
    VANADIEL_WEEKDAYS.
    """
    year: int
    month: int
    day_of_month: int
    hour: int
    minute: int
    second: int
    day_of_year: int          # 0-359
    weekday_index: int         # 0-7
    weekday: str
    wall_seconds: float        # the originating wall-clock seconds

    def __str__(self) -> str:
        return (f"{self.year}/{self.month:02d}/{self.day_of_month:02d} "
                f"{self.hour:02d}:{self.minute:02d}:{self.second:02d} "
                f"{self.weekday}")

    @property
    def hhmm(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    @property
    def is_night(self) -> bool:
        """Vana'diel night = 18:00 - 06:00 (FFXI mob spawn convention)."""
        return self.hour >= 18 or self.hour < 6

    @property
    def is_day(self) -> bool:
        return not self.is_night


def now_wall() -> float:
    """Wall-clock seconds since unix epoch. Wrapped for testability."""
    return _time.time()


def vanadiel_at(
    wall_seconds: float,
    *,
    reference_wall: float = DEFAULT_REFERENCE_WALL_TIME,
    reference_year: int = DEFAULT_REFERENCE_VANADIEL_YEAR,
    reference_day_of_year: int = DEFAULT_REFERENCE_VANADIEL_DAY_OF_YEAR,
    reference_weekday_index: int = DEFAULT_REFERENCE_WEEKDAY_INDEX,
) -> VanadielTime:
    """Given a wall-clock timestamp, return the Vana'diel time.

    Parameters let callers anchor their clock to whatever epoch the LSB
    server uses. Defaults match a clean "wall_seconds = 0 -> Vanadiel
    Year 887, Day 1, Hour 0, Lightsday" anchor.
    """
    delta_wall = wall_seconds - reference_wall
    vana_seconds = delta_wall * (86400.0 / WALL_SECONDS_PER_VANADIEL_DAY)
    # Now: vana_seconds is "in-game seconds since the reference moment"

    # Total Vana'diel days elapsed (integer + fractional)
    total_seconds = int(vana_seconds)
    days_since_ref = total_seconds // 86400
    second_of_day = total_seconds % 86400

    # Reduce to year/month/day-of-month
    abs_day = reference_day_of_year + days_since_ref
    year_offset, day_of_year = divmod(abs_day, 360)
    year = reference_year + int(year_offset)
    month = (day_of_year // 30) + 1
    day_of_month = (day_of_year % 30) + 1

    hour, rem = divmod(second_of_day, 3600)
    minute, second = divmod(rem, 60)

    weekday_index = (reference_weekday_index + (abs_day % 8)) % 8
    weekday = VANADIEL_WEEKDAYS[weekday_index]

    return VanadielTime(
        year=int(year),
        month=int(month),
        day_of_month=int(day_of_month),
        hour=int(hour),
        minute=int(minute),
        second=int(second),
        day_of_year=int(day_of_year),
        weekday_index=int(weekday_index),
        weekday=weekday,
        wall_seconds=wall_seconds,
    )


def vanadiel_now() -> VanadielTime:
    """Convenience: Vana'diel time at this moment."""
    return vanadiel_at(now_wall())


def parse_schedule_time(value) -> tuple[int, int]:
    """Parse a schedule time entry into (hour, minute).

    Accepted input forms:
        - datetime.time / datetime.datetime
        - "HH:MM" string (preferred; explicit)
        - "HHMM" or "HH" string (loose)
        - integer

    Integer disambiguation matters because PyYAML uses YAML 1.1 by
    default, which auto-parses unquoted "09:00" as the sexagesimal
    integer 540 (= 9*60). So an unquoted HH:MM in a YAML file ends up
    as a sexagesimal minute count, not an HHMM number. Our rules:

        value in [0, 23]      -> (value, 0)            "hours-only"
        value in [24, 1439]   -> (value // 60, value % 60)
                                                       sexagesimal minutes
        value in [1440, 2359] and value % 100 < 60
                              -> (value // 100, value % 100)  HHMM

    This means YAML authors can write unquoted times like `06:00` and
    the parser does the right thing without forcing every value to be
    quoted as a string.
    """
    import datetime as _dt
    if isinstance(value, _dt.time):
        return (value.hour, value.minute)
    if isinstance(value, _dt.datetime):
        return (value.hour, value.minute)
    if isinstance(value, int):
        if 0 <= value <= 23:
            return (value, 0)
        if 24 <= value < 1440:
            # YAML 1.1 sexagesimal minutes
            return (value // 60, value % 60)
        if 1440 <= value <= 2359 and (value % 100) < 60:
            return (value // 100, value % 100)
    if isinstance(value, str):
        s = value.strip()
        if ":" in s:
            h, m = s.split(":", 1)
            return (int(h), int(m))
        if s.isdigit():
            n = int(s)
            return parse_schedule_time(n)
    raise ValueError(f"unparseable schedule time: {value!r}")


def schedule_index_at(schedule, vana: VanadielTime) -> int:
    """Given an agent's schedule list and a Vana'diel time, return the
    index of the most-recent schedule entry that has fired (i.e. whose
    time is <= the current Vana'diel hh:mm).

    Schedule format (list of [time, location, animation]) per
    `agents/_SCHEMA.md`.
    Wraps around midnight: if no entry is at-or-before now, the active
    entry is the last entry of the list (which fired yesterday).
    """
    current_minute = vana.hour * 60 + vana.minute
    last_at_or_before = -1
    for i, entry in enumerate(schedule):
        if not entry or len(entry) < 1:
            continue
        try:
            h, m = parse_schedule_time(entry[0])
        except ValueError:
            continue
        entry_minute = h * 60 + m
        if entry_minute <= current_minute:
            last_at_or_before = i
        else:
            break
    if last_at_or_before == -1:
        # Wrap: use the last entry of the schedule (yesterday's tail)
        return len(schedule) - 1 if schedule else -1
    return last_at_or_before
