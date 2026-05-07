"""GearSwap leaderboard — public ranking of GS authors.

The /lb gearswap command surfaces the famous. Three
leaderboard kinds capture different ways to be respected:

    BY_ADOPTIONS    raw install count across all your
                    published luas; rewards prolific authors
                    whose stuff gets used
    BY_UPVOTES      net thumbs (ups - downs) — rewards
                    authors people actively endorse, not
                    just install
    BY_JOB          per-job ranking; lets a player look
                    up "who's the most adopted RDM author"

A board can be filtered to last-N-days for a "hot right
now" view, or all-time for the long-haul list.

The module reads from gearswap_publisher (who authored
what), gearswap_adopt (adopt counts), and gearswap_rating
(thumb counts) — pure aggregator, owns no data.

Public surface
--------------
    BoardKind enum
    LeaderboardEntry dataclass (frozen)
    GearswapLeaderboard
        .by_adoptions(job, limit) -> list[LeaderboardEntry]
        .by_upvotes(job, limit) -> list[LeaderboardEntry]
        .by_job(job, limit) -> list[LeaderboardEntry]
        .author_rank(author_id, kind, job)
            -> Optional[int]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)
from server.gearswap_rating import GearswapRating, Thumb


class BoardKind(str, enum.Enum):
    BY_ADOPTIONS = "by_adoptions"
    BY_UPVOTES = "by_upvotes"
    BY_JOB = "by_job"


@dataclasses.dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    author_id: str
    author_display_name: str
    score: int               # adopt-count or net-thumbs
    publish_count: int       # how many luas this author has


@dataclasses.dataclass
class GearswapLeaderboard:
    _publisher: GearswapPublisher
    _adopt: GearswapAdopt
    _rating: GearswapRating

    def _live_authors(self) -> dict[str, str]:
        """author_id -> display_name across all live publishes."""
        out: dict[str, str] = {}
        for entry in self._publisher._published.values():
            if entry.status == PublishStatus.PUBLISHED:
                out[entry.author_id] = entry.author_display_name
        return out

    def _author_publishes(
        self, author_id: str, job: str = "",
    ) -> list[str]:
        """publish_ids owned by author_id (PUBLISHED only,
        optionally filtered by job)."""
        out: list[str] = []
        for entry in self._publisher.by_author(author_id=author_id):
            if entry.status != PublishStatus.PUBLISHED:
                continue
            if job and entry.job != job:
                continue
            out.append(entry.publish_id)
        return out

    def _adopts_for_author(
        self, author_id: str, job: str = "",
    ) -> int:
        return sum(
            self._adopt.adopters_count(publish_id=pid)
            for pid in self._author_publishes(author_id, job)
        )

    def _net_thumbs_for_author(
        self, author_id: str, job: str = "",
    ) -> int:
        net = 0
        for pid in self._author_publishes(author_id, job):
            s = self._rating.summary(publish_id=pid)
            net += s.thumbs_up - s.thumbs_down
        return net

    def _rank(
        self, scored: list[tuple[str, str, int]],
        limit: int,
    ) -> list[LeaderboardEntry]:
        """scored = [(author_id, name, score), ...]"""
        scored.sort(key=lambda t: (-t[2], t[0]))
        out: list[LeaderboardEntry] = []
        for i, (aid, name, score) in enumerate(scored[:limit]):
            out.append(LeaderboardEntry(
                rank=i + 1, author_id=aid,
                author_display_name=name,
                score=score,
                publish_count=len(
                    self._author_publishes(aid),
                ),
            ))
        return out

    def by_adoptions(
        self, *, job: str = "", limit: int = 25,
    ) -> list[LeaderboardEntry]:
        if limit <= 0:
            return []
        scored = [
            (aid, name, self._adopts_for_author(aid, job))
            for aid, name in self._live_authors().items()
        ]
        # filter out authors with no publishes for this job
        if job:
            scored = [
                (aid, name, s) for (aid, name, s) in scored
                if self._author_publishes(aid, job)
            ]
        return self._rank(scored, limit)

    def by_upvotes(
        self, *, job: str = "", limit: int = 25,
    ) -> list[LeaderboardEntry]:
        if limit <= 0:
            return []
        scored = [
            (aid, name, self._net_thumbs_for_author(aid, job))
            for aid, name in self._live_authors().items()
        ]
        if job:
            scored = [
                (aid, name, s) for (aid, name, s) in scored
                if self._author_publishes(aid, job)
            ]
        return self._rank(scored, limit)

    def by_job(
        self, *, job: str, limit: int = 25,
    ) -> list[LeaderboardEntry]:
        """Per-job ranking by adoption count. job is required."""
        if not job:
            return []
        return self.by_adoptions(job=job, limit=limit)

    def author_rank(
        self, *, author_id: str, kind: BoardKind, job: str = "",
    ) -> t.Optional[int]:
        if kind == BoardKind.BY_ADOPTIONS:
            board = self.by_adoptions(job=job, limit=10000)
        elif kind == BoardKind.BY_UPVOTES:
            board = self.by_upvotes(job=job, limit=10000)
        elif kind == BoardKind.BY_JOB:
            if not job:
                return None
            board = self.by_job(job=job, limit=10000)
        else:
            return None
        for entry in board:
            if entry.author_id == author_id:
                return entry.rank
        return None


__all__ = [
    "BoardKind", "LeaderboardEntry", "GearswapLeaderboard",
]
