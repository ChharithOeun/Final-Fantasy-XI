"""Crafting engine — synthesis ritual + HQ tiers + Master Synthesis LB.

Per CRAFTING_SYSTEM.md, crafters are apex social content. Repair is
the steady-state economic engine; Master Synthesis is the apex.
Composes with EQUIPMENT_WEAR (repair), PLAYER_PROGRESSION (mastery
axis), NPC_PROGRESSION (NPC crafters level too), MOOD_SYSTEM
(mood-conditioned proc tables), and AUDIBLE_CALLOUTS.

Public surface:
    Craft, CraftTier, HqTier, SynthesisOutcome
    Recipe, sample_recipe_catalog
    CraftLevels (per-character state)
    SynthesisResolver, SynthesisResult
    MasterSynthesisLB (the apex limit break)
    tier_for_level, title_for_grandmaster, reputation_cap_raise
"""
from .crafter_state import (
    CraftLevels,
    grant_xp,
    title_for_grandmaster,
    reputation_cap_raise,
)
from .crafts import (
    Craft,
    CraftTier,
    HqTier,
    SynthesisOutcome,
    GAME_DAY_SECONDS,
    tier_for_level,
)
from .master_synthesis import (
    MASTER_SYNTHESIS_MIN_HQ,
    MASTER_SYNTHESIS_SIGNED_CHANCE,
    MasterSynthesisLB,
)
from .recipes import (
    Recipe,
    sample_recipe_catalog,
)
from .synthesis import (
    HQ_BASE_TABLE,
    MOOD_MODIFIERS,
    SynthesisResolver,
    SynthesisResult,
)

__all__ = [
    "Craft",
    "CraftTier",
    "HqTier",
    "SynthesisOutcome",
    "tier_for_level",
    "GAME_DAY_SECONDS",
    "Recipe",
    "sample_recipe_catalog",
    "CraftLevels",
    "grant_xp",
    "title_for_grandmaster",
    "reputation_cap_raise",
    "SynthesisResolver",
    "SynthesisResult",
    "HQ_BASE_TABLE",
    "MOOD_MODIFIERS",
    "MasterSynthesisLB",
    "MASTER_SYNTHESIS_MIN_HQ",
    "MASTER_SYNTHESIS_SIGNED_CHANCE",
]
