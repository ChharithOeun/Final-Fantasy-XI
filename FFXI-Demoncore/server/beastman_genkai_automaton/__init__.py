"""Beastman genkai — Maat-equivalent automaton trial chain.

A beastman doesn't go to Maat. They climb the IRON CRADLE
PROVING GROUND and face an awakened automaton — IRON_MAAT — at
the end of each level cap. Each genkai stage must be cleared
to proceed past the corresponding cap, mirroring the canon
Maat fight progression: 50, 55, 60, 65, 70, 75 — and a final
GRAND_PROOF unlocks the SECOND SUBJOB slot.

Public surface
--------------
    GenkaiStage enum      LEVEL_50 / 55 / 60 / 65 / 70 / 75 /
                          GRAND_PROOF (unlocks 2nd sub)
    StageStatus enum
    StageProgress dataclass
    BeastmanGenkaiAutomaton
        .start_stage(player_id, stage, current_level)
        .complete_stage(player_id, stage)
        .can_proceed_past(player_id, target_level) -> bool
        .has_second_subjob_slot(player_id) -> bool
        .progress_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GenkaiStage(str, enum.Enum):
    LEVEL_50 = "level_50"
    LEVEL_55 = "level_55"
    LEVEL_60 = "level_60"
    LEVEL_65 = "level_65"
    LEVEL_70 = "level_70"
    LEVEL_75 = "level_75"
    GRAND_PROOF = "grand_proof"   # unlocks 2nd subjob slot


_STAGE_GATE_LEVEL: dict[GenkaiStage, int] = {
    GenkaiStage.LEVEL_50: 50,
    GenkaiStage.LEVEL_55: 55,
    GenkaiStage.LEVEL_60: 60,
    GenkaiStage.LEVEL_65: 65,
    GenkaiStage.LEVEL_70: 70,
    GenkaiStage.LEVEL_75: 75,
    GenkaiStage.GRAND_PROOF: 75,    # also requires 75 cap
}


# Stage order — also encodes prereq sequencing.
_STAGE_ORDER: tuple[GenkaiStage, ...] = tuple(GenkaiStage)


class StageStatus(str, enum.Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass
class StageProgress:
    player_id: str
    stage: GenkaiStage
    status: StageStatus = StageStatus.IN_PROGRESS
    started_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    stage: GenkaiStage
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    stage: GenkaiStage
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanGenkaiAutomaton:
    _progress: dict[
        tuple[str, GenkaiStage], StageProgress,
    ] = dataclasses.field(default_factory=dict)

    def _completed_stages(
        self, player_id: str,
    ) -> set[GenkaiStage]:
        return {
            s for (pid, s), prog in self._progress.items()
            if pid == player_id
            and prog.status == StageStatus.COMPLETE
        }

    def start_stage(
        self, *, player_id: str,
        stage: GenkaiStage,
        current_level: int,
        now_seconds: float = 0.0,
    ) -> StartResult:
        if current_level < _STAGE_GATE_LEVEL[stage]:
            return StartResult(
                False, stage=stage,
                reason=(
                    f"level < {_STAGE_GATE_LEVEL[stage]}"
                ),
            )
        # Sequencing: must complete all prior stages
        idx = _STAGE_ORDER.index(stage)
        completed = self._completed_stages(player_id)
        for prior in _STAGE_ORDER[:idx]:
            if prior not in completed:
                return StartResult(
                    False, stage=stage,
                    reason=(
                        f"prior stage {prior.value}"
                        " not complete"
                    ),
                )
        key = (player_id, stage)
        if key in self._progress:
            return StartResult(
                False, stage=stage,
                reason="already started",
            )
        self._progress[key] = StageProgress(
            player_id=player_id, stage=stage,
            started_at_seconds=now_seconds,
            status=StageStatus.IN_PROGRESS,
        )
        return StartResult(accepted=True, stage=stage)

    def complete_stage(
        self, *, player_id: str,
        stage: GenkaiStage,
        now_seconds: float = 0.0,
    ) -> CompleteResult:
        prog = self._progress.get((player_id, stage))
        if prog is None:
            return CompleteResult(
                False, stage=stage,
                reason="not started",
            )
        if prog.status != StageStatus.IN_PROGRESS:
            return CompleteResult(
                False, stage=stage,
                reason="not in progress",
            )
        prog.status = StageStatus.COMPLETE
        prog.completed_at_seconds = now_seconds
        return CompleteResult(accepted=True, stage=stage)

    def has_completed_stage(
        self, *, player_id: str, stage: GenkaiStage,
    ) -> bool:
        return stage in self._completed_stages(player_id)

    def can_proceed_past(
        self, *, player_id: str, target_level: int,
    ) -> bool:
        """Required: have completed every cap-breaker through
        target_level - 1. e.g. to go past 60 you need LEVEL_60
        cleared (which gates 60->61)."""
        completed = self._completed_stages(player_id)
        for stage in _STAGE_ORDER:
            if stage == GenkaiStage.GRAND_PROOF:
                continue
            gate = _STAGE_GATE_LEVEL[stage]
            if (
                target_level > gate
                and stage not in completed
            ):
                return False
        return True

    def has_second_subjob_slot(
        self, *, player_id: str,
    ) -> bool:
        return GenkaiStage.GRAND_PROOF in (
            self._completed_stages(player_id)
        )

    def progress_for(
        self, *, player_id: str,
    ) -> tuple[StageProgress, ...]:
        rows = [
            prog for (pid, _), prog in self._progress.items()
            if pid == player_id
        ]
        rows.sort(
            key=lambda p: _STAGE_ORDER.index(p.stage),
        )
        return tuple(rows)

    def total_progress(self) -> int:
        return len(self._progress)


__all__ = [
    "GenkaiStage", "StageStatus",
    "StageProgress",
    "StartResult", "CompleteResult",
    "BeastmanGenkaiAutomaton",
]
