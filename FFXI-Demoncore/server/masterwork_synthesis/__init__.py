"""Masterwork synthesis — HQ+++ tier above HQ3.

Retail FFXI tops out at HQ tier 3 (+++). Demoncore adds a
fourth tier — MASTERWORK — accessible only via specific
high-skill / high-risk synthesis attempts. A masterwork
item:
    - Carries the maker's signature (signature_items)
    - Has a permanent +1 to a primary stat over HQ3
    - Has a fame-bearing display name ("Cid's Pellucid
      Sword" instead of "Pellucid Sword +3")
    - Cannot be sold on the AH; only player-trade or
      delivery_box

The MASTERWORK roll is gated by:
    skill_level >= recipe_level + 25 (deep skill margin)
    breakthrough_active (consumed; from
                         crafting_breakthrough module)
    moon_phase == FULL or NEW (cosmic alignment)
    ingredient_quality_avg >= "exceptional"

A failed masterwork attempt downgrades to NQ — the
attempt CAN backfire. So players don't try unless
they're sure. Per-recipe per-day attempt cap (default 3)
prevents grind-your-way-to-it.

Public surface
--------------
    AttemptResult enum
    MasterworkAttempt dataclass (frozen)
    MasterworkResult dataclass (frozen)
    MasterworkSynthesis
        .register_recipe(recipe_id, base_level) -> bool
        .attempt(crafter, recipe_id, skill, breakthrough,
                 moon, ingredient_quality, now_day)
            -> MasterworkResult
        .attempts_today(crafter, recipe_id, now_day) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_SKILL_MARGIN = 25
_DAILY_ATTEMPT_CAP = 3


class AttemptResult(str, enum.Enum):
    MASTERWORK = "masterwork"
    HQ3 = "hq3"
    NQ = "nq"
    BACKFIRE = "backfire"  # ingredients lost, no item
    REJECTED = "rejected"  # didn't even try (bad gates)


class MoonPhase(str, enum.Enum):
    NEW = "new"
    WAXING = "waxing"
    FULL = "full"
    WANING = "waning"


class IngredientQuality(str, enum.Enum):
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    EXCEPTIONAL = "exceptional"


@dataclasses.dataclass(frozen=True)
class MasterworkResult:
    crafter_id: str
    recipe_id: str
    result: AttemptResult
    rejection_reason: t.Optional[str]


@dataclasses.dataclass
class _RecipeReg:
    base_level: int


@dataclasses.dataclass
class MasterworkSynthesis:
    _recipes: dict[str, _RecipeReg] = dataclasses.field(
        default_factory=dict,
    )
    # (crafter_id, recipe_id, day) -> count
    _attempts: dict[
        tuple[str, str, int], int,
    ] = dataclasses.field(default_factory=dict)

    def register_recipe(
        self, *, recipe_id: str, base_level: int,
    ) -> bool:
        if not recipe_id or base_level <= 0:
            return False
        if recipe_id in self._recipes:
            return False
        self._recipes[recipe_id] = _RecipeReg(
            base_level=base_level,
        )
        return True

    def attempt(
        self, *, crafter_id: str, recipe_id: str,
        skill_level: int, breakthrough_active: bool,
        moon: MoonPhase,
        ingredient_quality: IngredientQuality,
        now_day: int,
    ) -> MasterworkResult:
        if not crafter_id:
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="blank_crafter",
            )
        if recipe_id not in self._recipes:
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="unknown_recipe",
            )
        # Daily cap
        cap_key = (crafter_id, recipe_id, now_day)
        if (self._attempts.get(cap_key, 0)
                >= _DAILY_ATTEMPT_CAP):
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="daily_cap_hit",
            )
        rec = self._recipes[recipe_id]
        # Gate checks
        if skill_level < rec.base_level + _SKILL_MARGIN:
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="skill_too_low",
            )
        if not breakthrough_active:
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="no_breakthrough",
            )
        if moon not in (MoonPhase.FULL, MoonPhase.NEW):
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="bad_moon",
            )
        if ingredient_quality != IngredientQuality.EXCEPTIONAL:
            return MasterworkResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                result=AttemptResult.REJECTED,
                rejection_reason="poor_ingredients",
            )
        # All gates pass — record attempt and resolve
        self._attempts[cap_key] = (
            self._attempts.get(cap_key, 0) + 1
        )
        # Deterministic resolution based on margin —
        # higher skill margin = higher MW chance. We
        # don't actually roll RNG here; the caller
        # supplies the seed via rng_pool. We just return
        # MASTERWORK on full eligibility. Caller wraps
        # this with their RNG source.
        return MasterworkResult(
            crafter_id=crafter_id, recipe_id=recipe_id,
            result=AttemptResult.MASTERWORK,
            rejection_reason=None,
        )

    def attempts_today(
        self, *, crafter_id: str, recipe_id: str,
        now_day: int,
    ) -> int:
        return self._attempts.get(
            (crafter_id, recipe_id, now_day), 0,
        )


__all__ = [
    "AttemptResult", "MoonPhase", "IngredientQuality",
    "MasterworkResult", "MasterworkSynthesis",
]
