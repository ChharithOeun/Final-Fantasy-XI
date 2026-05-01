"""Aggro range modifiers for mounted players.

Per MOUNTS.md aggro mechanics:
    Sound-aggro mobs (skeletons, ghosts) hear hooves at 1.5x range
    Sight-aggro mobs (goblins, orcs) see mounted players at the
        same range as unmounted (mount doesn't help silhouette)
    True-sight mobs (some NMs) ignore mount visibility entirely
    Magic-aggro mobs (undead) see mana auras; mount HP doesn't
        shield mana signature
"""
from __future__ import annotations

import enum


class AggroSense(str, enum.Enum):
    SOUND = "sound"             # skeletons / ghosts
    SIGHT = "sight"             # goblins / orcs
    TRUE_SIGHT = "true_sight"   # NMs that ignore visibility
    MAGIC = "magic"             # undead reading mana auras
    SCENT = "scent"             # tracking dogs / wolves (canonical aggro)


# Multipliers applied to baseline aggro range when the player is mounted.
SOUND_MOUNT_MULTIPLIER = 1.5    # hooves
SIGHT_MOUNT_MULTIPLIER = 1.0    # mount doesn't help silhouette-wise
TRUE_SIGHT_MOUNT_MULTIPLIER = 1.0
MAGIC_MOUNT_MULTIPLIER = 1.0    # mana signature unshielded
SCENT_MOUNT_MULTIPLIER = 1.2    # mount adds scent footprint


class MountAggroModifier:
    """Pure-function lookup for aggro range adjustments while mounted."""

    @staticmethod
    def aggro_range_multiplier(sense: AggroSense,
                                  *,
                                  is_mounted: bool) -> float:
        if not is_mounted:
            return 1.0
        return {
            AggroSense.SOUND: SOUND_MOUNT_MULTIPLIER,
            AggroSense.SIGHT: SIGHT_MOUNT_MULTIPLIER,
            AggroSense.TRUE_SIGHT: TRUE_SIGHT_MOUNT_MULTIPLIER,
            AggroSense.MAGIC: MAGIC_MOUNT_MULTIPLIER,
            AggroSense.SCENT: SCENT_MOUNT_MULTIPLIER,
        }.get(sense, 1.0)

    @staticmethod
    def effective_aggro_range(*,
                                base_range_cm: float,
                                sense: AggroSense,
                                is_mounted: bool) -> float:
        return base_range_cm * MountAggroModifier.aggro_range_multiplier(
            sense, is_mounted=is_mounted)
