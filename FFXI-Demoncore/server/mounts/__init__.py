"""Mount engine — speed without safety.

Per MOUNTS.md the user spec: 'A mount makes you fast. Not invincible.'
A mounted player has TWO HP pools: their own and the mount's. Damage
hits the mount first, spills onto the player when the mount dies.

This module owns:
    - Mount types + per-level stat scaling (mount.py)
    - Damage absorption + dismount-on-zero spillover (damage_absorption.py)
    - Mounted action modifiers (combat_modifiers.py)
    - Mount XP progression + 3-deaths-in-24h permadeath (progression.py)
    - Aggro range modifiers per sense type (aggro_modifier.py)

Public surface:
    MountType, MountSnapshot
    spawn_chocobo, stats_for_level
    DamageAbsorption, AbsorptionResult
    MountedActionModifiers
    MountProgression, MOUNT_LOSS_THRESHOLD, MOUNT_LOSS_WINDOW_SECONDS
    MountAggroModifier, AggroSense
"""
from .aggro_modifier import (
    AggroSense,
    MountAggroModifier,
)
from .combat_modifiers import (
    AUTO_ATTACK_DMG_MULT,
    CAST_TIME_MULT,
    MountedActionModifiers,
    WEAPON_SKILL_TP_COST_MULT,
)
from .damage_absorption import (
    AbsorptionResult,
    DamageAbsorption,
)
from .mount import (
    MountSnapshot,
    MountType,
    spawn_chocobo,
    stats_for_level,
)
from .progression import (
    MOUNT_LOSS_THRESHOLD,
    MOUNT_LOSS_WINDOW_SECONDS,
    MountProgression,
    XP_PER_HOSTILE_ZONE_RIDE,
    XP_PER_RACE_WIN,
)

__all__ = [
    "MountType",
    "MountSnapshot",
    "spawn_chocobo",
    "stats_for_level",
    "DamageAbsorption",
    "AbsorptionResult",
    "MountedActionModifiers",
    "AUTO_ATTACK_DMG_MULT",
    "CAST_TIME_MULT",
    "WEAPON_SKILL_TP_COST_MULT",
    "MountProgression",
    "MOUNT_LOSS_THRESHOLD",
    "MOUNT_LOSS_WINDOW_SECONDS",
    "XP_PER_HOSTILE_ZONE_RIDE",
    "XP_PER_RACE_WIN",
    "MountAggroModifier",
    "AggroSense",
]
