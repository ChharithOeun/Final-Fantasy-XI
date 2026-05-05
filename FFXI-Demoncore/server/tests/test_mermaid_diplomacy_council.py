"""Tests for mermaid diplomacy council."""
from __future__ import annotations

from server.mermaid_diplomacy_council import (
    DEFAULT_POLICY,
    DiplomacyCouncil,
    Faction,
    Policy,
)


def test_default_policy_when_empty():
    c = DiplomacyCouncil()
    assert c.current_policy() == DEFAULT_POLICY
    assert c.holding_court() is None


def test_seat_one_faction():
    c = DiplomacyCouncil()
    r = c.seat(faction=Faction.TIDE_KEEPERS, count=5)
    assert r.accepted is True
    assert c.seats_for(faction=Faction.TIDE_KEEPERS) == 5


def test_seat_negative_rejected():
    c = DiplomacyCouncil()
    r = c.seat(faction=Faction.TIDE_KEEPERS, count=-1)
    assert r.accepted is False


def test_remove_seats_happy():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=5)
    r = c.remove_seats(faction=Faction.TIDE_KEEPERS, count=2)
    assert r.accepted is True
    assert c.seats_for(faction=Faction.TIDE_KEEPERS) == 3


def test_remove_seats_too_many():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=2)
    r = c.remove_seats(faction=Faction.TIDE_KEEPERS, count=5)
    assert r.accepted is False
    assert r.reason == "not enough seats to remove"


def test_move_seats_happy():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.MERCHANT_PEARL, count=4)
    r = c.move_seats(
        from_faction=Faction.MERCHANT_PEARL,
        to_faction=Faction.TIDE_KEEPERS,
        count=3,
    )
    assert r.accepted is True
    assert c.seats_for(faction=Faction.MERCHANT_PEARL) == 1
    assert c.seats_for(faction=Faction.TIDE_KEEPERS) == 3


def test_move_seats_same_faction_rejected():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=4)
    r = c.move_seats(
        from_faction=Faction.TIDE_KEEPERS,
        to_faction=Faction.TIDE_KEEPERS,
        count=1,
    )
    assert r.accepted is False


def test_holding_court_plurality():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=5)
    c.seat(faction=Faction.MERCHANT_PEARL, count=3)
    c.seat(faction=Faction.DEEP_FAITHFUL, count=2)
    assert c.holding_court() == Faction.TIDE_KEEPERS


def test_tied_court_no_leader():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=3)
    c.seat(faction=Faction.MERCHANT_PEARL, count=3)
    assert c.holding_court() is None
    assert c.current_policy() == DEFAULT_POLICY


def test_policy_trade_open_under_tide_keepers():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.TIDE_KEEPERS, count=10)
    assert c.current_policy() == Policy.TRADE_OPEN


def test_policy_raid_under_deep_faithful():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.DEEP_FAITHFUL, count=10)
    assert c.current_policy() == Policy.RAID_THE_SURFACE


def test_policy_tribute_under_merchant_pearl():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.MERCHANT_PEARL, count=10)
    assert c.current_policy() == Policy.TRIBUTE_FOR_PEACE


def test_seats_for_unseated_faction_zero():
    c = DiplomacyCouncil()
    assert c.seats_for(faction=Faction.DEEP_FAITHFUL) == 0


def test_court_changes_when_seats_shift():
    c = DiplomacyCouncil()
    c.seat(faction=Faction.MERCHANT_PEARL, count=5)
    assert c.holding_court() == Faction.MERCHANT_PEARL
    # players run a quest that moves 4 seats to TIDE_KEEPERS
    c.move_seats(
        from_faction=Faction.MERCHANT_PEARL,
        to_faction=Faction.TIDE_KEEPERS,
        count=4,
    )
    assert c.holding_court() == Faction.TIDE_KEEPERS
    assert c.current_policy() == Policy.TRADE_OPEN
