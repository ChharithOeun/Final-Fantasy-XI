"""NPC legacy debts — financial obligations after relocation.

When an NPC defects, dies, or retires, their
outstanding DEBTS to creditors don't vanish. Settlement
follows one of these patterns:
    - debt FOLLOWS the NPC: creditor can pursue them in
      their new nation (delegated to extradition treaty)
    - debt is INHERITED by their estate (asset-forfeit
      proceeds pay creditors first)
    - debt is FORGIVEN by the creditor (rare, mostly
      diplomatic)
    - debt is DEFAULTED — creditor takes the loss

This module manages debts as records with debtor,
creditor, principal, interest_per_day_bps, accrual,
and a settlement state. tick(now_day) accrues
interest. settle() pays debts in priority order from a
provided pool of gil (e.g. seized assets).

Settlement mode:
    PAYABLE       still owed
    SETTLED       fully paid
    FORGIVEN      creditor wrote it off
    DEFAULTED     creditor abandoned collection
    FOLLOWING     marked to pursue debtor in new
                  nation

Public surface
--------------
    DebtState enum
    Debt dataclass (frozen)
    NPCLegacyDebtsSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DebtState(str, enum.Enum):
    PAYABLE = "payable"
    SETTLED = "settled"
    FORGIVEN = "forgiven"
    DEFAULTED = "defaulted"
    FOLLOWING = "following"


@dataclasses.dataclass(frozen=True)
class Debt:
    debt_id: str
    debtor_id: str
    creditor_id: str
    principal_gil: int
    interest_bps_per_day: int  # basis points
    accrued_interest_gil: int
    paid_gil: int
    incurred_day: int
    last_accrual_day: int
    priority: int  # lower = paid first
    state: DebtState


@dataclasses.dataclass
class NPCLegacyDebtsSystem:
    _debts: dict[str, Debt] = dataclasses.field(
        default_factory=dict,
    )

    def open_debt(
        self, *, debt_id: str, debtor_id: str,
        creditor_id: str, principal_gil: int,
        interest_bps_per_day: int,
        incurred_day: int, priority: int = 100,
    ) -> bool:
        if not debt_id or not debtor_id:
            return False
        if not creditor_id:
            return False
        if debtor_id == creditor_id:
            return False
        if principal_gil <= 0:
            return False
        if (interest_bps_per_day < 0
                or interest_bps_per_day > 1_000):
            return False
        if incurred_day < 0:
            return False
        if debt_id in self._debts:
            return False
        self._debts[debt_id] = Debt(
            debt_id=debt_id, debtor_id=debtor_id,
            creditor_id=creditor_id,
            principal_gil=principal_gil,
            interest_bps_per_day=(
                interest_bps_per_day
            ),
            accrued_interest_gil=0, paid_gil=0,
            incurred_day=incurred_day,
            last_accrual_day=incurred_day,
            priority=priority,
            state=DebtState.PAYABLE,
        )
        return True

    def accrue(
        self, *, debt_id: str, now_day: int,
    ) -> int:
        if debt_id not in self._debts:
            return 0
        d = self._debts[debt_id]
        if d.state != DebtState.PAYABLE:
            return 0
        if now_day <= d.last_accrual_day:
            return 0
        days = now_day - d.last_accrual_day
        # Interest = principal * bps/10_000 * days
        interest = (
            d.principal_gil
            * d.interest_bps_per_day
            * days // 10_000
        )
        if interest <= 0:
            self._debts[debt_id] = (
                dataclasses.replace(
                    d, last_accrual_day=now_day,
                )
            )
            return 0
        self._debts[debt_id] = dataclasses.replace(
            d, accrued_interest_gil=(
                d.accrued_interest_gil + interest
            ),
            last_accrual_day=now_day,
        )
        return interest

    def total_owed(
        self, *, debt_id: str,
    ) -> int:
        if debt_id not in self._debts:
            return 0
        d = self._debts[debt_id]
        return max(
            0,
            d.principal_gil
            + d.accrued_interest_gil
            - d.paid_gil,
        )

    def settle_from_pool(
        self, *, debtor_id: str, pool_gil: int,
        now_day: int,
    ) -> int:
        """Settle PAYABLE debts of debtor_id in
        priority order from pool_gil. Returns gil
        remaining unspent.
        """
        if pool_gil <= 0:
            return max(0, pool_gil)
        debts = sorted(
            (d for d in self._debts.values()
             if (d.debtor_id == debtor_id
                 and d.state == DebtState.PAYABLE)),
            key=lambda d: (d.priority, d.incurred_day),
        )
        remaining = pool_gil
        for d in debts:
            if remaining <= 0:
                break
            owed = self.total_owed(
                debt_id=d.debt_id,
            )
            if owed <= 0:
                continue
            pay = min(remaining, owed)
            new_paid = d.paid_gil + pay
            new_state = (
                DebtState.SETTLED
                if pay >= owed
                else DebtState.PAYABLE
            )
            self._debts[d.debt_id] = (
                dataclasses.replace(
                    d, paid_gil=new_paid,
                    state=new_state,
                )
            )
            remaining -= pay
        return remaining

    def forgive(
        self, *, debt_id: str, now_day: int,
    ) -> bool:
        if debt_id not in self._debts:
            return False
        d = self._debts[debt_id]
        if d.state != DebtState.PAYABLE:
            return False
        self._debts[debt_id] = dataclasses.replace(
            d, state=DebtState.FORGIVEN,
        )
        return True

    def default(
        self, *, debt_id: str, now_day: int,
    ) -> bool:
        if debt_id not in self._debts:
            return False
        d = self._debts[debt_id]
        if d.state != DebtState.PAYABLE:
            return False
        self._debts[debt_id] = dataclasses.replace(
            d, state=DebtState.DEFAULTED,
        )
        return True

    def mark_following(
        self, *, debt_id: str, now_day: int,
    ) -> bool:
        """Flag a payable debt for cross-border
        pursuit (debtor relocated)."""
        if debt_id not in self._debts:
            return False
        d = self._debts[debt_id]
        if d.state != DebtState.PAYABLE:
            return False
        self._debts[debt_id] = dataclasses.replace(
            d, state=DebtState.FOLLOWING,
        )
        return True

    def debts_of(
        self, *, debtor_id: str,
    ) -> list[Debt]:
        return [
            d for d in self._debts.values()
            if d.debtor_id == debtor_id
        ]

    def debts_owed_to(
        self, *, creditor_id: str,
    ) -> list[Debt]:
        return [
            d for d in self._debts.values()
            if d.creditor_id == creditor_id
        ]

    def debt(
        self, *, debt_id: str,
    ) -> t.Optional[Debt]:
        return self._debts.get(debt_id)


__all__ = [
    "DebtState", "Debt", "NPCLegacyDebtsSystem",
]
