"""World-first detector — automatic ledger feed for kill events.

Boss kills happen all the time. Most are routine. A few
are world-firsts: nobody on this server has ever felled
this NM/HNM/world-boss before. The detector watches kill
events and decides:
   - is this a WORLD_FIRST? (first ever)
   - is this a SECOND_KILL? (second team to fell it)
   - is it a SPEED_RECORD? (fastest tracked time)

When yes, it returns the event payload that should go to
server_history_log.record_event(). The detector itself
keeps a tiny state cache (per-boss kill counter + best
time) — it does NOT write to the ledger directly. That
keeps it composable with whatever event bus the live game
runs.

Public surface
--------------
    KillEvent dataclass (frozen)
    DetectorResult dataclass (frozen) — kind / summary / value
        kind=None when nothing notable happened
    WorldFirstDetector
        .observe_kill(boss_id, party_member_ids,
                      kill_duration_seconds, killed_at)
            -> DetectorResult
        .total_known_bosses() -> int
        .best_time_for(boss_id) -> Optional[int]
        .kills_for(boss_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.server_history_log import EventKind


@dataclasses.dataclass(frozen=True)
class KillEvent:
    boss_id: str
    party_member_ids: tuple[str, ...]
    kill_duration_seconds: int
    killed_at: int


@dataclasses.dataclass(frozen=True)
class DetectorResult:
    kind: t.Optional[EventKind]
    summary: str
    participants: tuple[str, ...]
    boss_id: str
    value: t.Optional[int]
    recorded_at: int


@dataclasses.dataclass
class _BossState:
    kill_count: int = 0
    best_time: t.Optional[int] = None


@dataclasses.dataclass
class WorldFirstDetector:
    _bosses: dict[str, _BossState] = dataclasses.field(
        default_factory=dict,
    )

    def observe_kill(
        self, *, boss_id: str,
        party_member_ids: t.Iterable[str],
        kill_duration_seconds: int,
        killed_at: int,
    ) -> DetectorResult:
        if not boss_id:
            return DetectorResult(
                kind=None, summary="", participants=(),
                boss_id="", value=None, recorded_at=killed_at,
            )
        parts = tuple(p for p in party_member_ids if p)
        if not parts:
            return DetectorResult(
                kind=None, summary="", participants=(),
                boss_id=boss_id, value=None, recorded_at=killed_at,
            )
        state = self._bosses.setdefault(boss_id, _BossState())
        state.kill_count += 1

        # WORLD_FIRST or SECOND_KILL takes priority over speed
        if state.kill_count == 1:
            state.best_time = kill_duration_seconds
            return DetectorResult(
                kind=EventKind.WORLD_FIRST_KILL,
                summary=f"World-first kill of {boss_id}",
                participants=parts, boss_id=boss_id,
                value=kill_duration_seconds,
                recorded_at=killed_at,
            )
        if state.kill_count == 2:
            if (state.best_time is None
                    or kill_duration_seconds < state.best_time):
                state.best_time = kill_duration_seconds
            return DetectorResult(
                kind=EventKind.SECOND_KILL,
                summary=f"Second kill of {boss_id}",
                participants=parts, boss_id=boss_id,
                value=kill_duration_seconds,
                recorded_at=killed_at,
            )

        # later kills: speed record only if better
        if (state.best_time is None
                or kill_duration_seconds < state.best_time):
            state.best_time = kill_duration_seconds
            return DetectorResult(
                kind=EventKind.SPEED_RECORD,
                summary=(
                    f"Speed record on {boss_id} "
                    f"({kill_duration_seconds}s)"
                ),
                participants=parts, boss_id=boss_id,
                value=kill_duration_seconds,
                recorded_at=killed_at,
            )
        return DetectorResult(
            kind=None, summary="", participants=parts,
            boss_id=boss_id, value=kill_duration_seconds,
            recorded_at=killed_at,
        )

    def total_known_bosses(self) -> int:
        return len(self._bosses)

    def best_time_for(
        self, *, boss_id: str,
    ) -> t.Optional[int]:
        s = self._bosses.get(boss_id)
        return s.best_time if s else None

    def kills_for(self, *, boss_id: str) -> int:
        s = self._bosses.get(boss_id)
        return s.kill_count if s else 0


__all__ = [
    "KillEvent", "DetectorResult", "WorldFirstDetector",
]
