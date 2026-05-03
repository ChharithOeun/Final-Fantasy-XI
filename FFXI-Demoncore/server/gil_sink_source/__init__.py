"""Gil sink/source tracker — inflation detector.

Mob drops, quest rewards, and NM kills create gil; vendor
purchases, repair fees, AH tax, teleport fees, and KO penalties
destroy it. If sources outpace sinks, gil inflates and the AH
becomes meaningless. If sinks outpace sources, gil deflates and
new players can't afford anything. Either is bad — the regulator
needs a knob.

This module tracks every gil flow in/out of the economy and
computes the net inflow per game-day. It also classifies the
state (HEALTHY / INFLATING / DEFLATING / CRISIS_*) and emits
recommended adjustments to the regulator's gil-related drop
rates.

Sources
-------
    MOB_DROP             gil dropped by ordinary mob kills
    NM_DROP              gil dropped by named monster kills
    BOSS_DROP            gil dropped by boss kills
    QUEST_REWARD         gil paid by quest turn-in
    BOUNTY_PAYOUT        gil from outlaw bounties
    BAZAAR_SALE          gil received from selling to NPC
                         (but the receiver got it; the world
                         net SAW gil enter another player's pocket)
    LOOT_RECOVERY        gil recovered from defeated outlaws

Sinks
-----
    NPC_VENDOR_BUY       player purchased from NPC merchant
    REPAIR               equipment_wear repair fees
    AH_TAX               auction house listing/sale tax
    TELEPORT_FEE         teleport / homepoint warp fees
    KO_PENALTY           death penalty drop
    INN_REST             inn fees (regen_resting paid)
    CRAFTING_FEE         workbench rental fees

Public surface
--------------
    GilSourceKind enum
    GilSinkKind enum
    GilFlow dataclass
    GilEconomyState enum
    GilFlowReport dataclass
    GilFlowTracker
        .record_source(kind, amount, now_seconds)
        .record_sink(kind, amount, now_seconds)
        .net_flow_per_day(now_seconds) -> int
        .state_at(now_seconds) -> GilEconomyState
        .report(now_seconds) -> GilFlowReport
        .top_sources / .top_sinks
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


GAME_DAY_SECONDS = 60 * 60 * 24
DEFAULT_WINDOW_SECONDS = GAME_DAY_SECONDS

# Healthy band — net inflow per day in [-X, +X] is fine.
HEALTHY_NET_PER_DAY = 50_000
INFLATION_THRESHOLD = 200_000     # net source > this = inflating
DEFLATION_THRESHOLD = -200_000    # net sink > this = deflating
CRISIS_INFLATION = 1_000_000
CRISIS_DEFLATION = -1_000_000


class GilSourceKind(str, enum.Enum):
    MOB_DROP = "mob_drop"
    NM_DROP = "nm_drop"
    BOSS_DROP = "boss_drop"
    QUEST_REWARD = "quest_reward"
    BOUNTY_PAYOUT = "bounty_payout"
    BAZAAR_SALE = "bazaar_sale"
    LOOT_RECOVERY = "loot_recovery"


class GilSinkKind(str, enum.Enum):
    NPC_VENDOR_BUY = "npc_vendor_buy"
    REPAIR = "repair"
    AH_TAX = "ah_tax"
    TELEPORT_FEE = "teleport_fee"
    KO_PENALTY = "ko_penalty"
    INN_REST = "inn_rest"
    CRAFTING_FEE = "crafting_fee"


class GilEconomyState(str, enum.Enum):
    HEALTHY = "healthy"
    INFLATING = "inflating"
    DEFLATING = "deflating"
    CRISIS_INFLATION = "crisis_inflation"
    CRISIS_DEFLATION = "crisis_deflation"


@dataclasses.dataclass(frozen=True)
class GilFlow:
    amount: int
    kind: t.Union[GilSourceKind, GilSinkKind]
    is_source: bool
    recorded_at_seconds: float


def _state_for_net(net_per_day: int) -> GilEconomyState:
    if net_per_day >= CRISIS_INFLATION:
        return GilEconomyState.CRISIS_INFLATION
    if net_per_day >= INFLATION_THRESHOLD:
        return GilEconomyState.INFLATING
    if net_per_day <= CRISIS_DEFLATION:
        return GilEconomyState.CRISIS_DEFLATION
    if net_per_day <= DEFLATION_THRESHOLD:
        return GilEconomyState.DEFLATING
    return GilEconomyState.HEALTHY


@dataclasses.dataclass(frozen=True)
class GilFlowReport:
    now_seconds: float
    window_seconds: float
    total_source_gil: int
    total_sink_gil: int
    net_per_day: int
    state: GilEconomyState
    top_sources: tuple[tuple[GilSourceKind, int], ...]
    top_sinks: tuple[tuple[GilSinkKind, int], ...]
    recommended_drop_rate_multiplier: float


def _recommended_multiplier(state: GilEconomyState) -> float:
    """How loot_table should adjust gil drops based on the
    macro state. Inflation -> reduce drops. Deflation -> bump."""
    if state == GilEconomyState.CRISIS_INFLATION:
        return 0.5
    if state == GilEconomyState.INFLATING:
        return 0.8
    if state == GilEconomyState.CRISIS_DEFLATION:
        return 1.5
    if state == GilEconomyState.DEFLATING:
        return 1.2
    return 1.0


@dataclasses.dataclass
class GilFlowTracker:
    window_seconds: float = DEFAULT_WINDOW_SECONDS
    _flows: list[GilFlow] = dataclasses.field(default_factory=list)

    def record_source(
        self, *, kind: GilSourceKind, amount: int,
        now_seconds: float,
    ) -> None:
        if amount <= 0:
            raise ValueError(f"amount {amount} must be positive")
        self._flows.append(GilFlow(
            amount=amount, kind=kind, is_source=True,
            recorded_at_seconds=now_seconds,
        ))
        self._trim(now_seconds)

    def record_sink(
        self, *, kind: GilSinkKind, amount: int,
        now_seconds: float,
    ) -> None:
        if amount <= 0:
            raise ValueError(f"amount {amount} must be positive")
        self._flows.append(GilFlow(
            amount=amount, kind=kind, is_source=False,
            recorded_at_seconds=now_seconds,
        ))
        self._trim(now_seconds)

    def _trim(self, now_seconds: float) -> None:
        # Keep only flows within the window. We retain the full
        # window to allow accurate net_flow_per_day computation.
        cutoff = now_seconds - self.window_seconds
        self._flows = [
            f for f in self._flows
            if f.recorded_at_seconds >= cutoff
        ]

    def total_source_gil(
        self, *, now_seconds: float,
    ) -> int:
        cutoff = now_seconds - self.window_seconds
        return sum(
            f.amount for f in self._flows
            if f.is_source and f.recorded_at_seconds >= cutoff
        )

    def total_sink_gil(
        self, *, now_seconds: float,
    ) -> int:
        cutoff = now_seconds - self.window_seconds
        return sum(
            f.amount for f in self._flows
            if not f.is_source and f.recorded_at_seconds >= cutoff
        )

    def net_flow_per_day(
        self, *, now_seconds: float,
    ) -> int:
        gross_in = self.total_source_gil(now_seconds=now_seconds)
        gross_out = self.total_sink_gil(now_seconds=now_seconds)
        net = gross_in - gross_out
        days = self.window_seconds / GAME_DAY_SECONDS
        if days <= 0:
            return net
        return int(round(net / days))

    def state_at(
        self, *, now_seconds: float,
    ) -> GilEconomyState:
        return _state_for_net(
            self.net_flow_per_day(now_seconds=now_seconds),
        )

    def top_sources(
        self, *, now_seconds: float, top_n: int = 5,
    ) -> tuple[tuple[GilSourceKind, int], ...]:
        cutoff = now_seconds - self.window_seconds
        totals: dict[GilSourceKind, int] = {}
        for f in self._flows:
            if f.is_source and f.recorded_at_seconds >= cutoff:
                kind = t.cast(GilSourceKind, f.kind)
                totals[kind] = totals.get(kind, 0) + f.amount
        ranked = sorted(
            totals.items(), key=lambda p: p[1], reverse=True,
        )[:top_n]
        return tuple(ranked)

    def top_sinks(
        self, *, now_seconds: float, top_n: int = 5,
    ) -> tuple[tuple[GilSinkKind, int], ...]:
        cutoff = now_seconds - self.window_seconds
        totals: dict[GilSinkKind, int] = {}
        for f in self._flows:
            if (not f.is_source
                    and f.recorded_at_seconds >= cutoff):
                kind = t.cast(GilSinkKind, f.kind)
                totals[kind] = totals.get(kind, 0) + f.amount
        ranked = sorted(
            totals.items(), key=lambda p: p[1], reverse=True,
        )[:top_n]
        return tuple(ranked)

    def report(
        self, *, now_seconds: float,
    ) -> GilFlowReport:
        net_per_day = self.net_flow_per_day(now_seconds=now_seconds)
        state = _state_for_net(net_per_day)
        return GilFlowReport(
            now_seconds=now_seconds,
            window_seconds=self.window_seconds,
            total_source_gil=self.total_source_gil(
                now_seconds=now_seconds,
            ),
            total_sink_gil=self.total_sink_gil(
                now_seconds=now_seconds,
            ),
            net_per_day=net_per_day,
            state=state,
            top_sources=self.top_sources(now_seconds=now_seconds),
            top_sinks=self.top_sinks(now_seconds=now_seconds),
            recommended_drop_rate_multiplier=(
                _recommended_multiplier(state)
            ),
        )

    def total_flows(self) -> int:
        return len(self._flows)


__all__ = [
    "GAME_DAY_SECONDS", "DEFAULT_WINDOW_SECONDS",
    "HEALTHY_NET_PER_DAY", "INFLATION_THRESHOLD",
    "DEFLATION_THRESHOLD", "CRISIS_INFLATION",
    "CRISIS_DEFLATION",
    "GilSourceKind", "GilSinkKind",
    "GilFlow", "GilEconomyState",
    "GilFlowReport", "GilFlowTracker",
]
