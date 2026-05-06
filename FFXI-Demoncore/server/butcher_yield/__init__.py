"""Butcher yield — what comes off the kill.

A felled beast is a pile of resources, but only if you
know how to take them out. Different butcher skill levels
yield different totals, and the wrong tool wastes the
best parts. This module turns "you killed a 14-yalm
dhalmel with a poison_tip arrow" into:

    raw_dhalmel_meat × 12
    dhalmel_hide      × 1   (ruined)
    sinew             × 4
    bone              × 8

The hide is "ruined" because the kill notes carried
ruined_hide=True (e.g. broadhead through a small target,
or arrow shaft tore the hide). Tannery_rack will refuse
ruined hides — they go straight to scrap.

Yields are deterministic given (carcass weight, kind,
butcher_skill, tool_kind, hide_status). The randomness
lives in the kill itself; once you have the carcass, the
math is fair.

Public surface
--------------
    PartKind enum  (MEAT/HIDE/SINEW/BONE/HORN/ORGAN)
    ToolKind enum
    Carcass dataclass (frozen)
    YieldBundle dataclass (frozen) — counts per part
    butcher_carcass(carcass, butcher_skill, tool) -> YieldBundle
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PartKind(str, enum.Enum):
    MEAT = "meat"
    HIDE = "hide"
    SINEW = "sinew"
    BONE = "bone"
    HORN = "horn"
    ORGAN = "organ"


class ToolKind(str, enum.Enum):
    BARE_HANDS = "bare_hands"      # awful — only meat scraps
    FLINT_KNIFE = "flint_knife"    # cheap, ok meat, no fine work
    STEEL_KNIFE = "steel_knife"    # standard
    BUTCHER_CLEAVER = "butcher_cleaver"  # best meat
    SCRIMSHAW_KIT = "scrimshaw_kit"      # specialized: bone/horn


@dataclasses.dataclass(frozen=True)
class Carcass:
    quarry_id: str           # e.g. "dhalmel"
    weight_kg: float
    has_horns: bool
    hide_intact: bool        # False if kill ruined the hide


@dataclasses.dataclass(frozen=True)
class YieldBundle:
    quarry_id: str
    meat: int
    hide: int                # always 0 or 1
    hide_ruined: bool        # if hide=0 because of damage
    sinew: int
    bone: int
    horn: int
    organ: int


# Per-tool multipliers on each part. A scrimshaw kit isn't
# good for meat, but it pulls every fragment of bone and
# horn. Bare hands gets you almost nothing.
_TOOL_FACTORS: dict[ToolKind, dict[PartKind, float]] = {
    ToolKind.BARE_HANDS: {
        PartKind.MEAT: 0.3, PartKind.HIDE: 0.0,
        PartKind.SINEW: 0.0, PartKind.BONE: 0.2,
        PartKind.HORN: 0.5, PartKind.ORGAN: 0.0,
    },
    ToolKind.FLINT_KNIFE: {
        PartKind.MEAT: 0.7, PartKind.HIDE: 0.7,
        PartKind.SINEW: 0.5, PartKind.BONE: 0.5,
        PartKind.HORN: 0.7, PartKind.ORGAN: 0.5,
    },
    ToolKind.STEEL_KNIFE: {
        PartKind.MEAT: 1.0, PartKind.HIDE: 1.0,
        PartKind.SINEW: 1.0, PartKind.BONE: 1.0,
        PartKind.HORN: 1.0, PartKind.ORGAN: 1.0,
    },
    ToolKind.BUTCHER_CLEAVER: {
        PartKind.MEAT: 1.3, PartKind.HIDE: 0.9,
        PartKind.SINEW: 1.0, PartKind.BONE: 1.0,
        PartKind.HORN: 1.0, PartKind.ORGAN: 1.0,
    },
    ToolKind.SCRIMSHAW_KIT: {
        PartKind.MEAT: 0.4, PartKind.HIDE: 0.5,
        PartKind.SINEW: 1.2, PartKind.BONE: 1.5,
        PartKind.HORN: 1.5, PartKind.ORGAN: 0.7,
    },
}


def _skill_factor(skill: int) -> float:
    # 0 → 0.5x, 50 → 1.0x, 100 → 1.5x, capped
    if skill <= 0:
        return 0.5
    if skill >= 100:
        return 1.5
    return 0.5 + (skill / 100.0)


def butcher_carcass(
    *, carcass: Carcass, butcher_skill: int,
    tool: ToolKind,
) -> YieldBundle:
    if not carcass.quarry_id:
        return YieldBundle(
            quarry_id="", meat=0, hide=0,
            hide_ruined=False, sinew=0,
            bone=0, horn=0, organ=0,
        )
    skill_mult = _skill_factor(butcher_skill)
    tool_factors = _TOOL_FACTORS[tool]
    # base counts derived from carcass weight
    w = max(carcass.weight_kg, 0.0)
    base_meat = w * 1.5         # 1.5 units per kg
    base_sinew = w * 0.4
    base_bone = w * 0.8
    base_organ = w * 0.3
    meat = int(base_meat * skill_mult * tool_factors[PartKind.MEAT])
    sinew = int(base_sinew * skill_mult * tool_factors[PartKind.SINEW])
    bone = int(base_bone * skill_mult * tool_factors[PartKind.BONE])
    organ = int(base_organ * skill_mult * tool_factors[PartKind.ORGAN])
    # hide: 1 if intact AND tool can pull it AND skill > 0
    hide = 0
    hide_ruined = False
    if not carcass.hide_intact:
        hide_ruined = True
    elif tool_factors[PartKind.HIDE] > 0 and butcher_skill > 0:
        hide = 1
    # horn: 1 each if quarry has horns and tool can pull
    horn = 0
    if carcass.has_horns and tool_factors[PartKind.HORN] > 0:
        # bigger animals carry bigger / more horns; +1 above 100kg
        horn = 1 + (1 if w >= 100 else 0)
    return YieldBundle(
        quarry_id=carcass.quarry_id,
        meat=meat, hide=hide, hide_ruined=hide_ruined,
        sinew=sinew, bone=bone, horn=horn, organ=organ,
    )


__all__ = [
    "PartKind", "ToolKind", "Carcass",
    "YieldBundle", "butcher_carcass",
]
