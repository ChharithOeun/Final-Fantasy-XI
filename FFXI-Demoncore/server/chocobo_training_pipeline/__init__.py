"""Chocobo training pipeline — 3-phase NPC training program.

After hatching, every chick goes through a structured training
program at the BREEDER NPC:

  PHASE_ABILITY (1 month) - establishes the chick's color-tied
                            abilities (skillchain readiness,
                            elemental spell casting, signature
                            color move). MANDATORY.
  PHASE_MOUNT   (1 month) - chick can be ridden as a non-combat
                            mount. MANDATORY.
  PHASE_COMBAT  (1 month) - chick becomes a combat mount/
                            companion. OPTIONAL — can be done
                            anytime after PHASE_MOUNT completes.

Each phase requires daily/weekly training session reports plus
RARE + R/EX resources. Phases run as real-earth-time clocks
(30 days each = 2_592_000 seconds).

Public surface
--------------
    Phase enum             ABILITY / MOUNT / COMBAT
    PhaseStatus enum       NOT_STARTED / IN_PROGRESS / COMPLETED
    Pipeline dataclass
    ChocoboTrainingPipeline
        .start_phase(player_id, chick_id, phase, now_seconds,
                     resources_paid)
        .progress(player_id, chick_id, sessions_done)
        .complete_phase(player_id, chick_id, phase, now_seconds)
        .status_for(player_id, chick_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Phase(str, enum.Enum):
    ABILITY = "ability"
    MOUNT = "mount"
    COMBAT = "combat"


class PhaseStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


_PHASE_DURATION_SECONDS = 30 * 86_400
_PHASE_REQUIRED_SESSIONS = 30


@dataclasses.dataclass
class Pipeline:
    player_id: str
    chick_id: str
    statuses: dict[Phase, PhaseStatus] = dataclasses.field(
        default_factory=lambda: {
            Phase.ABILITY: PhaseStatus.NOT_STARTED,
            Phase.MOUNT: PhaseStatus.NOT_STARTED,
            Phase.COMBAT: PhaseStatus.NOT_STARTED,
        }
    )
    started_at: dict[Phase, t.Optional[int]] = dataclasses.field(
        default_factory=lambda: {p: None for p in Phase}
    )
    sessions_done: dict[Phase, int] = dataclasses.field(
        default_factory=lambda: {p: 0 for p in Phase}
    )


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    phase: Phase
    started_at: int = 0
    deadline_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ProgressResult:
    accepted: bool
    phase: Phase
    sessions_done: int
    sessions_required: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    phase: Phase
    status: PhaseStatus
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class StatusSnapshot:
    statuses: dict[Phase, PhaseStatus]


def _key(player_id: str, chick_id: str) -> tuple[str, str]:
    return (player_id, chick_id)


@dataclasses.dataclass
class ChocoboTrainingPipeline:
    _pipelines: dict[
        tuple[str, str], Pipeline,
    ] = dataclasses.field(default_factory=dict)

    def _ensure(
        self, player_id: str, chick_id: str,
    ) -> Pipeline:
        k = _key(player_id, chick_id)
        p = self._pipelines.get(k)
        if p is None:
            p = Pipeline(player_id=player_id, chick_id=chick_id)
            self._pipelines[k] = p
        return p

    def start_phase(
        self, *, player_id: str,
        chick_id: str,
        phase: Phase,
        now_seconds: int,
        resources_paid: bool,
    ) -> StartResult:
        if not resources_paid:
            return StartResult(
                False, phase, reason="resources not paid",
            )
        p = self._ensure(player_id, chick_id)
        # Phase ordering: ABILITY → MOUNT → (optional) COMBAT
        if phase == Phase.MOUNT:
            if p.statuses[Phase.ABILITY] != PhaseStatus.COMPLETED:
                return StartResult(
                    False, phase,
                    reason="ability phase not completed",
                )
        if phase == Phase.COMBAT:
            if p.statuses[Phase.MOUNT] != PhaseStatus.COMPLETED:
                return StartResult(
                    False, phase,
                    reason="mount phase not completed",
                )
        if p.statuses[phase] != PhaseStatus.NOT_STARTED:
            return StartResult(
                False, phase, reason="phase already started",
            )
        p.statuses[phase] = PhaseStatus.IN_PROGRESS
        p.started_at[phase] = now_seconds
        return StartResult(
            accepted=True, phase=phase,
            started_at=now_seconds,
            deadline_at=now_seconds + _PHASE_DURATION_SECONDS,
        )

    def progress(
        self, *, player_id: str,
        chick_id: str,
        phase: Phase,
        sessions_done: int,
    ) -> ProgressResult:
        p = self._pipelines.get(_key(player_id, chick_id))
        if p is None:
            return ProgressResult(
                False, phase, 0, _PHASE_REQUIRED_SESSIONS,
                reason="no pipeline",
            )
        if p.statuses[phase] != PhaseStatus.IN_PROGRESS:
            return ProgressResult(
                False, phase, p.sessions_done[phase],
                _PHASE_REQUIRED_SESSIONS,
                reason="phase not in progress",
            )
        if sessions_done <= 0:
            return ProgressResult(
                False, phase, p.sessions_done[phase],
                _PHASE_REQUIRED_SESSIONS,
                reason="non-positive sessions",
            )
        p.sessions_done[phase] = min(
            _PHASE_REQUIRED_SESSIONS,
            p.sessions_done[phase] + sessions_done,
        )
        return ProgressResult(
            accepted=True, phase=phase,
            sessions_done=p.sessions_done[phase],
            sessions_required=_PHASE_REQUIRED_SESSIONS,
        )

    def complete_phase(
        self, *, player_id: str,
        chick_id: str,
        phase: Phase,
        now_seconds: int,
    ) -> CompleteResult:
        p = self._pipelines.get(_key(player_id, chick_id))
        if p is None:
            return CompleteResult(
                False, phase, PhaseStatus.NOT_STARTED,
                reason="no pipeline",
            )
        if p.statuses[phase] != PhaseStatus.IN_PROGRESS:
            return CompleteResult(
                False, phase, p.statuses[phase],
                reason="phase not in progress",
            )
        if p.sessions_done[phase] < _PHASE_REQUIRED_SESSIONS:
            return CompleteResult(
                False, phase, p.statuses[phase],
                reason="sessions incomplete",
            )
        started = p.started_at[phase] or 0
        if now_seconds - started < _PHASE_DURATION_SECONDS:
            return CompleteResult(
                False, phase, p.statuses[phase],
                reason="phase duration not elapsed",
            )
        p.statuses[phase] = PhaseStatus.COMPLETED
        return CompleteResult(
            accepted=True, phase=phase,
            status=PhaseStatus.COMPLETED,
        )

    def status_for(
        self, *, player_id: str, chick_id: str,
    ) -> StatusSnapshot:
        p = self._pipelines.get(_key(player_id, chick_id))
        if p is None:
            return StatusSnapshot(
                statuses={ph: PhaseStatus.NOT_STARTED for ph in Phase},
            )
        return StatusSnapshot(statuses=dict(p.statuses))

    def total_pipelines(self) -> int:
        return len(self._pipelines)


__all__ = [
    "Phase", "PhaseStatus",
    "StartResult", "ProgressResult", "CompleteResult",
    "StatusSnapshot",
    "ChocoboTrainingPipeline",
]
