"""Tests for boarding party pvp."""
from __future__ import annotations

from server.boarding_party_pvp import (
    BoardingPartyPvp,
    BoardingState,
    KO_REVIVE_WINDOW_SECONDS,
    Side,
)


def test_start_boarding_happy():
    b = BoardingPartyPvp()
    r = b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1", "a2"),
        defender_party=("d1", "d2"),
        sanctioned=False,
        now_seconds=0,
    )
    assert r.accepted is True
    assert r.flagged_outlaw is True


def test_start_boarding_sanctioned_no_outlaw_flag():
    b = BoardingPartyPvp()
    r = b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",),
        defender_party=("d1",),
        sanctioned=True,
        now_seconds=0,
    )
    assert r.flagged_outlaw is False


def test_start_boarding_overlapping_rejected():
    b = BoardingPartyPvp()
    r = b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1", "shared"),
        defender_party=("d1", "shared"),
        sanctioned=False, now_seconds=0,
    )
    assert r.accepted is False


def test_start_boarding_oversize_rejected():
    b = BoardingPartyPvp()
    r = b.start_boarding(
        boarding_id="b1",
        attacker_party=tuple(f"a{i}" for i in range(7)),
        defender_party=("d1",),
        sanctioned=False, now_seconds=0,
    )
    assert r.accepted is False


def test_start_boarding_empty_rejected():
    b = BoardingPartyPvp()
    r = b.start_boarding(
        boarding_id="b1",
        attacker_party=(),
        defender_party=("d1",),
        sanctioned=False, now_seconds=0,
    )
    assert r.accepted is False


def test_ko_fighter_happy():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",),
        defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    r = b.ko_fighter(
        boarding_id="b1", fighter_id="d1", now_seconds=10,
    )
    assert r.accepted is True


def test_ko_unknown_fighter():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    r = b.ko_fighter(
        boarding_id="b1", fighter_id="ghost", now_seconds=10,
    )
    assert r.accepted is False


def test_ko_already_ko():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    r = b.ko_fighter(
        boarding_id="b1", fighter_id="d1", now_seconds=20,
    )
    assert r.accepted is False


def test_revive_within_window():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    r = b.revive_fighter(
        boarding_id="b1", fighter_id="d1", now_seconds=30,
    )
    assert r.accepted is True


def test_revive_after_window():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    r = b.revive_fighter(
        boarding_id="b1", fighter_id="d1",
        now_seconds=10 + KO_REVIVE_WINDOW_SECONDS + 1,
    )
    assert r.accepted is False


def test_check_resolution_attacker_wins():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    r = b.check_resolution(
        boarding_id="b1",
        now_seconds=10 + KO_REVIVE_WINDOW_SECONDS + 1,
    )
    assert r.state == BoardingState.ATTACKER_WINS
    assert r.winner == Side.ATTACKER


def test_check_resolution_defender_wins():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="a1", now_seconds=10)
    r = b.check_resolution(
        boarding_id="b1",
        now_seconds=10 + KO_REVIVE_WINDOW_SECONDS + 1,
    )
    assert r.winner == Side.DEFENDER


def test_check_resolution_still_active():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    r = b.check_resolution(
        boarding_id="b1", now_seconds=10,
    )
    assert r.state == BoardingState.ACTIVE


def test_check_resolution_within_window_still_active():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=True, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    # within revive window — defender still counted as active
    r = b.check_resolution(
        boarding_id="b1", now_seconds=20,
    )
    assert r.state == BoardingState.ACTIVE


def test_unsanctioned_winner_flags_outlaw():
    b = BoardingPartyPvp()
    b.start_boarding(
        boarding_id="b1",
        attacker_party=("a1",), defender_party=("d1",),
        sanctioned=False, now_seconds=0,
    )
    b.ko_fighter(boarding_id="b1", fighter_id="d1", now_seconds=10)
    r = b.check_resolution(
        boarding_id="b1",
        now_seconds=10 + KO_REVIVE_WINDOW_SECONDS + 1,
    )
    assert r.flagged_outlaw is True
