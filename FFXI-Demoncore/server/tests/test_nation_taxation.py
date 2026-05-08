"""Tests for nation_taxation."""
from __future__ import annotations

from server.nation_taxation import (
    NationTaxationSystem, TaxKind, LevyState,
)


def _setup(s):
    s.set_rate(
        nation_id="bastok", kind=TaxKind.INCOME,
        rate_bps=500,  # 5%
        exemption_min_gil=100,
    )


def test_set_rate_happy():
    s = NationTaxationSystem()
    assert s.set_rate(
        nation_id="bastok", kind=TaxKind.INCOME,
        rate_bps=500,
    ) is True


def test_set_rate_blank():
    s = NationTaxationSystem()
    assert s.set_rate(
        nation_id="", kind=TaxKind.INCOME,
        rate_bps=500,
    ) is False


def test_set_rate_negative():
    s = NationTaxationSystem()
    assert s.set_rate(
        nation_id="bastok", kind=TaxKind.INCOME,
        rate_bps=-1,
    ) is False


def test_set_rate_over_max():
    s = NationTaxationSystem()
    assert s.set_rate(
        nation_id="bastok", kind=TaxKind.INCOME,
        rate_bps=10_001,
    ) is False


def test_open_cycle_happy():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    assert cid is not None


def test_open_cycle_no_rate():
    s = NationTaxationSystem()
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    assert cid is None


def test_open_cycle_zero_period():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=0,
    )
    assert cid is None


def test_record_taxable_happy():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    owed = s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=15,
    )
    # 5% of 10_000 = 500
    assert owed == 500


def test_record_below_exemption():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    owed = s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=50, now_day=15,
    )
    assert owed == 0


def test_record_after_period_blocked():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    owed = s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=50,
    )
    assert owed == 0


def test_record_zero_gil():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    owed = s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=0, now_day=15,
    )
    assert owed == 0


def test_record_unknown_cycle():
    s = NationTaxationSystem()
    owed = s.record_taxable(
        cycle_id="ghost", payer_id="bob",
        base_gil=10_000, now_day=15,
    )
    assert owed == 0


def test_record_after_close_blocked():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.close_cycle(cycle_id=cid, ended_day=15)
    owed = s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=16,
    )
    assert owed == 0


def test_close_cycle_returns_total():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=15,
    )
    s.record_taxable(
        cycle_id=cid, payer_id="cara",
        base_gil=20_000, now_day=16,
    )
    total = s.close_cycle(
        cycle_id=cid, ended_day=40,
    )
    assert total == 1500


def test_close_double_blocked():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.close_cycle(cycle_id=cid, ended_day=40)
    assert s.close_cycle(
        cycle_id=cid, ended_day=41,
    ) == 0


def test_revenue_for_nation_aggregates():
    s = NationTaxationSystem()
    _setup(s)
    cid_a = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.record_taxable(
        cycle_id=cid_a, payer_id="bob",
        base_gil=10_000, now_day=15,
    )
    s.set_rate(
        nation_id="bastok", kind=TaxKind.SALES,
        rate_bps=200,
    )
    cid_b = s.open_cycle(
        nation_id="bastok", kind=TaxKind.SALES,
        started_day=10, period_days=30,
    )
    s.record_taxable(
        cycle_id=cid_b, payer_id="cara",
        base_gil=10_000, now_day=15,
    )
    # 500 + 200 = 700
    assert s.revenue_for(nation_id="bastok") == 700


def test_per_payer_accumulates():
    s = NationTaxationSystem()
    _setup(s)
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=15,
    )
    s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=20_000, now_day=16,
    )
    # 500 + 1000 = 1500
    assert s.per_payer(
        cycle_id=cid, payer_id="bob",
    ) == 1500


def test_active_cycles_filter():
    s = NationTaxationSystem()
    _setup(s)
    cid_open = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    s.set_rate(
        nation_id="bastok", kind=TaxKind.SALES,
        rate_bps=200,
    )
    cid_closed = s.open_cycle(
        nation_id="bastok", kind=TaxKind.SALES,
        started_day=10, period_days=30,
    )
    s.close_cycle(cycle_id=cid_closed, ended_day=40)
    out = s.active_cycles(nation_id="bastok")
    ids = [c.cycle_id for c in out]
    assert cid_open in ids
    assert cid_closed not in ids


def test_cycle_unknown():
    s = NationTaxationSystem()
    assert s.cycle(cycle_id="ghost") is None


def test_zero_rate_collects_nothing():
    s = NationTaxationSystem()
    s.set_rate(
        nation_id="bastok", kind=TaxKind.INCOME,
        rate_bps=0,
    )
    cid = s.open_cycle(
        nation_id="bastok", kind=TaxKind.INCOME,
        started_day=10, period_days=30,
    )
    assert s.record_taxable(
        cycle_id=cid, payer_id="bob",
        base_gil=10_000, now_day=15,
    ) == 0


def test_enum_counts():
    assert len(list(TaxKind)) == 6
    assert len(list(LevyState)) == 2
