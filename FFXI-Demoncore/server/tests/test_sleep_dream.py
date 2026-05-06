"""Tests for sleep_dream."""
from __future__ import annotations

from server.sleep_dream import (
    DreamKind,
    DreamReward,
    LocationKind,
    SleepDreamEngine,
)


def test_begin_sleep_happy():
    e = SleepDreamEngine()
    ok = e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE,
        started_at=0,
    )
    assert ok is True
    assert e.is_sleeping(player_id="alice") is True


def test_blank_player_blocked():
    e = SleepDreamEngine()
    out = e.begin_sleep(
        player_id="",
        location_kind=LocationKind.INN, started_at=0,
    )
    assert out is False


def test_double_begin_blocked():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE, started_at=0,
    )
    again = e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.INN, started_at=10,
    )
    assert again is False


def test_short_sleep_dreamless():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE, started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=30)
    assert out is not None
    assert out.kind == DreamKind.EMPTY


def test_end_without_begin_returns_none():
    e = SleepDreamEngine()
    out = e.end_sleep(player_id="ghost", ended_at=100)
    assert out is None


def test_long_mog_house_sleep_grants_lore():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE, started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=600)
    assert out is not None
    assert out.kind == DreamKind.LORE_FRAGMENT


def test_long_bedroll_sleep_grants_seal():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.BEDROLL, started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=600)
    assert out is not None
    # bedroll quality 30 < 80 → falls to seal default
    assert out.kind == DreamKind.AF_SEAL


def test_short_bedroll_dreamless():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.BEDROLL, started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=120)
    assert out is not None
    # not enough time for rich-threshold but past minimum
    assert out.kind == DreamKind.EMPTY


def test_min_sleep_constant():
    e = SleepDreamEngine()
    assert e.min_sleep_for_dream() == 60


def test_after_end_no_longer_sleeping():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE, started_at=0,
    )
    e.end_sleep(player_id="alice", ended_at=600)
    assert e.is_sleeping(player_id="alice") is False


def test_inn_location_grants_lore_at_long_sleep():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.INN, started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=600)
    assert out is not None
    # inn quality 80 → meets ≥80 threshold
    assert out.kind == DreamKind.LORE_FRAGMENT


def test_outlaw_hideout_grants_seal_default():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.OUTLAW_HIDEOUT,
        started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=600)
    assert out is not None
    # quality 50 — not high enough for lore
    assert out.kind == DreamKind.AF_SEAL


def test_custom_roller():
    e = SleepDreamEngine()
    def fixed_roller(slept, qpct):
        return DreamReward(
            kind=DreamKind.SKILL_UNLOCK,
            payload="ki_secret_signet",
            summary="A skill awakens.",
        )
    e.set_roller(roller=fixed_roller)
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE,
        started_at=0,
    )
    out = e.end_sleep(player_id="alice", ended_at=600)
    assert out is not None
    assert out.kind == DreamKind.SKILL_UNLOCK
    assert out.payload == "ki_secret_signet"


def test_per_player_independent():
    e = SleepDreamEngine()
    e.begin_sleep(
        player_id="alice",
        location_kind=LocationKind.MOG_HOUSE, started_at=0,
    )
    e.begin_sleep(
        player_id="bob",
        location_kind=LocationKind.BEDROLL, started_at=0,
    )
    a = e.end_sleep(player_id="alice", ended_at=600)
    b = e.end_sleep(player_id="bob", ended_at=600)
    assert a is not None and b is not None
    assert a.kind == DreamKind.LORE_FRAGMENT
    assert b.kind == DreamKind.AF_SEAL


def test_five_dream_kinds():
    assert len(list(DreamKind)) == 5


def test_four_location_kinds():
    assert len(list(LocationKind)) == 4
