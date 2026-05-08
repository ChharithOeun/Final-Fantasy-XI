"""Nation taxation — collection from zones and citizens.

Governments need revenue. nation_taxation tracks per-
nation TAX RATES (set via nation_edict's TAX_RATE
edicts, but the rate value is stored here) and ZONE
LEVIES collected periodically.

Tax kinds:
    INCOME           % of player gil-earned
    SALES            % of bazaar/AH transactions
    PROPERTY         flat per-Mog-House plot per cycle
    HEAD             flat per-citizen per cycle
    TARIFF           % on inter-nation trade goods
    LUXURY           % on auction-house high-value
                     listings

A LevyCycle:
    cycle_id, nation_id, kind, period_days, rate_bps
    (basis points; 100 bps = 1%), exemption_min_gil,
    started_day, ended_day, total_collected_gil

The system supports:
    - set_rate(nation, kind, rate_bps,
               exemption_min) -> bool
    - open_cycle(nation, kind, started_day,
                 period_days) -> Optional[str]
    - record_taxable(cycle_id, payer_id,
                     base_gil, now_day) -> int
                     (gil collected on this txn)
    - close_cycle(cycle_id, ended_day) -> int
                     (total)
    - revenue_for(nation_id) -> int  (lifetime)
    - per_payer(cycle_id, payer_id) -> int
    - active_cycles(nation_id) -> list[LevyCycle]

All math is integer; rate_bps is 0..10_000.

Public surface
--------------
    TaxKind enum
    LevyState enum
    TaxRate dataclass (frozen)
    LevyCycle dataclass (frozen)
    NationTaxationSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TaxKind(str, enum.Enum):
    INCOME = "income"
    SALES = "sales"
    PROPERTY = "property"
    HEAD = "head"
    TARIFF = "tariff"
    LUXURY = "luxury"


class LevyState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class TaxRate:
    nation_id: str
    kind: TaxKind
    rate_bps: int
    exemption_min_gil: int


@dataclasses.dataclass(frozen=True)
class LevyCycle:
    cycle_id: str
    nation_id: str
    kind: TaxKind
    rate_bps: int
    exemption_min_gil: int
    period_days: int
    started_day: int
    ended_day: t.Optional[int]
    total_collected_gil: int
    state: LevyState


@dataclasses.dataclass
class NationTaxationSystem:
    _rates: dict[tuple[str, TaxKind], TaxRate] = (
        dataclasses.field(default_factory=dict)
    )
    _cycles: dict[str, LevyCycle] = dataclasses.field(
        default_factory=dict,
    )
    _per_payer: dict[tuple[str, str], int] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def set_rate(
        self, *, nation_id: str, kind: TaxKind,
        rate_bps: int, exemption_min_gil: int = 0,
    ) -> bool:
        if not nation_id:
            return False
        if rate_bps < 0 or rate_bps > 10_000:
            return False
        if exemption_min_gil < 0:
            return False
        self._rates[(nation_id, kind)] = TaxRate(
            nation_id=nation_id, kind=kind,
            rate_bps=rate_bps,
            exemption_min_gil=exemption_min_gil,
        )
        return True

    def open_cycle(
        self, *, nation_id: str, kind: TaxKind,
        started_day: int, period_days: int,
    ) -> t.Optional[str]:
        if (nation_id, kind) not in self._rates:
            return None
        if started_day < 0 or period_days <= 0:
            return None
        rate = self._rates[(nation_id, kind)]
        cid = f"levy_{self._next_id}"
        self._next_id += 1
        self._cycles[cid] = LevyCycle(
            cycle_id=cid, nation_id=nation_id,
            kind=kind, rate_bps=rate.rate_bps,
            exemption_min_gil=rate.exemption_min_gil,
            period_days=period_days,
            started_day=started_day, ended_day=None,
            total_collected_gil=0,
            state=LevyState.OPEN,
        )
        return cid

    def record_taxable(
        self, *, cycle_id: str, payer_id: str,
        base_gil: int, now_day: int,
    ) -> int:
        if cycle_id not in self._cycles:
            return 0
        if not payer_id or base_gil <= 0:
            return 0
        c = self._cycles[cycle_id]
        if c.state != LevyState.OPEN:
            return 0
        end = c.started_day + c.period_days
        if now_day < c.started_day or now_day > end:
            return 0
        if base_gil < c.exemption_min_gil:
            return 0
        # Integer math; bps / 10_000
        owed = base_gil * c.rate_bps // 10_000
        if owed <= 0:
            return 0
        self._cycles[cycle_id] = dataclasses.replace(
            c, total_collected_gil=(
                c.total_collected_gil + owed
            ),
        )
        key = (cycle_id, payer_id)
        self._per_payer[key] = (
            self._per_payer.get(key, 0) + owed
        )
        return owed

    def close_cycle(
        self, *, cycle_id: str, ended_day: int,
    ) -> int:
        if cycle_id not in self._cycles:
            return 0
        c = self._cycles[cycle_id]
        if c.state != LevyState.OPEN:
            return 0
        if ended_day < c.started_day:
            return 0
        self._cycles[cycle_id] = dataclasses.replace(
            c, state=LevyState.CLOSED,
            ended_day=ended_day,
        )
        return c.total_collected_gil

    def revenue_for(self, *, nation_id: str) -> int:
        return sum(
            c.total_collected_gil
            for c in self._cycles.values()
            if c.nation_id == nation_id
        )

    def per_payer(
        self, *, cycle_id: str, payer_id: str,
    ) -> int:
        return self._per_payer.get(
            (cycle_id, payer_id), 0,
        )

    def active_cycles(
        self, *, nation_id: str,
    ) -> list[LevyCycle]:
        return [
            c for c in self._cycles.values()
            if (c.nation_id == nation_id
                and c.state == LevyState.OPEN)
        ]

    def cycle(
        self, *, cycle_id: str,
    ) -> t.Optional[LevyCycle]:
        return self._cycles.get(cycle_id)


__all__ = [
    "TaxKind", "LevyState", "TaxRate", "LevyCycle",
    "NationTaxationSystem",
]
