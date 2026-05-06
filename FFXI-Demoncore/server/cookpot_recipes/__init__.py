"""Cookpot recipes — turn ingredients into named dishes.

The hunter's pot, distinct from the guild kitchen
(crafting/COOKING). This is "I have meat, herbs, water,
and a fire — what can I make right now in the field?"
The output is a named dish carrying a buff payload that
meal_buff_engine actually applies.

Each recipe is a deterministic ingredient → dish map.
The same ingredients can match multiple recipes — the
caller picks which one to attempt. Higher-tier dishes
demand more inputs; basic ones are tolerant.

Buff dimensions
---------------
Each dish carries a BuffPayload describing what it does:
    str_bonus, dex_bonus, vit_bonus     stat tilts
    regen_per_tick, refresh_per_tick    sustain
    hp_max_pct, mp_max_pct              ceilings
    cold_resist, heat_resist            climate
    duration_seconds                    how long it lasts

Public surface
--------------
    DishKind enum (named dishes)
    BuffPayload dataclass (frozen)
    Recipe dataclass (frozen)
    CookpotResult dataclass (frozen)
    CookpotRecipeRegistry
        .define_recipe(dish, ingredients, payload) -> bool
        .cook(ingredients_offered, dish_kind) -> CookpotResult
        .recipes_for_dish(dish) -> Optional[Recipe]
        .all_dishes() -> list[DishKind]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DishKind(str, enum.Enum):
    HUNTERS_STEW = "hunters_stew"            # meat + root + water
    BERRY_PORRIDGE = "berry_porridge"        # grain + berry + water
    SPICED_JERKY_BROTH = "spiced_jerky_broth"  # jerky + herb + water
    HEARTH_ROAST = "hearth_roast"            # meat + meat + herb
    FORAGER_SALAD = "forager_salad"          # mushroom + berry + leaf
    WARMING_TEA = "warming_tea"              # herb + water (cold-fight)
    COOLING_DRAUGHT = "cooling_draught"      # mint + water (heat-fight)


@dataclasses.dataclass(frozen=True)
class BuffPayload:
    str_bonus: int = 0
    dex_bonus: int = 0
    vit_bonus: int = 0
    regen_per_tick: int = 0
    refresh_per_tick: int = 0
    hp_max_pct: int = 0
    mp_max_pct: int = 0
    cold_resist: int = 0
    heat_resist: int = 0
    duration_seconds: int = 1800   # 30 min default


@dataclasses.dataclass(frozen=True)
class Recipe:
    dish: DishKind
    ingredients: dict[str, int]   # ingredient_id -> qty needed
    payload: BuffPayload


@dataclasses.dataclass(frozen=True)
class CookpotResult:
    success: bool
    dish: t.Optional[DishKind]
    payload: t.Optional[BuffPayload]
    reason: str


@dataclasses.dataclass
class CookpotRecipeRegistry:
    _recipes: dict[DishKind, Recipe] = dataclasses.field(
        default_factory=dict,
    )

    def define_recipe(
        self, *, dish: DishKind,
        ingredients: dict[str, int],
        payload: BuffPayload,
    ) -> bool:
        if not ingredients:
            return False
        for k, v in ingredients.items():
            if not k or v <= 0:
                return False
        if dish in self._recipes:
            return False
        self._recipes[dish] = Recipe(
            dish=dish, ingredients=dict(ingredients),
            payload=payload,
        )
        return True

    def recipes_for_dish(
        self, *, dish: DishKind,
    ) -> t.Optional[Recipe]:
        return self._recipes.get(dish)

    def cook(
        self, *, ingredients_offered: dict[str, int],
        dish_kind: DishKind,
    ) -> CookpotResult:
        recipe = self._recipes.get(dish_kind)
        if recipe is None:
            return CookpotResult(
                success=False, dish=None, payload=None,
                reason="unknown_recipe",
            )
        # all required ingredients must be present in
        # at least the listed quantities
        for ing, qty in recipe.ingredients.items():
            if ingredients_offered.get(ing, 0) < qty:
                return CookpotResult(
                    success=False, dish=None, payload=None,
                    reason="missing_" + ing,
                )
        return CookpotResult(
            success=True, dish=dish_kind,
            payload=recipe.payload, reason="",
        )

    def all_dishes(self) -> list[DishKind]:
        return list(self._recipes.keys())

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "DishKind", "BuffPayload", "Recipe",
    "CookpotResult", "CookpotRecipeRegistry",
]
