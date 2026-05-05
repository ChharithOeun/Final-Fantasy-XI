"""Crew ship inventory — shared cargo hold across the crew.

Each pirate_crew_charter has a SHARED HOLD — a cargo
inventory accessible by all members but with deposit/withdraw
permissions tied to crew_role.

Permissions:
  CAPTAIN  - deposit, withdraw, audit
  OFFICER  - deposit, withdraw (rate-limited per day),
             audit
  CREW     - deposit only; can withdraw their OWN deposits
             within the redaw window (24h)

Stack rules:
  Hold has fixed slot count (default 100). Same-item-id
  stacks accumulate; different items use new slots.
  Capped per-stack at MAX_STACK = 999.

Ship inventory is keyed on charter_id, NOT individual
ships — when you change ships the cargo follows the crew.

Public surface
--------------
    InventoryAction enum
    DepositResult / WithdrawResult dataclasses
    CrewShipInventory
        .deposit(charter_id, member_id, role, item_id,
                 quantity, now_seconds)
        .withdraw(charter_id, member_id, role, item_id,
                  quantity, now_seconds)
        .holdings(charter_id) -> dict[item_id, qty]
        .audit_recent(charter_id) -> list[entry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CrewRole(str, enum.Enum):
    CAPTAIN = "captain"
    OFFICER = "officer"
    CREW = "crew"


MAX_STACK = 999
MAX_SLOTS = 100
CREW_REDRAW_WINDOW_SECONDS = 24 * 3_600
OFFICER_DAILY_WITHDRAW_LIMIT = 10  # per officer per day


@dataclasses.dataclass
class _Deposit:
    member_id: str
    item_id: str
    quantity: int
    deposited_at: int


@dataclasses.dataclass
class _OfficerDayLog:
    officer_id: str
    day_seconds: int    # which 24h bucket
    withdraws_today: int


@dataclasses.dataclass
class _Hold:
    charter_id: str
    items: dict[str, int] = dataclasses.field(default_factory=dict)
    audit: list[_Deposit] = dataclasses.field(default_factory=list)
    officer_log: dict[str, _OfficerDayLog] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass(frozen=True)
class DepositResult:
    accepted: bool
    item_id: str
    quantity: int = 0
    new_total: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class WithdrawResult:
    accepted: bool
    item_id: str
    quantity: int = 0
    remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CrewShipInventory:
    _holds: dict[str, _Hold] = dataclasses.field(default_factory=dict)

    def _ensure(self, charter_id: str) -> _Hold:
        h = self._holds.get(charter_id)
        if h is None:
            h = _Hold(charter_id=charter_id)
            self._holds[charter_id] = h
        return h

    def deposit(
        self, *, charter_id: str,
        member_id: str,
        role: CrewRole,
        item_id: str,
        quantity: int,
        now_seconds: int,
    ) -> DepositResult:
        if not charter_id or not member_id or not item_id:
            return DepositResult(False, item_id=item_id, reason="bad ids")
        if role not in CrewRole:
            return DepositResult(False, item_id=item_id, reason="bad role")
        if quantity <= 0:
            return DepositResult(False, item_id=item_id, reason="bad qty")
        h = self._ensure(charter_id)
        # slot cap
        if (
            item_id not in h.items
            and len(h.items) >= MAX_SLOTS
        ):
            return DepositResult(
                False, item_id=item_id, reason="hold full",
            )
        # stack cap
        current = h.items.get(item_id, 0)
        if current + quantity > MAX_STACK:
            allowed = MAX_STACK - current
            if allowed <= 0:
                return DepositResult(
                    False, item_id=item_id, reason="stack at cap",
                )
            quantity = allowed
        h.items[item_id] = h.items.get(item_id, 0) + quantity
        h.audit.append(_Deposit(
            member_id=member_id,
            item_id=item_id,
            quantity=quantity,
            deposited_at=now_seconds,
        ))
        return DepositResult(
            accepted=True, item_id=item_id,
            quantity=quantity,
            new_total=h.items[item_id],
        )

    def withdraw(
        self, *, charter_id: str,
        member_id: str,
        role: CrewRole,
        item_id: str,
        quantity: int,
        now_seconds: int,
    ) -> WithdrawResult:
        if not charter_id or not member_id or not item_id:
            return WithdrawResult(False, item_id=item_id, reason="bad ids")
        if quantity <= 0:
            return WithdrawResult(False, item_id=item_id, reason="bad qty")
        h = self._holds.get(charter_id)
        if h is None or h.items.get(item_id, 0) < quantity:
            return WithdrawResult(
                False, item_id=item_id, reason="insufficient",
            )
        # role gating
        if role == CrewRole.CREW:
            # crew can only redraw their own recent deposits
            owned_recent = sum(
                d.quantity for d in h.audit
                if d.member_id == member_id
                and d.item_id == item_id
                and now_seconds - d.deposited_at <= CREW_REDRAW_WINDOW_SECONDS
            )
            if owned_recent < quantity:
                return WithdrawResult(
                    False, item_id=item_id,
                    reason="crew redraw limit",
                )
        elif role == CrewRole.OFFICER:
            # rate-limit officer withdraws to N/day per officer
            day_bucket = now_seconds // (24 * 3_600)
            log = h.officer_log.get(member_id)
            if log is None or log.day_seconds != day_bucket:
                log = _OfficerDayLog(
                    officer_id=member_id,
                    day_seconds=day_bucket,
                    withdraws_today=0,
                )
                h.officer_log[member_id] = log
            if (
                log.withdraws_today + 1
                > OFFICER_DAILY_WITHDRAW_LIMIT
            ):
                return WithdrawResult(
                    False, item_id=item_id,
                    reason="officer daily limit",
                )
            log.withdraws_today += 1
        # captain: no extra gates
        h.items[item_id] -= quantity
        if h.items[item_id] == 0:
            del h.items[item_id]
        return WithdrawResult(
            accepted=True, item_id=item_id,
            quantity=quantity,
            remaining=h.items.get(item_id, 0),
        )

    def holdings(self, *, charter_id: str) -> dict[str, int]:
        h = self._holds.get(charter_id)
        if h is None:
            return {}
        return dict(h.items)

    def audit_recent(
        self, *, charter_id: str,
    ) -> tuple[_Deposit, ...]:
        h = self._holds.get(charter_id)
        if h is None:
            return ()
        return tuple(h.audit)


__all__ = [
    "CrewRole", "DepositResult", "WithdrawResult",
    "CrewShipInventory",
    "MAX_STACK", "MAX_SLOTS",
    "CREW_REDRAW_WINDOW_SECONDS", "OFFICER_DAILY_WITHDRAW_LIMIT",
]
