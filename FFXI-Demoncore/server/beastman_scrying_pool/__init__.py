"""Beastman scrying pool — Lamia divination system.

The Lamia keep SCRYING POOLS in their tidegrottos — quiet
mirror-pools that, when activated with FOCUS POINTS (a
trading currency from sea-fishing), grant a glimpse of the
near future. Each scry returns a SCRY OUTCOME — a structured
hint about an upcoming world event the engine has scheduled
(NM spawn, festival window, weather shift, raid call).

Scries have a RANK (LIGHT / DEEP / TRUE) — higher ranks cost
more focus and reveal events further out / with more detail,
but each player can only run a TRUE scry once per real-world
day (cooldown).

Public surface
--------------
    ScryRank enum
    ScryOutcome dataclass
    BeastmanScryingPool
        .grant_focus(player_id, amount)
        .focus_for(player_id)
        .scry(player_id, rank, now_seconds, scheduled_events)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ScryRank(str, enum.Enum):
    LIGHT = "light"
    DEEP = "deep"
    TRUE = "true"


_RANK_COST: dict[ScryRank, int] = {
    ScryRank.LIGHT: 5,
    ScryRank.DEEP: 25,
    ScryRank.TRUE: 100,
}


_RANK_HORIZON_SECONDS: dict[ScryRank, int] = {
    ScryRank.LIGHT: 600,        # next 10 min
    ScryRank.DEEP: 7_200,       # next 2 hours
    ScryRank.TRUE: 86_400,      # next day
}


_TRUE_COOLDOWN_SECONDS = 86_400


@dataclasses.dataclass(frozen=True)
class ScheduledEvent:
    event_id: str
    fires_at: int
    short_description: str


@dataclasses.dataclass(frozen=True)
class ScryHit:
    event_id: str
    fires_at: int
    short_description: str


@dataclasses.dataclass(frozen=True)
class ScryOutcome:
    accepted: bool
    rank: ScryRank
    focus_charged: int = 0
    hits: tuple[ScryHit, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanScryingPool:
    _focus: dict[str, int] = dataclasses.field(default_factory=dict)
    _last_true_at: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def grant_focus(
        self, *, player_id: str, amount: int,
    ) -> bool:
        if amount <= 0:
            return False
        self._focus[player_id] = self._focus.get(player_id, 0) + amount
        return True

    def focus_for(self, *, player_id: str) -> int:
        return self._focus.get(player_id, 0)

    def scry(
        self, *, player_id: str,
        rank: ScryRank,
        now_seconds: int,
        scheduled_events: tuple[ScheduledEvent, ...],
    ) -> ScryOutcome:
        cost = _RANK_COST[rank]
        balance = self._focus.get(player_id, 0)
        if balance < cost:
            return ScryOutcome(
                False, rank, reason="insufficient focus",
            )
        if rank == ScryRank.TRUE:
            last = self._last_true_at.get(player_id)
            if (
                last is not None
                and now_seconds - last < _TRUE_COOLDOWN_SECONDS
            ):
                return ScryOutcome(
                    False, rank, reason="true scry cooldown",
                )
        horizon = now_seconds + _RANK_HORIZON_SECONDS[rank]
        # Filter events in window, sort by fires_at then event_id
        in_window = [
            e for e in scheduled_events
            if now_seconds <= e.fires_at <= horizon
        ]
        in_window.sort(key=lambda e: (e.fires_at, e.event_id))
        hits = tuple(
            ScryHit(
                event_id=e.event_id,
                fires_at=e.fires_at,
                short_description=e.short_description,
            )
            for e in in_window
        )
        # Charge focus
        self._focus[player_id] = balance - cost
        if rank == ScryRank.TRUE:
            self._last_true_at[player_id] = now_seconds
        return ScryOutcome(
            accepted=True,
            rank=rank,
            focus_charged=cost,
            hits=hits,
        )

    def total_players_with_focus(self) -> int:
        return sum(1 for v in self._focus.values() if v > 0)


__all__ = [
    "ScryRank", "ScheduledEvent",
    "ScryHit", "ScryOutcome",
    "BeastmanScryingPool",
]
