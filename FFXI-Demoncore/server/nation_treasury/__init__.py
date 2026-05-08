"""Nation treasury — gil flow at the nation level.

A nation's gov spends gil on military, infrastructure,
and festivals. It collects gil from taxes and conquest
tribute. nation_treasury is the central ledger.

Inflows:
    TAX_INCOME             AH listing fees, item taxes
    CONQUEST_TRIBUTE       conquest_tally rewards
    SIEGE_VICTORY_SPOILS   siege_system loot share
    TRADE_TARIFF           cross-border AH fees

Outflows:
    MILITARY_PAY           guard NPC salaries
    PUBLIC_WORKS_GRANT     fund public_works projects
    FESTIVAL_BUDGET        seasonal_events spending
    DIPLOMATIC_GIFT        treaty signing bonuses
    EMERGENCY_RESERVE      held aside for crises

Each nation has a separate treasury balance. Negative
balance = deficit; modules can read deficit_state to
adjust gameplay (high tax announcements, recruitment
freezes, etc).

Per-transaction we record the sign + reason + amount;
a rolling ledger of last 200 entries is queryable for
in-game audit.

Public surface
--------------
    InflowKind enum
    OutflowKind enum
    LedgerEntry dataclass (frozen)
    NationTreasury
        .open_treasury(nation, starting_balance) -> bool
        .record_inflow(nation, kind, amount, source) -> bool
        .record_outflow(nation, kind, amount, dest) -> bool
        .balance(nation) -> int
        .ledger(nation, n=200) -> list[LedgerEntry]
        .deficit_state(nation) -> bool   # true if balance < 0
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_LEDGER_MAX = 200


class InflowKind(str, enum.Enum):
    TAX_INCOME = "tax_income"
    CONQUEST_TRIBUTE = "conquest_tribute"
    SIEGE_VICTORY_SPOILS = "siege_victory_spoils"
    TRADE_TARIFF = "trade_tariff"


class OutflowKind(str, enum.Enum):
    MILITARY_PAY = "military_pay"
    PUBLIC_WORKS_GRANT = "public_works_grant"
    FESTIVAL_BUDGET = "festival_budget"
    DIPLOMATIC_GIFT = "diplomatic_gift"
    EMERGENCY_RESERVE = "emergency_reserve"


@dataclasses.dataclass(frozen=True)
class LedgerEntry:
    nation: str
    is_inflow: bool
    kind: str
    amount: int
    counterparty: str  # "ah", "siege_dragon_di", a player_id, etc.


@dataclasses.dataclass
class _T:
    balance: int
    ledger: list[LedgerEntry] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class NationTreasury:
    _treasuries: dict[str, _T] = dataclasses.field(
        default_factory=dict,
    )

    def open_treasury(
        self, *, nation: str, starting_balance: int,
    ) -> bool:
        if not nation:
            return False
        if starting_balance < 0:
            return False
        if nation in self._treasuries:
            return False
        self._treasuries[nation] = _T(
            balance=starting_balance,
        )
        return True

    def _append(
        self, nation: str, entry: LedgerEntry,
    ) -> None:
        led = self._treasuries[nation].ledger
        led.append(entry)
        # Trim to max
        if len(led) > _LEDGER_MAX:
            del led[0:len(led) - _LEDGER_MAX]

    def record_inflow(
        self, *, nation: str, kind: InflowKind,
        amount: int, source: str,
    ) -> bool:
        if amount <= 0 or not source:
            return False
        if nation not in self._treasuries:
            return False
        t_ = self._treasuries[nation]
        t_.balance += amount
        self._append(nation, LedgerEntry(
            nation=nation, is_inflow=True,
            kind=kind.value, amount=amount,
            counterparty=source,
        ))
        return True

    def record_outflow(
        self, *, nation: str, kind: OutflowKind,
        amount: int, dest: str,
    ) -> bool:
        if amount <= 0 or not dest:
            return False
        if nation not in self._treasuries:
            return False
        t_ = self._treasuries[nation]
        t_.balance -= amount
        self._append(nation, LedgerEntry(
            nation=nation, is_inflow=False,
            kind=kind.value, amount=amount,
            counterparty=dest,
        ))
        return True

    def balance(self, *, nation: str) -> int:
        if nation not in self._treasuries:
            return 0
        return self._treasuries[nation].balance

    def ledger(
        self, *, nation: str, n: int = _LEDGER_MAX,
    ) -> list[LedgerEntry]:
        if nation not in self._treasuries:
            return []
        led = self._treasuries[nation].ledger
        # Most recent first
        return list(reversed(led))[:n]

    def deficit_state(self, *, nation: str) -> bool:
        return self.balance(nation=nation) < 0


__all__ = [
    "InflowKind", "OutflowKind", "LedgerEntry",
    "NationTreasury",
]
