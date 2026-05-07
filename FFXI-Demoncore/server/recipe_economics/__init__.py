"""Recipe economics — track cost, yield, profit margin
over time, and detect AH price drift.

GS publishes have content_hash to detect "the source
changed". Strategy guides have win-rate-from-others.
Recipes have a different time-decay vector: the COST of
the materials shifts as the AH market moves. A recipe
that was 5k profit per synth at publish time can become
2k loss six months later if the mat prices doubled.

This module owns the per-recipe ECONOMIC TRUTH at any
moment:
    - publish-time cost snapshot (the author's cost
      when they wrote it)
    - rolling AH price samples for each material
    - current cost projection (sum of latest mat prices)
    - latest yield value (NPC + AH for the output)
    - profit_margin = yield - current_cost
    - drift_pct vs publish-time cost (how stale is this?)

The samples come from the caller's AH watcher. We just
aggregate.

Public surface
--------------
    PriceSample dataclass (frozen)
    CostSnapshot dataclass (frozen)
    EconomicReport dataclass (frozen)
    RecipeEconomics
        .seed_publish_cost(recipe_id, mat_costs,
                           output_value, snap_at) -> bool
        .record_mat_price(item_id, gil, sampled_at) -> bool
        .record_output_price(recipe_id, gil, sampled_at)
            -> bool
        .latest_mat_price(item_id) -> int     # 0 if no sample
        .report(recipe_id, materials) -> EconomicReport
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class PriceSample:
    item_id: str
    gil: int
    sampled_at: int


@dataclasses.dataclass(frozen=True)
class CostSnapshot:
    recipe_id: str
    mat_costs: tuple[tuple[str, int], ...]    # (item_id, gil)
    output_value: int                          # gil
    snap_at: int


@dataclasses.dataclass(frozen=True)
class EconomicReport:
    recipe_id: str
    publish_cost: int
    publish_output_value: int
    current_cost: int
    current_output_value: int
    profit_margin: int
    drift_pct: float       # (current_cost - publish_cost) / publish_cost
    has_full_cost_data: bool


@dataclasses.dataclass
class RecipeEconomics:
    _publish_snapshots: dict[
        str, CostSnapshot,
    ] = dataclasses.field(default_factory=dict)
    # item_id -> latest PriceSample
    _latest_mat: dict[str, PriceSample] = dataclasses.field(
        default_factory=dict,
    )
    # recipe_id -> latest output price sample
    _latest_output: dict[
        str, PriceSample,
    ] = dataclasses.field(default_factory=dict)

    def seed_publish_cost(
        self, *, recipe_id: str,
        mat_costs: list[tuple[str, int]],
        output_value: int, snap_at: int,
    ) -> bool:
        if not recipe_id:
            return False
        if any(g < 0 for _, g in mat_costs):
            return False
        if output_value < 0:
            return False
        # Idempotent: don't overwrite the first publish
        # snapshot — that's a permanent record of the
        # author's economics at publish time.
        if recipe_id in self._publish_snapshots:
            return False
        self._publish_snapshots[recipe_id] = CostSnapshot(
            recipe_id=recipe_id,
            mat_costs=tuple(mat_costs),
            output_value=output_value, snap_at=snap_at,
        )
        return True

    def record_mat_price(
        self, *, item_id: str, gil: int, sampled_at: int,
    ) -> bool:
        if not item_id or gil < 0:
            return False
        existing = self._latest_mat.get(item_id)
        if (existing is not None
                and existing.sampled_at >= sampled_at):
            return False  # we already have a fresher sample
        self._latest_mat[item_id] = PriceSample(
            item_id=item_id, gil=gil, sampled_at=sampled_at,
        )
        return True

    def record_output_price(
        self, *, recipe_id: str, gil: int,
        sampled_at: int,
    ) -> bool:
        if not recipe_id or gil < 0:
            return False
        existing = self._latest_output.get(recipe_id)
        if (existing is not None
                and existing.sampled_at >= sampled_at):
            return False
        self._latest_output[recipe_id] = PriceSample(
            item_id=recipe_id, gil=gil,
            sampled_at=sampled_at,
        )
        return True

    def latest_mat_price(self, *, item_id: str) -> int:
        s = self._latest_mat.get(item_id)
        return s.gil if s is not None else 0

    def report(
        self, *, recipe_id: str, materials: list[str],
    ) -> EconomicReport:
        snap = self._publish_snapshots.get(recipe_id)
        if snap is None:
            return EconomicReport(
                recipe_id=recipe_id, publish_cost=0,
                publish_output_value=0,
                current_cost=0, current_output_value=0,
                profit_margin=0, drift_pct=0.0,
                has_full_cost_data=False,
            )
        publish_cost = sum(g for _, g in snap.mat_costs)
        # Sum of latest mat prices for the SUPPLIED material
        # list — order-of-truth is the recipe's current
        # mat list, not the publish snapshot (in case the
        # recipe got revised).
        current_cost = 0
        full = True
        for m in materials:
            sample = self._latest_mat.get(m)
            if sample is None:
                full = False
                continue
            current_cost += sample.gil
        # Output: latest sample if any; else snapshot value
        out_sample = self._latest_output.get(recipe_id)
        current_output = (
            out_sample.gil if out_sample is not None
            else snap.output_value
        )
        margin = current_output - current_cost
        drift = (
            (current_cost - publish_cost) / publish_cost
            if publish_cost > 0 else 0.0
        )
        return EconomicReport(
            recipe_id=recipe_id,
            publish_cost=publish_cost,
            publish_output_value=snap.output_value,
            current_cost=current_cost,
            current_output_value=current_output,
            profit_margin=margin, drift_pct=drift,
            has_full_cost_data=full,
        )

    def total_recipes(self) -> int:
        return len(self._publish_snapshots)


__all__ = [
    "PriceSample", "CostSnapshot", "EconomicReport",
    "RecipeEconomics",
]
