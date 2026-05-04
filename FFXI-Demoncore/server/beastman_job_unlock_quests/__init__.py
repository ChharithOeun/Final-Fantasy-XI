"""Beastman job unlock quests — full job access via quest path.

Extends beastman_job_availability. Each race starts with a
small STARTER pool plus an EXTENDED pool gated on a single
unlock quest. Any job not in either pool — and any job that's
in extended for a race — can ALSO be reached via a longer
"PROVING CHAIN" of 3-5 quests. The chains are cross-tribal:
to unlock an RDM as a Yagudo (RDM isn't on the Yagudo list)
you have to seek out a Lamia tutor, complete their disciple
chain, and forge a contract with them.

Public surface
--------------
    UnlockChainStatus enum
    UnlockChainStep dataclass
    UnlockChain dataclass
    BeastmanJobUnlockQuests
        .register_chain(race, job, steps, tutor_npc)
        .start_chain(player_id, race, job)
        .complete_step(player_id, race, job, step_index)
        .complete_chain(player_id, race, job)  -> notifies job
                                                  availability
        .unlocked_via_chain(player_id, race, job)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace
from server.beastman_job_availability import (
    BeastmanJobAvailability, JobCode, JobAvailabilityKind,
)


class UnlockChainStatus(str, enum.Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass(frozen=True)
class UnlockChainStep:
    step_index: int
    label: str
    description: str = ""


@dataclasses.dataclass(frozen=True)
class UnlockChain:
    race: BeastmanRace
    job: JobCode
    tutor_npc_id: str
    steps: tuple[UnlockChainStep, ...]


@dataclasses.dataclass
class _PlayerProgress:
    player_id: str
    race: BeastmanRace
    job: JobCode
    completed_steps: list[int] = dataclasses.field(
        default_factory=list,
    )
    status: UnlockChainStatus = UnlockChainStatus.IN_PROGRESS


@dataclasses.dataclass(frozen=True)
class StepResult:
    accepted: bool
    race: BeastmanRace
    job: JobCode
    step_index: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteChainResult:
    accepted: bool
    race: BeastmanRace
    job: JobCode
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanJobUnlockQuests:
    job_availability: BeastmanJobAvailability
    _chains: dict[
        tuple[BeastmanRace, JobCode], UnlockChain,
    ] = dataclasses.field(default_factory=dict)
    _progress: dict[
        tuple[str, BeastmanRace, JobCode], _PlayerProgress,
    ] = dataclasses.field(default_factory=dict)
    # Per-(player, race) set of jobs unlocked via this module
    _unlocked: dict[
        tuple[str, BeastmanRace], set[JobCode],
    ] = dataclasses.field(default_factory=dict)

    def register_chain(
        self, *, race: BeastmanRace, job: JobCode,
        tutor_npc_id: str,
        steps: tuple[UnlockChainStep, ...],
    ) -> t.Optional[UnlockChain]:
        if not tutor_npc_id:
            return None
        if not steps:
            return None
        # Steps must be 0-indexed contiguous
        for i, s in enumerate(steps):
            if s.step_index != i:
                return None
        key = (race, job)
        if key in self._chains:
            return None
        chain = UnlockChain(
            race=race, job=job,
            tutor_npc_id=tutor_npc_id, steps=steps,
        )
        self._chains[key] = chain
        return chain

    def chain(
        self, *, race: BeastmanRace, job: JobCode,
    ) -> t.Optional[UnlockChain]:
        return self._chains.get((race, job))

    def start_chain(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> bool:
        chain = self._chains.get((race, job))
        if chain is None:
            return False
        # Already starter-available? No need for chain.
        kind = self.job_availability.availability_kind(
            race=race, job=job,
        )
        if kind == JobAvailabilityKind.STARTER:
            return False
        # Already unlocked through availability or this module?
        if self.job_availability.has_unlocked(
            player_id=player_id, race=race, job=job,
        ):
            return False
        if self.unlocked_via_chain(
            player_id=player_id, race=race, job=job,
        ):
            return False
        key = (player_id, race, job)
        if key in self._progress:
            return False
        self._progress[key] = _PlayerProgress(
            player_id=player_id, race=race, job=job,
        )
        return True

    def complete_step(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
        step_index: int,
    ) -> StepResult:
        chain = self._chains.get((race, job))
        if chain is None:
            return StepResult(
                False, race=race, job=job,
                step_index=step_index,
                reason="no chain registered",
            )
        prog = self._progress.get(
            (player_id, race, job),
        )
        if prog is None:
            return StepResult(
                False, race=race, job=job,
                step_index=step_index,
                reason="chain not started",
            )
        if prog.status != UnlockChainStatus.IN_PROGRESS:
            return StepResult(
                False, race=race, job=job,
                step_index=step_index,
                reason="chain not in progress",
            )
        next_idx = len(prog.completed_steps)
        if step_index != next_idx:
            return StepResult(
                False, race=race, job=job,
                step_index=step_index,
                reason=(
                    f"out of order; expected {next_idx}"
                ),
            )
        prog.completed_steps.append(step_index)
        return StepResult(
            accepted=True, race=race, job=job,
            step_index=step_index,
        )

    def can_complete_chain(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> bool:
        chain = self._chains.get((race, job))
        prog = self._progress.get(
            (player_id, race, job),
        )
        if chain is None or prog is None:
            return False
        if prog.status != UnlockChainStatus.IN_PROGRESS:
            return False
        return len(prog.completed_steps) == len(chain.steps)

    def complete_chain(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> CompleteChainResult:
        if not self.can_complete_chain(
            player_id=player_id, race=race, job=job,
        ):
            return CompleteChainResult(
                False, race=race, job=job,
                reason="steps incomplete",
            )
        prog = self._progress[(player_id, race, job)]
        prog.status = UnlockChainStatus.COMPLETE
        self._unlocked.setdefault(
            (player_id, race), set(),
        ).add(job)
        return CompleteChainResult(
            accepted=True, race=race, job=job,
        )

    def unlocked_via_chain(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> bool:
        return job in self._unlocked.get(
            (player_id, race), set(),
        )

    def can_play(
        self, *, player_id: str,
        race: BeastmanRace, job: JobCode,
    ) -> bool:
        """Composite: STARTER, EXTENDED-unlocked, or chain-unlocked."""
        if self.job_availability.can_change_to(
            player_id=player_id, race=race, job=job,
        ):
            return True
        return self.unlocked_via_chain(
            player_id=player_id, race=race, job=job,
        )

    def total_chains(self) -> int:
        return len(self._chains)


__all__ = [
    "UnlockChainStatus", "UnlockChainStep",
    "UnlockChain",
    "StepResult", "CompleteChainResult",
    "BeastmanJobUnlockQuests",
]
