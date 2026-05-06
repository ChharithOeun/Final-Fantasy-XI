"""Lifetime dive log — permanent per-player underwater stats.

Every dive matters. The log accumulates lifetime totals
that never reset, plus all-time bests:

    deepest_dive_meters       - highest depth ever reached
    longest_session_seconds   - longest single dive
    total_kraken_kills        - sum across all kraken-family
    total_wrecks_salvaged     - count of wrecks completed
    total_landmarks_found     - cloud + seafloor combined
    longest_drowned_pact      - longest active pact streak

Plus per-stat global leaderboards: top 100 players in each
category. The leaderboard is stable — sorted by stat value
desc, with player_id as tiebreaker.

Public surface
--------------
    DiveStats dataclass (frozen)
    LifetimeDiveLog
        .record_dive(player_id, depth_m, duration_seconds,
                     pact_active)
        .record_kraken_kill(player_id)
        .record_wreck_salvaged(player_id)
        .record_landmark_found(player_id)
        .stats_for(player_id) -> DiveStats
        .leaderboard(stat, top_n=100)
            -> tuple[(player_id, value), ...]
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class _PlayerStats:
    deepest_dive_meters: float = 0.0
    longest_session_seconds: int = 0
    total_kraken_kills: int = 0
    total_wrecks_salvaged: int = 0
    total_landmarks_found: int = 0
    longest_drowned_pact: int = 0  # max consecutive pact-active dives


@dataclasses.dataclass(frozen=True)
class DiveStats:
    deepest_dive_meters: float
    longest_session_seconds: int
    total_kraken_kills: int
    total_wrecks_salvaged: int
    total_landmarks_found: int
    longest_drowned_pact: int


_LEADERBOARD_STATS = {
    "deepest_dive_meters",
    "longest_session_seconds",
    "total_kraken_kills",
    "total_wrecks_salvaged",
    "total_landmarks_found",
    "longest_drowned_pact",
}


@dataclasses.dataclass
class LifetimeDiveLog:
    _stats: dict[str, _PlayerStats] = dataclasses.field(default_factory=dict)
    # tracks current pact streak per player (resets on non-pact dive)
    _pact_streak: dict[str, int] = dataclasses.field(default_factory=dict)

    def record_dive(
        self, *, player_id: str,
        depth_m: float,
        duration_seconds: int,
        pact_active: bool = False,
    ) -> bool:
        if not player_id:
            return False
        s = self._stats.setdefault(player_id, _PlayerStats())
        if depth_m > s.deepest_dive_meters:
            s.deepest_dive_meters = depth_m
        if duration_seconds > s.longest_session_seconds:
            s.longest_session_seconds = duration_seconds
        # pact streak: count consecutive dives where pact_active=True
        if pact_active:
            cur = self._pact_streak.get(player_id, 0) + 1
            self._pact_streak[player_id] = cur
            if cur > s.longest_drowned_pact:
                s.longest_drowned_pact = cur
        else:
            self._pact_streak[player_id] = 0
        return True

    def record_kraken_kill(self, *, player_id: str) -> bool:
        if not player_id:
            return False
        s = self._stats.setdefault(player_id, _PlayerStats())
        s.total_kraken_kills += 1
        return True

    def record_wreck_salvaged(self, *, player_id: str) -> bool:
        if not player_id:
            return False
        s = self._stats.setdefault(player_id, _PlayerStats())
        s.total_wrecks_salvaged += 1
        return True

    def record_landmark_found(self, *, player_id: str) -> bool:
        if not player_id:
            return False
        s = self._stats.setdefault(player_id, _PlayerStats())
        s.total_landmarks_found += 1
        return True

    def stats_for(self, *, player_id: str) -> DiveStats:
        s = self._stats.get(player_id) or _PlayerStats()
        return DiveStats(
            deepest_dive_meters=s.deepest_dive_meters,
            longest_session_seconds=s.longest_session_seconds,
            total_kraken_kills=s.total_kraken_kills,
            total_wrecks_salvaged=s.total_wrecks_salvaged,
            total_landmarks_found=s.total_landmarks_found,
            longest_drowned_pact=s.longest_drowned_pact,
        )

    def leaderboard(
        self, *, stat: str, top_n: int = 100,
    ) -> tuple[tuple[str, float], ...]:
        if stat not in _LEADERBOARD_STATS:
            return ()
        rows = []
        for pid, s in self._stats.items():
            value = getattr(s, stat)
            if value > 0:
                rows.append((pid, value))
        # sort by value desc, then player_id asc for stable tiebreak
        rows.sort(key=lambda r: (-r[1], r[0]))
        return tuple(rows[:top_n])


__all__ = [
    "DiveStats", "LifetimeDiveLog",
]
