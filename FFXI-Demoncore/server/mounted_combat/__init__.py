"""Mounted combat — cavalry stance, mount equipment, monster taming.

Per the user direction following mounts: now that mounts no longer
provide immunity from aggro/damage, mounted combat itself becomes
a real gameplay axis. At level 75+ players who raised their own
mount (or tamed a wild monster) can switch to CAVALRY stance and
fight from horseback like a real cavalry unit.

Three pieces:
    - cavalry_actions.py  — Charge / Lance / Trample / Rear Kick catalog
                              + per-action requirements
    - mount_equipment.py  — Barding / Saddle / Headgear / Saddlebags
                              with weight + stats + extra storage
    - monster_taming.py   — Wild mount catalog (wolf/dhalmel/raptor/
                              tiger/buffalo) + tame difficulty
    - combat_stance.py    — TRANSIT vs CAVALRY toggle; cavalry unlock
                              check; weapon-fit modifiers (lance/bow
                              cavalry bonus, greataxe penalty)

Public surface:
    CavalryStance, can_enter_cavalry_stance
    CavalryAction, CAVALRY_CATALOG, resolve_cavalry_action
    MountEquipmentSlot, MountEquipment, MountEquipmentLoadout
    SAMPLE_BARDINGS, SAMPLE_SADDLES, SAMPLE_HEADGEAR, SAMPLE_SADDLEBAGS
    TameableMonster, WILD_MOUNTS, attempt_tame, TameResult
    weapon_fit_multiplier, CAVALRY_UNLOCK_LEVEL, TAME_THRESHOLD_HP_PCT
"""
from .cavalry_actions import (
    CAVALRY_CATALOG,
    CavalryAction,
    CavalryActionResult,
    resolve_cavalry_action,
)
from .combat_stance import (
    CAVALRY_UNLOCK_LEVEL,
    CavalryStance,
    can_enter_cavalry_stance,
    weapon_fit_multiplier,
)
from .monster_taming import (
    TAME_THRESHOLD_HP_PCT,
    TameResult,
    TameableMonster,
    WILD_MOUNTS,
    attempt_tame,
)
from .mount_equipment import (
    MountEquipment,
    MountEquipmentLoadout,
    MountEquipmentSlot,
    SAMPLE_BARDINGS,
    SAMPLE_HEADGEAR,
    SAMPLE_SADDLEBAGS,
    SAMPLE_SADDLES,
)

__all__ = [
    # Stance
    "CavalryStance",
    "CAVALRY_UNLOCK_LEVEL",
    "can_enter_cavalry_stance",
    "weapon_fit_multiplier",
    # Actions
    "CavalryAction",
    "CAVALRY_CATALOG",
    "CavalryActionResult",
    "resolve_cavalry_action",
    # Equipment
    "MountEquipment",
    "MountEquipmentSlot",
    "MountEquipmentLoadout",
    "SAMPLE_BARDINGS",
    "SAMPLE_SADDLES",
    "SAMPLE_HEADGEAR",
    "SAMPLE_SADDLEBAGS",
    # Taming
    "TameableMonster",
    "WILD_MOUNTS",
    "attempt_tame",
    "TameResult",
    "TAME_THRESHOLD_HP_PCT",
]
