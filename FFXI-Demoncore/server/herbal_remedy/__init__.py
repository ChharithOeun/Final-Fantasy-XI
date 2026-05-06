"""Herbal remedy — turn foraged herbs into useful potions.

Herbs from wild_forage become brewed potions. Each remedy
takes (herb_kind × quantity) ingredients plus boiling water
and produces a potion with a specific effect.

5 RemedyKinds, each addressing a survival channel:
    SUSTENANCE       restores hunger 50
    HYDRATION        restores thirst 50
    WARMTH_TONIC     +20 cold insulation for 30 min
    COOLING_TONIC    +20 heat insulation for 30 min
    VITALITY_DRAUGHT + 80 HP restore over 30 sec

The brewer needs a campfire (or alchemy bench), a cauldron,
and the right herbs in the right amounts.

Public surface
--------------
    RemedyKind enum
    RemedyRecipe dataclass (frozen)
    BrewedPotion dataclass (frozen)
    HerbalRemedyEngine
        .define_recipe(kind, herb_requirements, water_units)
        .brew(player_id, kind, herb_inventory,
              water_available, has_fire, brewed_at)
            -> Optional[BrewedPotion]
        .recipe_for(kind) -> Optional[RemedyRecipe]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RemedyKind(str, enum.Enum):
    SUSTENANCE = "sustenance"
    HYDRATION = "hydration"
    WARMTH_TONIC = "warmth_tonic"
    COOLING_TONIC = "cooling_tonic"
    VITALITY_DRAUGHT = "vitality_draught"


@dataclasses.dataclass(frozen=True)
class RemedyRecipe:
    kind: RemedyKind
    herb_requirements: dict[str, int]
    water_units: int


@dataclasses.dataclass(frozen=True)
class BrewedPotion:
    kind: RemedyKind
    brewed_at: int
    brewer_id: str


@dataclasses.dataclass
class HerbalRemedyEngine:
    _recipes: dict[RemedyKind, RemedyRecipe] = dataclasses.field(
        default_factory=dict,
    )

    def define_recipe(
        self, *, kind: RemedyKind,
        herb_requirements: dict[str, int],
        water_units: int,
    ) -> bool:
        if water_units < 0:
            return False
        if not herb_requirements:
            return False
        for h, q in herb_requirements.items():
            if not h or q <= 0:
                return False
        if kind in self._recipes:
            return False
        self._recipes[kind] = RemedyRecipe(
            kind=kind,
            herb_requirements=dict(herb_requirements),
            water_units=water_units,
        )
        return True

    def recipe_for(
        self, *, kind: RemedyKind,
    ) -> t.Optional[RemedyRecipe]:
        return self._recipes.get(kind)

    def brew(
        self, *, player_id: str, kind: RemedyKind,
        herb_inventory: dict[str, int],
        water_available: int,
        has_fire: bool, brewed_at: int,
    ) -> t.Optional[BrewedPotion]:
        if not player_id:
            return None
        if not has_fire:
            return None
        recipe = self._recipes.get(kind)
        if recipe is None:
            return None
        if water_available < recipe.water_units:
            return None
        # check herbs
        for herb, qty in recipe.herb_requirements.items():
            if herb_inventory.get(herb, 0) < qty:
                return None
        return BrewedPotion(
            kind=kind, brewed_at=brewed_at,
            brewer_id=player_id,
        )

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "RemedyKind", "RemedyRecipe", "BrewedPotion",
    "HerbalRemedyEngine",
]
