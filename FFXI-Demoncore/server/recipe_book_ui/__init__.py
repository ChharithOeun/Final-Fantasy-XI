"""Recipe book UI — per-player recipe discovery + search.

A player's recipe book accumulates DISCOVERED recipes as they
synthesize successful crafts. Each entry knows the craft, the
required skill level, the inputs, and the result. The book lets
the player:
  * search by name substring
  * filter by craft (smithing, alchemy, woodworking, etc.)
  * filter by craftable-now (have all materials)
  * see missing materials per recipe

Distinct from server/crafting (the synthesis engine itself)
and server/recipe_data (the static recipe catalog). This is
the player-facing INDEX.

Public surface
--------------
    CraftKind enum
    Recipe dataclass
    RecipeEntry dataclass
    SearchHit dataclass
    RecipeBookUI
        .register_recipe(recipe)
        .discover(player_id, recipe_id)
        .update_inventory(player_id, item -> qty)
        .search(player_id, query, ...) -> tuple[SearchHit]
        .missing_for(player_id, recipe_id) -> dict[item, qty]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CraftKind(str, enum.Enum):
    SMITHING = "smithing"
    GOLDSMITHING = "goldsmithing"
    LEATHERCRAFT = "leathercraft"
    BONECRAFT = "bonecraft"
    ALCHEMY = "alchemy"
    CLOTHCRAFT = "clothcraft"
    WOODWORKING = "woodworking"
    COOKING = "cooking"
    FISHING = "fishing"


@dataclasses.dataclass(frozen=True)
class Recipe:
    recipe_id: str
    label: str
    craft: CraftKind
    skill_required: int
    inputs: t.Mapping[str, int]      # item_id -> qty
    output_item_id: str
    output_qty: int = 1


@dataclasses.dataclass(frozen=True)
class RecipeEntry:
    recipe_id: str
    discovered_at_seconds: float
    times_synthesized: int


@dataclasses.dataclass(frozen=True)
class SearchHit:
    recipe_id: str
    label: str
    craft: CraftKind
    skill_required: int
    have_materials: bool
    missing: t.Mapping[str, int]
    times_synthesized: int


@dataclasses.dataclass
class _PlayerBook:
    player_id: str
    discovered: dict[str, RecipeEntry] = dataclasses.field(
        default_factory=dict,
    )
    inventory: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class RecipeBookUI:
    _recipes: dict[str, Recipe] = dataclasses.field(
        default_factory=dict,
    )
    _books: dict[str, _PlayerBook] = dataclasses.field(
        default_factory=dict,
    )

    def register_recipe(
        self, *, recipe: Recipe,
    ) -> bool:
        if recipe.recipe_id in self._recipes:
            return False
        if not recipe.inputs:
            return False
        if recipe.output_qty <= 0:
            return False
        self._recipes[recipe.recipe_id] = recipe
        return True

    def _book(self, player_id: str) -> _PlayerBook:
        b = self._books.get(player_id)
        if b is None:
            b = _PlayerBook(player_id=player_id)
            self._books[player_id] = b
        return b

    def discover(
        self, *, player_id: str, recipe_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        if recipe_id not in self._recipes:
            return False
        b = self._book(player_id)
        if recipe_id in b.discovered:
            entry = b.discovered[recipe_id]
            b.discovered[recipe_id] = RecipeEntry(
                recipe_id=recipe_id,
                discovered_at_seconds=(
                    entry.discovered_at_seconds
                ),
                times_synthesized=(
                    entry.times_synthesized + 1
                ),
            )
        else:
            b.discovered[recipe_id] = RecipeEntry(
                recipe_id=recipe_id,
                discovered_at_seconds=now_seconds,
                times_synthesized=1,
            )
        return True

    def update_inventory(
        self, *, player_id: str,
        item_qty: t.Mapping[str, int],
    ) -> bool:
        b = self._book(player_id)
        for item, qty in dict(item_qty).items():
            if qty <= 0:
                b.inventory.pop(item, None)
            else:
                b.inventory[item] = qty
        return True

    def missing_for(
        self, *, player_id: str, recipe_id: str,
    ) -> t.Optional[dict[str, int]]:
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            return None
        b = self._books.get(player_id)
        inv = b.inventory if b is not None else {}
        out: dict[str, int] = {}
        for item, need in recipe.inputs.items():
            have = inv.get(item, 0)
            if have < need:
                out[item] = need - have
        return out

    def discovered_for(
        self, *, player_id: str,
    ) -> tuple[RecipeEntry, ...]:
        b = self._books.get(player_id)
        if b is None:
            return ()
        return tuple(b.discovered.values())

    def search(
        self, *, player_id: str,
        query: str = "",
        craft: t.Optional[CraftKind] = None,
        craftable_now: bool = False,
        max_skill: t.Optional[int] = None,
        max_results: int = 200,
    ) -> tuple[SearchHit, ...]:
        b = self._books.get(player_id)
        if b is None:
            return ()
        q = query.lower() if query else ""
        out: list[SearchHit] = []
        for rid, entry in b.discovered.items():
            recipe = self._recipes.get(rid)
            if recipe is None:
                continue
            if (
                craft is not None
                and recipe.craft != craft
            ):
                continue
            if (
                max_skill is not None
                and recipe.skill_required > max_skill
            ):
                continue
            if q and q not in recipe.label.lower():
                continue
            missing = self.missing_for(
                player_id=player_id, recipe_id=rid,
            ) or {}
            have_all = not missing
            if craftable_now and not have_all:
                continue
            out.append(SearchHit(
                recipe_id=rid,
                label=recipe.label,
                craft=recipe.craft,
                skill_required=recipe.skill_required,
                have_materials=have_all,
                missing=missing,
                times_synthesized=entry.times_synthesized,
            ))
        out.sort(
            key=lambda h: (
                h.craft.value, h.skill_required, h.recipe_id,
            ),
        )
        return tuple(out[:max_results])

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "CraftKind", "Recipe", "RecipeEntry", "SearchHit",
    "RecipeBookUI",
]
