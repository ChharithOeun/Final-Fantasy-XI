"""Conquest objectives — per-zone NM kill order, mini-games, oxygen drops.

Each conquest zone in each phase has a chain of objectives
the alliance must clear in order. The most important
constraint: certain NMs MUST be killed in the right order,
because the correct sequence drops AOE oxygen tanks the
alliance needs to survive the next wave.

Three objective kinds:
    KILL_NM     - kill a specific NM; out-of-order kills
                  fail the chain
    MINIGAME    - timed mini-game (tide-puzzle, current-
                  surfing, kelp-maze, pearl-trace)
    QUEST_STEP  - narrative step (rescue mermaid scout,
                  recover relic, pray at shrine)

When a KILL_NM with `oxygen_drop=True` is killed in the
correct sequence, an AOE oxygen tank drops at its
location, granting +5 minutes underwater breathing to
players within the drop radius.

Public surface
--------------
    ObjectiveKind enum
    ObjectiveStatus enum
    Objective dataclass (frozen)
    ObjectiveResult dataclass (frozen)
    ConquestObjectives
        .register_chain(chain_id, zone_id, phase, objectives)
        .complete_objective(chain_id, objective_id,
                            killed_nm_id, now_seconds)
            -> ObjectiveResult
        .current_objective(chain_id) -> Optional[Objective]
        .progress_for(chain_id) -> tuple[Objective, ...]
        .all_complete(chain_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ObjectiveKind(str, enum.Enum):
    KILL_NM = "kill_nm"
    MINIGAME = "minigame"
    QUEST_STEP = "quest_step"


class ObjectiveStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# AOE oxygen tank parameters
OXYGEN_TANK_BONUS_SECONDS = 5 * 60   # +5 minutes
OXYGEN_TANK_RADIUS_YALMS = 30


@dataclasses.dataclass(frozen=True)
class Objective:
    objective_id: str
    kind: ObjectiveKind
    label: str
    nm_id: t.Optional[str] = None     # required if KILL_NM
    oxygen_drop: bool = False         # if True, drops AOE tank on kill
    minigame_seconds: int = 0


@dataclasses.dataclass(frozen=True)
class ObjectiveResult:
    accepted: bool
    objective_completed: bool = False
    oxygen_tank_dropped: bool = False
    chain_failed: bool = False
    next_objective_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _ChainState:
    chain_id: str
    zone_id: str
    phase: int
    objectives: list[Objective]
    statuses: list[ObjectiveStatus]
    cursor: int = 0   # index of next pending objective
    failed: bool = False


@dataclasses.dataclass
class ConquestObjectives:
    _chains: dict[str, _ChainState] = dataclasses.field(default_factory=dict)

    def register_chain(
        self, *, chain_id: str,
        zone_id: str, phase: int,
        objectives: t.Iterable[Objective],
    ) -> bool:
        if not chain_id or chain_id in self._chains:
            return False
        objs = list(objectives)
        if not objs:
            return False
        # validate KILL_NM objectives have nm_id
        ids = set()
        for o in objs:
            if not o.objective_id or o.objective_id in ids:
                return False
            ids.add(o.objective_id)
            if o.kind == ObjectiveKind.KILL_NM and not o.nm_id:
                return False
        self._chains[chain_id] = _ChainState(
            chain_id=chain_id, zone_id=zone_id, phase=phase,
            objectives=objs,
            statuses=[ObjectiveStatus.PENDING] * len(objs),
        )
        return True

    def complete_objective(
        self, *, chain_id: str,
        objective_id: str,
        killed_nm_id: t.Optional[str] = None,
        now_seconds: int = 0,
    ) -> ObjectiveResult:
        c = self._chains.get(chain_id)
        if c is None:
            return ObjectiveResult(False, reason="unknown chain")
        if c.failed:
            return ObjectiveResult(False, reason="chain failed")
        if c.cursor >= len(c.objectives):
            return ObjectiveResult(False, reason="chain complete")
        expected = c.objectives[c.cursor]
        if expected.objective_id != objective_id:
            # out of order — fail the chain
            c.failed = True
            return ObjectiveResult(
                False, chain_failed=True,
                reason="out-of-order objective",
            )
        # for KILL_NM, the killed NM must match
        if expected.kind == ObjectiveKind.KILL_NM:
            if killed_nm_id != expected.nm_id:
                c.failed = True
                return ObjectiveResult(
                    False, chain_failed=True,
                    reason="wrong nm killed",
                )
        # accepted
        c.statuses[c.cursor] = ObjectiveStatus.COMPLETED
        c.cursor += 1
        next_id = (
            c.objectives[c.cursor].objective_id
            if c.cursor < len(c.objectives)
            else None
        )
        return ObjectiveResult(
            accepted=True,
            objective_completed=True,
            oxygen_tank_dropped=(
                expected.kind == ObjectiveKind.KILL_NM
                and expected.oxygen_drop
            ),
            next_objective_id=next_id,
        )

    def current_objective(
        self, *, chain_id: str,
    ) -> t.Optional[Objective]:
        c = self._chains.get(chain_id)
        if c is None or c.failed or c.cursor >= len(c.objectives):
            return None
        return c.objectives[c.cursor]

    def progress_for(
        self, *, chain_id: str,
    ) -> tuple[Objective, ...]:
        c = self._chains.get(chain_id)
        if c is None:
            return ()
        return tuple(
            c.objectives[i]
            for i in range(c.cursor)
        )

    def all_complete(self, *, chain_id: str) -> bool:
        c = self._chains.get(chain_id)
        if c is None or c.failed:
            return False
        return c.cursor >= len(c.objectives)


__all__ = [
    "ObjectiveKind", "ObjectiveStatus", "Objective",
    "ObjectiveResult", "ConquestObjectives",
    "OXYGEN_TANK_BONUS_SECONDS", "OXYGEN_TANK_RADIUS_YALMS",
]
