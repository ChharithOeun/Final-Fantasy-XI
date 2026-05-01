"""Per-job tuning profiles.

Per WEIGHT_PHYSICS.md "Job-specific weight identities": each job has
a target weight band, a casting modifier (for cast_time formula),
and an interrupt-resist multiplier (for interrupt_chance formula).

These are the structure-fixed values the doc commits to. Bands are
tuning-bait — playtest will refine.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class JobProfile:
    """Tuning bundle per job."""
    job: str
    weight_band_low: int                # lower target W
    weight_band_high: int               # upper target W
    cast_time_modifier: float = 1.0     # SCH 0.85, RDM 0.90, BRD 0.95
    interrupt_resist: float = 1.00      # NIN 0.30, RDM 0.50, etc.
    can_walk_cast: bool = False         # RDM/BRD true
    can_run_cast_under_chainspell: bool = False   # RDM only
    uses_hand_signs: bool = False       # NIN; signs ignore movement
    notes: str = ""


JOB_PROFILES: dict[str, JobProfile] = {
    "WAR": JobProfile("WAR", 80, 120,
                       interrupt_resist=1.00,
                       notes="bonus dmg/acc per weight on stationary swings"),
    "DRK": JobProfile("DRK", 100, 140,
                       interrupt_resist=1.00,
                       notes="absorb skills cost more weight to cast"),
    "PLD": JobProfile("PLD", 90, 130,
                       interrupt_resist=1.00,
                       notes="heavy gear unlocks shield-bash dmg scaling"),
    "MNK": JobProfile("MNK", 8, 25,
                       interrupt_resist=1.00,
                       notes="chakra requires <30 W"),
    "THF": JobProfile("THF", 20, 40,
                       interrupt_resist=1.00,
                       notes="TH/Steal full effectiveness only when gear<50"),
    "RNG": JobProfile("RNG", 30, 60,
                       interrupt_resist=1.00,
                       notes="snapshot scales inversely with weight"),
    "RDM": JobProfile("RDM", 25, 50,
                       cast_time_modifier=0.90,
                       interrupt_resist=0.50,
                       can_walk_cast=True,
                       can_run_cast_under_chainspell=True,
                       notes="walks while casting; chainspell allows running"),
    "WHM": JobProfile("WHM", 15, 30,
                       interrupt_resist=0.90,
                       notes="staff weight is a real cost"),
    "BLM": JobProfile("BLM", 30, 50,
                       interrupt_resist=1.00,
                       notes="heavy stance lowers cast-time penalty stationary"),
    "BRD": JobProfile("BRD", 20, 40,
                       cast_time_modifier=0.95,
                       interrupt_resist=0.55,
                       can_walk_cast=True,
                       notes="sings while walking; weight raises song interrupt"),
    "SMN": JobProfile("SMN", 25, 45,
                       interrupt_resist=1.00,
                       notes="avatar summon cost in weight scales with tier"),
    "NIN": JobProfile("NIN", 10, 30,
                       interrupt_resist=0.30,
                       uses_hand_signs=True,
                       notes="hand signs ignore movement-cost penalty entirely"),
    "SAM": JobProfile("SAM", 50, 80,
                       interrupt_resist=1.00,
                       notes="hassou/seigan +30% interrupt resist stationary"),
    "DRG": JobProfile("DRG", 60, 100,
                       interrupt_resist=1.00,
                       notes="wyvern-mounted ignores rider weight for movement"),
    "BLU": JobProfile("BLU", 25, 45,
                       interrupt_resist=1.00,
                       notes="spell weight is the cast cost"),
    "COR": JobProfile("COR", 20, 40,
                       interrupt_resist=1.00,
                       notes="quick draw is instant-cast (bypasses weight)"),
    "PUP": JobProfile("PUP", 45, 80,
                       interrupt_resist=1.00,
                       notes="automaton has its own weight column"),
    "DNC": JobProfile("DNC", 18, 35,
                       interrupt_resist=1.00,
                       notes="step-while-casting at running speed"),
    "SCH": JobProfile("SCH", 30, 50,
                       cast_time_modifier=0.85,
                       interrupt_resist=0.80,
                       notes="strategos: -20% spell weight for active arts"),
}


def job_modifiers_for(job: str) -> JobProfile:
    """Look up a job profile. Falls back to a neutral profile for
    unknown jobs (useful for NPCs/mobs without a strict job tag)."""
    profile = JOB_PROFILES.get(job)
    if profile is not None:
        return profile
    return JobProfile(job=job, weight_band_low=30, weight_band_high=80)
