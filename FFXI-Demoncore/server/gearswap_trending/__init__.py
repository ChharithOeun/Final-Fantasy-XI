"""GearSwap trending — what's hot this week.

The "Top all-time" list rewards old prolific authors who
got in early; trending rewards luas that are picking up
NOW. A new RDM build that nailed a recent boss meta gets
its moment on the trending tab even though Chharith's
five-year-old set still has more total adopts.

Trending score, per publish, in a window:
    score = recent_adopts + (recent_thumbs_up * 2)
            - recent_thumbs_down

Recent here means events with timestamp >= (now -
window_days * 86400). Thumbs are counted at posting time.

Comments and reports are NOT in the score — they're
moderation signals, not popularity signals.

The module reads from publisher / adopt / rating; it
needs a 'thumb_posted_at' history that gearswap_rating
doesn't expose, so we instead track thumbs via a small
sidecar dataclass the trending module owns. record_thumb()
is called by the UI right after gearswap_rating.rate(),
in the same controller flow.

Public surface
--------------
    TrendingEntry dataclass (frozen)
    GearswapTrending
        .record_thumb(player_id, publish_id, thumb,
                      posted_at) -> bool
        .top(window_days, job, limit) -> list[TrendingEntry]
        .score_for(publish_id, now, window_days) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)
from server.gearswap_rating import Thumb


_SECONDS_PER_DAY = 86400


@dataclasses.dataclass(frozen=True)
class TrendingEntry:
    rank: int
    publish_id: str
    addon_id: str
    author_display_name: str
    job: str
    score: int
    recent_adopts: int
    recent_thumbs_up: int
    recent_thumbs_down: int


@dataclasses.dataclass(frozen=True)
class _ThumbEvent:
    player_id: str
    publish_id: str
    thumb: Thumb
    posted_at: int


@dataclasses.dataclass
class GearswapTrending:
    _publisher: GearswapPublisher
    _adopt: GearswapAdopt
    _now_provider: t.Callable[[], int] = lambda: 0
    _thumb_log: list[_ThumbEvent] = dataclasses.field(
        default_factory=list,
    )

    def record_thumb(
        self, *, player_id: str, publish_id: str,
        thumb: Thumb, posted_at: int,
    ) -> bool:
        if not player_id or not publish_id:
            return False
        if self._publisher.lookup(publish_id=publish_id) is None:
            return False
        self._thumb_log.append(_ThumbEvent(
            player_id=player_id, publish_id=publish_id,
            thumb=thumb, posted_at=posted_at,
        ))
        return True

    def _recent_adopts(
        self, publish_id: str, cutoff: int,
    ) -> int:
        return sum(
            1 for r in self._adopt._adoptions.values()
            if r.publish_id == publish_id
            and r.adopted_at >= cutoff
        )

    def _recent_thumbs(
        self, publish_id: str, cutoff: int,
    ) -> tuple[int, int]:
        ups = downs = 0
        for ev in self._thumb_log:
            if ev.publish_id != publish_id:
                continue
            if ev.posted_at < cutoff:
                continue
            if ev.thumb == Thumb.UP:
                ups += 1
            else:
                downs += 1
        return ups, downs

    def score_for(
        self, *, publish_id: str, now: int,
        window_days: int,
    ) -> int:
        if window_days <= 0:
            return 0
        cutoff = now - (window_days * _SECONDS_PER_DAY)
        adopts = self._recent_adopts(publish_id, cutoff)
        ups, downs = self._recent_thumbs(publish_id, cutoff)
        return adopts + ups * 2 - downs

    def top(
        self, *, now: int, window_days: int = 7,
        job: str = "", limit: int = 25,
    ) -> list[TrendingEntry]:
        if limit <= 0 or window_days <= 0:
            return []
        cutoff = now - (window_days * _SECONDS_PER_DAY)
        candidates: list[TrendingEntry] = []
        for entry in self._publisher._published.values():
            if entry.status != PublishStatus.PUBLISHED:
                continue
            if job and entry.job != job:
                continue
            adopts = self._recent_adopts(
                entry.publish_id, cutoff,
            )
            ups, downs = self._recent_thumbs(
                entry.publish_id, cutoff,
            )
            score = adopts + ups * 2 - downs
            if adopts == 0 and ups == 0 and downs == 0:
                continue   # quiet — not trending
            candidates.append(TrendingEntry(
                rank=0,   # filled after sort
                publish_id=entry.publish_id,
                addon_id=entry.addon_id,
                author_display_name=entry.author_display_name,
                job=entry.job,
                score=score, recent_adopts=adopts,
                recent_thumbs_up=ups,
                recent_thumbs_down=downs,
            ))
        candidates.sort(
            key=lambda e: (-e.score, e.publish_id),
        )
        return [
            dataclasses.replace(c, rank=i + 1)
            for i, c in enumerate(candidates[:limit])
        ]


__all__ = [
    "TrendingEntry", "GearswapTrending",
]
