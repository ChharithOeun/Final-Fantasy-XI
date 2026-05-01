"""Siege + Campaign — macro-warfare layer.

Per SIEGE_CAMPAIGN.md: beastmen periodically raid nations, and
nations deploy military NPCs to occupied zones based on weekly zone
rankings. Both halves give non-player entities (mobs, NMs, military
NPCs) real XP routes. The world is alive even when no players are
online.

Two halves:
    Siege - per-hour rolls for beastman raids on nations; composition
            scales with vulnerability; rewards on defense / scars on
            failure.
    Campaign - weekly per-zone classification (stable / contested /
            beastman_dominant) drives military NPC deployment per
            nation. Military NPCs level up via cross-race kills; on
            death they respawn after 8 hours.

Public surface:
    ZoneStatus, ZoneMetrics
    ZoneRankingComputer
    MilitaryDeploymentPlanner, DeploymentRecommendation
    MilitaryNpcManager, MilitaryNpcSnapshot
    SiegeProbabilityCalculator
    RaidSize, RaidComposition, RaidComposer
    RaidRewardDistributor, RaidReward
    NATION_MILITARY_COMPOSITIONS
"""
from .deployment import (
    DeploymentRecommendation,
    MilitaryDeploymentPlanner,
    NATION_MILITARY_COMPOSITIONS,
    PER_NATION_DEPLOYMENT_CAP,
)
from .military_npc import (
    MILITARY_RESPAWN_SECONDS,
    MilitaryNpcManager,
    MilitaryNpcSnapshot,
)
from .raid import (
    DEFENSE_MEDAL_BASE,
    RaidComposer,
    RaidComposition,
    RaidReward,
    RaidRewardDistributor,
    RaidSize,
)
from .siege_probability import (
    BASE_HOURLY_RATE,
    SiegeProbabilityCalculator,
)
from .zone_rankings import (
    ZoneMetrics,
    ZoneRankingComputer,
    ZoneStatus,
)

__all__ = [
    "ZoneStatus",
    "ZoneMetrics",
    "ZoneRankingComputer",
    "DeploymentRecommendation",
    "MilitaryDeploymentPlanner",
    "NATION_MILITARY_COMPOSITIONS",
    "PER_NATION_DEPLOYMENT_CAP",
    "MilitaryNpcManager",
    "MilitaryNpcSnapshot",
    "MILITARY_RESPAWN_SECONDS",
    "SiegeProbabilityCalculator",
    "BASE_HOURLY_RATE",
    "RaidSize",
    "RaidComposition",
    "RaidComposer",
    "RaidRewardDistributor",
    "RaidReward",
    "DEFENSE_MEDAL_BASE",
]
