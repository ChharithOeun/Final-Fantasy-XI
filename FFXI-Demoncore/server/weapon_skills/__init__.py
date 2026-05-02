"""Weapon skills — TP-gated finishing moves with skillchain attributes.

A weapon skill consumes 1000 TP minimum (TP carries over above 1000
but doesn't double-fire). Each WS has an attribute set defining its
skillchain element, hit count, fTP modifier curve, and stat
multipliers.

Public surface
--------------
    SkillchainElement enum
    WeaponSkill catalog
    use_weapon_skill(actor_tp, ws_id) -> UseResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


TP_THRESHOLD_TO_USE = 1000
MAX_TP = 3000
TP_RESET_TO = 0


class SkillchainElement(str, enum.Enum):
    LIGHT = "light"
    DARKNESS = "darkness"
    FUSION = "fusion"
    FRAGMENTATION = "fragmentation"
    DISTORTION = "distortion"
    GRAVITATION = "gravitation"
    LIQUEFACTION = "liquefaction"
    INDURATION = "induration"
    REVERBERATION = "reverberation"
    IMPACTION = "impaction"
    DETONATION = "detonation"
    SCISSION = "scission"
    COMPRESSION = "compression"
    TRANSFIXION = "transfixion"


@dataclasses.dataclass(frozen=True)
class WeaponSkill:
    ws_id: str
    label: str
    weapon_family: str               # sword / dagger / great_sword etc.
    hit_count: int
    skillchain_element: SkillchainElement
    primary_stat: str                # str / dex / agi / int / mnd
    ftp_at_1000: float               # base ftp at 1000 TP
    ftp_at_2000: float               # boosted at 2000
    ftp_at_3000: float               # boosted at 3000
    aoe_radius_yalms: float = 0.0    # 0 = single target


# Sample catalog
WS_CATALOG: tuple[WeaponSkill, ...] = (
    WeaponSkill("vorpal_blade", "Vorpal Blade",
                weapon_family="sword", hit_count=2,
                skillchain_element=SkillchainElement.LIGHT,
                primary_stat="str",
                ftp_at_1000=0.5, ftp_at_2000=2.5, ftp_at_3000=4.0),
    WeaponSkill("savage_blade", "Savage Blade",
                weapon_family="sword", hit_count=1,
                skillchain_element=SkillchainElement.FUSION,
                primary_stat="str",
                ftp_at_1000=2.5, ftp_at_2000=3.5, ftp_at_3000=4.5),
    WeaponSkill("rampage", "Rampage",
                weapon_family="axe", hit_count=5,
                skillchain_element=SkillchainElement.LIQUEFACTION,
                primary_stat="str",
                ftp_at_1000=0.7, ftp_at_2000=1.6, ftp_at_3000=2.4),
    WeaponSkill("resolution", "Resolution",
                weapon_family="great_sword", hit_count=4,
                skillchain_element=SkillchainElement.DISTORTION,
                primary_stat="str",
                ftp_at_1000=2.625, ftp_at_2000=4.25, ftp_at_3000=6.5),
    WeaponSkill("evisceration", "Evisceration",
                weapon_family="dagger", hit_count=5,
                skillchain_element=SkillchainElement.DARKNESS,
                primary_stat="dex",
                ftp_at_1000=2.0, ftp_at_2000=3.0, ftp_at_3000=4.0),
    WeaponSkill("blade_ku", "Blade: Ku",
                weapon_family="katana", hit_count=2,
                skillchain_element=SkillchainElement.LIGHT,
                primary_stat="str",
                ftp_at_1000=2.5, ftp_at_2000=3.5, ftp_at_3000=4.5),
    WeaponSkill("dragon_kick", "Dragon Kick",
                weapon_family="hand_to_hand", hit_count=2,
                skillchain_element=SkillchainElement.FUSION,
                primary_stat="str",
                ftp_at_1000=1.875, ftp_at_2000=2.5, ftp_at_3000=3.0),
    WeaponSkill("last_resort_aoe", "Reverence",
                weapon_family="scythe", hit_count=2,
                skillchain_element=SkillchainElement.DARKNESS,
                primary_stat="str",
                ftp_at_1000=0.5, ftp_at_2000=2.0, ftp_at_3000=4.0,
                aoe_radius_yalms=10.0),
)

WS_BY_ID: dict[str, WeaponSkill] = {ws.ws_id: ws for ws in WS_CATALOG}


@dataclasses.dataclass(frozen=True)
class UseResult:
    accepted: bool
    ws_id: str
    ftp: float = 0.0
    tp_consumed: int = 0
    skillchain_element: t.Optional[SkillchainElement] = None
    reason: t.Optional[str] = None


def ftp_at_tp(ws: WeaponSkill, tp: int) -> float:
    """Linear interpolation between fTP plateaus (1000/2000/3000)."""
    tp = max(TP_THRESHOLD_TO_USE, min(tp, MAX_TP))
    if tp <= 1000:
        return ws.ftp_at_1000
    if tp <= 2000:
        # Linear between 1000 and 2000
        ratio = (tp - 1000) / 1000.0
        return ws.ftp_at_1000 + (ws.ftp_at_2000 - ws.ftp_at_1000) * ratio
    ratio = (tp - 2000) / 1000.0
    return ws.ftp_at_2000 + (ws.ftp_at_3000 - ws.ftp_at_2000) * ratio


def use_weapon_skill(
    *,
    ws_id: str,
    current_tp: int,
    weapon_family_equipped: str,
) -> UseResult:
    ws = WS_BY_ID.get(ws_id)
    if ws is None:
        return UseResult(False, ws_id, reason="unknown WS")
    if ws.weapon_family != weapon_family_equipped:
        return UseResult(False, ws_id,
                          reason="wrong weapon family equipped")
    if current_tp < TP_THRESHOLD_TO_USE:
        return UseResult(False, ws_id,
                          reason="not enough TP")
    ftp = ftp_at_tp(ws, current_tp)
    return UseResult(
        accepted=True, ws_id=ws_id,
        ftp=ftp,
        tp_consumed=current_tp,
        skillchain_element=ws.skillchain_element,
    )


__all__ = [
    "TP_THRESHOLD_TO_USE", "MAX_TP", "TP_RESET_TO",
    "SkillchainElement", "WeaponSkill",
    "WS_CATALOG", "WS_BY_ID",
    "UseResult", "ftp_at_tp", "use_weapon_skill",
]
