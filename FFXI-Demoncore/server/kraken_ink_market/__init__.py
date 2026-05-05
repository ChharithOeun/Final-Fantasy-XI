"""Kraken ink market — pirate fence converts kraken loot to gear.

After the kraken is defeated, the materials it drops
(KRAKEN_INK, HOLLOW_PEARL, ABYSSAL_FRAGMENT) need somewhere
to spend. The pirate fence at TANGLED_FLAG hideout takes
them — at a 30% markup over fair value, because pirates —
and trades them for INK_GEAR: a tier of underwater gear with
KRAKEN_RESIST and abyss-affinity stats.

Stock listings:
  Each ink_gear piece has a recipe: gil + N kraken loot
  items. Buying decrements stock; the fence restocks once
  per Vana'diel day (24h real-time clock).

Public surface
--------------
    InkLoot enum
    InkGear enum
    GearRecipe dataclass
    PurchaseResult dataclass
    KrakenInkMarket
        .restock(now_seconds)
        .purchase(player_id, gear, loot_inventory, gil_paid,
                  now_seconds)
        .stock_remaining(gear)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class InkLoot(str, enum.Enum):
    ABYSSAL_FRAGMENT = "abyssal_fragment"
    KRAKEN_INK = "kraken_ink"
    HOLLOW_PEARL = "hollow_pearl"


class InkGear(str, enum.Enum):
    INKBLOT_BAND = "inkblot_band"           # ring; cheap
    INKBLOOD_CHARM = "inkblood_charm"       # neck
    HOLLOW_TRIDENT = "hollow_trident"       # weapon; rare


@dataclasses.dataclass(frozen=True)
class GearRecipe:
    gear: InkGear
    gil_cost: int
    fragments: int
    inks: int
    pearls: int
    base_stock_per_day: int


_RECIPES: dict[InkGear, GearRecipe] = {
    InkGear.INKBLOT_BAND: GearRecipe(
        gear=InkGear.INKBLOT_BAND,
        gil_cost=15_000, fragments=3, inks=1, pearls=0,
        base_stock_per_day=5,
    ),
    InkGear.INKBLOOD_CHARM: GearRecipe(
        gear=InkGear.INKBLOOD_CHARM,
        gil_cost=60_000, fragments=5, inks=2, pearls=1,
        base_stock_per_day=2,
    ),
    InkGear.HOLLOW_TRIDENT: GearRecipe(
        gear=InkGear.HOLLOW_TRIDENT,
        gil_cost=300_000, fragments=10, inks=4, pearls=2,
        base_stock_per_day=1,
    ),
}

# 24-hour restock window (real seconds)
_RESTOCK_INTERVAL_SECONDS = 24 * 3_600


@dataclasses.dataclass(frozen=True)
class PurchaseResult:
    accepted: bool
    gear: t.Optional[InkGear] = None
    gil_consumed: int = 0
    loot_consumed: t.Optional[dict[InkLoot, int]] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class KrakenInkMarket:
    _stock: dict[InkGear, int] = dataclasses.field(default_factory=dict)
    _last_restock: int = -_RESTOCK_INTERVAL_SECONDS

    def restock(self, *, now_seconds: int) -> bool:
        if now_seconds - self._last_restock < _RESTOCK_INTERVAL_SECONDS:
            return False
        for gear, recipe in _RECIPES.items():
            self._stock[gear] = recipe.base_stock_per_day
        self._last_restock = now_seconds
        return True

    def stock_remaining(self, *, gear: InkGear) -> int:
        return self._stock.get(gear, 0)

    @staticmethod
    def recipe_for(*, gear: InkGear) -> t.Optional[GearRecipe]:
        return _RECIPES.get(gear)

    def purchase(
        self, *, player_id: str,
        gear: InkGear,
        loot_inventory: dict[InkLoot, int],
        gil_paid: int,
        now_seconds: int,
    ) -> PurchaseResult:
        if not player_id:
            return PurchaseResult(False, reason="bad player")
        recipe = _RECIPES.get(gear)
        if recipe is None:
            return PurchaseResult(False, reason="unknown gear")
        # auto-restock if window elapsed
        self.restock(now_seconds=now_seconds)
        if self.stock_remaining(gear=gear) <= 0:
            return PurchaseResult(
                False, gear=gear, reason="out of stock",
            )
        if gil_paid < recipe.gil_cost:
            return PurchaseResult(
                False, gear=gear, reason="insufficient gil",
            )
        # check loot
        have_frag = loot_inventory.get(InkLoot.ABYSSAL_FRAGMENT, 0)
        have_ink = loot_inventory.get(InkLoot.KRAKEN_INK, 0)
        have_pearl = loot_inventory.get(InkLoot.HOLLOW_PEARL, 0)
        if (
            have_frag < recipe.fragments
            or have_ink < recipe.inks
            or have_pearl < recipe.pearls
        ):
            return PurchaseResult(
                False, gear=gear, reason="insufficient loot",
            )
        self._stock[gear] = self._stock[gear] - 1
        consumed = {
            InkLoot.ABYSSAL_FRAGMENT: recipe.fragments,
            InkLoot.KRAKEN_INK: recipe.inks,
            InkLoot.HOLLOW_PEARL: recipe.pearls,
        }
        return PurchaseResult(
            accepted=True,
            gear=gear,
            gil_consumed=recipe.gil_cost,
            loot_consumed=consumed,
        )


__all__ = [
    "InkLoot", "InkGear",
    "GearRecipe", "PurchaseResult",
    "KrakenInkMarket",
]
