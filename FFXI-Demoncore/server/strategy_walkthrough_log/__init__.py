"""Strategy walkthrough log — runs against a guide + win rate.

When a player engages an encounter with an adopted guide
pinned, the encounter result (win or wipe) gets recorded
against THAT guide. Over time, each guide accumulates a
real-world win rate that's distinct from the author's
personal clear rate at publish time.

That's the "does this guide actually work for OTHER
people" signal. If Chharith's RDM-soloes-Maat guide has
20% win rate when Bobs and Caras try it, the gallery
should label it "expert difficulty" or surface a warning.

Logged result kinds:
    WIN       cleared the encounter
    WIPE      whole party died
    BAILED    player disengaged before resolution
              (counts neither for nor against the guide
              — incomplete data)

The log is per (guide_id, run_id) so a player who runs
the same guide 10 times produces 10 entries. Walkthroughs
are aggregated to give:
    runs_total
    wins
    wipes
    bailed
    win_rate (wins / (wins + wipes); bailed excluded)

A 7-day rolling window slice is also supported so the UI
can flag "win rate dropped this week" — useful when a
patch invalidates an old strat.

Public surface
--------------
    RunResult enum
    WalkthroughEntry dataclass (frozen)
    GuideStats dataclass (frozen)
    StrategyWalkthroughLog
        .record_run(player_id, guide_id, result, ran_at)
            -> Optional[WalkthroughEntry]
        .stats_for(guide_id) -> GuideStats
        .stats_for_window(guide_id, now, day_window)
            -> GuideStats
        .runs_for_player(player_id, guide_id)
            -> list[WalkthroughEntry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_SECONDS_PER_DAY = 86400


class RunResult(str, enum.Enum):
    WIN = "win"
    WIPE = "wipe"
    BAILED = "bailed"


@dataclasses.dataclass(frozen=True)
class WalkthroughEntry:
    player_id: str
    guide_id: str
    result: RunResult
    ran_at: int


@dataclasses.dataclass(frozen=True)
class GuideStats:
    guide_id: str
    runs_total: int
    wins: int
    wipes: int
    bailed: int
    win_rate: float


@dataclasses.dataclass
class StrategyWalkthroughLog:
    _entries: list[WalkthroughEntry] = dataclasses.field(
        default_factory=list,
    )

    def record_run(
        self, *, player_id: str, guide_id: str,
        result: RunResult, ran_at: int,
    ) -> t.Optional[WalkthroughEntry]:
        if not player_id or not guide_id:
            return None
        e = WalkthroughEntry(
            player_id=player_id, guide_id=guide_id,
            result=result, ran_at=ran_at,
        )
        self._entries.append(e)
        return e

    def _aggregate(
        self, *, guide_id: str,
        entries: list[WalkthroughEntry],
    ) -> GuideStats:
        wins = wipes = bailed = 0
        for e in entries:
            if e.guide_id != guide_id:
                continue
            if e.result == RunResult.WIN:
                wins += 1
            elif e.result == RunResult.WIPE:
                wipes += 1
            else:
                bailed += 1
        decisive = wins + wipes
        win_rate = wins / decisive if decisive else 0.0
        return GuideStats(
            guide_id=guide_id,
            runs_total=wins + wipes + bailed,
            wins=wins, wipes=wipes, bailed=bailed,
            win_rate=win_rate,
        )

    def stats_for(self, *, guide_id: str) -> GuideStats:
        return self._aggregate(
            guide_id=guide_id, entries=self._entries,
        )

    def stats_for_window(
        self, *, guide_id: str, now: int, day_window: int,
    ) -> GuideStats:
        if day_window <= 0:
            return GuideStats(
                guide_id=guide_id, runs_total=0,
                wins=0, wipes=0, bailed=0, win_rate=0.0,
            )
        cutoff = now - (day_window * _SECONDS_PER_DAY)
        recent = [
            e for e in self._entries if e.ran_at >= cutoff
        ]
        return self._aggregate(
            guide_id=guide_id, entries=recent,
        )

    def runs_for_player(
        self, *, player_id: str, guide_id: str,
    ) -> list[WalkthroughEntry]:
        out = [
            e for e in self._entries
            if e.player_id == player_id
            and e.guide_id == guide_id
        ]
        out.sort(key=lambda e: e.ran_at)
        return out

    def total_runs(self) -> int:
        return len(self._entries)


__all__ = [
    "RunResult", "WalkthroughEntry", "GuideStats",
    "StrategyWalkthroughLog",
]
