"""Stratosphere-temple synthesis — aerial endgame crafting.

Mirrors wave_temple_synthesis but for the aerial loop. Lives
on top of named WEATHER_PILLAR landmarks at STRATOSPHERE
band — visiting requires:

  - WYVERN_LORDS reputation >= +25 (so they let you in
    instead of attacking on sight)
  - crafter_skill >= 90 (Master Synthesis tier)

Recipes consume cloud_pearl + jet_essence + wyvern_scale.
Same success curve as wave temple: 50% at-difficulty, +5%
per 10 skill over, capped at 95%. 5% HQ. Failure consumes
the materials. The output ladder is the aerial twin of
the abyssal one — i-lvl 119–175 sky-spec gear.

Public surface
--------------
    AerialRecipe dataclass (frozen)
    SynthResult dataclass (frozen)
    StratosphereTempleSynthesis
        .register_recipe(recipe_id, name, ilvl,
                         materials, difficulty)
        .can_use(crafter_id, wyvern_lord_rep, crafter_skill)
            -> (bool, reason)
        .attempt(crafter_id, recipe_id, mats_supplied,
                 wyvern_lord_rep, crafter_skill,
                 rng_roll, hq_roll) -> SynthResult
        .recipes_for(crafter_skill) -> tuple[AerialRecipe, ...]
"""
from __future__ import annotations

import dataclasses
import typing as t


MIN_CRAFTER_LEVEL_TO_USE = 90
MIN_WYVERN_REP = 25
SUCCESS_BASE_PCT = 50
SUCCESS_PER_10_OVER = 5
SUCCESS_CAP_PCT = 95
HQ_BASE_PCT = 5


@dataclasses.dataclass(frozen=True)
class AerialRecipe:
    recipe_id: str
    name: str
    output_ilvl: int
    materials: dict[str, int]
    difficulty: int


@dataclasses.dataclass(frozen=True)
class SynthResult:
    accepted: bool
    success: bool = False
    is_hq: bool = False
    output_ilvl: int = 0
    consumed_materials: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    reason: t.Optional[str] = None


@dataclasses.dataclass
class StratosphereTempleSynthesis:
    _recipes: dict[str, AerialRecipe] = dataclasses.field(
        default_factory=dict,
    )

    def register_recipe(
        self, *, recipe_id: str, name: str,
        output_ilvl: int,
        materials: dict[str, int],
        difficulty: int,
    ) -> bool:
        if not recipe_id or not name:
            return False
        if output_ilvl < 119 or output_ilvl > 175:
            return False
        if not materials:
            return False
        if recipe_id in self._recipes:
            return False
        self._recipes[recipe_id] = AerialRecipe(
            recipe_id=recipe_id, name=name,
            output_ilvl=output_ilvl,
            materials=dict(materials),
            difficulty=difficulty,
        )
        return True

    def can_use(
        self, *, crafter_id: str,
        wyvern_lord_rep: int,
        crafter_skill: int,
    ) -> tuple[bool, t.Optional[str]]:
        if not crafter_id:
            return False, "bad crafter"
        if wyvern_lord_rep < MIN_WYVERN_REP:
            return False, "wyvern lords hostile"
        if crafter_skill < MIN_CRAFTER_LEVEL_TO_USE:
            return False, "crafter skill too low"
        return True, None

    def attempt(
        self, *, crafter_id: str, recipe_id: str,
        mats_supplied: dict[str, int],
        wyvern_lord_rep: int,
        crafter_skill: int,
        rng_roll: int, hq_roll: int,
    ) -> SynthResult:
        ok, reason = self.can_use(
            crafter_id=crafter_id,
            wyvern_lord_rep=wyvern_lord_rep,
            crafter_skill=crafter_skill,
        )
        if not ok:
            return SynthResult(False, reason=reason)
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return SynthResult(False, reason="unknown recipe")
        for mat, qty in recipe.materials.items():
            if mats_supplied.get(mat, 0) < qty:
                return SynthResult(False, reason="missing materials")
        skill_over = crafter_skill - recipe.difficulty
        bonus = max(0, skill_over // 10) * SUCCESS_PER_10_OVER
        pct = min(SUCCESS_CAP_PCT, SUCCESS_BASE_PCT + bonus)
        success = rng_roll < pct
        consumed = dict(recipe.materials)
        if not success:
            return SynthResult(
                accepted=True, success=False,
                consumed_materials=consumed,
            )
        is_hq = hq_roll < HQ_BASE_PCT
        return SynthResult(
            accepted=True, success=True, is_hq=is_hq,
            output_ilvl=recipe.output_ilvl,
            consumed_materials=consumed,
        )

    def recipes_for(
        self, *, crafter_skill: int,
    ) -> tuple[AerialRecipe, ...]:
        return tuple(
            r for r in self._recipes.values()
            if crafter_skill >= max(
                MIN_CRAFTER_LEVEL_TO_USE, r.difficulty - 30,
            )
        )


__all__ = [
    "AerialRecipe", "SynthResult",
    "StratosphereTempleSynthesis",
    "MIN_CRAFTER_LEVEL_TO_USE", "MIN_WYVERN_REP",
    "SUCCESS_BASE_PCT", "SUCCESS_PER_10_OVER",
    "SUCCESS_CAP_PCT", "HQ_BASE_PCT",
]
