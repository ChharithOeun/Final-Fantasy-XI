"""Player brewing — beer, wine, and aging cycles.

Brewing is the slow craft. Mash, ferment, age, bottle.
A batch takes weeks to mature, and patience is
literally rewarded — same recipe, longer aged, higher
quality grade. Players queue up multiple casks at once
in their Mog House cellar and check back later.

Stages:
    MASHING        crushing/preparing the base
    FERMENTING     yeast at work; needs time
    AGING          slow flavor development
    BOTTLED        ready to drink/sell
    SPOILED        neglected past spoilage_day or
                   cellar conditions wrong

Quality grade is a function of aging_days_actual vs
aging_days_optimal: at optimal you get standard, past
optimal up to spoilage you can squeeze higher grade,
beyond spoilage it's ruined.

Public surface
--------------
    BrewStage enum
    QualityGrade enum
    Recipe dataclass (frozen)
    Cask dataclass (frozen)
    PlayerBrewingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BrewStage(str, enum.Enum):
    MASHING = "mashing"
    FERMENTING = "fermenting"
    AGING = "aging"
    BOTTLED = "bottled"
    SPOILED = "spoiled"


class QualityGrade(str, enum.Enum):
    POOR = "poor"
    STANDARD = "standard"
    FINE = "fine"
    EXCELLENT = "excellent"
    RESERVE = "reserve"


@dataclasses.dataclass(frozen=True)
class Recipe:
    recipe_id: str
    name: str
    mash_days: int
    ferment_days: int
    aging_days_optimal: int
    spoilage_days_after_optimal: int
    base_yield_bottles: int


@dataclasses.dataclass(frozen=True)
class Cask:
    cask_id: str
    owner_id: str
    recipe_id: str
    started_day: int
    last_tick_day: int
    days_in_stage: int
    stage: BrewStage
    aging_days_total: int
    bottled_grade: t.Optional[QualityGrade]
    bottles_yielded: int


@dataclasses.dataclass
class PlayerBrewingSystem:
    _recipes: dict[str, Recipe] = dataclasses.field(
        default_factory=dict,
    )
    _casks: dict[str, Cask] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def register_recipe(
        self, *, recipe: Recipe,
    ) -> bool:
        if not recipe.recipe_id or not recipe.name:
            return False
        if recipe.mash_days <= 0:
            return False
        if recipe.ferment_days <= 0:
            return False
        if recipe.aging_days_optimal <= 0:
            return False
        if recipe.spoilage_days_after_optimal <= 0:
            return False
        if recipe.base_yield_bottles <= 0:
            return False
        if recipe.recipe_id in self._recipes:
            return False
        self._recipes[recipe.recipe_id] = recipe
        return True

    def start_cask(
        self, *, owner_id: str, recipe_id: str,
        started_day: int,
    ) -> t.Optional[str]:
        if not owner_id:
            return None
        if recipe_id not in self._recipes:
            return None
        if started_day < 0:
            return None
        cid = f"cask_{self._next_id}"
        self._next_id += 1
        self._casks[cid] = Cask(
            cask_id=cid, owner_id=owner_id,
            recipe_id=recipe_id,
            started_day=started_day,
            last_tick_day=started_day,
            days_in_stage=0,
            stage=BrewStage.MASHING,
            aging_days_total=0,
            bottled_grade=None,
            bottles_yielded=0,
        )
        return cid

    def tick(
        self, *, cask_id: str, now_day: int,
    ) -> t.Optional[BrewStage]:
        if cask_id not in self._casks:
            return None
        c = self._casks[cask_id]
        if c.stage in (
            BrewStage.BOTTLED, BrewStage.SPOILED,
        ):
            return c.stage
        if now_day <= c.last_tick_day:
            return c.stage
        recipe = self._recipes[c.recipe_id]
        elapsed = now_day - c.last_tick_day
        new_days = c.days_in_stage + elapsed
        new_stage = c.stage
        new_aging_total = c.aging_days_total
        if (c.stage == BrewStage.MASHING
                and new_days >= recipe.mash_days):
            new_stage = BrewStage.FERMENTING
            new_days = new_days - recipe.mash_days
        if (new_stage == BrewStage.FERMENTING
                and new_days >= recipe.ferment_days):
            new_stage = BrewStage.AGING
            new_days = new_days - recipe.ferment_days
            new_aging_total = 0
        if new_stage == BrewStage.AGING:
            new_aging_total = (
                c.aging_days_total
                + elapsed
                if c.stage == BrewStage.AGING
                else new_days
            )
            # Recompute precisely: aging_days_total
            # accumulates only days while in AGING.
            spoilage_threshold = (
                recipe.aging_days_optimal
                + recipe.spoilage_days_after_optimal
            )
            if new_aging_total >= spoilage_threshold:
                new_stage = BrewStage.SPOILED
        self._casks[cask_id] = dataclasses.replace(
            c, last_tick_day=now_day,
            days_in_stage=new_days,
            stage=new_stage,
            aging_days_total=new_aging_total,
        )
        return new_stage

    def bottle(
        self, *, cask_id: str, now_day: int,
    ) -> t.Optional[QualityGrade]:
        if cask_id not in self._casks:
            return None
        c = self._casks[cask_id]
        if c.stage != BrewStage.AGING:
            return None
        recipe = self._recipes[c.recipe_id]
        # Recompute aging accurately at bottling
        # using elapsed since last tick.
        aging = (
            c.aging_days_total
            + max(0, now_day - c.last_tick_day)
        )
        opt = recipe.aging_days_optimal
        spoilage = (
            opt + recipe.spoilage_days_after_optimal
        )
        if aging < opt // 2:
            grade = QualityGrade.POOR
        elif aging < opt:
            grade = QualityGrade.STANDARD
        elif aging < opt + (
            recipe.spoilage_days_after_optimal // 3
        ):
            grade = QualityGrade.FINE
        elif aging < opt + (
            recipe.spoilage_days_after_optimal
            * 2 // 3
        ):
            grade = QualityGrade.EXCELLENT
        elif aging < spoilage:
            grade = QualityGrade.RESERVE
        else:
            # Past spoilage threshold
            self._casks[cask_id] = (
                dataclasses.replace(
                    c, stage=BrewStage.SPOILED,
                    last_tick_day=now_day,
                    aging_days_total=aging,
                )
            )
            return None
        bottles = recipe.base_yield_bottles
        # Higher grade -> +1 bottle bonus per tier
        grade_bonus = {
            QualityGrade.POOR: -1,
            QualityGrade.STANDARD: 0,
            QualityGrade.FINE: 1,
            QualityGrade.EXCELLENT: 2,
            QualityGrade.RESERVE: 3,
        }[grade]
        bottles = max(1, bottles + grade_bonus)
        self._casks[cask_id] = dataclasses.replace(
            c, stage=BrewStage.BOTTLED,
            last_tick_day=now_day,
            aging_days_total=aging,
            bottled_grade=grade,
            bottles_yielded=bottles,
        )
        return grade

    def cask(
        self, *, cask_id: str,
    ) -> t.Optional[Cask]:
        return self._casks.get(cask_id)

    def casks_of(
        self, *, owner_id: str,
    ) -> list[Cask]:
        return [
            c for c in self._casks.values()
            if c.owner_id == owner_id
        ]

    def recipe(
        self, *, recipe_id: str,
    ) -> t.Optional[Recipe]:
        return self._recipes.get(recipe_id)


__all__ = [
    "BrewStage", "QualityGrade", "Recipe", "Cask",
    "PlayerBrewingSystem",
]
