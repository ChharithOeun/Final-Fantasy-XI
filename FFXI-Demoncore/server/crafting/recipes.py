"""Recipe catalog — sample entries spanning all 7 crafts + universals.

Real recipe data lives in LSB items.sql + crafts.sql. This module
provides a small in-memory catalog used by the synthesis resolver
for tests and demo purposes; production wires the same Recipe shape
to the SQL loader.
"""
from __future__ import annotations

import dataclasses

from .crafts import Craft


@dataclasses.dataclass(frozen=True)
class Recipe:
    """A single craft recipe."""
    recipe_id: str
    craft: Craft
    required_level: int
    materials: dict[str, int]      # material_id -> quantity required
    output_id: str
    output_qty: int = 1
    description: str = ""


def sample_recipe_catalog() -> dict[str, Recipe]:
    """Return a small in-memory catalog covering every craft.

    Levels span the tiers (apprentice 5 -> grandmaster 95) so tests
    can exercise the level/recipe relationship without authoring
    hundreds of recipes."""
    catalog: list[Recipe] = [
        # --- Smithing ---
        Recipe(
            recipe_id="bronze_sword",
            craft=Craft.SMITHING, required_level=5,
            materials={"copper_ore": 2, "tin_ore": 1, "fire_crystal": 1},
            output_id="bronze_sword",
            description="apprentice smith starter weapon",
        ),
        Recipe(
            recipe_id="mythril_sword",
            craft=Craft.SMITHING, required_level=35,
            materials={"mythril_ore": 4, "fire_crystal": 1},
            output_id="mythril_sword",
            description="journeyman smith mid-tier blade",
        ),
        Recipe(
            recipe_id="excalibur",
            craft=Craft.SMITHING, required_level=95,
            materials={"adaman_ingot": 8, "elemental_ore": 2,
                        "ancient_crystal": 1, "lightning_crystal": 1},
            output_id="excalibur",
            description="grandmaster smith mythic-tier",
        ),

        # --- Goldsmithing ---
        Recipe(
            recipe_id="iron_ring",
            craft=Craft.GOLDSMITHING, required_level=10,
            materials={"iron_ingot": 1, "earth_crystal": 1},
            output_id="iron_ring",
        ),
        Recipe(
            recipe_id="ruby_amulet",
            craft=Craft.GOLDSMITHING, required_level=50,
            materials={"gold_ingot": 1, "ruby": 1, "fire_crystal": 1},
            output_id="ruby_amulet",
        ),

        # --- Leatherworking ---
        Recipe(
            recipe_id="cotton_belt",
            craft=Craft.LEATHERWORKING, required_level=8,
            materials={"cotton_thread": 2, "lightning_crystal": 1},
            output_id="cotton_belt",
        ),

        # --- Woodworking ---
        Recipe(
            recipe_id="oak_staff",
            craft=Craft.WOODWORKING, required_level=20,
            materials={"oak_lumber": 3, "wind_crystal": 1},
            output_id="oak_staff",
        ),

        # --- Cloth ---
        Recipe(
            recipe_id="silk_robe",
            craft=Craft.CLOTH, required_level=45,
            materials={"silk_thread": 6, "lightning_crystal": 1},
            output_id="silk_robe",
        ),

        # --- Alchemy ---
        Recipe(
            recipe_id="hi_potion",
            craft=Craft.ALCHEMY, required_level=30,
            materials={"sage": 1, "water_crystal": 1, "distilled_water": 1},
            output_id="hi_potion",
            output_qty=3,
        ),

        # --- Bonecraft ---
        Recipe(
            recipe_id="bone_ring",
            craft=Craft.BONECRAFT, required_level=12,
            materials={"clean_bone": 1, "earth_crystal": 1},
            output_id="bone_ring",
        ),

        # --- Cooking (universal) ---
        Recipe(
            recipe_id="meat_mithkabob",
            craft=Craft.COOKING, required_level=18,
            materials={"giant_sheep_meat": 1, "fire_crystal": 1,
                        "rolanberry": 1, "san_dorian_grape": 1},
            output_id="meat_mithkabob",
            output_qty=4,
        ),

        # --- Fishing (universal; here represented as a 'recipe' for catch) ---
        Recipe(
            recipe_id="catch_moat_carp",
            craft=Craft.FISHING, required_level=3,
            materials={"insect_paste_bait": 1},
            output_id="moat_carp",
        ),
    ]
    return {r.recipe_id: r for r in catalog}
