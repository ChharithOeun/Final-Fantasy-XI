"""Tests for anniversary_engine."""
from __future__ import annotations

from server.anniversary_engine import (
    AnniversaryEngine,
    AnniversaryTier,
)


YEAR = 365 * 24 * 3600   # one game year in seconds (real-time)


def test_schedule_happy():
    e = AnniversaryEngine()
    ok = e.schedule(
        commemoration_id="vorrak",
        source_entry_id="hist_42",
        summary="Vorrak fell.",
        origin_seconds=0, seconds_per_year=YEAR,
    )
    assert ok is True
    assert e.total_scheduled() == 1


def test_schedule_blank_id_blocked():
    e = AnniversaryEngine()
    out = e.schedule(
        commemoration_id="", source_entry_id="x",
        summary="x", origin_seconds=0,
        seconds_per_year=YEAR,
    )
    assert out is False


def test_schedule_blank_source_blocked():
    e = AnniversaryEngine()
    out = e.schedule(
        commemoration_id="x", source_entry_id="",
        summary="x", origin_seconds=0,
        seconds_per_year=YEAR,
    )
    assert out is False


def test_schedule_zero_seconds_per_year_blocked():
    e = AnniversaryEngine()
    out = e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=0,
    )
    assert out is False


def test_duplicate_commemoration_blocked():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    again = e.schedule(
        commemoration_id="x", source_entry_id="z",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    assert again is False


def test_no_event_before_one_year():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=YEAR // 2)
    assert out == ()


def test_yearly_tier_at_1y():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=YEAR)
    assert len(out) == 1
    assert out[0].tier == AnniversaryTier.YEARLY


def test_lustrum_at_5y():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    # tick to year 5
    out = e.check_now(now_seconds=5 * YEAR)
    assert len(out) == 1
    assert out[0].tier == AnniversaryTier.LUSTRUM
    assert out[0].year_count == 5


def test_decennial_at_10y():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=12 * YEAR)
    assert out[0].tier == AnniversaryTier.DECENNIAL


def test_quarter_at_25y():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=27 * YEAR)
    assert out[0].tier == AnniversaryTier.QUARTER


def test_centennial_at_100y():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=100 * YEAR)
    assert out[0].tier == AnniversaryTier.CENTENNIAL


def test_does_not_re_fire_same_year():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    out1 = e.check_now(now_seconds=YEAR + 100)
    out2 = e.check_now(now_seconds=YEAR + 200)
    assert len(out1) == 1
    assert len(out2) == 0


def test_fires_again_next_year():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    e.check_now(now_seconds=YEAR + 100)
    out = e.check_now(now_seconds=2 * YEAR)
    assert len(out) == 1
    assert out[0].year_count == 2


def test_last_fired_tier_recorded():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=0, seconds_per_year=YEAR,
    )
    e.check_now(now_seconds=10 * YEAR)
    assert e.last_fired_tier(commemoration_id="x") == (
        AnniversaryTier.DECENNIAL
    )


def test_negative_elapsed_no_event():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="y",
        summary="x", origin_seconds=1000,
        seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=500)
    assert out == ()


def test_event_carries_summary_and_source():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="x", source_entry_id="hist_42",
        summary="A heroic deed", origin_seconds=0,
        seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=YEAR)
    assert out[0].source_entry_id == "hist_42"
    assert out[0].summary == "A heroic deed"


def test_multiple_commemorations_independent():
    e = AnniversaryEngine()
    e.schedule(
        commemoration_id="a", source_entry_id="ha",
        summary="A", origin_seconds=0,
        seconds_per_year=YEAR,
    )
    e.schedule(
        commemoration_id="b", source_entry_id="hb",
        summary="B", origin_seconds=YEAR,
        seconds_per_year=YEAR,
    )
    out = e.check_now(now_seconds=2 * YEAR)
    # a is at year 2, b is at year 1
    assert len(out) == 2


def test_six_anniversary_tiers():
    assert len(list(AnniversaryTier)) == 6
