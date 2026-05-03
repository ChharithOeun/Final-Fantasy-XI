"""AI reflection cycle — nightly distillation pass.

Each in-game night, the orchestrator runs a "reflection" pass on
the live AI entities. This is the world's THINKING TIME — the
pass that distills the day into long-term beliefs, prunes
trivial events, updates goals based on what just happened, and
lets factions update their strategic posture.

Without this, AI agents drift: their memory grows unbounded,
their goals stay stale, their factions hold yesterday's plans
forever. With it, the world feels like it's *processing* what
happened — which it actually is.

Cycle steps (run in order)
--------------------------
1) MEMORY_COMPACT — drop zero-salience memories from each
   entity_memory store.
2) GOAL_REVIEW — for each NPC with a goal stack, advance
   completed-goal cleanup; flag stalled goals.
3) FACTION_REVIEW — beastmen factions reassess stance
   based on threat ranking and committed forces.
4) RUMOR_AGE — rumors past their stale window get compacted.
5) ECONOMY_REGULATOR_TICK — supply/demand snapshot drives
   regulator decisions.

This module is the SCHEDULER + ORCHESTRATOR for those passes.
It exposes a simple `run_cycle(now_seconds)` entry point. Each
sub-pass is pluggable via callbacks so tests can stub them.

Public surface
--------------
    CycleStage enum
    StageResult dataclass — counters per stage
    CycleReport dataclass — full report
    ReflectionCycle
        .register_stage(stage, callable)
        .run_cycle(now_seconds) -> CycleReport
        .last_run_at() / .runs_completed()
"""
from __future__ import annotations

import dataclasses
import enum
import time
import typing as t


# Default night-hour window for cycle to run.
DEFAULT_REFLECTION_HOUR = 4   # 4am Vana'diel time


class CycleStage(str, enum.Enum):
    MEMORY_COMPACT = "memory_compact"
    GOAL_REVIEW = "goal_review"
    FACTION_REVIEW = "faction_review"
    RUMOR_AGE = "rumor_age"
    ECONOMY_REGULATOR_TICK = "economy_regulator_tick"


# Canonical run order.
DEFAULT_STAGE_ORDER: tuple[CycleStage, ...] = (
    CycleStage.MEMORY_COMPACT,
    CycleStage.GOAL_REVIEW,
    CycleStage.FACTION_REVIEW,
    CycleStage.RUMOR_AGE,
    CycleStage.ECONOMY_REGULATOR_TICK,
)


@dataclasses.dataclass(frozen=True)
class StageResult:
    stage: CycleStage
    success: bool
    items_processed: int = 0
    duration_ms: float = 0.0
    error: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CycleReport:
    started_at_seconds: float
    completed_at_seconds: float
    cycle_number: int
    stages: tuple[StageResult, ...]

    @property
    def total_items_processed(self) -> int:
        return sum(s.items_processed for s in self.stages)

    @property
    def all_succeeded(self) -> bool:
        return all(s.success for s in self.stages)


# Stage callback signature: takes now_seconds, returns
# items_processed (int). Raises on failure.
StageCallback = t.Callable[[float], int]


@dataclasses.dataclass
class ReflectionCycle:
    stage_order: tuple[CycleStage, ...] = DEFAULT_STAGE_ORDER
    _callbacks: dict[
        CycleStage, StageCallback,
    ] = dataclasses.field(default_factory=dict)
    _runs_completed: int = 0
    _last_run_at_seconds: t.Optional[float] = None
    _last_report: t.Optional[CycleReport] = None

    def register_stage(
        self, *, stage: CycleStage, callback: StageCallback,
    ) -> None:
        self._callbacks[stage] = callback

    def has_stage(self, stage: CycleStage) -> bool:
        return stage in self._callbacks

    def run_cycle(self, *, now_seconds: float) -> CycleReport:
        start_perf = time.perf_counter()
        results: list[StageResult] = []
        for stage in self.stage_order:
            cb = self._callbacks.get(stage)
            stage_start = time.perf_counter()
            if cb is None:
                results.append(StageResult(
                    stage=stage, success=True,
                    items_processed=0,
                    duration_ms=0.0,
                ))
                continue
            try:
                processed = cb(now_seconds)
                duration_ms = (
                    time.perf_counter() - stage_start
                ) * 1000
                results.append(StageResult(
                    stage=stage, success=True,
                    items_processed=processed,
                    duration_ms=duration_ms,
                ))
            except Exception as exc:
                duration_ms = (
                    time.perf_counter() - stage_start
                ) * 1000
                results.append(StageResult(
                    stage=stage, success=False,
                    items_processed=0,
                    duration_ms=duration_ms,
                    error=str(exc),
                ))
        self._runs_completed += 1
        self._last_run_at_seconds = now_seconds
        finished = now_seconds + (
            time.perf_counter() - start_perf
        )
        report = CycleReport(
            started_at_seconds=now_seconds,
            completed_at_seconds=finished,
            cycle_number=self._runs_completed,
            stages=tuple(results),
        )
        self._last_report = report
        return report

    def last_run_at(self) -> t.Optional[float]:
        return self._last_run_at_seconds

    def runs_completed(self) -> int:
        return self._runs_completed

    def last_report(self) -> t.Optional[CycleReport]:
        return self._last_report


def should_run_cycle(
    *, hour_of_day: int,
    last_run_at_seconds: t.Optional[float],
    now_seconds: float,
    target_hour: int = DEFAULT_REFLECTION_HOUR,
    cooldown_seconds: float = 60 * 60 * 12,
) -> bool:
    """Decision helper: should the cycle run NOW?

    Triggers when the current hour matches the target reflection
    hour AND it's been at least cooldown_seconds since the last
    run (so a long-paused server doesn't ping a dozen cycles in
    a row when hours catch up)."""
    if hour_of_day % 24 != target_hour:
        return False
    if last_run_at_seconds is None:
        return True
    return (now_seconds - last_run_at_seconds) >= cooldown_seconds


__all__ = [
    "DEFAULT_REFLECTION_HOUR", "DEFAULT_STAGE_ORDER",
    "CycleStage", "StageResult", "CycleReport",
    "StageCallback", "ReflectionCycle",
    "should_run_cycle",
]
