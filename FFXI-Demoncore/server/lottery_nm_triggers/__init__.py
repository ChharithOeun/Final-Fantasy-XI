"""Lottery NM triggers — item-trigger NM spawns.

Canonical FFXI lottery / placement NMs work like this: place a
specific item at a specific spot, the trigger consumes it, and a
named monster pops. Examples: dropping the "Black Coral Scale"
at the Mhaura altar to spawn Naelos; placing flowers at a grave
to lure a Spectre NM.

This module owns the registry + dispatch logic, separate from
notorious_monsters (which handles ToD-window spawns) and from
encounter_gen (which handles dynamic spawns).

A `TriggerRecipe` declares:
* nm_id and zone_id
* required_item_id (and required_count)
* placement position tile + tolerance radius
* placement_window_required (optional time-of-day window)
* spawn_cooldown — minimum game-time between consecutive
  legitimate spawns (prevents farm trains)
* fail_cause if conditions are wrong (wrong zone, wrong item,
  wrong position, wrong time, on cooldown)

Public surface
--------------
    TriggerOutcome enum
    TriggerRecipe dataclass
    TriggerAttempt dataclass — record of an attempt
    LotteryNMRegistry
        .register_recipe(recipe)
        .place_trigger(player_id, zone_id, item_id, position,
                        now_seconds, hour) -> TriggerAttempt
        .last_spawn_for(nm_id) / .recipes_for_zone(zone_id)
        .reset_cooldown(nm_id)
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class TriggerOutcome(str, enum.Enum):
    SPAWNED = "spawned"
    NO_RECIPE = "no_recipe"
    WRONG_ITEM = "wrong_item"
    INSUFFICIENT_ITEMS = "insufficient_items"
    WRONG_POSITION = "wrong_position"
    WRONG_TIME = "wrong_time"
    ON_COOLDOWN = "on_cooldown"


@dataclasses.dataclass(frozen=True)
class TriggerRecipe:
    nm_id: str
    zone_id: str
    required_item_id: str
    placement_position: tuple[int, int]
    tolerance_tiles: int = 3
    required_item_count: int = 1
    # Optional time-of-day window — inclusive [start, end).
    # If end < start, the window wraps midnight.
    required_hour_start: t.Optional[int] = None
    required_hour_end: t.Optional[int] = None
    spawn_cooldown_seconds: float = 60 * 60 * 4
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class TriggerAttempt:
    outcome: TriggerOutcome
    nm_id: t.Optional[str]
    spawned_at_seconds: t.Optional[float] = None
    consumed_items: int = 0
    reason: str = ""


def _hour_in_window(
    *, hour: int, start: int, end: int,
) -> bool:
    h = hour % 24
    if start <= end:
        return start <= h < end
    return h >= start or h < end


def _within_tolerance(
    *, a: tuple[int, int], b: tuple[int, int], tolerance: int,
) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tolerance


@dataclasses.dataclass
class LotteryNMRegistry:
    _recipes: dict[str, TriggerRecipe] = dataclasses.field(
        default_factory=dict,
    )
    _last_spawn_at: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )

    def register_recipe(
        self, recipe: TriggerRecipe,
    ) -> TriggerRecipe:
        self._recipes[recipe.nm_id] = recipe
        return recipe

    def recipe_for(self, nm_id: str) -> t.Optional[TriggerRecipe]:
        return self._recipes.get(nm_id)

    def recipes_for_zone(
        self, zone_id: str,
    ) -> tuple[TriggerRecipe, ...]:
        return tuple(
            r for r in self._recipes.values()
            if r.zone_id == zone_id
        )

    def last_spawn_for(self, nm_id: str) -> t.Optional[float]:
        return self._last_spawn_at.get(nm_id)

    def reset_cooldown(self, nm_id: str) -> bool:
        return self._last_spawn_at.pop(nm_id, None) is not None

    def place_trigger(
        self, *, player_id: str, zone_id: str, item_id: str,
        item_count: int, position: tuple[int, int],
        now_seconds: float, hour: int,
    ) -> TriggerAttempt:
        # Find recipes in this zone matching the item
        candidates = [
            r for r in self._recipes.values()
            if r.zone_id == zone_id
            and r.required_item_id == item_id
        ]
        if not candidates:
            return TriggerAttempt(
                outcome=TriggerOutcome.NO_RECIPE, nm_id=None,
                reason=(
                    "no recipe in this zone takes that item"
                ),
            )
        # Try each recipe in turn — we accept the first that
        # passes ALL checks. If none pass, return the most
        # diagnostic failure.
        last_failure: t.Optional[TriggerAttempt] = None
        for recipe in candidates:
            if item_count < recipe.required_item_count:
                last_failure = TriggerAttempt(
                    outcome=TriggerOutcome.INSUFFICIENT_ITEMS,
                    nm_id=recipe.nm_id,
                    reason=(
                        f"need {recipe.required_item_count}x"
                        f" {recipe.required_item_id}"
                    ),
                )
                continue
            if not _within_tolerance(
                a=position, b=recipe.placement_position,
                tolerance=recipe.tolerance_tiles,
            ):
                last_failure = TriggerAttempt(
                    outcome=TriggerOutcome.WRONG_POSITION,
                    nm_id=recipe.nm_id,
                    reason=(
                        f"item must be placed near "
                        f"{recipe.placement_position}"
                    ),
                )
                continue
            if (
                recipe.required_hour_start is not None
                and recipe.required_hour_end is not None
            ):
                if not _hour_in_window(
                    hour=hour,
                    start=recipe.required_hour_start,
                    end=recipe.required_hour_end,
                ):
                    last_failure = TriggerAttempt(
                        outcome=TriggerOutcome.WRONG_TIME,
                        nm_id=recipe.nm_id,
                        reason=(
                            f"window is "
                            f"{recipe.required_hour_start}h.."
                            f"{recipe.required_hour_end}h"
                        ),
                    )
                    continue
            last = self._last_spawn_at.get(recipe.nm_id)
            if (
                last is not None
                and (now_seconds - last)
                < recipe.spawn_cooldown_seconds
            ):
                last_failure = TriggerAttempt(
                    outcome=TriggerOutcome.ON_COOLDOWN,
                    nm_id=recipe.nm_id,
                    reason=(
                        "NM still recovering from prior spawn"
                    ),
                )
                continue
            # SUCCESS
            self._last_spawn_at[recipe.nm_id] = now_seconds
            return TriggerAttempt(
                outcome=TriggerOutcome.SPAWNED,
                nm_id=recipe.nm_id,
                spawned_at_seconds=now_seconds,
                consumed_items=recipe.required_item_count,
            )
        return last_failure or TriggerAttempt(
            outcome=TriggerOutcome.WRONG_POSITION,
            nm_id=None, reason="placement rejected",
        )

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "TriggerOutcome", "TriggerRecipe", "TriggerAttempt",
    "LotteryNMRegistry",
]
