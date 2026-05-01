"""Fomor gear progression: the recursive purple-stat loop.

Per FOMOR_GEAR_PROGRESSION.md: every fomor wears the gear of the
player who became it. Killing the fomor rolls 3% per equipped piece;
each successful roll drops the piece **at one tier higher** than the
fomor was wearing it. Tiers cap at +V (25%% over base).

This module owns:
    - Gear template + per-piece state with lineage
    - Tier-aware stat scaling
    - The drop engine (3% per piece, anti-farming protections)
    - Spawn pool (level-band-matching zones; leveled fomors roam wider)
    - Loss conditions (fomor-vs-fomor wipes wardrobe, recursion miss
      returns piece to live world)

Public surface:
    GearTier, GearPiece, GearTemplate, GearRequirements, LineageEvent
    FomorWardrobe
    DropEngine, DropResult, KillerSnapshot
    SpawnPool
    EligibilityChecker
"""
from .drop_engine import (
    BASE_DROP_RATE,
    DAILY_DROP_LIMIT,
    DropEngine,
    DropResult,
    EligibilityChecker,
    FomorSpawnCooldownTracker,
    KillerSnapshot,
    PER_FOMOR_COOLDOWN_SECONDS,
    SESSION_DR_RATES,
)
from .lineage import (
    GearPiece,
    GearRequirements,
    GearTemplate,
    GearTier,
    HolderType,
    LineageEvent,
    scaled_stats,
)
from .spawn_pool import (
    SpawnPool,
    ZONE_LEVEL_BANDS,
)
from .wardrobe import (
    FomorWardrobe,
)

__all__ = [
    "GearTier",
    "GearPiece",
    "GearTemplate",
    "GearRequirements",
    "LineageEvent",
    "HolderType",
    "scaled_stats",
    "FomorWardrobe",
    "DropEngine",
    "DropResult",
    "KillerSnapshot",
    "EligibilityChecker",
    "FomorSpawnCooldownTracker",
    "SpawnPool",
    "ZONE_LEVEL_BANDS",
    "BASE_DROP_RATE",
    "DAILY_DROP_LIMIT",
    "PER_FOMOR_COOLDOWN_SECONDS",
    "SESSION_DR_RATES",
]
