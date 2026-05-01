"""Cavalry stance toggle + weapon-fit modifiers.

Per the user spec: at level 75+, players who raised their own mount
or tamed a wild monster can enter CAVALRY stance — full cavalry
combat instead of the reduced-action TRANSIT mode.

TRANSIT: existing mount modifiers (auto 0.5x, cast 1.5x, WS TP 1.25x)
CAVALRY: full cavalry actions, weapon-fit-aware bonuses, no penalty
          on auto-attack damage but still no 2hr / no stealth.

Weapon fit (cavalry historicity):
    Lance / polearm        : +20% (canonical cavalry weapon)
    One-handed sword       : +5%
    Bow / crossbow         : +15% (mounted archer)
    Two-handed sword       : -10% (unwieldy from horseback)
    Two-handed axe / scythe: -15%
    Hand-to-hand           : -25% (you can't punch from a saddle)
    Staff                  : -10% (hard to channel while balancing)
"""
from __future__ import annotations

import enum
import typing as t


CAVALRY_UNLOCK_LEVEL = 75   # rider level required to enter cavalry stance
CAVALRY_MOUNT_LEVEL = 75    # mount level required as well


class CavalryStance(str, enum.Enum):
    """Mounted combat stance."""
    TRANSIT = "transit"          # default reduced-combat mode
    CAVALRY = "cavalry"          # full mounted combat at lvl 75+


def can_enter_cavalry_stance(*,
                                rider_level: int,
                                mount_level: int,
                                mount_is_alive: bool,
                                mount_is_lost: bool = False) -> bool:
    """Both rider and mount must be at lvl 75+; mount must be alive
    and not permanently lost."""
    if not mount_is_alive or mount_is_lost:
        return False
    if rider_level < CAVALRY_UNLOCK_LEVEL:
        return False
    if mount_level < CAVALRY_MOUNT_LEVEL:
        return False
    return True


# Per-weapon-class fit multiplier (1.0 = neutral)
WEAPON_FIT_TABLE: dict[str, float] = {
    "lance":             1.20,
    "polearm":           1.20,
    "one_handed_sword":  1.05,
    "scimitar":          1.05,
    "bow":               1.15,
    "crossbow":          1.15,
    "marksmanship":      1.15,
    "two_handed_sword":  0.90,
    "great_sword":       0.90,
    "great_axe":         0.85,
    "great_scythe":      0.85,
    "hand_to_hand":      0.75,
    "fists":             0.75,
    "staff":             0.90,
}


def weapon_fit_multiplier(weapon_class: str) -> float:
    """Cavalry damage/effectiveness multiplier per weapon class.
    Unknown weapon classes return 1.0 (neutral)."""
    return WEAPON_FIT_TABLE.get(weapon_class.lower(), 1.0)
