"""Beastman race-job affinity — racial bonuses on signature jobs.

Each beastman race has a list of jobs they're naturally suited
to. Running an affinity job grants a passive RACIAL BONUS:
* +5% damage / healing (job-relevant scaling)
* +3% main-stat
* small fame multiplier (1.10x) on quest rewards while playing
  the affinity job

Affinity is a "you're at home in this body" bonus — it stacks
with regular gear and buffs but does NOT stack with itself if a
player somehow runs two affinity jobs simultaneously (impossible
under normal rules but the system gates anyway).

Spec'd affinity sets (from the user):
* Lamia: PUP, BST, SMN, BRD, GEO, DNC, COR, SCH
* Yagudo: SAM, BLU, NIN, MNK, PUP, BLM, WHM
* Quadav: WAR, PLD, DRK, DRG (with pet), RUN
* Orc: THF, RDM, RNG, COR, WAR, MNK, BST

Public surface
--------------
    AffinityBonus dataclass
    BeastmanRaceJobAffinity
        .has_affinity(race, job) -> bool
        .bonus_for(race, job, drg_with_pet=False) -> AffinityBonus
        .affinity_jobs(race) -> tuple[JobCode]
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.beastman_playable_races import BeastmanRace
from server.beastman_job_availability import JobCode


# Default bonuses (percent values).
DEFAULT_DAMAGE_HEAL_PCT = 5
DEFAULT_MAIN_STAT_PCT = 3
DEFAULT_FAME_MULTIPLIER = 1.10


_AFFINITY_BY_RACE: dict[
    BeastmanRace, frozenset[JobCode],
] = {
    BeastmanRace.LAMIA: frozenset({
        JobCode.PUP, JobCode.BST, JobCode.SMN,
        JobCode.BRD, JobCode.GEO, JobCode.DNC,
        JobCode.COR, JobCode.SCH,
    }),
    BeastmanRace.YAGUDO: frozenset({
        JobCode.SAM, JobCode.BLU, JobCode.NIN,
        JobCode.MNK, JobCode.PUP, JobCode.BLM,
        JobCode.WHM,
    }),
    BeastmanRace.QUADAV: frozenset({
        JobCode.WAR, JobCode.PLD, JobCode.DRK,
        JobCode.DRG, JobCode.RUN,
    }),
    BeastmanRace.ORC: frozenset({
        JobCode.THF, JobCode.RDM, JobCode.RNG,
        JobCode.COR, JobCode.WAR, JobCode.MNK,
        JobCode.BST,
    }),
}


# Quadav DRG affinity is GATED on the player keeping their
# wyvern pet alive — without the pet, DRG drops to no bonus.
_PET_GATED: dict[
    BeastmanRace, frozenset[JobCode],
] = {
    BeastmanRace.QUADAV: frozenset({JobCode.DRG}),
}


@dataclasses.dataclass(frozen=True)
class AffinityBonus:
    has_bonus: bool
    damage_heal_pct: int = 0
    main_stat_pct: int = 0
    fame_multiplier: float = 1.0
    note: str = ""


@dataclasses.dataclass
class BeastmanRaceJobAffinity:
    damage_heal_pct: int = DEFAULT_DAMAGE_HEAL_PCT
    main_stat_pct: int = DEFAULT_MAIN_STAT_PCT
    fame_multiplier: float = DEFAULT_FAME_MULTIPLIER

    def has_affinity(
        self, *, race: BeastmanRace, job: JobCode,
    ) -> bool:
        return job in _AFFINITY_BY_RACE.get(
            race, frozenset(),
        )

    def affinity_jobs(
        self, *, race: BeastmanRace,
    ) -> tuple[JobCode, ...]:
        return tuple(
            sorted(
                _AFFINITY_BY_RACE.get(race, frozenset()),
                key=lambda j: j.value,
            )
        )

    def bonus_for(
        self, *, race: BeastmanRace, job: JobCode,
        pet_active: bool = False,
    ) -> AffinityBonus:
        if not self.has_affinity(race=race, job=job):
            return AffinityBonus(
                has_bonus=False,
                note="no affinity",
            )
        # Pet-gated jobs require the pet to be active
        if (
            job in _PET_GATED.get(race, frozenset())
            and not pet_active
        ):
            return AffinityBonus(
                has_bonus=False,
                note="pet not active",
            )
        return AffinityBonus(
            has_bonus=True,
            damage_heal_pct=self.damage_heal_pct,
            main_stat_pct=self.main_stat_pct,
            fame_multiplier=self.fame_multiplier,
            note="racial affinity",
        )

    def is_pet_gated(
        self, *, race: BeastmanRace, job: JobCode,
    ) -> bool:
        return job in _PET_GATED.get(
            race, frozenset(),
        )

    def total_affinity_jobs(self, *, race: BeastmanRace) -> int:
        return len(_AFFINITY_BY_RACE.get(race, frozenset()))


__all__ = [
    "DEFAULT_DAMAGE_HEAL_PCT",
    "DEFAULT_MAIN_STAT_PCT",
    "DEFAULT_FAME_MULTIPLIER",
    "AffinityBonus",
    "BeastmanRaceJobAffinity",
]
