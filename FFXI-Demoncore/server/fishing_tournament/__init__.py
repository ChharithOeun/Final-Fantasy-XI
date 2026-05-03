"""Fishing tournaments — periodic competitive fishing events.

Hosted by the Fishing Guild. Each tournament:
* runs for a fixed window (3 Vana'diel days = 3 real-time hours)
* has a target species + a leaderboard sorted by either
  WEIGHT or LENGTH (alternates per event)
* tracks each entrant's BEST single catch (not cumulative)
* pays prize tiers to top 3 finishers + a participation reward
  for everyone who registered

Prize structure (canonical):
    1st  : Big Prize — premium gear + title
    2nd  : Mid Prize — gear-grade rod + title
    3rd  : Mid Prize — premium bait stack + title
    4-10 : Small prize — gil + signed angler badge
    11+  : Participation — gil + Mog Garden seed packet

Public surface
--------------
    Tournament dataclass
    LeaderboardKind enum (WEIGHT / LENGTH)
    CatchEntry dataclass
    TournamentRegistry
        .open_tournament(...) -> bool
        .register(player_id) / .submit_catch(player_id, weight, length)
        .resolve(now) -> dict[player_id, PrizeRecord]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


TOURNAMENT_DURATION_SECONDS = 3 * 60 * 60     # 3 real-time hours


class LeaderboardKind(str, enum.Enum):
    WEIGHT = "weight"      # heaviest fish wins
    LENGTH = "length"      # longest fish wins


class TournamentState(str, enum.Enum):
    OPEN = "open"          # registration open, not yet started
    ACTIVE = "active"      # accepting catch submissions
    RESOLVED = "resolved"


@dataclasses.dataclass(frozen=True)
class PrizeRecord:
    rank: int
    title: t.Optional[str]
    items: tuple[str, ...]
    gil: int


def _prize_for_rank(rank: int) -> PrizeRecord:
    if rank == 1:
        return PrizeRecord(
            rank=1, title="Master Angler",
            items=("anglers_signed_rod_premium",
                    "fishing_master_pendant"),
            gil=100000,
        )
    if rank == 2:
        return PrizeRecord(
            rank=2, title="Champion Angler",
            items=("anglers_signed_rod_grade_a",),
            gil=50000,
        )
    if rank == 3:
        return PrizeRecord(
            rank=3, title="Veteran Angler",
            items=("premium_bait_stack",),
            gil=25000,
        )
    if 4 <= rank <= 10:
        return PrizeRecord(
            rank=rank, title="Signed Angler",
            items=("signed_angler_badge",),
            gil=5000,
        )
    return PrizeRecord(
        rank=rank, title=None,
        items=("mog_garden_seed_packet",),
        gil=500,
    )


@dataclasses.dataclass
class CatchEntry:
    player_id: str
    weight: int = 0       # in pounds
    length: int = 0       # in inches


@dataclasses.dataclass
class Tournament:
    tournament_id: str
    target_species: str
    leaderboard_kind: LeaderboardKind
    state: TournamentState = TournamentState.OPEN
    started_at_seconds: float = 0.0
    ends_at_seconds: float = 0.0
    registrations: list[str] = dataclasses.field(default_factory=list)
    best_catch: dict[str, CatchEntry] = dataclasses.field(
        default_factory=dict,
    )

    def begin(self, *, now_seconds: float) -> bool:
        if self.state != TournamentState.OPEN:
            return False
        self.state = TournamentState.ACTIVE
        self.started_at_seconds = now_seconds
        self.ends_at_seconds = (
            now_seconds + TOURNAMENT_DURATION_SECONDS
        )
        return True

    def register(self, *, player_id: str) -> bool:
        if self.state == TournamentState.RESOLVED:
            return False
        if player_id in self.registrations:
            return False
        self.registrations.append(player_id)
        return True

    def submit_catch(
        self, *, player_id: str, weight: int, length: int,
        now_seconds: float,
    ) -> bool:
        if self.state != TournamentState.ACTIVE:
            return False
        if player_id not in self.registrations:
            return False
        if now_seconds > self.ends_at_seconds:
            return False
        if weight <= 0 or length <= 0:
            return False
        existing = self.best_catch.get(player_id)
        if existing is None:
            self.best_catch[player_id] = CatchEntry(
                player_id=player_id, weight=weight, length=length,
            )
            return True
        # Update if better on the leaderboard axis
        cur_metric = (
            existing.weight if self.leaderboard_kind == LeaderboardKind.WEIGHT
            else existing.length
        )
        new_metric = (
            weight if self.leaderboard_kind == LeaderboardKind.WEIGHT
            else length
        )
        if new_metric > cur_metric:
            self.best_catch[player_id] = CatchEntry(
                player_id=player_id, weight=weight, length=length,
            )
        return True

    def resolve(
        self, *, now_seconds: float,
    ) -> dict[str, PrizeRecord]:
        if self.state == TournamentState.RESOLVED:
            return {}
        if (now_seconds < self.ends_at_seconds
                and self.state == TournamentState.ACTIVE):
            return {}
        self.state = TournamentState.RESOLVED
        # Sort entrants by leaderboard metric, descending
        sorted_entries = sorted(
            self.best_catch.values(),
            key=lambda e: (
                -e.weight if self.leaderboard_kind == LeaderboardKind.WEIGHT
                else -e.length
            ),
        )
        prizes: dict[str, PrizeRecord] = {}
        for rank, entry in enumerate(sorted_entries, start=1):
            prizes[entry.player_id] = _prize_for_rank(rank)
        # Registered but never submitted — participation prize
        for pid in self.registrations:
            if pid not in prizes:
                prizes[pid] = _prize_for_rank(99)   # always a participant
        return prizes


__all__ = [
    "TOURNAMENT_DURATION_SECONDS",
    "LeaderboardKind", "TournamentState",
    "PrizeRecord", "CatchEntry", "Tournament",
]
