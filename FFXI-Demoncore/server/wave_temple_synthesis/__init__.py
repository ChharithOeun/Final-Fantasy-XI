"""Wave-temple synthesis — the abyssal crafting endpoint.

Hauling abyssal mats up from the deep is the hard part of
the underwater loop. The crafting bench that turns them
into gear is the payoff. Wave-temple synthesis lives at
the bottom of named hydrothermal vents — visiting it
requires Drowned Pact (cult arc) and crafter level >= 90.
That gating is intentional: the abyssal i-lvl ladder is
the final-mile reward for players who:

  - Survived the cult dark path (drowned_pact_completed)
  - Hit Master Synthesis tier in any one craft
  - Salvaged enough vent steam + spire dust + cult tokens

A successful synthesis rolls against (crafter_skill -
recipe_difficulty) — every 10 points above difficulty
adds 5% chance, capped at 95%. Failure consumes the mats
but yields nothing. HQ procs at 5% on success.

Public surface
--------------
    AbyssalRecipe dataclass (frozen)
    SynthResult dataclass (frozen)
    WaveTempleSynthesis
        .register_recipe(recipe_id, name, ilvl,
                         materials, difficulty)
        .can_use(crafter_id, drowned_pact, crafter_skill)
            -> (bool, reason)
        .attempt(crafter_id, recipe_id,
                 mats_supplied, drowned_pact,
                 crafter_skill, rng_roll, hq_roll) -> SynthResult
        .recipes_for(crafter_skill) -> tuple[AbyssalRecipe, ...]
"""
from __future__ import annotations

import dataclasses
import typing as t


MIN_CRAFTER_LEVEL_TO_USE = 90
SUCCESS_BASE_PCT = 50
SUCCESS_PER_10_OVER = 5
SUCCESS_CAP_PCT = 95
HQ_BASE_PCT = 5


@dataclasses.dataclass(frozen=True)
class AbyssalRecipe:
    recipe_id: str
    name: str
    output_ilvl: int
    materials: dict[str, int]   # item_id -> qty
    difficulty: int


@dataclasses.dataclass(frozen=True)
class SynthResult:
    accepted: bool
    success: bool = False
    is_hq: bool = False
    output_ilvl: int = 0
    consumed_materials: dict[str, int] = dataclasses.field(default_factory=dict)
    reason: t.Optional[str] = None


@dataclasses.dataclass
class WaveTempleSynthesis:
    _recipes: dict[str, AbyssalRecipe] = dataclasses.field(default_factory=dict)

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
        self._recipes[recipe_id] = AbyssalRecipe(
            recipe_id=recipe_id, name=name,
            output_ilvl=output_ilvl,
            materials=dict(materials),
            difficulty=difficulty,
        )
        return True

    def can_use(
        self, *, crafter_id: str,
        drowned_pact: bool,
        crafter_skill: int,
    ) -> tuple[bool, t.Optional[str]]:
        if not crafter_id:
            return False, "bad crafter"
        if not drowned_pact:
            return False, "missing drowned pact"
        if crafter_skill < MIN_CRAFTER_LEVEL_TO_USE:
            return False, "crafter skill too low"
        return True, None

    def attempt(
        self, *, crafter_id: str, recipe_id: str,
        mats_supplied: dict[str, int],
        drowned_pact: bool,
        crafter_skill: int,
        rng_roll: int,   # 0..99
        hq_roll: int,    # 0..99
    ) -> SynthResult:
        ok, reason = self.can_use(
            crafter_id=crafter_id,
            drowned_pact=drowned_pact,
            crafter_skill=crafter_skill,
        )
        if not ok:
            return SynthResult(False, reason=reason)
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return SynthResult(False, reason="unknown recipe")
        # check materials
        for mat, qty_needed in recipe.materials.items():
            if mats_supplied.get(mat, 0) < qty_needed:
                return SynthResult(False, reason="missing materials")
        # success chance
        skill_over = crafter_skill - recipe.difficulty
        bonus = max(0, skill_over // 10) * SUCCESS_PER_10_OVER
        pct = min(SUCCESS_CAP_PCT, SUCCESS_BASE_PCT + bonus)
        success = rng_roll < pct
        # mats are consumed regardless of success
        consumed = dict(recipe.materials)
        if not success:
            return SynthResult(
                accepted=True, success=False,
                consumed_materials=consumed,
            )
        is_hq = hq_roll < HQ_BASE_PCT
        return SynthResult(
            accepted=True, success=True,
            is_hq=is_hq,
            output_ilvl=recipe.output_ilvl,
            consumed_materials=consumed,
        )

    def recipes_for(
        self, *, crafter_skill: int,
    ) -> tuple[AbyssalRecipe, ...]:
        out = [
            r for r in self._recipes.values()
            if crafter_skill >= max(
                MIN_CRAFTER_LEVEL_TO_USE, r.difficulty - 30,
            )
        ]
        return tuple(out)


__all__ = [
    "AbyssalRecipe", "SynthResult", "WaveTempleSynthesis",
    "MIN_CRAFTER_LEVEL_TO_USE",
    "SUCCESS_BASE_PCT", "SUCCESS_PER_10_OVER",
    "SUCCESS_CAP_PCT", "HQ_BASE_PCT",
]
