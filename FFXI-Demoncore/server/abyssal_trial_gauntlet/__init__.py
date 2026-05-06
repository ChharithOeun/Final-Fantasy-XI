"""Abyssal Trial Gauntlet — solo personal-skill challenge.

A 7-stage solo run through escalating depths. No party, no
trusts, no pets — just the player against scaling encounters.
Each stage clears in DURATION_PER_STAGE seconds; failing
the timer or dying ends the run.

Players collect a TIER_TOKEN at each cleared stage. All 7
tokens together unlock entry to the Abyssal Throne T7 fight
(THE_DROWNED_KING) — the only solo-earned T7 ticket. Each
stage may be replayed individually, but the run only
counts as "complete" if all 7 are cleared in a single
session within MAX_RUN_SECONDS.

Public surface
--------------
    GauntletStage int enum
    StageResult dataclass (frozen)
    AbyssalTrialGauntlet
        .start_run(player_id, now_seconds)
        .clear_stage(player_id, stage, cleared_in_seconds,
                     now_seconds)
        .fail_run(player_id, reason, now_seconds)
        .tokens_held(player_id) -> tuple[GauntletStage, ...]
        .full_run_completed(player_id) -> bool
        .current_stage(player_id) -> Optional[GauntletStage]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GauntletStage(int, enum.Enum):
    SHALLOW_TIDE = 1
    KELP_LABYRINTH = 2
    SAHUAGIN_GAUNTLET = 3
    HYDROTHERMAL_RUSH = 4
    SHARK_BOUND = 5
    ABYSS_DESCENT = 6
    DROWNED_VOW = 7


# canonical timer per stage in seconds (escalating difficulty)
DURATION_PER_STAGE: dict[GauntletStage, int] = {
    GauntletStage.SHALLOW_TIDE: 180,
    GauntletStage.KELP_LABYRINTH: 240,
    GauntletStage.SAHUAGIN_GAUNTLET: 300,
    GauntletStage.HYDROTHERMAL_RUSH: 360,
    GauntletStage.SHARK_BOUND: 420,
    GauntletStage.ABYSS_DESCENT: 480,
    GauntletStage.DROWNED_VOW: 600,
}

# total run must complete within this for "full run" credit
MAX_RUN_SECONDS = sum(DURATION_PER_STAGE.values()) * 2  # generous buffer


@dataclasses.dataclass(frozen=True)
class StageResult:
    stage: GauntletStage
    cleared_at: int
    cleared_in_seconds: int


@dataclasses.dataclass
class _RunState:
    player_id: str
    started_at: int
    cleared: list[StageResult] = dataclasses.field(default_factory=list)
    failed: bool = False


@dataclasses.dataclass
class AbyssalTrialGauntlet:
    _runs: dict[str, _RunState] = dataclasses.field(default_factory=dict)
    # historic completed full-runs per player
    _full_runs: dict[str, int] = dataclasses.field(default_factory=dict)

    def start_run(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        if not player_id:
            return False
        # any existing run is wiped — only one active run per player
        self._runs[player_id] = _RunState(
            player_id=player_id, started_at=now_seconds,
        )
        return True

    def clear_stage(
        self, *, player_id: str,
        stage: GauntletStage,
        cleared_in_seconds: int,
        now_seconds: int,
    ) -> bool:
        r = self._runs.get(player_id)
        if r is None or r.failed:
            return False
        # must clear stages in order
        next_stage = GauntletStage(len(r.cleared) + 1)
        if stage != next_stage:
            return False
        # under timer?
        if cleared_in_seconds > DURATION_PER_STAGE[stage]:
            r.failed = True
            return False
        # under max-run window?
        if (now_seconds - r.started_at) > MAX_RUN_SECONDS:
            r.failed = True
            return False
        r.cleared.append(StageResult(
            stage=stage,
            cleared_at=now_seconds,
            cleared_in_seconds=cleared_in_seconds,
        ))
        # full run on the 7th clear
        if len(r.cleared) == len(GauntletStage):
            self._full_runs[player_id] = self._full_runs.get(player_id, 0) + 1
        return True

    def fail_run(
        self, *, player_id: str, reason: str,
        now_seconds: int,
    ) -> bool:
        r = self._runs.get(player_id)
        if r is None:
            return False
        r.failed = True
        return True

    def tokens_held(
        self, *, player_id: str,
    ) -> tuple[GauntletStage, ...]:
        r = self._runs.get(player_id)
        if r is None:
            return ()
        return tuple(s.stage for s in r.cleared)

    def full_run_completed(
        self, *, player_id: str,
    ) -> bool:
        return self._full_runs.get(player_id, 0) > 0

    def current_stage(
        self, *, player_id: str,
    ) -> t.Optional[GauntletStage]:
        r = self._runs.get(player_id)
        if r is None or r.failed:
            return None
        next_idx = len(r.cleared) + 1
        if next_idx > len(GauntletStage):
            return None
        return GauntletStage(next_idx)


__all__ = [
    "GauntletStage", "StageResult", "AbyssalTrialGauntlet",
    "DURATION_PER_STAGE", "MAX_RUN_SECONDS",
]
