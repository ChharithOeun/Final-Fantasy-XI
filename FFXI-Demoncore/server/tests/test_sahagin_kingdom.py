"""Tests for sahagin kingdom."""
from __future__ import annotations

from server.sahagin_kingdom import (
    SahaginKingdom,
    SahaginPresence,
)


def test_set_capital_happy():
    k = SahaginKingdom()
    assert k.set_capital(
        zone_id="kings_brood", band=4, fortification=100,
    ) is True


def test_set_capital_blank():
    k = SahaginKingdom()
    assert k.set_capital(zone_id="", band=4) is False


def test_set_capital_bad_fortification():
    k = SahaginKingdom()
    assert k.set_capital(
        zone_id="kings_brood", band=4, fortification=150,
    ) is False


def test_capital_marks_presence():
    k = SahaginKingdom()
    k.set_capital(zone_id="kings_brood", band=4)
    assert k.presence_in(
        zone_id="kings_brood", band=4,
    ) == SahaginPresence.CAPITAL


def test_is_capital():
    k = SahaginKingdom()
    k.set_capital(zone_id="kings_brood", band=4)
    assert k.is_capital(zone_id="kings_brood", band=4) is True
    assert k.is_capital(zone_id="elsewhere", band=4) is False


def test_add_presence_happy():
    k = SahaginKingdom()
    assert k.add_presence(
        zone_id="reef_a", band=2,
        presence=SahaginPresence.CELL,
    ) is True


def test_add_presence_capital_blocked():
    k = SahaginKingdom()
    assert k.add_presence(
        zone_id="reef_a", band=2,
        presence=SahaginPresence.CAPITAL,
    ) is False


def test_add_presence_blank():
    k = SahaginKingdom()
    assert k.add_presence(
        zone_id="", band=2,
        presence=SahaginPresence.CELL,
    ) is False


def test_add_presence_cant_overwrite_capital():
    k = SahaginKingdom()
    k.set_capital(zone_id="kings_brood", band=4)
    ok = k.add_presence(
        zone_id="kings_brood", band=4,
        presence=SahaginPresence.SCOUT,
    )
    assert ok is False
    assert k.presence_in(
        zone_id="kings_brood", band=4,
    ) == SahaginPresence.CAPITAL


def test_presence_default_none():
    k = SahaginKingdom()
    assert k.presence_in(
        zone_id="ghost", band=2,
    ) == SahaginPresence.NONE


def test_all_presence_zones():
    k = SahaginKingdom()
    k.set_capital(zone_id="kings_brood", band=4)
    k.add_presence(
        zone_id="reef_a", band=2, presence=SahaginPresence.CELL,
    )
    k.add_presence(
        zone_id="reef_b", band=3, presence=SahaginPresence.SCOUT,
    )
    out = k.all_presence_zones()
    assert len(out) == 3


def test_territory_count():
    k = SahaginKingdom()
    assert k.territory_count() == 0
    k.set_capital(zone_id="kings_brood", band=4)
    assert k.territory_count() == 1
    k.add_presence(
        zone_id="reef_a", band=2, presence=SahaginPresence.CELL,
    )
    assert k.territory_count() == 2


def test_presence_can_be_upgraded():
    k = SahaginKingdom()
    k.add_presence(
        zone_id="reef_a", band=2, presence=SahaginPresence.SCOUT,
    )
    k.add_presence(
        zone_id="reef_a", band=2, presence=SahaginPresence.STRONGHOLD,
    )
    assert k.presence_in(
        zone_id="reef_a", band=2,
    ) == SahaginPresence.STRONGHOLD
