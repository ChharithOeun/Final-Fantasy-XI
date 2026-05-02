"""Character stats — six attributes + race + level scaling.

Every character has six base attributes:
    STR (physical attack/damage)
    DEX (accuracy/crit rate)
    AGI (evasion/ranged accuracy)
    INT (magic damage)
    MND (healing magic + magic accuracy)
    CHR (charm + bard songs + nation reputation)

Racial bias gives each race a slight tilt across these. Level
scaling applies a per-job-per-level delta (job_curve). HP/MP are
derived from VIT/MND/level and job-specific multipliers.

Public surface
--------------
    Race enum (5 races)
    BaseStats dataclass
    JobStatBias dataclass per job
    derived_hp(level, race, job, vit) -> int
    derived_mp(level, race, job, mnd) -> int
    aggregate_attributes(race, job, level) -> AttributeBlock
"""
from __future__ import annotations

import dataclasses
import enum


class Race(str, enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    GALKA = "galka"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"


@dataclasses.dataclass(frozen=True)
class AttributeBlock:
    str_: int
    dex: int
    vit: int
    agi: int
    int_: int
    mnd: int
    chr_: int


# Racial baselines at level 1 (representative)
RACE_BASELINE: dict[Race, AttributeBlock] = {
    Race.HUME:     AttributeBlock(7, 7, 7, 7, 7, 7, 7),
    Race.ELVAAN:   AttributeBlock(8, 6, 7, 6, 6, 8, 7),
    Race.GALKA:    AttributeBlock(9, 6, 9, 5, 5, 6, 5),
    Race.TARUTARU: AttributeBlock(5, 6, 5, 7, 9, 8, 6),
    Race.MITHRA:   AttributeBlock(6, 9, 6, 8, 6, 6, 6),
}


@dataclasses.dataclass(frozen=True)
class JobStatGrowth:
    """Per-level stat growth for a job. Highest job-grade attributes
    grow ~+1 every 2 levels; lowest grow ~+1 every 4."""
    str_per_level: float
    dex_per_level: float
    vit_per_level: float
    agi_per_level: float
    int_per_level: float
    mnd_per_level: float
    chr_per_level: float
    # Derived stat multipliers (HP at lvl 75 / VIT scaling, etc.)
    hp_per_level: int
    mp_per_level: int


# Sample job growth tables (representative, not retail-perfect)
JOB_GROWTH: dict[str, JobStatGrowth] = {
    "warrior": JobStatGrowth(
        str_per_level=0.50, dex_per_level=0.25,
        vit_per_level=0.50, agi_per_level=0.25,
        int_per_level=0.10, mnd_per_level=0.10,
        chr_per_level=0.10,
        hp_per_level=14, mp_per_level=2,
    ),
    "white_mage": JobStatGrowth(
        str_per_level=0.10, dex_per_level=0.15,
        vit_per_level=0.20, agi_per_level=0.15,
        int_per_level=0.30, mnd_per_level=0.50,
        chr_per_level=0.20,
        hp_per_level=8, mp_per_level=12,
    ),
    "black_mage": JobStatGrowth(
        str_per_level=0.10, dex_per_level=0.15,
        vit_per_level=0.15, agi_per_level=0.20,
        int_per_level=0.50, mnd_per_level=0.30,
        chr_per_level=0.15,
        hp_per_level=7, mp_per_level=13,
    ),
    "thief": JobStatGrowth(
        str_per_level=0.30, dex_per_level=0.50,
        vit_per_level=0.25, agi_per_level=0.45,
        int_per_level=0.20, mnd_per_level=0.15,
        chr_per_level=0.20,
        hp_per_level=11, mp_per_level=4,
    ),
    "monk": JobStatGrowth(
        str_per_level=0.45, dex_per_level=0.40,
        vit_per_level=0.50, agi_per_level=0.30,
        int_per_level=0.15, mnd_per_level=0.20,
        chr_per_level=0.20,
        hp_per_level=15, mp_per_level=2,
    ),
    "red_mage": JobStatGrowth(
        str_per_level=0.30, dex_per_level=0.30,
        vit_per_level=0.25, agi_per_level=0.30,
        int_per_level=0.40, mnd_per_level=0.40,
        chr_per_level=0.20,
        hp_per_level=10, mp_per_level=10,
    ),
}


def aggregate_attributes(
    *, race: Race, job: str, level: int,
) -> AttributeBlock:
    """Race base + per-level growth = current attribute block."""
    if level < 1:
        raise ValueError("level must be >= 1")
    base = RACE_BASELINE[race]
    growth = JOB_GROWTH.get(job)
    if growth is None:
        # Use warrior-ish default
        growth = JOB_GROWTH["warrior"]
    levels_above_1 = level - 1
    return AttributeBlock(
        str_=base.str_ + int(growth.str_per_level * levels_above_1),
        dex=base.dex + int(growth.dex_per_level * levels_above_1),
        vit=base.vit + int(growth.vit_per_level * levels_above_1),
        agi=base.agi + int(growth.agi_per_level * levels_above_1),
        int_=base.int_ + int(growth.int_per_level * levels_above_1),
        mnd=base.mnd + int(growth.mnd_per_level * levels_above_1),
        chr_=base.chr_ + int(growth.chr_per_level * levels_above_1),
    )


def derived_hp(*, level: int, race: Race, job: str, vit: int) -> int:
    """HP = 50 + (hp_per_level * level) + VIT * 2 + race tilt."""
    growth = JOB_GROWTH.get(job, JOB_GROWTH["warrior"])
    race_tilt = {
        Race.HUME: 0,
        Race.ELVAAN: 5,
        Race.GALKA: 25,        # Galka are HP-tilted
        Race.TARUTARU: -15,
        Race.MITHRA: 0,
    }[race]
    return 50 + growth.hp_per_level * level + vit * 2 + race_tilt


def derived_mp(*, level: int, race: Race, job: str, mnd: int) -> int:
    """MP = 30 + (mp_per_level * level) + MND * 2 + race tilt."""
    growth = JOB_GROWTH.get(job, JOB_GROWTH["warrior"])
    race_tilt = {
        Race.HUME: 0,
        Race.ELVAAN: 0,
        Race.GALKA: -15,        # Galka MP-light
        Race.TARUTARU: 25,      # Taru MP-tilted
        Race.MITHRA: 0,
    }[race]
    return 30 + growth.mp_per_level * level + mnd * 2 + race_tilt


__all__ = [
    "Race", "AttributeBlock",
    "RACE_BASELINE", "JobStatGrowth", "JOB_GROWTH",
    "aggregate_attributes", "derived_hp", "derived_mp",
]
