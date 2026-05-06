"""Tests for mourning_period."""
from __future__ import annotations

from server.mourning_period import (
    MourningPeriod,
    MourningSeverity,
)


SECONDS_PER_DAY = 24 * 3600


def test_begin_mourning_legendary():
    m = MourningPeriod()
    ok = m.begin_mourning(
        deceased_id="alice", deceased_name="Alice the Bold",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert ok is True
    state = m.current_state(now_seconds=10)
    assert state is not None
    assert state.severity == MourningSeverity.LIGHT


def test_begin_mourning_mythic():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="bob", deceased_name="Bob",
        deceased_title_tier="mythic",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    state = m.current_state(now_seconds=10)
    assert state is not None
    assert state.severity == MourningSeverity.HEAVY


def test_begin_mourning_extended():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="founder", deceased_name="Server Founder",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
        extended=True,
    )
    state = m.current_state(now_seconds=10)
    assert state is not None
    assert state.severity == MourningSeverity.SERVER_DEFINING


def test_lower_tier_skipped():
    m = MourningPeriod()
    out = m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="rare",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert out is False


def test_blank_id_blocked():
    m = MourningPeriod()
    out = m.begin_mourning(
        deceased_id="", deceased_name="X",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert out is False


def test_zero_seconds_per_day_blocked():
    m = MourningPeriod()
    out = m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=0,
    )
    assert out is False


def test_legendary_lasts_3_days():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m.is_mourning(now_seconds=2 * SECONDS_PER_DAY) is True
    assert m.is_mourning(now_seconds=4 * SECONDS_PER_DAY) is False


def test_mythic_lasts_7_days():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="mythic",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m.is_mourning(now_seconds=6 * SECONDS_PER_DAY) is True
    assert m.is_mourning(now_seconds=8 * SECONDS_PER_DAY) is False


def test_extended_lasts_14_days():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
        extended=True,
    )
    assert m.is_mourning(now_seconds=13 * SECONDS_PER_DAY) is True
    assert m.is_mourning(now_seconds=15 * SECONDS_PER_DAY) is False


def test_xp_bonus_for_each_tier():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m.xp_bonus_pct(now_seconds=10) == 5

    m2 = MourningPeriod()
    m2.begin_mourning(
        deceased_id="b", deceased_name="B",
        deceased_title_tier="mythic",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m2.xp_bonus_pct(now_seconds=10) == 10

    m3 = MourningPeriod()
    m3.begin_mourning(
        deceased_id="c", deceased_name="C",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
        extended=True,
    )
    assert m3.xp_bonus_pct(now_seconds=10) == 15


def test_xp_bonus_zero_after_mourning_ends():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m.xp_bonus_pct(
        now_seconds=10 * SECONDS_PER_DAY,
    ) == 0


def test_seconds_remaining():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    rem = m.seconds_remaining(now_seconds=SECONDS_PER_DAY)
    assert rem == 2 * SECONDS_PER_DAY


def test_seconds_remaining_zero_after_end():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    assert m.seconds_remaining(
        now_seconds=10 * SECONDS_PER_DAY,
    ) == 0


def test_higher_tier_replaces_active():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    # mid-mourning, mythic dies
    ok = m.begin_mourning(
        deceased_id="b", deceased_name="B",
        deceased_title_tier="mythic",
        started_at=SECONDS_PER_DAY,
        seconds_per_day=SECONDS_PER_DAY,
    )
    assert ok is True
    state = m.current_state(now_seconds=SECONDS_PER_DAY + 10)
    assert state is not None
    assert state.deceased_id == "b"
    assert state.severity == MourningSeverity.HEAVY


def test_lower_tier_does_not_replace():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="b", deceased_name="B",
        deceased_title_tier="mythic",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    ok = m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=SECONDS_PER_DAY,
        seconds_per_day=SECONDS_PER_DAY,
    )
    assert ok is False
    state = m.current_state(now_seconds=SECONDS_PER_DAY + 10)
    assert state is not None
    assert state.deceased_id == "b"


def test_after_expiry_new_mourning_allowed():
    m = MourningPeriod()
    m.begin_mourning(
        deceased_id="a", deceased_name="A",
        deceased_title_tier="legendary",
        started_at=0, seconds_per_day=SECONDS_PER_DAY,
    )
    # 4 days later (after expiry), a different player permadies
    ok = m.begin_mourning(
        deceased_id="b", deceased_name="B",
        deceased_title_tier="legendary",
        started_at=4 * SECONDS_PER_DAY,
        seconds_per_day=SECONDS_PER_DAY,
    )
    assert ok is True


def test_is_mourning_false_when_none():
    m = MourningPeriod()
    assert m.is_mourning(now_seconds=10) is False


def test_four_severity_levels():
    assert len(list(MourningSeverity)) == 4
