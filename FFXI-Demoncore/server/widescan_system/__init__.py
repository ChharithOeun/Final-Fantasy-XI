"""Widescan system — minimap right-click reveals nearby mobs.

Right-clicking the minimap triggers WIDESCAN. Every job gets a
baseline 100-yalm scan radius around the caster — but mobs are
only listed, not pinned to the live minimap. Specialist jobs
extend the radius:

  RNG    ZONEWIDE              (the Ranger flag)
  BST    500 yalms
  THF    300 yalms

Subjobs add ON TOP of the main:
  Sub RNG  +200 yalms (1st sub) ; +100 (2nd sub)
  Sub BST  +100 yalms (1st sub) ; +50  (2nd sub)
  Sub THF  +50  yalms (1st sub) ; +25  (2nd sub)

Two-subjob stacking: tertiary_subjob system already lets a
player carry a primary sub + a secondary sub at half level. The
widescan bonus from the secondary is HALF the primary bonus
(rounded), as encoded above.

Combinatorial example from the user:
  RDM/RNG/THF = 100 + 200 + 25 = 325 yalms.

Special handling:
* Main RNG yields zonewide regardless of subs (no further bonus
  needed — the whole zone is already revealed).
* Stacked subs of the same kind don't double-up: RNG/RNG/RNG
  resolves as zonewide once.

Public surface
--------------
    JobKind enum
    WidescanResult dataclass
    WidescanSystem
        .compute_radius(main_job, sub_job, secondary_sub_job)
        .scan(player_id, main_job, sub_job, secondary, mobs_in_zone,
              caster_x, caster_y, zone_id) -> WidescanResult
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Baselines.
BASE_SCAN_RADIUS = 100
THF_MAIN_BONUS = 200            # 100 -> 300
BST_MAIN_BONUS = 400            # 100 -> 500
RNG_MAIN_ZONEWIDE = True

# Subjob bonuses (1st sub -> 2nd sub).
RNG_SUB_PRIMARY = 200
RNG_SUB_SECONDARY = 100
BST_SUB_PRIMARY = 100
BST_SUB_SECONDARY = 50
THF_SUB_PRIMARY = 50
THF_SUB_SECONDARY = 25


# Sentinel for zonewide
ZONEWIDE = -1


class JobKind(str, enum.Enum):
    WAR = "war"
    MNK = "mnk"
    WHM = "whm"
    BLM = "blm"
    RDM = "rdm"
    THF = "thf"
    PLD = "pld"
    DRK = "drk"
    BST = "bst"
    BRD = "brd"
    RNG = "rng"
    SAM = "sam"
    NIN = "nin"
    DRG = "drg"
    SMN = "smn"
    BLU = "blu"
    COR = "cor"
    PUP = "pup"
    DNC = "dnc"
    SCH = "sch"
    GEO = "geo"
    RUN = "run"
    NONE = "none"


# Lookup tables for sub bonuses.
_SUB_PRIMARY_BONUS: dict[JobKind, int] = {
    JobKind.RNG: RNG_SUB_PRIMARY,
    JobKind.BST: BST_SUB_PRIMARY,
    JobKind.THF: THF_SUB_PRIMARY,
}
_SUB_SECONDARY_BONUS: dict[JobKind, int] = {
    JobKind.RNG: RNG_SUB_SECONDARY,
    JobKind.BST: BST_SUB_SECONDARY,
    JobKind.THF: THF_SUB_SECONDARY,
}


@dataclasses.dataclass(frozen=True)
class MobScanRecord:
    mob_id: str
    label: str
    x: float
    y: float
    z: float = 0.0


@dataclasses.dataclass(frozen=True)
class WidescanResult:
    player_id: str
    zone_id: str
    radius: int                 # yalms; ZONEWIDE = -1
    is_zonewide: bool
    revealed_mobs: tuple[MobScanRecord, ...]


@dataclasses.dataclass
class WidescanSystem:
    base_radius: int = BASE_SCAN_RADIUS

    def compute_radius(
        self, *, main_job: JobKind,
        sub_job: JobKind = JobKind.NONE,
        secondary_sub_job: JobKind = JobKind.NONE,
    ) -> int:
        # Main RNG → zonewide regardless
        if main_job == JobKind.RNG and RNG_MAIN_ZONEWIDE:
            return ZONEWIDE
        # Main job baseline + main-class bonus
        radius = self.base_radius
        if main_job == JobKind.BST:
            radius += BST_MAIN_BONUS
        elif main_job == JobKind.THF:
            radius += THF_MAIN_BONUS
        # Sub bonuses (sub != main, otherwise duplicate)
        if (
            sub_job != JobKind.NONE
            and sub_job != main_job
        ):
            radius += _SUB_PRIMARY_BONUS.get(sub_job, 0)
        if (
            secondary_sub_job != JobKind.NONE
            and secondary_sub_job != main_job
            and secondary_sub_job != sub_job
        ):
            radius += _SUB_SECONDARY_BONUS.get(
                secondary_sub_job, 0,
            )
        # Sub RNG never escalates to zonewide — only main RNG
        # does. (Spec: the bonus is +200/+100 yalms.)
        return radius

    def scan(
        self, *, player_id: str, zone_id: str,
        caster_x: float, caster_y: float,
        caster_z: float = 0.0,
        main_job: JobKind = JobKind.WAR,
        sub_job: JobKind = JobKind.NONE,
        secondary_sub_job: JobKind = JobKind.NONE,
        mobs_in_zone: tuple[MobScanRecord, ...] = (),
    ) -> WidescanResult:
        radius = self.compute_radius(
            main_job=main_job,
            sub_job=sub_job,
            secondary_sub_job=secondary_sub_job,
        )
        is_zonewide = radius == ZONEWIDE
        if is_zonewide:
            revealed = mobs_in_zone
        else:
            out: list[MobScanRecord] = []
            for m in mobs_in_zone:
                dx = m.x - caster_x
                dy = m.y - caster_y
                dz = m.z - caster_z
                dist = math.sqrt(
                    dx * dx + dy * dy + dz * dz,
                )
                if dist <= radius:
                    out.append(m)
            revealed = tuple(out)
        return WidescanResult(
            player_id=player_id, zone_id=zone_id,
            radius=radius, is_zonewide=is_zonewide,
            revealed_mobs=revealed,
        )


__all__ = [
    "BASE_SCAN_RADIUS",
    "THF_MAIN_BONUS", "BST_MAIN_BONUS",
    "RNG_MAIN_ZONEWIDE",
    "RNG_SUB_PRIMARY", "RNG_SUB_SECONDARY",
    "BST_SUB_PRIMARY", "BST_SUB_SECONDARY",
    "THF_SUB_PRIMARY", "THF_SUB_SECONDARY",
    "ZONEWIDE",
    "JobKind", "MobScanRecord", "WidescanResult",
    "WidescanSystem",
]
