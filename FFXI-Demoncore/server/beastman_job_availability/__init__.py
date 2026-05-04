"""Beastman job availability — canonical job sets per race.

In retail FFXI, beastmen run distinctive job archetypes. We
mirror that: each beastman race has a STARTING JOB POOL plus an
unlockable EXTENDED POOL. Lamia / Orc / Quadav / Yagudo each
get distinct combinations.

Canon picks (extracted from how beastmen behave in retail):
* Yagudo: WHM, MNK, BRD, NIN — clergy and martial artists.
* Quadav: BLM, PLD, WAR, GEO — earth-magic and bulwark.
* Lamia: THF, RDM, RNG, BLU, COR — predator with tricks.
* Orc: WAR, DRG, SAM, DRK, BST — pure brute, axes/lances.

Extended jobs become available after the player completes a
JOB UNLOCK QUEST in the corresponding city. Each unlock quest
is per-(race, job).

Public surface
--------------
    JobCode enum
    JobAvailabilityKind enum (STARTER / EXTENDED / FORBIDDEN)
    BeastmanJobAvailability
        .available_jobs(race) -> tuple[JobCode]
        .availability_kind(race, job) -> JobAvailabilityKind
        .complete_unlock_quest(player_id, race, job)
        .can_change_to(player_id, race, job) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class JobCode(str, enum.Enum):
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


class JobAvailabilityKind(str, enum.Enum):
    STARTER = "starter"          # available from char creation
    EXTENDED = "extended"        # gated behind unlock quest
    FORBIDDEN = "forbidden"      # not available to this race


_STARTER_JOBS: dict[BeastmanRace, frozenset[JobCode]] = {
    BeastmanRace.YAGUDO: frozenset({
        JobCode.WHM, JobCode.MNK,
    }),
    BeastmanRace.QUADAV: frozenset({
        JobCode.BLM, JobCode.PLD,
    }),
    BeastmanRace.LAMIA: frozenset({
        JobCode.THF, JobCode.RDM,
    }),
    BeastmanRace.ORC: frozenset({
        JobCode.WAR, JobCode.DRG,
    }),
}


_EXTENDED_JOBS: dict[BeastmanRace, frozenset[JobCode]] = {
    BeastmanRace.YAGUDO: frozenset({
        JobCode.BRD, JobCode.NIN,
    }),
    BeastmanRace.QUADAV: frozenset({
        JobCode.WAR, JobCode.GEO,
    }),
    BeastmanRace.LAMIA: frozenset({
        JobCode.RNG, JobCode.BLU, JobCode.COR,
    }),
    BeastmanRace.ORC: frozenset({
        JobCode.SAM, JobCode.DRK, JobCode.BST,
    }),
}


@dataclasses.dataclass
class BeastmanJobAvailability:
    # (player_id, race) -> set of unlocked extended jobs
    _unlocked: dict[
        tuple[str, BeastmanRace], set[JobCode],
    ] = dataclasses.field(default_factory=dict)

    def available_jobs(
        self, *, race: BeastmanRace,
    ) -> tuple[JobCode, ...]:
        starters = _STARTER_JOBS.get(race, frozenset())
        extended = _EXTENDED_JOBS.get(race, frozenset())
        combined = starters | extended
        return tuple(
            sorted(combined, key=lambda j: j.value),
        )

    def availability_kind(
        self, *, race: BeastmanRace, job: JobCode,
    ) -> JobAvailabilityKind:
        if job in _STARTER_JOBS.get(race, frozenset()):
            return JobAvailabilityKind.STARTER
        if job in _EXTENDED_JOBS.get(race, frozenset()):
            return JobAvailabilityKind.EXTENDED
        return JobAvailabilityKind.FORBIDDEN

    def complete_unlock_quest(
        self, *, player_id: str,
        race: BeastmanRace,
        job: JobCode,
    ) -> bool:
        kind = self.availability_kind(
            race=race, job=job,
        )
        if kind != JobAvailabilityKind.EXTENDED:
            return False
        key = (player_id, race)
        s = self._unlocked.setdefault(key, set())
        if job in s:
            return False
        s.add(job)
        return True

    def has_unlocked(
        self, *, player_id: str,
        race: BeastmanRace,
        job: JobCode,
    ) -> bool:
        return job in self._unlocked.get(
            (player_id, race), set(),
        )

    def can_change_to(
        self, *, player_id: str,
        race: BeastmanRace,
        job: JobCode,
    ) -> bool:
        kind = self.availability_kind(
            race=race, job=job,
        )
        if kind == JobAvailabilityKind.FORBIDDEN:
            return False
        if kind == JobAvailabilityKind.STARTER:
            return True
        # EXTENDED — must have completed the unlock quest
        return self.has_unlocked(
            player_id=player_id, race=race, job=job,
        )

    def all_unlocked_for(
        self, *, player_id: str,
        race: BeastmanRace,
    ) -> tuple[JobCode, ...]:
        return tuple(
            sorted(
                self._unlocked.get(
                    (player_id, race), set(),
                ),
                key=lambda j: j.value,
            )
        )

    def total_unlocks(
        self, *, player_id: str,
    ) -> int:
        return sum(
            len(s) for (pid, _), s in self._unlocked.items()
            if pid == player_id
        )


__all__ = [
    "JobCode", "JobAvailabilityKind",
    "BeastmanJobAvailability",
]
