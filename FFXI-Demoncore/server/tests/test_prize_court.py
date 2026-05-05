"""Tests for prize court."""
from __future__ import annotations

from server.prize_court import Disposition, PrizeCourt


def test_file_prize_happy():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="prize1",
        captured_ship_id="ship_x",
        attacker_party=("captain", "off1", "off2", "crew1", "crew2"),
        captain="captain",
        officers=("off1", "off2"),
        cargo_value=1_000,
        gil_in_hold=0,
        has_letter_of_marque=True,
        attacker_fleet_open_slots=1,
    )
    assert ok is True


def test_file_prize_blank_ids():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="",
        captured_ship_id="ship_x",
        attacker_party=("c",), captain="c",
        officers=(), cargo_value=0, gil_in_hold=0,
        has_letter_of_marque=False, attacker_fleet_open_slots=0,
    )
    assert ok is False


def test_file_prize_captain_not_in_party():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("a", "b"), captain="c",
        officers=(), cargo_value=0, gil_in_hold=0,
        has_letter_of_marque=False, attacker_fleet_open_slots=0,
    )
    assert ok is False


def test_file_prize_too_many_officers():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c", "o1", "o2", "o3"),
        captain="c",
        officers=("o1", "o2", "o3"),
        cargo_value=0, gil_in_hold=0,
        has_letter_of_marque=False, attacker_fleet_open_slots=0,
    )
    assert ok is False


def test_file_prize_officer_not_in_party():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c", "crew"), captain="c",
        officers=("ghost",),
        cargo_value=0, gil_in_hold=0,
        has_letter_of_marque=False, attacker_fleet_open_slots=0,
    )
    assert ok is False


def test_file_prize_negative_cargo():
    p = PrizeCourt()
    ok = p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c",), captain="c",
        officers=(), cargo_value=-1, gil_in_hold=0,
        has_letter_of_marque=False, attacker_fleet_open_slots=0,
    )
    assert ok is False


def test_resolve_with_letter_takes_nation_tax():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("captain", "off1", "crew1"),
        captain="captain", officers=("off1",),
        cargo_value=10_000, gil_in_hold=0,
        has_letter_of_marque=True,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    # nation tax 10% of 10000 = 1000
    assert r.nation_tax == 1_000
    # captain 30% = 3000
    assert r.captain_share == 3_000
    # officer pool 30% = 3000; 1 officer -> 3000
    assert r.officer_shares["off1"] == 3_000


def test_resolve_without_letter_no_nation_cut():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("captain", "off1", "crew1"),
        captain="captain", officers=("off1",),
        cargo_value=10_000, gil_in_hold=0,
        has_letter_of_marque=False,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    assert r.nation_tax == 0


def test_resolve_disposition_keep_when_slot_open():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c",), captain="c",
        officers=(), cargo_value=100, gil_in_hold=0,
        has_letter_of_marque=False,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    assert r.disposition == Disposition.KEEP_AS_PRIZE


def test_resolve_disposition_scuttle_when_full():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c",), captain="c",
        officers=(), cargo_value=100, gil_in_hold=0,
        has_letter_of_marque=False,
        attacker_fleet_open_slots=0,
    )
    r = p.resolve(prize_id="x")
    assert r.disposition == Disposition.SCUTTLE


def test_resolve_unknown_prize():
    p = PrizeCourt()
    r = p.resolve(prize_id="ghost")
    assert r.accepted is False


def test_resolve_double_rejected():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("c",), captain="c",
        officers=(), cargo_value=100, gil_in_hold=0,
        has_letter_of_marque=False,
        attacker_fleet_open_slots=0,
    )
    p.resolve(prize_id="x")
    r = p.resolve(prize_id="x")
    assert r.accepted is False


def test_crew_split_evenly():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("captain", "c1", "c2", "c3"),
        captain="captain", officers=(),
        cargo_value=10_000, gil_in_hold=0,
        has_letter_of_marque=True,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    # crew pool: 10000 - 1000 nation - 3000 captain - 3000 officer
    # = 3000; split among 3 crew = 1000 each
    crew_values = list(r.crew_shares.values())
    assert all(v == 1_000 for v in crew_values)


def test_no_officers_pool_unallocated():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("captain", "c1"),
        captain="captain", officers=(),
        cargo_value=10_000, gil_in_hold=0,
        has_letter_of_marque=True,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    assert r.officer_shares == {}


def test_gil_and_cargo_combined():
    p = PrizeCourt()
    p.file_prize(
        prize_id="x", captured_ship_id="s",
        attacker_party=("captain",),
        captain="captain", officers=(),
        cargo_value=4_000, gil_in_hold=6_000,
        has_letter_of_marque=True,
        attacker_fleet_open_slots=1,
    )
    r = p.resolve(prize_id="x")
    # total 10000, nation tax 1000, captain 3000
    assert r.captain_share == 3_000
    assert r.nation_tax == 1_000
