"""Teleport spells — canonical WHM/SCH crystal warps + Recall.

Six outdoor crystal warps (Teleport-X) plus three Recall spells.
Each requires the matching key item (Holla Gate Crystal etc.)
held by the caster. Cast time and MP cost match canonical FFXI.

Crystal Teleports drop the party at a fixed altar. Recall
spells warp the entire alliance to specific zones.

Public surface
--------------
    TeleportSpell enum
    TeleportEntry dataclass / TELEPORT_CATALOG / SPELL_BY_ID
    can_cast(spell, caster_job, caster_level, key_items_held)
    target_zone(spell) -> str
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TeleportSpell(str, enum.Enum):
    # Outdoor crystal Teleports (WHM 50)
    TELEPORT_HOLLA = "teleport_holla"
    TELEPORT_DEM = "teleport_dem"
    TELEPORT_MEA = "teleport_mea"
    # Mid-game Teleports (WHM 60+)
    TELEPORT_ALTEP = "teleport_altep"
    TELEPORT_YHOAT = "teleport_yhoat"
    TELEPORT_VAHZL = "teleport_vahzl"
    # Recalls (WHM 50, alliance warp to nation)
    RECALL_PASHH = "recall_pashh"
    RECALL_MERIPH = "recall_meriph"
    RECALL_JUGNER = "recall_jugner"


@dataclasses.dataclass(frozen=True)
class TeleportEntry:
    spell_id: TeleportSpell
    label: str
    target_zone: str
    required_key_item: str
    mp_cost: int
    cast_seconds: float
    job_min_level: dict[str, int]   # job -> min level


TELEPORT_CATALOG: tuple[TeleportEntry, ...] = (
    # ---- Crystal Teleports (Konschtat / Tahrongi / La Theine)
    TeleportEntry(
        TeleportSpell.TELEPORT_HOLLA, "Teleport-Holla",
        target_zone="konschtat_highlands",
        required_key_item="holla_gate_crystal",
        mp_cost=150, cast_seconds=8.0,
        job_min_level={"white_mage": 50, "scholar": 50},
    ),
    TeleportEntry(
        TeleportSpell.TELEPORT_DEM, "Teleport-Dem",
        target_zone="la_theine_plateau",
        required_key_item="dem_gate_crystal",
        mp_cost=150, cast_seconds=8.0,
        job_min_level={"white_mage": 50, "scholar": 50},
    ),
    TeleportEntry(
        TeleportSpell.TELEPORT_MEA, "Teleport-Mea",
        target_zone="tahrongi_canyon",
        required_key_item="mea_gate_crystal",
        mp_cost=150, cast_seconds=8.0,
        job_min_level={"white_mage": 50, "scholar": 50},
    ),
    # ---- Mid-tier (Altepa, Yhoator, Beaucedine via Vahzl)
    TeleportEntry(
        TeleportSpell.TELEPORT_ALTEP, "Teleport-Altep",
        target_zone="eastern_altepa_desert",
        required_key_item="altep_gate_crystal",
        mp_cost=180, cast_seconds=8.0,
        job_min_level={"white_mage": 60, "scholar": 65},
    ),
    TeleportEntry(
        TeleportSpell.TELEPORT_YHOAT, "Teleport-Yhoat",
        target_zone="yhoator_jungle",
        required_key_item="yhoat_gate_crystal",
        mp_cost=180, cast_seconds=8.0,
        job_min_level={"white_mage": 65, "scholar": 70},
    ),
    TeleportEntry(
        TeleportSpell.TELEPORT_VAHZL, "Teleport-Vahzl",
        target_zone="xarcabard",
        required_key_item="vahzl_gate_crystal",
        mp_cost=200, cast_seconds=10.0,
        job_min_level={"white_mage": 70, "scholar": 75},
    ),
    # ---- Recalls (alliance warp to nation outlying zone)
    TeleportEntry(
        TeleportSpell.RECALL_PASHH, "Recall-Pashh",
        target_zone="pashhow_marshlands",
        required_key_item="recall_pashh_rune",
        mp_cost=200, cast_seconds=10.0,
        job_min_level={"white_mage": 50, "scholar": 60},
    ),
    TeleportEntry(
        TeleportSpell.RECALL_MERIPH, "Recall-Meriph",
        target_zone="meriphataud_mountains",
        required_key_item="recall_meriph_rune",
        mp_cost=200, cast_seconds=10.0,
        job_min_level={"white_mage": 50, "scholar": 60},
    ),
    TeleportEntry(
        TeleportSpell.RECALL_JUGNER, "Recall-Jugner",
        target_zone="jugner_forest",
        required_key_item="recall_jugner_rune",
        mp_cost=200, cast_seconds=10.0,
        job_min_level={"white_mage": 50, "scholar": 60},
    ),
)


SPELL_BY_ID: dict[TeleportSpell, TeleportEntry] = {
    e.spell_id: e for e in TELEPORT_CATALOG
}


@dataclasses.dataclass(frozen=True)
class CastEligibility:
    can_cast: bool
    reason: t.Optional[str] = None
    spell: t.Optional[TeleportEntry] = None


def can_cast(
    *, spell_id: TeleportSpell, caster_job: str,
    caster_level: int, key_items_held: t.Iterable[str],
    current_mp: int,
) -> CastEligibility:
    spell = SPELL_BY_ID.get(spell_id)
    if spell is None:
        return CastEligibility(False, reason="unknown spell")
    min_level = spell.job_min_level.get(caster_job)
    if min_level is None:
        return CastEligibility(False, reason="job cannot cast this")
    if caster_level < min_level:
        return CastEligibility(
            False, reason=f"requires level {min_level}", spell=spell,
        )
    if spell.required_key_item not in set(key_items_held):
        return CastEligibility(
            False, reason="missing key item", spell=spell,
        )
    if current_mp < spell.mp_cost:
        return CastEligibility(
            False, reason="insufficient MP", spell=spell,
        )
    return CastEligibility(True, spell=spell)


def target_zone(spell_id: TeleportSpell) -> t.Optional[str]:
    e = SPELL_BY_ID.get(spell_id)
    return e.target_zone if e else None


def crystal_teleports() -> tuple[TeleportSpell, ...]:
    return (
        TeleportSpell.TELEPORT_HOLLA,
        TeleportSpell.TELEPORT_DEM,
        TeleportSpell.TELEPORT_MEA,
        TeleportSpell.TELEPORT_ALTEP,
        TeleportSpell.TELEPORT_YHOAT,
        TeleportSpell.TELEPORT_VAHZL,
    )


def recall_spells() -> tuple[TeleportSpell, ...]:
    return (
        TeleportSpell.RECALL_PASHH,
        TeleportSpell.RECALL_MERIPH,
        TeleportSpell.RECALL_JUGNER,
    )


__all__ = [
    "TeleportSpell", "TeleportEntry",
    "TELEPORT_CATALOG", "SPELL_BY_ID",
    "CastEligibility", "can_cast",
    "target_zone", "crystal_teleports", "recall_spells",
]
