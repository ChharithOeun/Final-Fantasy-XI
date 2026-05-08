"""Tests for nation_treasury."""
from __future__ import annotations

from server.nation_treasury import (
    InflowKind, NationTreasury, OutflowKind,
)


def test_open_treasury_happy():
    t = NationTreasury()
    assert t.open_treasury(
        nation="bastok", starting_balance=100000,
    ) is True
    assert t.balance(nation="bastok") == 100000


def test_open_treasury_blank_blocked():
    t = NationTreasury()
    assert t.open_treasury(
        nation="", starting_balance=1000,
    ) is False


def test_open_negative_blocked():
    t = NationTreasury()
    assert t.open_treasury(
        nation="bastok", starting_balance=-1,
    ) is False


def test_open_dup_blocked():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=100)
    assert t.open_treasury(
        nation="bastok", starting_balance=200,
    ) is False


def test_record_inflow():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    assert t.record_inflow(
        nation="bastok", kind=InflowKind.TAX_INCOME,
        amount=500, source="ah",
    ) is True
    assert t.balance(nation="bastok") == 1500


def test_record_inflow_zero_blocked():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    assert t.record_inflow(
        nation="bastok", kind=InflowKind.TAX_INCOME,
        amount=0, source="ah",
    ) is False


def test_record_inflow_blank_source_blocked():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    assert t.record_inflow(
        nation="bastok", kind=InflowKind.TAX_INCOME,
        amount=500, source="",
    ) is False


def test_record_inflow_unknown_nation_blocked():
    t = NationTreasury()
    assert t.record_inflow(
        nation="ghost", kind=InflowKind.TAX_INCOME,
        amount=500, source="ah",
    ) is False


def test_record_outflow():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    assert t.record_outflow(
        nation="bastok", kind=OutflowKind.MILITARY_PAY,
        amount=300, dest="cid",
    ) is True
    assert t.balance(nation="bastok") == 700


def test_record_outflow_into_deficit():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=100)
    t.record_outflow(
        nation="bastok", kind=OutflowKind.MILITARY_PAY,
        amount=500, dest="cid",
    )
    assert t.balance(nation="bastok") == -400
    assert t.deficit_state(nation="bastok") is True


def test_no_deficit_with_positive_balance():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    assert t.deficit_state(nation="bastok") is False


def test_balance_unknown_nation():
    t = NationTreasury()
    assert t.balance(nation="ghost") == 0


def test_ledger_records_entries_newest_first():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    t.record_inflow(
        nation="bastok", kind=InflowKind.TAX_INCOME,
        amount=100, source="ah",
    )
    t.record_outflow(
        nation="bastok", kind=OutflowKind.MILITARY_PAY,
        amount=50, dest="cid",
    )
    led = t.ledger(nation="bastok")
    assert len(led) == 2
    # Newest first
    assert led[0].kind == "military_pay"
    assert led[0].is_inflow is False
    assert led[1].kind == "tax_income"


def test_ledger_unknown_nation():
    t = NationTreasury()
    assert t.ledger(nation="ghost") == []


def test_ledger_truncates_at_200():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000000)
    for i in range(250):
        t.record_inflow(
            nation="bastok", kind=InflowKind.TAX_INCOME,
            amount=1, source="ah",
        )
    led = t.ledger(nation="bastok")
    assert len(led) == 200


def test_ledger_n_limit():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=1000)
    for _ in range(5):
        t.record_inflow(
            nation="bastok", kind=InflowKind.TAX_INCOME,
            amount=100, source="ah",
        )
    led = t.ledger(nation="bastok", n=3)
    assert len(led) == 3


def test_inflow_outflow_combine():
    t = NationTreasury()
    t.open_treasury(nation="bastok", starting_balance=10000)
    t.record_inflow(
        nation="bastok",
        kind=InflowKind.CONQUEST_TRIBUTE,
        amount=5000, source="conquest_week_5",
    )
    t.record_outflow(
        nation="bastok",
        kind=OutflowKind.PUBLIC_WORKS_GRANT,
        amount=8000, dest="bastok_river_bridge",
    )
    assert t.balance(nation="bastok") == 7000


def test_four_inflow_kinds():
    assert len(list(InflowKind)) == 4


def test_five_outflow_kinds():
    assert len(list(OutflowKind)) == 5
