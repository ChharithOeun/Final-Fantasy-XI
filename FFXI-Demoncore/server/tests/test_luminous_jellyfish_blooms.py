"""Tests for luminous jellyfish blooms."""
from __future__ import annotations

from server.luminous_jellyfish_blooms import (
    BloomKind,
    BloomState,
    LuminousBlooms,
)


def test_open_bloom_at_high_tide():
    b = LuminousBlooms()
    ok = b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high",
        now_seconds=0,
    )
    assert ok is True
    assert b.state_of(kind=BloomKind.PEARLBLOOM) == BloomState.OPEN


def test_open_bloom_rejected_off_tide():
    b = LuminousBlooms()
    ok = b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="ebbing",
        now_seconds=0,
    )
    assert ok is False


def test_open_already_open_rejected():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=0,
    )
    ok = b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=10,
    )
    assert ok is False


def test_close_bloom_resets_strength():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=0,
    )
    b.close_bloom(kind=BloomKind.PEARLBLOOM, now_seconds=10)
    assert b.state_of(kind=BloomKind.PEARLBLOOM) == BloomState.DORMANT
    assert b.strength_of(kind=BloomKind.PEARLBLOOM) == 0


def test_close_bloom_idempotent():
    b = LuminousBlooms()
    ok = b.close_bloom(
        kind=BloomKind.PEARLBLOOM, now_seconds=0,
    )
    assert ok is False


def test_harvest_happy():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=0,
    )
    r = b.harvest(
        player_id="p",
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high",
        now_seconds=10,
    )
    assert r.accepted is True
    assert r.units == 1
    assert r.strength_after == 29


def test_harvest_blocked_off_tide():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=0,
    )
    r = b.harvest(
        player_id="p",
        kind=BloomKind.PEARLBLOOM,
        tide_phase="low",
        now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "tide not high"


def test_harvest_blocked_when_dormant():
    b = LuminousBlooms()
    r = b.harvest(
        player_id="p",
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high",
        now_seconds=0,
    )
    assert r.accepted is False
    assert r.reason == "bloom not open"


def test_harvest_depletes_strength_to_zero():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.REQUIEMBLOOM,  # base 8
        tide_phase="high", now_seconds=0,
    )
    for _ in range(8):
        r = b.harvest(
            player_id="p",
            kind=BloomKind.REQUIEMBLOOM,
            tide_phase="high",
            now_seconds=1,
        )
        assert r.accepted is True
    # 9th harvest fails
    r = b.harvest(
        player_id="p",
        kind=BloomKind.REQUIEMBLOOM,
        tide_phase="high",
        now_seconds=1,
    )
    assert r.accepted is False
    assert r.reason == "bloom depleted"


def test_harvest_blank_player():
    b = LuminousBlooms()
    b.open_bloom(
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high", now_seconds=0,
    )
    r = b.harvest(
        player_id="",
        kind=BloomKind.PEARLBLOOM,
        tide_phase="high",
        now_seconds=10,
    )
    assert r.accepted is False


def test_state_unknown_kind_dormant():
    b = LuminousBlooms()
    assert b.state_of(kind=BloomKind.EMBERBLOOM) == BloomState.DORMANT
