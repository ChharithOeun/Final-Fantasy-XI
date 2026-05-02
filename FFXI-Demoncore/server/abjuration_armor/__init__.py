"""Abjuration armor — HQ NM-drop -> crafted armor pipeline.

Canonical loop:
* HNM drops an Abjuration (e.g. Hauberk Hide -> Adamantoise).
* Player trades the abjuration + materials to a crafter.
* Synthesis succeeds (consuming the abjuration) or fails
  (abjuration is preserved, materials may or may not be lost
   depending on craft type — kept here as preserved-only for
   simplicity).
* Output: HQ armor piece (Hauberk).

Each abjuration is one-shot per attempt. Higher craft skill
raises success rate.

Public surface
--------------
    AbjurationKind enum (HEAD/BODY/HANDS/LEGS/FEET)
    Abjuration dataclass
    ArmorRecipe dataclass
    ABJURATION_CATALOG / RECIPE_CATALOG
    synth_attempt(recipe, abjuration, materials, craft_skill, rng)
       -> SynthResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class AbjurationKind(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"


@dataclasses.dataclass(frozen=True)
class Abjuration:
    abj_id: str
    kind: AbjurationKind
    label: str


ABJURATION_CATALOG: dict[str, Abjuration] = {
    # Adamantoise (Body)
    "hauberk_hide": Abjuration(
        "hauberk_hide", AbjurationKind.BODY, "Hauberk Hide",
    ),
    # Behemoth (Body)
    "shadow_mantle_chunk": Abjuration(
        "shadow_mantle_chunk", AbjurationKind.BODY,
        "Shadow Mantle Chunk",
    ),
    # Aspidochelone (Head)
    "kabuto_blackened": Abjuration(
        "kabuto_blackened", AbjurationKind.HEAD,
        "Blackened Kabuto",
    ),
    # Fafnir (Hands)
    "fafnir_gauntlet_metal": Abjuration(
        "fafnir_gauntlet_metal", AbjurationKind.HANDS,
        "Fafnir Gauntlet Metal",
    ),
    # Nidhogg (Legs)
    "nidhogg_cuisses_chain": Abjuration(
        "nidhogg_cuisses_chain", AbjurationKind.LEGS,
        "Nidhogg Cuisses Chain",
    ),
    # Vrtra (Feet)
    "vrtra_sollerets_band": Abjuration(
        "vrtra_sollerets_band", AbjurationKind.FEET,
        "Vrtra Sollerets Band",
    ),
}


@dataclasses.dataclass(frozen=True)
class ArmorRecipe:
    recipe_id: str
    abj_id: str
    output_item_id: str
    required_materials: tuple[str, ...]
    craft_kind: str          # smithing/leathercraft/etc
    base_success_pct: int    # at minimum skill threshold
    min_craft_skill: int


RECIPE_CATALOG: dict[str, ArmorRecipe] = {
    "hauberk_recipe": ArmorRecipe(
        "hauberk_recipe", "hauberk_hide", "hauberk",
        required_materials=("steel_ingot_x4", "linen_cloth_x2"),
        craft_kind="smithing",
        base_success_pct=60, min_craft_skill=110,
    ),
    "shadow_mantle_recipe": ArmorRecipe(
        "shadow_mantle_recipe", "shadow_mantle_chunk",
        "shadow_mantle",
        required_materials=("dragon_scales_x2", "wool_cloth_x1"),
        craft_kind="leathercraft",
        base_success_pct=55, min_craft_skill=100,
    ),
    "kabuto_recipe": ArmorRecipe(
        "kabuto_recipe", "kabuto_blackened", "blackened_kabuto",
        required_materials=("wyvern_scales_x2", "darksteel_ingot_x1"),
        craft_kind="smithing",
        base_success_pct=50, min_craft_skill=120,
    ),
    "fafnir_gaunt_recipe": ArmorRecipe(
        "fafnir_gaunt_recipe", "fafnir_gauntlet_metal",
        "fafnir_gauntlets",
        required_materials=("orichalcum_ingot_x1",
                             "fiery_steel_x1"),
        craft_kind="smithing",
        base_success_pct=45, min_craft_skill=130,
    ),
}


@dataclasses.dataclass(frozen=True)
class SynthResult:
    accepted: bool
    success: bool = False
    output_item_id: t.Optional[str] = None
    abjuration_consumed: bool = False
    reason: t.Optional[str] = None


def _success_chance(recipe: ArmorRecipe, *, craft_skill: int) -> int:
    """Base chance + 1% per skill point above min, capped at 95."""
    if craft_skill < recipe.min_craft_skill:
        return 0
    delta = craft_skill - recipe.min_craft_skill
    return min(95, recipe.base_success_pct + delta)


def synth_attempt(*, recipe: ArmorRecipe,
                   abjuration_id: str,
                   materials_held: t.Iterable[str],
                   craft_skill: int,
                   rng_pool: RngPool) -> SynthResult:
    if abjuration_id != recipe.abj_id:
        return SynthResult(False, reason="abjuration mismatch")
    held = set(materials_held)
    if not all(m in held for m in recipe.required_materials):
        return SynthResult(False, reason="missing materials")
    chance = _success_chance(recipe, craft_skill=craft_skill)
    if chance == 0:
        return SynthResult(False, reason="below min craft skill")
    roll = rng_pool.randint(STREAM_LOOT_DROPS, 1, 100)
    success = roll <= chance
    return SynthResult(
        accepted=True,
        success=success,
        output_item_id=recipe.output_item_id if success else None,
        abjuration_consumed=success,   # only consumed on success
    )


__all__ = [
    "AbjurationKind",
    "Abjuration", "ABJURATION_CATALOG",
    "ArmorRecipe", "RECIPE_CATALOG",
    "SynthResult", "synth_attempt",
]
