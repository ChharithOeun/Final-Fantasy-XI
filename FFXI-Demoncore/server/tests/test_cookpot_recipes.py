"""Tests for cookpot_recipes."""
from __future__ import annotations

from server.cookpot_recipes import (
    BuffPayload, CookpotRecipeRegistry, DishKind,
)


def _setup():
    r = CookpotRecipeRegistry()
    r.define_recipe(
        dish=DishKind.HUNTERS_STEW,
        ingredients={"raw_meat": 2, "root_veg": 1, "water": 1},
        payload=BuffPayload(str_bonus=3, vit_bonus=2, duration_seconds=1800),
    )
    r.define_recipe(
        dish=DishKind.BERRY_PORRIDGE,
        ingredients={"wild_grain": 2, "red_berry": 3, "water": 1},
        payload=BuffPayload(regen_per_tick=2, duration_seconds=1200),
    )
    r.define_recipe(
        dish=DishKind.WARMING_TEA,
        ingredients={"ginger_root": 1, "water": 1},
        payload=BuffPayload(cold_resist=15, duration_seconds=900),
    )
    return r


def test_define_recipe_happy():
    r = _setup()
    assert r.total_recipes() == 3


def test_define_no_ingredients_blocked():
    r = CookpotRecipeRegistry()
    out = r.define_recipe(
        dish=DishKind.HUNTERS_STEW,
        ingredients={}, payload=BuffPayload(),
    )
    assert out is False


def test_define_zero_qty_blocked():
    r = CookpotRecipeRegistry()
    out = r.define_recipe(
        dish=DishKind.HUNTERS_STEW,
        ingredients={"x": 0}, payload=BuffPayload(),
    )
    assert out is False


def test_define_blank_ingredient_blocked():
    r = CookpotRecipeRegistry()
    out = r.define_recipe(
        dish=DishKind.HUNTERS_STEW,
        ingredients={"": 1}, payload=BuffPayload(),
    )
    assert out is False


def test_define_duplicate_blocked():
    r = _setup()
    out = r.define_recipe(
        dish=DishKind.HUNTERS_STEW,
        ingredients={"x": 1}, payload=BuffPayload(),
    )
    assert out is False


def test_cook_happy():
    r = _setup()
    out = r.cook(
        ingredients_offered={"raw_meat": 2, "root_veg": 1, "water": 5},
        dish_kind=DishKind.HUNTERS_STEW,
    )
    assert out.success is True
    assert out.dish == DishKind.HUNTERS_STEW
    assert out.payload.str_bonus == 3


def test_cook_unknown_recipe():
    r = _setup()
    out = r.cook(
        ingredients_offered={"x": 99},
        dish_kind=DishKind.HEARTH_ROAST,
    )
    assert out.success is False
    assert out.reason == "unknown_recipe"


def test_cook_missing_ingredient():
    r = _setup()
    out = r.cook(
        ingredients_offered={"raw_meat": 2, "water": 1},  # no root_veg
        dish_kind=DishKind.HUNTERS_STEW,
    )
    assert out.success is False
    assert out.reason == "missing_root_veg"


def test_cook_insufficient_qty():
    r = _setup()
    out = r.cook(
        ingredients_offered={"raw_meat": 1, "root_veg": 1, "water": 1},
        dish_kind=DishKind.HUNTERS_STEW,
    )
    assert out.success is False
    assert out.reason == "missing_raw_meat"


def test_cook_extra_ingredients_allowed():
    r = _setup()
    # offer way more than required → still cooks
    out = r.cook(
        ingredients_offered={"raw_meat": 99, "root_veg": 5, "water": 99,
                              "spare": 100},
        dish_kind=DishKind.HUNTERS_STEW,
    )
    assert out.success is True


def test_recipe_for_dish_returns():
    r = _setup()
    rec = r.recipes_for_dish(dish=DishKind.WARMING_TEA)
    assert rec is not None
    assert rec.payload.cold_resist == 15


def test_recipe_for_unknown_returns_none():
    r = _setup()
    rec = r.recipes_for_dish(dish=DishKind.HEARTH_ROAST)
    assert rec is None


def test_all_dishes_lists_defined():
    r = _setup()
    dishes = r.all_dishes()
    assert DishKind.HUNTERS_STEW in dishes
    assert len(dishes) == 3


def test_seven_dish_kinds_in_enum():
    assert len(list(DishKind)) == 7


def test_buff_payload_defaults_zero():
    p = BuffPayload()
    assert p.str_bonus == 0
    assert p.regen_per_tick == 0
    assert p.duration_seconds == 1800


def test_warming_tea_carries_cold_resist():
    r = _setup()
    out = r.cook(
        ingredients_offered={"ginger_root": 1, "water": 1},
        dish_kind=DishKind.WARMING_TEA,
    )
    assert out.success is True
    assert out.payload.cold_resist == 15
    assert out.payload.heat_resist == 0
