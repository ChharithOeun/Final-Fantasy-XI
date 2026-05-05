"""Tests for octopi scholar research."""
from __future__ import annotations

from server.octopi_scholar_research import (
    OctopiScholarResearch,
    SampleKind,
    Tome,
)


def test_initial_standing_zero():
    o = OctopiScholarResearch()
    assert o.standing(player_id="p") == 0


def test_turn_in_mob_notes_adds_standing():
    o = OctopiScholarResearch()
    r = o.turn_in(
        player_id="p",
        kind=SampleKind.MOB_NOTE,
        qty=10,
    )
    assert r.accepted is True
    assert r.standing_gained == 10
    assert r.new_standing == 10


def test_turn_in_requiem_record_high_value():
    o = OctopiScholarResearch()
    r = o.turn_in(
        player_id="p",
        kind=SampleKind.REQUIEM_RECORD,
        qty=1,
    )
    assert r.standing_gained == 40


def test_turn_in_zero_qty_rejected():
    o = OctopiScholarResearch()
    r = o.turn_in(
        player_id="p",
        kind=SampleKind.MOB_NOTE,
        qty=0,
    )
    assert r.accepted is False


def test_turn_in_blank_player_rejected():
    o = OctopiScholarResearch()
    r = o.turn_in(
        player_id="",
        kind=SampleKind.MOB_NOTE,
        qty=1,
    )
    assert r.accepted is False


def test_turn_in_accumulates():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p", kind=SampleKind.MOB_NOTE, qty=5,
    )
    o.turn_in(
        player_id="p", kind=SampleKind.ABYSSAL_FRAG, qty=2,
    )
    # 5*1 + 2*5 = 15
    assert o.standing(player_id="p") == 15


def test_no_trades_available_at_zero():
    o = OctopiScholarResearch()
    trades = o.available_trades(player_id="p")
    assert len(trades) == 0


def test_coral_tome_unlocks_at_5_standing():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p", kind=SampleKind.MOB_NOTE, qty=5,
    )
    trades = o.available_trades(player_id="p")
    tomes = {t.tome for t in trades}
    assert Tome.CORAL_TOME in tomes
    assert Tome.ABYSSAL_CODEX not in tomes


def test_all_tomes_unlock_at_high_standing():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p",
        kind=SampleKind.REQUIEM_RECORD,
        qty=10,
    )  # 400 standing
    trades = o.available_trades(player_id="p")
    tomes = {t.tome for t in trades}
    assert Tome.CORAL_TOME in tomes
    assert Tome.ABYSSAL_CODEX in tomes
    assert Tome.REQUIEM_LIBRO in tomes
    assert Tome.KRAKEN_PRIMER in tomes


def test_request_tome_below_standing_rejected():
    o = OctopiScholarResearch()
    r = o.request_tome(
        player_id="p", tome=Tome.CORAL_TOME,
    )
    assert r.accepted is False
    assert r.reason == "standing too low"


def test_request_tome_consumes_standing():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p",
        kind=SampleKind.MOB_NOTE, qty=10,
    )  # 10 standing
    r = o.request_tome(
        player_id="p", tome=Tome.CORAL_TOME,
    )
    assert r.accepted is True
    # CORAL_TOME costs 5 standing -> 10 - 5 = 5
    assert r.standing_after == 5
    assert o.standing(player_id="p") == 5


def test_request_kraken_primer_high_cost():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p",
        kind=SampleKind.REQUIEM_RECORD,
        qty=10,
    )  # 400 standing
    r = o.request_tome(
        player_id="p", tome=Tome.KRAKEN_PRIMER,
    )
    assert r.accepted is True
    # 400 - 150 = 250
    assert r.standing_after == 250


def test_request_blocks_at_low_standing_after_consume():
    o = OctopiScholarResearch()
    o.turn_in(
        player_id="p",
        kind=SampleKind.MOB_NOTE, qty=5,
    )  # 5 standing -> coral unlocked
    o.request_tome(player_id="p", tome=Tome.CORAL_TOME)
    # 0 standing now, coral_tome should be locked again
    trades = o.available_trades(player_id="p")
    assert len(trades) == 0
