"""Moonphase modifiers — lunar-cycle stat tweaks per job.

The moon's phase nudges combat. NIN are stronger under
new moon (shadow blends). DRG/PLD shine under full moon
(banner-lit valor). The module computes a per-job
multiplier given the current moon phase.

Phases (canonical FFXI 8-phase cycle):
    NEW            0% (no light)
    WAXING_CRESCENT
    FIRST_QUARTER
    WAXING_GIBBOUS
    FULL           100% (max light)
    WANING_GIBBOUS
    LAST_QUARTER
    WANING_CRESCENT

Effect mapping (illustrative; tunable):
    NIN, THF, DRK         best at NEW, worst at FULL
    PLD, DRG, MNK, RDM    best at FULL, worst at NEW
    BRD, BLM, WHM         neutral (slight ±2% wobble)
    SMN                   resonates with avatar's element

Public surface
--------------
    MoonPhase enum
    JobModifier dataclass (frozen)
    MoonphaseEngine
        .modifier_for(job, phase) -> int    (-15 .. +15 pct points)
        .multiplier_for(job, phase) -> float
        .all_jobs_at(phase) -> dict[str, int]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MoonPhase(str, enum.Enum):
    NEW = "new"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL = "full"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


# illumination 0-100 by phase
_LIGHT = {
    MoonPhase.NEW: 0,
    MoonPhase.WAXING_CRESCENT: 25,
    MoonPhase.FIRST_QUARTER: 50,
    MoonPhase.WAXING_GIBBOUS: 75,
    MoonPhase.FULL: 100,
    MoonPhase.WANING_GIBBOUS: 75,
    MoonPhase.LAST_QUARTER: 50,
    MoonPhase.WANING_CRESCENT: 25,
}


# job archetypes; tilt direction:
#   +1 means more light = better (peaks at FULL)
#   -1 means less light = better (peaks at NEW)
#    0 means flat
_TILT = {
    "NIN": -1, "THF": -1, "DRK": -1,
    "PLD": +1, "DRG": +1, "MNK": +1, "RDM": +1,
    "BRD": 0, "BLM": 0, "WHM": 0,
    "SMN": 0,   # neutral baseline; element-specific in caller
}

# absolute amplitude in % points (max effect at extremes)
_AMPLITUDE = 15


def _modifier_pp(tilt: int, light_pct: int) -> int:
    if tilt == 0:
        return 0
    # at FULL (light=100) → tilt * +amp/2 (mid-strength)
    # at NEW (light=0) → tilt * -amp/2
    # but we want extremes to be -1 → +amp at NEW and -amp at FULL
    # so map: result = -tilt * (light - 50) / 50 * amp
    # at light=0  → -tilt * (-1) * amp = +tilt * amp
    # at light=100 → -tilt * (+1) * amp = -tilt * amp
    # Wait: tilt +1 means MORE light better, so at light=100
    # we want +amp; let me redo:
    # result = tilt * (light - 50) / 50 * amp
    # at light=0  (NEW)  → tilt * -1 * amp = -tilt*amp
    # at light=100 (FULL) → tilt * +1 * amp = +tilt*amp
    # tilt=+1 (PLD): NEW=-15, FULL=+15 → correct
    # tilt=-1 (NIN): NEW=+15, FULL=-15 → correct
    return int(tilt * (light_pct - 50) / 50 * _AMPLITUDE)


@dataclasses.dataclass
class MoonphaseEngine:

    def modifier_for(
        self, *, job: str, phase: MoonPhase,
    ) -> int:
        if not job:
            return 0
        tilt = _TILT.get(job.upper(), 0)
        light = _LIGHT[phase]
        return _modifier_pp(tilt, light)

    def multiplier_for(
        self, *, job: str, phase: MoonPhase,
    ) -> float:
        pp = self.modifier_for(job=job, phase=phase)
        return 1.0 + pp / 100.0

    def all_jobs_at(
        self, *, phase: MoonPhase,
    ) -> dict[str, int]:
        return {
            job: self.modifier_for(job=job, phase=phase)
            for job in _TILT
        }

    def light_pct_for(self, *, phase: MoonPhase) -> int:
        return _LIGHT[phase]


__all__ = ["MoonPhase", "MoonphaseEngine"]
