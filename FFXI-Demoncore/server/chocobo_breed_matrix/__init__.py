"""Chocobo breed matrix — cross-breed combo table + roll engine.

Two players (one with a male chocobo, one with a female) bring
their mounts to a BREEDER NPC. The NPC consumes a recipe of
RARE / R/EX resources from the Shadowlands and the Chocobo
Forest, and produces a single egg whose color is rolled against
a per-(parent_color, parent_color) probability table.

Same-color parents heavily favor that color; mixed pairs trend
toward the dominant parent and have a small chance to roll a
COLORED VARIANT (a third color). RAINBOW chocobos cannot breed
(see chocobo_colors). A microscopic 0.0001% (1 in 1_000_000)
chance to produce a RAINBOW EGG exists on every successful
roll, regardless of parent colors.

Combined level + combat skill bonus boosts the COLORED VARIANT
chance up to a cap. Trait inheritance is computed alongside.

Public surface
--------------
    BreedRecipe dataclass
    BreedRollResult dataclass
    ChocoboBreedMatrix
        .roll(male_color, female_color, combined_level,
              combined_skill, roll_pct_color, roll_pct_rainbow)
        .recipe_for(male_color, female_color)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.chocobo_colors import ChocoboColor


# Common rare items. Real implementation would key into the item DB.
_OZ_ROOT = "shadowlands_oz_root"
_HALV_BLOOD = "halvung_volcanic_blood"
_LAMIA_PEARL = "lamia_tide_pearl"
_QUADAV_FOSSIL = "quadav_fossil_horn"
_FOREST_FEATHER = "chocobo_forest_glittering_feather"
_FOREST_GRAIN = "chocobo_forest_amber_grain"
_REX_FEATHER = "rainbow_feather_rex"


@dataclasses.dataclass(frozen=True)
class BreedRecipe:
    items: tuple[tuple[str, int], ...]
    gil_cost: int
    quest_npc: str = "old_breeder_dlatish"


# Outcome distribution: cumulative thresholds 0..100. Each row is
# (cumulative_pct, output_color). Higher rows beat lower thresholds.
# A separate COLOURED_VARIANT slice is layered in by the roll
# function based on combined level + skill bonus.
_BASE_DIST: dict[
    tuple[ChocoboColor, ChocoboColor], tuple[tuple[int, ChocoboColor], ...],
] = {
    # Same-color (yellow x yellow etc.) — strongly self-replicating
    (ChocoboColor.YELLOW, ChocoboColor.YELLOW): (
        (88, ChocoboColor.YELLOW),
        (96, ChocoboColor.BROWN),
        (100, ChocoboColor.GREEN),
    ),
    (ChocoboColor.BROWN, ChocoboColor.BROWN): (
        (88, ChocoboColor.BROWN),
        (96, ChocoboColor.YELLOW),
        (100, ChocoboColor.RED),
    ),
    (ChocoboColor.LIGHT_BLUE, ChocoboColor.LIGHT_BLUE): (
        (88, ChocoboColor.LIGHT_BLUE),
        (96, ChocoboColor.BLUE),
        (100, ChocoboColor.YELLOW),
    ),
    (ChocoboColor.BLUE, ChocoboColor.BLUE): (
        (88, ChocoboColor.BLUE),
        (96, ChocoboColor.LIGHT_BLUE),
        (100, ChocoboColor.WHITE),
    ),
    (ChocoboColor.LIGHT_PURPLE, ChocoboColor.LIGHT_PURPLE): (
        (88, ChocoboColor.LIGHT_PURPLE),
        (96, ChocoboColor.BLUE),
        (100, ChocoboColor.WHITE),
    ),
    (ChocoboColor.GREEN, ChocoboColor.GREEN): (
        (88, ChocoboColor.GREEN),
        (96, ChocoboColor.YELLOW),
        (100, ChocoboColor.LIGHT_BLUE),
    ),
    (ChocoboColor.RED, ChocoboColor.RED): (
        (88, ChocoboColor.RED),
        (96, ChocoboColor.BROWN),
        (100, ChocoboColor.LIGHT_PURPLE),
    ),
    (ChocoboColor.WHITE, ChocoboColor.WHITE): (
        (90, ChocoboColor.WHITE),
        (97, ChocoboColor.YELLOW),
        (100, ChocoboColor.LIGHT_PURPLE),
    ),
    (ChocoboColor.GREY, ChocoboColor.GREY): (
        (88, ChocoboColor.GREY),
        (96, ChocoboColor.RED),
        (100, ChocoboColor.LIGHT_PURPLE),
    ),
    # Mixed-color combos — color-theory mixing
    (ChocoboColor.YELLOW, ChocoboColor.BROWN): (
        (50, ChocoboColor.YELLOW),
        (90, ChocoboColor.BROWN),
        (100, ChocoboColor.RED),
    ),
    (ChocoboColor.YELLOW, ChocoboColor.RED): (
        (45, ChocoboColor.RED),
        (80, ChocoboColor.YELLOW),
        (100, ChocoboColor.BROWN),
    ),
    (ChocoboColor.YELLOW, ChocoboColor.GREEN): (
        (50, ChocoboColor.GREEN),
        (88, ChocoboColor.YELLOW),
        (100, ChocoboColor.LIGHT_BLUE),
    ),
    (ChocoboColor.BLUE, ChocoboColor.LIGHT_BLUE): (
        (60, ChocoboColor.BLUE),
        (95, ChocoboColor.LIGHT_BLUE),
        (100, ChocoboColor.WHITE),
    ),
    (ChocoboColor.LIGHT_BLUE, ChocoboColor.GREEN): (
        (50, ChocoboColor.LIGHT_BLUE),
        (88, ChocoboColor.GREEN),
        (100, ChocoboColor.YELLOW),
    ),
    (ChocoboColor.RED, ChocoboColor.LIGHT_PURPLE): (
        (45, ChocoboColor.RED),
        (88, ChocoboColor.LIGHT_PURPLE),
        (100, ChocoboColor.WHITE),
    ),
    (ChocoboColor.RED, ChocoboColor.BROWN): (
        (50, ChocoboColor.RED),
        (90, ChocoboColor.BROWN),
        (100, ChocoboColor.YELLOW),
    ),
    (ChocoboColor.GREEN, ChocoboColor.LIGHT_PURPLE): (
        (45, ChocoboColor.GREEN),
        (85, ChocoboColor.LIGHT_PURPLE),
        (100, ChocoboColor.YELLOW),
    ),
    (ChocoboColor.WHITE, ChocoboColor.YELLOW): (
        (50, ChocoboColor.YELLOW),
        (88, ChocoboColor.WHITE),
        (100, ChocoboColor.LIGHT_PURPLE),
    ),
    (ChocoboColor.WHITE, ChocoboColor.LIGHT_BLUE): (
        (45, ChocoboColor.LIGHT_BLUE),
        (85, ChocoboColor.WHITE),
        (100, ChocoboColor.BLUE),
    ),
    (ChocoboColor.GREY, ChocoboColor.RED): (
        (50, ChocoboColor.GREY),
        (90, ChocoboColor.RED),
        (100, ChocoboColor.LIGHT_PURPLE),
    ),
    (ChocoboColor.GREY, ChocoboColor.LIGHT_PURPLE): (
        (50, ChocoboColor.GREY),
        (88, ChocoboColor.LIGHT_PURPLE),
        (100, ChocoboColor.WHITE),
    ),
    (ChocoboColor.GREY, ChocoboColor.BROWN): (
        (55, ChocoboColor.GREY),
        (92, ChocoboColor.BROWN),
        (100, ChocoboColor.RED),
    ),
}


_DEFAULT_RECIPE_BASE: tuple[tuple[str, int], ...] = (
    (_OZ_ROOT, 3),
    (_FOREST_GRAIN, 5),
    (_FOREST_FEATHER, 1),
)


_RAINBOW_THRESHOLD_PER_MILLION = 1


def _norm_pair(
    a: ChocoboColor, b: ChocoboColor,
) -> tuple[ChocoboColor, ChocoboColor]:
    # Symmetric lookup — sort by enum value for stable key
    if a.value <= b.value:
        return (a, b)
    return (b, a)


@dataclasses.dataclass(frozen=True)
class BreedRollResult:
    accepted: bool
    egg_color: t.Optional[ChocoboColor] = None
    is_rainbow: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ChocoboBreedMatrix:
    def roll(
        self, *, male_color: ChocoboColor,
        female_color: ChocoboColor,
        combined_level: int,
        combined_skill: int,
        roll_pct_color: int,
        roll_pct_rainbow: int,
    ) -> BreedRollResult:
        if (
            male_color == ChocoboColor.RAINBOW
            or female_color == ChocoboColor.RAINBOW
        ):
            return BreedRollResult(
                False, reason="rainbow chocobos cannot breed",
            )
        if combined_level <= 0:
            return BreedRollResult(
                False, reason="non-positive combined level",
            )
        if combined_skill < 0:
            return BreedRollResult(
                False, reason="negative combined skill",
            )
        if not (0 <= roll_pct_color <= 100):
            return BreedRollResult(
                False, reason="invalid color roll",
            )
        if not (0 <= roll_pct_rainbow <= 999_999):
            return BreedRollResult(
                False, reason="invalid rainbow roll (0..999_999)",
            )
        # 1 in 1_000_000 rainbow proc
        if roll_pct_rainbow < _RAINBOW_THRESHOLD_PER_MILLION:
            return BreedRollResult(
                accepted=True,
                egg_color=ChocoboColor.RAINBOW,
                is_rainbow=True,
            )
        # Look up both orderings to absorb dict-key vs norm_pair
        # mismatches transparently
        dist = (
            _BASE_DIST.get((male_color, female_color))
            or _BASE_DIST.get((female_color, male_color))
        )
        if dist is None:
            # Unknown pair — fall back to MOTHER's color dominant
            dist = (
                (60, female_color),
                (95, male_color),
                (100, ChocoboColor.YELLOW),
            )
        # Combined level + skill widens the colored-variant slice:
        # at combined_level >= 200 and skill >= 1000, shift the
        # FIRST threshold down by 8 points (so ~12% more variants).
        shift = 0
        if combined_level >= 200:
            shift += 4
        if combined_skill >= 1000:
            shift += 4
        # Apply shift only to the FIRST (dominant) threshold,
        # capped so it never inverts ordering.
        adjusted: list[tuple[int, ChocoboColor]] = []
        for idx, (ceil, color) in enumerate(dist):
            if idx == 0:
                ceil = max(50, ceil - shift)
            adjusted.append((ceil, color))
        for ceil, color in adjusted:
            if roll_pct_color < ceil:
                return BreedRollResult(
                    accepted=True,
                    egg_color=color,
                )
        return BreedRollResult(
            accepted=True,
            egg_color=adjusted[-1][1],
        )

    def recipe_for(
        self, *, male_color: ChocoboColor,
        female_color: ChocoboColor,
    ) -> t.Optional[BreedRecipe]:
        if (
            male_color == ChocoboColor.RAINBOW
            or female_color == ChocoboColor.RAINBOW
        ):
            return None
        # Same-color recipes use the base. Cross-color recipes add
        # one signature item from each parent's element-region.
        if male_color == female_color:
            return BreedRecipe(
                items=_DEFAULT_RECIPE_BASE,
                gil_cost=50_000,
            )
        signature_for: dict[ChocoboColor, str] = {
            ChocoboColor.YELLOW: _FOREST_GRAIN,
            ChocoboColor.BROWN: _QUADAV_FOSSIL,
            ChocoboColor.LIGHT_BLUE: _LAMIA_PEARL,
            ChocoboColor.BLUE: _LAMIA_PEARL,
            ChocoboColor.LIGHT_PURPLE: _OZ_ROOT,
            ChocoboColor.GREEN: _FOREST_FEATHER,
            ChocoboColor.RED: _HALV_BLOOD,
            ChocoboColor.WHITE: _FOREST_FEATHER,
            ChocoboColor.GREY: _OZ_ROOT,
        }
        items = list(_DEFAULT_RECIPE_BASE) + [
            (signature_for[male_color], 2),
            (signature_for[female_color], 2),
        ]
        # Rare R/EX feather extra cost for grey/white pairs
        if {male_color, female_color} & {
            ChocoboColor.WHITE, ChocoboColor.GREY,
        }:
            items.append((_REX_FEATHER, 1))
        return BreedRecipe(
            items=tuple(items),
            gil_cost=200_000,
        )


__all__ = [
    "BreedRecipe", "BreedRollResult",
    "ChocoboBreedMatrix",
]
