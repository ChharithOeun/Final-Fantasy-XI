"""Tests for player_brewing."""
from __future__ import annotations

from server.player_brewing import (
    PlayerBrewingSystem, BrewStage, QualityGrade,
    Recipe,
)


def _wine():
    return Recipe(
        recipe_id="windy_red", name="Windy Red Wine",
        mash_days=2, ferment_days=5,
        aging_days_optimal=30,
        spoilage_days_after_optimal=30,
        base_yield_bottles=6,
    )


def test_register_recipe():
    s = PlayerBrewingSystem()
    assert s.register_recipe(recipe=_wine()) is True


def test_register_recipe_invalid():
    s = PlayerBrewingSystem()
    bad = Recipe(
        recipe_id="x", name="x", mash_days=0,
        ferment_days=1, aging_days_optimal=1,
        spoilage_days_after_optimal=1,
        base_yield_bottles=1,
    )
    assert s.register_recipe(recipe=bad) is False


def test_register_recipe_dup():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    assert s.register_recipe(
        recipe=_wine(),
    ) is False


def test_start_cask_happy():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    assert cid is not None


def test_start_cask_unknown_recipe():
    s = PlayerBrewingSystem()
    cid = s.start_cask(
        owner_id="bob", recipe_id="ghost",
        started_day=10,
    )
    assert cid is None


def test_tick_progresses_stages():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    # Tick after 2 mash + 5 ferment = 7 days into AGING
    s.tick(cask_id=cid, now_day=18)
    c = s.cask(cask_id=cid)
    assert c.stage == BrewStage.AGING


def test_tick_into_spoiled_when_aged_too_long():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    # Move into AGING
    s.tick(cask_id=cid, now_day=18)
    # Then long past spoilage (optimal 30 +
    # spoilage 30 = 60 days from aging start)
    s.tick(cask_id=cid, now_day=200)
    c = s.cask(cask_id=cid)
    assert c.stage == BrewStage.SPOILED


def test_bottle_at_optimal_returns_fine():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    # 30 days into aging from day 18 = day 48
    grade = s.bottle(cask_id=cid, now_day=48)
    assert grade == QualityGrade.FINE


def test_bottle_too_early_is_poor():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    grade = s.bottle(cask_id=cid, now_day=20)
    # 2 days aging vs 30 optimal -> POOR
    assert grade == QualityGrade.POOR


def test_bottle_at_excellent_window():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    # opt=30, +1/3 of spoilage_30 = +10 -> 40-50
    grade = s.bottle(cask_id=cid, now_day=63)
    # 45 days aging
    assert grade == QualityGrade.EXCELLENT


def test_bottle_at_reserve_window():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    # 50-60 -> RESERVE
    grade = s.bottle(cask_id=cid, now_day=73)
    assert grade == QualityGrade.RESERVE


def test_bottle_too_late_spoils():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    # 60+ -> SPOILED
    grade = s.bottle(cask_id=cid, now_day=100)
    assert grade is None
    assert s.cask(
        cask_id=cid,
    ).stage == BrewStage.SPOILED


def test_bottle_not_aging_blocked():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    # Still mashing
    grade = s.bottle(cask_id=cid, now_day=11)
    assert grade is None


def test_bottle_yields_grade_bonus():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    cid = s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=18)
    s.bottle(cask_id=cid, now_day=63)
    c = s.cask(cask_id=cid)
    # base_yield 6 + EXCELLENT bonus 2 = 8
    assert c.bottles_yielded == 8


def test_bottle_poor_yields_min_one():
    s = PlayerBrewingSystem()
    # Recipe with low base yield
    low = Recipe(
        recipe_id="cheap_ale", name="Cheap Ale",
        mash_days=1, ferment_days=1,
        aging_days_optimal=10,
        spoilage_days_after_optimal=10,
        base_yield_bottles=1,
    )
    s.register_recipe(recipe=low)
    cid = s.start_cask(
        owner_id="bob", recipe_id="cheap_ale",
        started_day=10,
    )
    s.tick(cask_id=cid, now_day=12)
    s.bottle(cask_id=cid, now_day=13)
    c = s.cask(cask_id=cid)
    # 1 + (-1 POOR) = 0, clamp to 1
    assert c.bottles_yielded >= 1


def test_casks_of_owner():
    s = PlayerBrewingSystem()
    s.register_recipe(recipe=_wine())
    s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=10,
    )
    s.start_cask(
        owner_id="bob", recipe_id="windy_red",
        started_day=11,
    )
    s.start_cask(
        owner_id="other", recipe_id="windy_red",
        started_day=12,
    )
    out = s.casks_of(owner_id="bob")
    assert len(out) == 2


def test_cask_unknown():
    s = PlayerBrewingSystem()
    assert s.cask(cask_id="ghost") is None


def test_recipe_unknown():
    s = PlayerBrewingSystem()
    assert s.recipe(recipe_id="ghost") is None


def test_tick_unknown():
    s = PlayerBrewingSystem()
    assert s.tick(
        cask_id="ghost", now_day=10,
    ) is None


def test_enum_counts():
    assert len(list(BrewStage)) == 5
    assert len(list(QualityGrade)) == 5
