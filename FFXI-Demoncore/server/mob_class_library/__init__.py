"""13-family bestiary catalog from MOB_CLASS_LIBRARY.md.

The world is populated by ~80 mob classes split into 13 families.
Each family declares element affinity (per MOB_RESISTANCES.md),
voice tone (per AUDIBLE_CALLOUTS.md), RL-policy archetype (per
AI_WORLD_DENSITY.md Tier 4). Sub-variants spread level 1-90 with
distinct roles and signature attacks.

Boss authors pick a sub-variant, customize per BOSS_GRAMMAR.md,
ship in 4-6 hours.

Module layout:
    families.py      - 13 MobFamily entries with affinity rules
    sub_variants.py  - 30+ SubVariant rows with roles + signatures
    catalog.py       - query API (level bands / roles / healers /
                          encounter_composition)
"""
from .catalog import (
    boss_grade_variants,
    encounter_composition,
    families_strong_vs,
    families_weak_to,
    families_with_affinity,
    healers_for_family,
    variants_in_level_band,
    variants_with_role,
)
from .families import (
    FAMILIES,
    Element,
    FamilyId,
    MobFamily,
    all_families,
    family_count,
    get_family,
)
from .sub_variants import (
    SUB_VARIANTS,
    MobRole,
    SubVariant,
    all_sub_variants,
    get_sub_variant,
    sub_variant_count,
    variants_in_family,
)

__all__ = [
    # families
    "Element", "FamilyId", "MobFamily", "FAMILIES",
    "get_family", "all_families", "family_count",
    # sub_variants
    "MobRole", "SubVariant", "SUB_VARIANTS",
    "get_sub_variant", "variants_in_family",
    "all_sub_variants", "sub_variant_count",
    # catalog
    "families_weak_to", "families_strong_vs",
    "families_with_affinity",
    "variants_in_level_band", "variants_with_role",
    "healers_for_family", "boss_grade_variants",
    "encounter_composition",
]
