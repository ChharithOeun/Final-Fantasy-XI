"""Craft enum + tier brackets + HQ tier definitions.

Per CRAFTING_SYSTEM.md the seven crafts (smithing, goldsmithing,
leatherworking, woodworking, cloth, alchemy, bonecraft) plus two
universals (cooking, fishing). Each scales 0-99. Mastery is real.
"""
from __future__ import annotations

import enum


GAME_DAY_SECONDS = 24 * 3600   # for the once-per-game-day Master Synthesis


class Craft(str, enum.Enum):
    """The 7 crafts + 2 universals."""
    SMITHING = "smithing"
    GOLDSMITHING = "goldsmithing"
    LEATHERWORKING = "leatherworking"
    WOODWORKING = "woodworking"
    CLOTH = "cloth"
    ALCHEMY = "alchemy"
    BONECRAFT = "bonecraft"
    COOKING = "cooking"
    FISHING = "fishing"


class CraftTier(str, enum.Enum):
    """Per-craft mastery bracket."""
    APPRENTICE = "apprentice"      # 0-15
    JOURNEYMAN = "journeyman"      # 16-40
    ARTISAN = "artisan"            # 41-65
    MASTER = "master"              # 66-89
    GRANDMASTER = "grandmaster"    # 90-99


# Tier boundary table — each entry is (tier, max_level_in_tier)
TIER_BANDS = (
    (CraftTier.APPRENTICE, 15),
    (CraftTier.JOURNEYMAN, 40),
    (CraftTier.ARTISAN, 65),
    (CraftTier.MASTER, 89),
    (CraftTier.GRANDMASTER, 99),
)


def tier_for_level(level: int) -> CraftTier:
    """Return the tier name for a craft level 0..99."""
    if level < 0:
        return CraftTier.APPRENTICE
    for tier, max_level in TIER_BANDS:
        if level <= max_level:
            return tier
    return CraftTier.GRANDMASTER


class HqTier(enum.IntEnum):
    """High-Quality tier on a successful synth."""
    STANDARD = 0      # base recipe
    PLUS_1 = 1        # 15% standard rate
    PLUS_2 = 2        # 3% standard rate
    PLUS_3 = 3        # 0.3% standard rate, trade-bound
    PLUS_4 = 4        # signed (Master Synthesis LB only)


class SynthesisOutcome(str, enum.Enum):
    SUCCESS = "success"
    FAILED = "failed"
    REFUSED = "refused"   # furious mood: cannot craft
