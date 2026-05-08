"""Tests for guild_treasury."""
from __future__ import annotations

from server.guild_treasury import (
    GuildTreasurySystem, TxKind, PendingState,
)


def _open(s, **overrides):
    args = dict(
        ls_id="ls_alpha", withdraw_min_rank=3,
        large_threshold=100_000,
    )
    args.update(overrides)
    return s.open_treasury(**args)


def test_open_happy():
    s = GuildTreasurySystem()
    assert _open(s) is True


def test_open_blank_ls():
    s = GuildTreasurySystem()
    assert _open(s, ls_id="") is False


def test_open_negative_rank():
    s = GuildTreasurySystem()
    assert _open(s, withdraw_min_rank=-1) is False


def test_open_dup():
    s = GuildTreasurySystem()
    _open(s)
    assert _open(s) is False


def test_deposit_happy():
    s = GuildTreasurySystem()
    _open(s)
    assert s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=5_000,
        now_day=1,
    ) is True
    assert s.balance(ls_id="ls_alpha") == 5_000


def test_deposit_zero_blocked():
    s = GuildTreasurySystem()
    _open(s)
    assert s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=0,
        now_day=1,
    ) is False


def test_deposit_unknown_ls():
    s = GuildTreasurySystem()
    assert s.deposit(
        ls_id="ghost", member_id="bob", gil=100,
        now_day=1,
    ) is False


def test_withdraw_happy_small():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=10_000,
        now_day=1,
    )
    ok, tag = s.withdraw(
        ls_id="ls_alpha", member_id="cara", gil=1_000,
        member_rank=5, now_day=2,
    )
    assert ok and tag == "settled"
    assert s.balance(ls_id="ls_alpha") == 9_000


def test_withdraw_low_rank_blocked():
    s = GuildTreasurySystem()
    _open(s, withdraw_min_rank=5)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=10_000,
        now_day=1,
    )
    ok, tag = s.withdraw(
        ls_id="ls_alpha", member_id="cara", gil=1_000,
        member_rank=2, now_day=2,
    )
    assert ok is False and tag == "rank_too_low"


def test_withdraw_insufficient_funds():
    s = GuildTreasurySystem()
    _open(s)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500,
        now_day=1,
    )
    ok, tag = s.withdraw(
        ls_id="ls_alpha", member_id="cara", gil=2_000,
        member_rank=5, now_day=2,
    )
    assert ok is False and tag == "insufficient_funds"


def test_withdraw_large_queues():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    ok, tag = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    assert ok is True
    assert tag.startswith("pw_")
    # Balance hasn't moved
    assert s.balance(ls_id="ls_alpha") == 500_000


def test_approve_pending_settles():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    assert s.approve_pending(
        ls_id="ls_alpha", pending_id=pid, now_day=3,
    ) is True
    assert s.balance(ls_id="ls_alpha") == 300_000


def test_approve_unknown():
    s = GuildTreasurySystem()
    _open(s)
    assert s.approve_pending(
        ls_id="ls_alpha", pending_id="ghost",
        now_day=3,
    ) is False


def test_reject_pending():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    assert s.reject_pending(
        ls_id="ls_alpha", pending_id=pid,
    ) is True
    assert s.balance(ls_id="ls_alpha") == 500_000


def test_double_approve_blocked():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    s.approve_pending(
        ls_id="ls_alpha", pending_id=pid, now_day=3,
    )
    assert s.approve_pending(
        ls_id="ls_alpha", pending_id=pid, now_day=4,
    ) is False


def test_auto_approve_overdue():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    out = s.auto_approve_overdue(
        now_day=10, grace_days=5,
    )
    assert pid in out
    assert s.balance(ls_id="ls_alpha") == 300_000


def test_auto_approve_within_grace_skipped():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    out = s.auto_approve_overdue(
        now_day=4, grace_days=5,
    )
    assert pid not in out


def test_ledger_records_deposit():
    s = GuildTreasurySystem()
    _open(s)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=5_000,
        now_day=1, reason="dues",
    )
    led = s.ledger_for(ls_id="ls_alpha")
    assert len(led) == 1
    assert led[0].kind == TxKind.DEPOSIT
    assert led[0].balance_after == 5_000


def test_pending_for():
    s = GuildTreasurySystem()
    _open(s, large_threshold=100_000)
    s.deposit(
        ls_id="ls_alpha", member_id="bob", gil=500_000,
        now_day=1,
    )
    _, pid = s.withdraw(
        ls_id="ls_alpha", member_id="cara",
        gil=200_000, member_rank=5, now_day=2,
    )
    out = s.pending_for(ls_id="ls_alpha")
    assert len(out) == 1
    assert out[0].state == PendingState.PENDING


def test_balance_unknown():
    s = GuildTreasurySystem()
    assert s.balance(ls_id="ghost") == 0


def test_ledger_unknown():
    s = GuildTreasurySystem()
    assert s.ledger_for(ls_id="ghost") == []


def test_enum_counts():
    assert len(list(TxKind)) == 3
    assert len(list(PendingState)) == 4
