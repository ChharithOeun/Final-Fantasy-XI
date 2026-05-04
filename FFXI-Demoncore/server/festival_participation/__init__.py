"""Festival participation — track players in seasonal events.

Vana'fete, Mog Bonanza, Sunbreeze, Starlight, Egg-Hunt — each
festival emits PARTICIPATION EVENTS (entered, completed a task,
collected a token, won a mini-game). Players accumulate
contribution points per festival; tiered BADGES unlock at
thresholds. A leaderboard ranks the top contributors per
festival.

A festival has a finite WINDOW. Open while
opens_at..closes_at; outside that, contributions are rejected.

Public surface
--------------
    FestivalKind enum
    EventKind enum
    BadgeTier enum
    FestivalDef dataclass
    PlayerStanding dataclass
    LeaderboardEntry dataclass
    FestivalParticipation
        .open_festival(festival_id, kind, opens_at, closes_at)
        .close_festival(festival_id)
        .record(player_id, festival_id, kind, points, at_seconds)
        .standing(player_id, festival_id) -> PlayerStanding
        .leaderboard(festival_id, top_n)
        .badges_for(player_id, festival_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FestivalKind(str, enum.Enum):
    VANAFETE = "vanafete"
    MOG_BONANZA = "mog_bonanza"
    SUNBREEZE = "sunbreeze"
    STARLIGHT = "starlight"
    EGG_HUNT = "egg_hunt"
    HARVEST = "harvest"
    DEMONCORE_REMEMBRANCE = "demoncore_remembrance"


class EventKind(str, enum.Enum):
    ENTERED = "entered"
    TASK_COMPLETED = "task_completed"
    TOKEN_COLLECTED = "token_collected"
    MINI_GAME_WIN = "mini_game_win"
    GIFT_HANDED_OUT = "gift_handed_out"


class BadgeTier(str, enum.Enum):
    NONE = "none"
    BRONZE = "bronze"        # 50 points
    SILVER = "silver"        # 200
    GOLD = "gold"            # 600
    PLATINUM = "platinum"    # 1500
    LEGENDARY = "legendary"  # 5000


_BADGE_THRESHOLDS: tuple[
    tuple[BadgeTier, int], ...,
] = (
    (BadgeTier.LEGENDARY, 5000),
    (BadgeTier.PLATINUM, 1500),
    (BadgeTier.GOLD, 600),
    (BadgeTier.SILVER, 200),
    (BadgeTier.BRONZE, 50),
)


class FestivalStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass
class FestivalDef:
    festival_id: str
    kind: FestivalKind
    opens_at_seconds: float
    closes_at_seconds: float
    status: FestivalStatus = FestivalStatus.SCHEDULED


@dataclasses.dataclass(frozen=True)
class PlayerStanding:
    player_id: str
    festival_id: str
    points: int
    badge: BadgeTier
    rank: int          # 1-based; 0 if no participation


@dataclasses.dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    player_id: str
    points: int
    badge: BadgeTier


def _badge_for_points(points: int) -> BadgeTier:
    for tier, threshold in _BADGE_THRESHOLDS:
        if points >= threshold:
            return tier
    return BadgeTier.NONE


@dataclasses.dataclass
class FestivalParticipation:
    _festivals: dict[str, FestivalDef] = dataclasses.field(
        default_factory=dict,
    )
    # (player_id, festival_id) -> total_points
    _points: dict[
        tuple[str, str], int,
    ] = dataclasses.field(default_factory=dict)

    def open_festival(
        self, *, festival_id: str,
        kind: FestivalKind,
        opens_at_seconds: float,
        closes_at_seconds: float,
    ) -> t.Optional[FestivalDef]:
        if festival_id in self._festivals:
            return None
        if closes_at_seconds <= opens_at_seconds:
            return None
        f = FestivalDef(
            festival_id=festival_id, kind=kind,
            opens_at_seconds=opens_at_seconds,
            closes_at_seconds=closes_at_seconds,
            status=FestivalStatus.OPEN,
        )
        self._festivals[festival_id] = f
        return f

    def close_festival(
        self, *, festival_id: str,
    ) -> bool:
        f = self._festivals.get(festival_id)
        if f is None or f.status == FestivalStatus.CLOSED:
            return False
        f.status = FestivalStatus.CLOSED
        return True

    def record(
        self, *, player_id: str, festival_id: str,
        kind: EventKind, points: int = 1,
        at_seconds: float = 0.0,
    ) -> bool:
        f = self._festivals.get(festival_id)
        if f is None:
            return False
        if f.status != FestivalStatus.OPEN:
            return False
        if (
            at_seconds < f.opens_at_seconds
            or at_seconds > f.closes_at_seconds
        ):
            return False
        if points <= 0:
            return False
        key = (player_id, festival_id)
        self._points[key] = (
            self._points.get(key, 0) + points
        )
        return True

    def standing(
        self, *, player_id: str, festival_id: str,
    ) -> PlayerStanding:
        if festival_id not in self._festivals:
            return PlayerStanding(
                player_id=player_id,
                festival_id=festival_id,
                points=0, badge=BadgeTier.NONE, rank=0,
            )
        points = self._points.get(
            (player_id, festival_id), 0,
        )
        if points == 0:
            return PlayerStanding(
                player_id=player_id,
                festival_id=festival_id,
                points=0, badge=BadgeTier.NONE, rank=0,
            )
        # Compute rank
        ordered = self._sorted_for_festival(festival_id)
        rank = 1
        for r, (pid, _) in enumerate(ordered, start=1):
            if pid == player_id:
                rank = r
                break
        return PlayerStanding(
            player_id=player_id,
            festival_id=festival_id,
            points=points,
            badge=_badge_for_points(points),
            rank=rank,
        )

    def _sorted_for_festival(
        self, festival_id: str,
    ) -> list[tuple[str, int]]:
        rows = [
            (pid, pts)
            for (pid, fid), pts in self._points.items()
            if fid == festival_id
        ]
        rows.sort(key=lambda r: (-r[1], r[0]))
        return rows

    def leaderboard(
        self, *, festival_id: str, top_n: int = 10,
    ) -> tuple[LeaderboardEntry, ...]:
        ordered = self._sorted_for_festival(festival_id)
        out: list[LeaderboardEntry] = []
        for rank, (pid, pts) in enumerate(
            ordered[:top_n], start=1,
        ):
            out.append(LeaderboardEntry(
                rank=rank, player_id=pid, points=pts,
                badge=_badge_for_points(pts),
            ))
        return tuple(out)

    def badges_for(
        self, *, player_id: str,
        festival_id: str,
    ) -> tuple[BadgeTier, ...]:
        """Return all earned badge tiers (bronze through highest
        unlocked)."""
        points = self._points.get(
            (player_id, festival_id), 0,
        )
        if points == 0:
            return ()
        out: list[BadgeTier] = []
        # Iterate from lowest threshold up
        for tier, threshold in reversed(_BADGE_THRESHOLDS):
            if points >= threshold:
                out.append(tier)
        return tuple(out)

    def total_festivals(self) -> int:
        return len(self._festivals)


__all__ = [
    "FestivalKind", "EventKind", "BadgeTier",
    "FestivalStatus",
    "FestivalDef", "PlayerStanding", "LeaderboardEntry",
    "FestivalParticipation",
]
