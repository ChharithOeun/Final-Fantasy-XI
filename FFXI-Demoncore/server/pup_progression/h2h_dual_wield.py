"""H2H dual-wield rule.

Per the user direction: 'pup master themselves are hand 2 hand,
let's make all hand 2 hand weapons a dual wield, so they have to
buy a right and left hand weapon, same for monks or warriors that
use h2h weapons'.

This module enforces the rule: any character whose main weapon is
a hand-to-hand class needs BOTH a left and a right H2H weapon
equipped to fight effectively.
"""
from __future__ import annotations

import typing as t


# Jobs that natively use H2H as a primary weapon. Per the user
# correction: only MNK / PUP / WAR / RDM / NIN can use H2H weapons.
H2H_DUAL_WIELD_JOBS = frozenset({"MNK", "PUP", "WAR", "RDM", "NIN"})

# Weapon classes considered H2H
H2H_WEAPON_CLASSES = frozenset({
    "hand_to_hand", "fists", "knuckles", "claws", "cesti",
})


def h2h_requires_dual_wield(job: str, weapon_class: str) -> bool:
    """Does this (job, weapon_class) require both hands to be filled
    with H2H weapons?

    The MNK using a staff (not H2H): no dual-wield rule.
    The MNK using fists: yes — needs left + right cesti.
    """
    if job.upper() not in H2H_DUAL_WIELD_JOBS:
        return False
    if weapon_class.lower() not in H2H_WEAPON_CLASSES:
        return False
    return True


def is_dual_wield_complete(*,
                            main_hand_class: t.Optional[str],
                            off_hand_class: t.Optional[str]) -> bool:
    """Both hands carry an H2H weapon — the dual-wield rule is satisfied."""
    if main_hand_class is None or off_hand_class is None:
        return False
    return (main_hand_class.lower() in H2H_WEAPON_CLASSES
              and off_hand_class.lower() in H2H_WEAPON_CLASSES)
