"""Tests for crew ship inventory."""
from __future__ import annotations

from server.crew_ship_inventory import (
    CrewRole,
    CrewShipInventory,
    OFFICER_DAILY_WITHDRAW_LIMIT,
)


def test_deposit_happy():
    i = CrewShipInventory()
    r = i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW,
        item_id="cargo_a", quantity=10, now_seconds=0,
    )
    assert r.accepted is True
    assert r.new_total == 10


def test_deposit_blank_ids():
    i = CrewShipInventory()
    r = i.deposit(
        charter_id="", member_id="m",
        role=CrewRole.CREW, item_id="x", quantity=1,
        now_seconds=0,
    )
    assert r.accepted is False


def test_deposit_zero_qty_rejected():
    i = CrewShipInventory()
    r = i.deposit(
        charter_id="c1", member_id="m",
        role=CrewRole.CREW, item_id="x", quantity=0,
        now_seconds=0,
    )
    assert r.accepted is False


def test_deposit_stack_cap():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m",
        role=CrewRole.CREW, item_id="x", quantity=900,
        now_seconds=0,
    )
    r = i.deposit(
        charter_id="c1", member_id="m",
        role=CrewRole.CREW, item_id="x", quantity=200,
        now_seconds=0,
    )
    # capped at 999 -> only 99 actually added
    assert r.quantity == 99
    assert r.new_total == 999


def test_captain_withdraw_unrestricted():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="x", quantity=50,
        now_seconds=0,
    )
    r = i.withdraw(
        charter_id="c1", member_id="cap",
        role=CrewRole.CAPTAIN,
        item_id="x", quantity=30, now_seconds=10,
    )
    assert r.accepted is True
    assert r.remaining == 20


def test_crew_can_redraw_own_recent():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="x", quantity=50,
        now_seconds=0,
    )
    r = i.withdraw(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW,
        item_id="x", quantity=20, now_seconds=10,
    )
    assert r.accepted is True


def test_crew_cannot_take_others_items():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="x", quantity=50,
        now_seconds=0,
    )
    r = i.withdraw(
        charter_id="c1", member_id="m2",
        role=CrewRole.CREW,
        item_id="x", quantity=20, now_seconds=10,
    )
    assert r.accepted is False
    assert r.reason == "crew redraw limit"


def test_crew_redraw_window_expires():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="x", quantity=50,
        now_seconds=0,
    )
    # 25h later — outside redraw window
    r = i.withdraw(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW,
        item_id="x", quantity=20,
        now_seconds=25 * 3_600,
    )
    assert r.accepted is False


def test_officer_daily_withdraw_limit():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CAPTAIN, item_id="x",
        quantity=999, now_seconds=0,
    )
    for n in range(OFFICER_DAILY_WITHDRAW_LIMIT):
        r = i.withdraw(
            charter_id="c1", member_id="off1",
            role=CrewRole.OFFICER,
            item_id="x", quantity=1, now_seconds=10,
        )
        assert r.accepted is True
    # next withdraw same day should fail
    r = i.withdraw(
        charter_id="c1", member_id="off1",
        role=CrewRole.OFFICER,
        item_id="x", quantity=1, now_seconds=20,
    )
    assert r.accepted is False
    assert r.reason == "officer daily limit"


def test_officer_limit_resets_next_day():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CAPTAIN, item_id="x",
        quantity=999, now_seconds=0,
    )
    for n in range(OFFICER_DAILY_WITHDRAW_LIMIT):
        i.withdraw(
            charter_id="c1", member_id="off1",
            role=CrewRole.OFFICER,
            item_id="x", quantity=1, now_seconds=10,
        )
    # next day
    r = i.withdraw(
        charter_id="c1", member_id="off1",
        role=CrewRole.OFFICER,
        item_id="x", quantity=1,
        now_seconds=24 * 3_600 + 100,
    )
    assert r.accepted is True


def test_withdraw_insufficient_holdings():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CAPTAIN, item_id="x",
        quantity=10, now_seconds=0,
    )
    r = i.withdraw(
        charter_id="c1", member_id="cap",
        role=CrewRole.CAPTAIN,
        item_id="x", quantity=20, now_seconds=10,
    )
    assert r.accepted is False


def test_holdings_returns_state():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="cargo_a", quantity=5,
        now_seconds=0,
    )
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="cargo_b", quantity=3,
        now_seconds=0,
    )
    h = i.holdings(charter_id="c1")
    assert h["cargo_a"] == 5
    assert h["cargo_b"] == 3


def test_holdings_empty_for_unknown_charter():
    i = CrewShipInventory()
    assert i.holdings(charter_id="ghost") == {}


def test_audit_records_deposits():
    i = CrewShipInventory()
    i.deposit(
        charter_id="c1", member_id="m1",
        role=CrewRole.CREW, item_id="x",
        quantity=5, now_seconds=42,
    )
    audit = i.audit_recent(charter_id="c1")
    assert len(audit) == 1
    assert audit[0].member_id == "m1"
    assert audit[0].deposited_at == 42
