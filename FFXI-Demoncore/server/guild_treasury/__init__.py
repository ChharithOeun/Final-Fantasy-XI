"""Guild treasury — shared LS bank with rank-gated access.

A linkshell that has installed a TREASURY_VAULT room in
its guild hall unlocks a SHARED TREASURY — a pooled gil
account members can deposit into and (rank-permitting)
withdraw from. Unlike a personal pearlsack, the treasury
is governed by LS rules:

    - Any member can DEPOSIT freely.
    - WITHDRAW requires officer-or-higher rank
      (configurable per-LS minimum).
    - Withdrawals over a configurable LARGE_THRESHOLD
      are LOGGED and must be approved by the leader on
      next login (or auto-approved after grace days).
    - Every transaction is recorded in an append-only
      ledger — no anonymous theft.

The treasury system is RANK-AGNOSTIC at the data layer:
the caller passes the requesting member's effective rank.
Validation of "is this member actually rank R?" is the
LS module's job. Treasury only checks rank-vs-policy.

Public surface
--------------
    TxKind enum (DEPOSIT / WITHDRAW / FEE)
    PendingState enum (NONE / PENDING / APPROVED /
                       REJECTED)
    LedgerEntry dataclass (frozen)
    PendingWithdrawal dataclass (frozen)
    GuildTreasurySystem
        .open_treasury(ls_id, withdraw_min_rank,
                       large_threshold) -> bool
        .deposit(ls_id, member_id, gil, now_day,
                 reason) -> bool
        .withdraw(ls_id, member_id, gil, member_rank,
                  now_day, reason) -> tuple[bool, str]
        .approve_pending(ls_id, pending_id, now_day) -> bool
        .reject_pending(ls_id, pending_id) -> bool
        .auto_approve_overdue(now_day, grace_days) ->
                       list[str]
        .balance(ls_id) -> int
        .ledger_for(ls_id) -> list[LedgerEntry]
        .pending_for(ls_id) -> list[PendingWithdrawal]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TxKind(str, enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    FEE = "fee"


class PendingState(str, enum.Enum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclasses.dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    ls_id: str
    member_id: str
    kind: TxKind
    gil_delta: int  # signed; +deposit, -withdraw/-fee
    balance_after: int
    day: int
    reason: str


@dataclasses.dataclass(frozen=True)
class PendingWithdrawal:
    pending_id: str
    ls_id: str
    member_id: str
    gil_amount: int
    requested_day: int
    state: PendingState
    reason: str


@dataclasses.dataclass
class _Treasury:
    ls_id: str
    withdraw_min_rank: int
    large_threshold: int
    balance: int = 0


@dataclasses.dataclass
class GuildTreasurySystem:
    _vaults: dict[str, _Treasury] = dataclasses.field(
        default_factory=dict,
    )
    _ledger: dict[str, list[LedgerEntry]] = (
        dataclasses.field(default_factory=dict)
    )
    _pending: dict[str, PendingWithdrawal] = (
        dataclasses.field(default_factory=dict)
    )
    _next_entry: int = 1
    _next_pending: int = 1

    def open_treasury(
        self, *, ls_id: str, withdraw_min_rank: int,
        large_threshold: int,
    ) -> bool:
        if not ls_id:
            return False
        if withdraw_min_rank < 0:
            return False
        if large_threshold < 0:
            return False
        if ls_id in self._vaults:
            return False
        self._vaults[ls_id] = _Treasury(
            ls_id=ls_id,
            withdraw_min_rank=withdraw_min_rank,
            large_threshold=large_threshold,
        )
        self._ledger[ls_id] = []
        return True

    def _record(
        self, ls_id: str, member_id: str, kind: TxKind,
        delta: int, day: int, reason: str,
    ) -> None:
        v = self._vaults[ls_id]
        v.balance += delta
        eid = f"tx_{self._next_entry}"
        self._next_entry += 1
        self._ledger[ls_id].append(LedgerEntry(
            entry_id=eid, ls_id=ls_id,
            member_id=member_id, kind=kind,
            gil_delta=delta, balance_after=v.balance,
            day=day, reason=reason,
        ))

    def deposit(
        self, *, ls_id: str, member_id: str, gil: int,
        now_day: int, reason: str = "",
    ) -> bool:
        if ls_id not in self._vaults:
            return False
        if not member_id or gil <= 0 or now_day < 0:
            return False
        self._record(
            ls_id, member_id, TxKind.DEPOSIT, gil,
            now_day, reason,
        )
        return True

    def withdraw(
        self, *, ls_id: str, member_id: str, gil: int,
        member_rank: int, now_day: int,
        reason: str = "",
    ) -> tuple[bool, str]:
        if ls_id not in self._vaults:
            return (False, "no_treasury")
        if not member_id or gil <= 0 or now_day < 0:
            return (False, "bad_input")
        v = self._vaults[ls_id]
        if member_rank < v.withdraw_min_rank:
            return (False, "rank_too_low")
        if gil > v.balance:
            return (False, "insufficient_funds")
        # Large withdrawals queue for approval
        if gil >= v.large_threshold:
            pid = f"pw_{self._next_pending}"
            self._next_pending += 1
            self._pending[pid] = PendingWithdrawal(
                pending_id=pid, ls_id=ls_id,
                member_id=member_id, gil_amount=gil,
                requested_day=now_day,
                state=PendingState.PENDING, reason=reason,
            )
            return (True, pid)
        # Small withdrawal — settles immediately
        self._record(
            ls_id, member_id, TxKind.WITHDRAW, -gil,
            now_day, reason,
        )
        return (True, "settled")

    def approve_pending(
        self, *, ls_id: str, pending_id: str,
        now_day: int,
    ) -> bool:
        if pending_id not in self._pending:
            return False
        pw = self._pending[pending_id]
        if pw.ls_id != ls_id:
            return False
        if pw.state != PendingState.PENDING:
            return False
        v = self._vaults[ls_id]
        if pw.gil_amount > v.balance:
            return False
        self._record(
            ls_id, pw.member_id, TxKind.WITHDRAW,
            -pw.gil_amount, now_day, pw.reason,
        )
        self._pending[pending_id] = dataclasses.replace(
            pw, state=PendingState.APPROVED,
        )
        return True

    def reject_pending(
        self, *, ls_id: str, pending_id: str,
    ) -> bool:
        if pending_id not in self._pending:
            return False
        pw = self._pending[pending_id]
        if pw.ls_id != ls_id:
            return False
        if pw.state != PendingState.PENDING:
            return False
        self._pending[pending_id] = dataclasses.replace(
            pw, state=PendingState.REJECTED,
        )
        return True

    def auto_approve_overdue(
        self, *, now_day: int, grace_days: int,
    ) -> list[str]:
        approved: list[str] = []
        for pid, pw in list(self._pending.items()):
            if pw.state != PendingState.PENDING:
                continue
            if now_day - pw.requested_day < grace_days:
                continue
            if self.approve_pending(
                ls_id=pw.ls_id, pending_id=pid,
                now_day=now_day,
            ):
                approved.append(pid)
        return approved

    def balance(self, *, ls_id: str) -> int:
        if ls_id not in self._vaults:
            return 0
        return self._vaults[ls_id].balance

    def ledger_for(
        self, *, ls_id: str,
    ) -> list[LedgerEntry]:
        return list(self._ledger.get(ls_id, ()))

    def pending_for(
        self, *, ls_id: str,
    ) -> list[PendingWithdrawal]:
        return [
            pw for pw in self._pending.values()
            if pw.ls_id == ls_id
        ]


__all__ = [
    "TxKind", "PendingState", "LedgerEntry",
    "PendingWithdrawal", "GuildTreasurySystem",
]
