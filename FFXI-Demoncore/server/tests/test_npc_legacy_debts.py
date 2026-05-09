"""Tests for npc_legacy_debts."""
from __future__ import annotations

from server.npc_legacy_debts import (
    NPCLegacyDebtsSystem, DebtState,
)


def _open(s, **overrides):
    args = dict(
        debt_id="d1", debtor_id="off_volker",
        creditor_id="bastok_treasury",
        principal_gil=100_000,
        interest_bps_per_day=10,  # 0.1%/day
        incurred_day=10, priority=100,
    )
    args.update(overrides)
    return s.open_debt(**args)


def test_open_happy():
    s = NPCLegacyDebtsSystem()
    assert _open(s) is True


def test_open_blank():
    s = NPCLegacyDebtsSystem()
    assert _open(s, debt_id="") is False


def test_open_self_debt():
    s = NPCLegacyDebtsSystem()
    assert _open(
        s, debtor_id="x", creditor_id="x",
    ) is False


def test_open_zero_principal():
    s = NPCLegacyDebtsSystem()
    assert _open(s, principal_gil=0) is False


def test_open_negative_interest():
    s = NPCLegacyDebtsSystem()
    assert _open(
        s, interest_bps_per_day=-1,
    ) is False


def test_open_excessive_interest():
    s = NPCLegacyDebtsSystem()
    assert _open(
        s, interest_bps_per_day=1_500,
    ) is False


def test_open_dup_blocked():
    s = NPCLegacyDebtsSystem()
    _open(s)
    assert _open(s) is False


def test_accrue_interest():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=100_000,
          interest_bps_per_day=10,
          incurred_day=10)
    # 100k * 10bps/10000 = 100 gil/day, * 30 days = 3000
    interest = s.accrue(debt_id="d1", now_day=40)
    assert interest == 3_000


def test_accrue_no_passage():
    s = NPCLegacyDebtsSystem()
    _open(s, incurred_day=10)
    assert s.accrue(debt_id="d1", now_day=10) == 0


def test_accrue_already_settled_blocked():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=100_000,
          incurred_day=10)
    s.settle_from_pool(
        debtor_id="off_volker", pool_gil=200_000,
        now_day=20,
    )
    assert s.accrue(
        debt_id="d1", now_day=50,
    ) == 0


def test_total_owed():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=100_000,
          interest_bps_per_day=10,
          incurred_day=10)
    s.accrue(debt_id="d1", now_day=40)
    # 100_000 + 3_000
    assert s.total_owed(debt_id="d1") == 103_000


def test_settle_clears_smaller_pool():
    s = NPCLegacyDebtsSystem()
    _open(s, debt_id="a",
          debtor_id="o", creditor_id="c1",
          principal_gil=100_000,
          interest_bps_per_day=0,
          incurred_day=10, priority=10)
    _open(s, debt_id="b",
          debtor_id="o", creditor_id="c2",
          principal_gil=50_000,
          interest_bps_per_day=0,
          incurred_day=10, priority=20)
    remaining = s.settle_from_pool(
        debtor_id="o", pool_gil=120_000,
        now_day=20,
    )
    # a (100k, priority 10) settles first.
    # b: 20k toward 50k = partial.
    assert remaining == 0
    a = s.debt(debt_id="a")
    b = s.debt(debt_id="b")
    assert a.state == DebtState.SETTLED
    assert b.state == DebtState.PAYABLE
    assert b.paid_gil == 20_000


def test_settle_full_payment():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=50_000,
          interest_bps_per_day=0,
          incurred_day=10)
    rem = s.settle_from_pool(
        debtor_id="off_volker", pool_gil=100_000,
        now_day=20,
    )
    assert rem == 50_000
    assert s.debt(
        debt_id="d1",
    ).state == DebtState.SETTLED


def test_settle_zero_pool():
    s = NPCLegacyDebtsSystem()
    _open(s)
    rem = s.settle_from_pool(
        debtor_id="off_volker", pool_gil=0,
        now_day=20,
    )
    assert rem == 0


def test_settle_priority_order():
    s = NPCLegacyDebtsSystem()
    _open(s, debt_id="low_pri",
          debtor_id="o", creditor_id="c1",
          principal_gil=20_000,
          interest_bps_per_day=0,
          incurred_day=10, priority=999)
    _open(s, debt_id="high_pri",
          debtor_id="o", creditor_id="c2",
          principal_gil=20_000,
          interest_bps_per_day=0,
          incurred_day=10, priority=1)
    s.settle_from_pool(
        debtor_id="o", pool_gil=20_000,
        now_day=20,
    )
    # high_pri is paid first
    assert s.debt(
        debt_id="high_pri",
    ).state == DebtState.SETTLED
    assert s.debt(
        debt_id="low_pri",
    ).state == DebtState.PAYABLE


def test_forgive():
    s = NPCLegacyDebtsSystem()
    _open(s)
    assert s.forgive(
        debt_id="d1", now_day=20,
    ) is True


def test_forgive_settled_blocked():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=10_000,
          interest_bps_per_day=0,
          incurred_day=10)
    s.settle_from_pool(
        debtor_id="off_volker", pool_gil=20_000,
        now_day=15,
    )
    assert s.forgive(
        debt_id="d1", now_day=20,
    ) is False


def test_default():
    s = NPCLegacyDebtsSystem()
    _open(s)
    assert s.default(
        debt_id="d1", now_day=20,
    ) is True


def test_mark_following():
    s = NPCLegacyDebtsSystem()
    _open(s)
    assert s.mark_following(
        debt_id="d1", now_day=400,
    ) is True
    assert s.debt(
        debt_id="d1",
    ).state == DebtState.FOLLOWING


def test_mark_following_settled_blocked():
    s = NPCLegacyDebtsSystem()
    _open(s, principal_gil=10_000,
          interest_bps_per_day=0,
          incurred_day=10)
    s.settle_from_pool(
        debtor_id="off_volker", pool_gil=20_000,
        now_day=15,
    )
    assert s.mark_following(
        debt_id="d1", now_day=400,
    ) is False


def test_debts_of_filter():
    s = NPCLegacyDebtsSystem()
    _open(s, debt_id="a",
          debtor_id="o1", creditor_id="c1")
    _open(s, debt_id="b",
          debtor_id="o2", creditor_id="c1")
    _open(s, debt_id="c",
          debtor_id="o1", creditor_id="c2")
    out = s.debts_of(debtor_id="o1")
    ids = sorted(d.debt_id for d in out)
    assert ids == ["a", "c"]


def test_debts_owed_to():
    s = NPCLegacyDebtsSystem()
    _open(s, debt_id="a",
          debtor_id="o1", creditor_id="bank")
    _open(s, debt_id="b",
          debtor_id="o2", creditor_id="bank")
    _open(s, debt_id="c",
          debtor_id="o1", creditor_id="other")
    out = s.debts_owed_to(creditor_id="bank")
    assert len(out) == 2


def test_debt_unknown():
    s = NPCLegacyDebtsSystem()
    assert s.debt(debt_id="ghost") is None


def test_enum_count():
    assert len(list(DebtState)) == 5
