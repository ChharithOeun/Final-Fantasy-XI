"""Economy regulator — drop-rate balancer AI.

The world's economy is autonomous; players, NPC merchants, AI
mob-killers, AI-driven crafters all create and consume goods.
Without a regulator, an essential mat (iron ore, cure potions)
can drift into shortage and grind the economy to a halt. With
one, drop rates breathe — temporarily bumping when supply runs
low and relaxing when supply rebuilds.

This module is the BRAIN. It reads:
    * supply: economy_supply_index.snapshot_at(...)
    * demand: economy_demand_signal.signal_for(...)
    * essentiality: mat_essentiality_registry.priority_for(...)

And produces a drop_rate_multiplier(item_id) -> float in [1.0,
MAX_BOOST]. The multiplier expires automatically; the orchestrator
re-runs the regulator on each economy tick and the multiplier
table refreshes.

The regulator never DROPS rates below 1.0 — over-supply is
handled by demand naturally rising or by NPCs hoarding. Boosts
only.

Scarcity score
--------------
For each item:
    raw_scarcity =
        max(0, demand_per_hour) - (supply_total / SCARCITY_SUPPLY_DIVISOR)
        + max(0, -supply_trend_pct)        # supply dropping bumps score
        + max(0, demand_trend_pct) * 0.5    # demand rising bumps score
    weighted = raw_scarcity * (essentiality_priority / 100)

scarcity > THRESHOLD_HEAVY  -> 2.0x drop multiplier
scarcity > THRESHOLD_LIGHT  -> 1.5x
otherwise                   -> 1.0x

Multipliers DECAY toward 1.0 each tick if the underlying scarcity
is no longer present — prevents whiplash.

Public surface
--------------
    BoostLevel enum (NONE / LIGHT / HEAVY / CRITICAL)
    RegulatorDecision dataclass
    EconomyRegulator
        .recompute(now_seconds)
        .drop_rate_multiplier(item_id) -> float
        .decisions_for_top(top_n) -> tuple[RegulatorDecision, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.economy_demand_signal import EconomyDemandTracker
from server.economy_supply_index import EconomySupplyIndex
from server.mat_essentiality_registry import (
    MatEssentialityRegistry,
)


SCARCITY_SUPPLY_DIVISOR = 100.0
THRESHOLD_LIGHT = 5.0
THRESHOLD_HEAVY = 15.0
THRESHOLD_CRITICAL = 30.0
MAX_BOOST = 3.0
LIGHT_BOOST = 1.5
HEAVY_BOOST = 2.0
CRITICAL_BOOST = 3.0
# Per-tick decay toward 1.0 when scarcity has eased.
DECAY_PER_TICK = 0.1


class BoostLevel(str, enum.Enum):
    NONE = "none"
    LIGHT = "light"
    HEAVY = "heavy"
    CRITICAL = "critical"


def _level_for_score(score: float) -> BoostLevel:
    if score >= THRESHOLD_CRITICAL:
        return BoostLevel.CRITICAL
    if score >= THRESHOLD_HEAVY:
        return BoostLevel.HEAVY
    if score >= THRESHOLD_LIGHT:
        return BoostLevel.LIGHT
    return BoostLevel.NONE


def _multiplier_for_level(level: BoostLevel) -> float:
    if level == BoostLevel.CRITICAL:
        return CRITICAL_BOOST
    if level == BoostLevel.HEAVY:
        return HEAVY_BOOST
    if level == BoostLevel.LIGHT:
        return LIGHT_BOOST
    return 1.0


@dataclasses.dataclass(frozen=True)
class RegulatorDecision:
    item_id: str
    scarcity_score: float
    boost_level: BoostLevel
    multiplier: float
    reason: str
    essentiality_priority: int
    supply_total: int
    demand_per_hour: float


@dataclasses.dataclass
class EconomyRegulator:
    supply: EconomySupplyIndex
    demand: EconomyDemandTracker
    essentiality: MatEssentialityRegistry
    # Live multiplier table — items not present default to 1.0
    _multipliers: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    _last_decisions: dict[str, RegulatorDecision] = dataclasses.field(
        default_factory=dict,
    )

    def _scarcity_score(
        self, *, item_id: str, now_seconds: float,
    ) -> tuple[float, str, int, float]:
        """Compute the raw weighted scarcity score for an item.
        Returns (score, reason, supply_total, demand_per_hour)."""
        priority = self.essentiality.priority_for(item_id)
        if priority == 0:
            # Unregistered or LUXURY — never boost.
            return 0.0, "non-essential", 0, 0.0
        snap = self.supply.snapshot_at(
            item_id=item_id, now_seconds=now_seconds,
        )
        sig = self.demand.signal_for(
            item_id=item_id, now_seconds=now_seconds,
        )
        # Base scarcity: demand minus supply-relative cushion
        raw = sig.rate_per_hour - (
            snap.total_count / SCARCITY_SUPPLY_DIVISOR
        )
        # Supply trending DOWN bumps the score (only if we have a
        # prior history point — sample_count >= 2)
        if snap.trend_pct < 0 and snap.sample_count >= 2:
            raw += abs(snap.trend_pct) * 0.1
        # Demand trending UP bumps the score, but ONLY if there was
        # a real previous window. A cold-start spike (prev=0) reads
        # as 100% growth and would falsely amplify; ignore it until
        # the regulator has at least one prior window of demand
        # data.
        if (
            sig.trend_pct > 0
            and sig.previous_window_count > 0
        ):
            raw += sig.trend_pct * 0.05
        weighted = max(0.0, raw) * (priority / 100.0)
        reason = (
            f"demand={sig.rate_per_hour:.1f}/hr, "
            f"supply={snap.total_count}, "
            f"supply_trend={snap.trend_pct:.1f}%, "
            f"demand_trend={sig.trend_pct:.1f}%"
        )
        return weighted, reason, snap.total_count, sig.rate_per_hour

    def recompute(
        self, *, now_seconds: float,
    ) -> tuple[RegulatorDecision, ...]:
        """Walk every registered essential item, score its
        scarcity, update the multiplier table. Returns the
        decisions made this tick."""
        decisions: list[RegulatorDecision] = []
        # Iterate over the union of essentiality + supply + demand
        candidate_ids: set[str] = set()
        for ranked in self.essentiality.priority_rank():
            candidate_ids.add(ranked.item_id)
        candidate_ids.update(self.supply.all_items())
        candidate_ids.update(self.demand.all_items())
        for item_id in candidate_ids:
            score, reason, supply_total, demand_rate = (
                self._scarcity_score(
                    item_id=item_id, now_seconds=now_seconds,
                )
            )
            level = _level_for_score(score)
            target = _multiplier_for_level(level)
            current = self._multipliers.get(item_id, 1.0)
            # Apply the new multiplier WITH DECAY toward target.
            # If target > current, snap up (bump should be quick).
            # If target < current, decay down gradually.
            if target >= current:
                new = target
            else:
                new = max(target, current - DECAY_PER_TICK)
            # Keep table compact — drop entries that are at 1.0
            if new <= 1.0:
                self._multipliers.pop(item_id, None)
                final = 1.0
            else:
                self._multipliers[item_id] = new
                final = new
            d = RegulatorDecision(
                item_id=item_id, scarcity_score=score,
                boost_level=level, multiplier=final,
                reason=reason,
                essentiality_priority=(
                    self.essentiality.priority_for(item_id)
                ),
                supply_total=supply_total,
                demand_per_hour=demand_rate,
            )
            decisions.append(d)
            self._last_decisions[item_id] = d
        return tuple(decisions)

    def drop_rate_multiplier(self, item_id: str) -> float:
        """The number loot_table multiplies the base drop rate by.
        Defaults to 1.0 for items the regulator hasn't boosted."""
        return self._multipliers.get(item_id, 1.0)

    def decisions_for_top(
        self, *, top_n: int = 10,
    ) -> tuple[RegulatorDecision, ...]:
        ranked = sorted(
            self._last_decisions.values(),
            key=lambda d: d.scarcity_score, reverse=True,
        )
        return tuple(ranked[:top_n])

    def boosted_items(self) -> tuple[str, ...]:
        return tuple(self._multipliers.keys())


__all__ = [
    "SCARCITY_SUPPLY_DIVISOR",
    "THRESHOLD_LIGHT", "THRESHOLD_HEAVY", "THRESHOLD_CRITICAL",
    "MAX_BOOST", "LIGHT_BOOST", "HEAVY_BOOST", "CRITICAL_BOOST",
    "DECAY_PER_TICK",
    "BoostLevel", "RegulatorDecision", "EconomyRegulator",
]
