"""GearSwap author dashboard — your own publishing analytics.

When Chharith opens his author panel he wants to see, at
a glance: how many people are running my stuff, which one
is the runaway hit, where's the bleeding (downvotes /
reports), is anyone abandoning me?

This module is the per-author rollup. It reads from the
publisher, adopt, rating, and version_history modules and
returns one snapshot the UI renders.

The dashboard is intentionally read-only — it never writes.
Per-day adoption history is computed from AdoptionRecord
timestamps, bucketed into the dashboard's day_window.

Public surface
--------------
    PerLuaStats dataclass (frozen)
    AuthorDashboard dataclass (frozen)
    GearswapAuthorDashboard
        .for_author(author_id, now, day_window)
            -> Optional[AuthorDashboard]
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)
from server.gearswap_rating import GearswapRating
from server.gearswap_version_history import (
    GearswapVersionHistory,
)


_SECONDS_PER_DAY = 86400


@dataclasses.dataclass(frozen=True)
class PerLuaStats:
    publish_id: str
    addon_id: str
    job: str
    status: str   # PublishStatus value
    adopt_count: int
    thumbs_up: int
    thumbs_down: int
    report_count: int
    revision_count: int
    published_at: int


@dataclasses.dataclass(frozen=True)
class AuthorDashboard:
    author_id: str
    author_display_name: str
    total_publishes: int       # PUBLISHED + UNLISTED + REVOKED
    live_publishes: int        # PUBLISHED only
    total_adopts: int
    net_thumbs: int            # ups - downs
    total_reports: int
    adopts_in_window: int      # last `day_window` days
    luas: list[PerLuaStats]


@dataclasses.dataclass
class GearswapAuthorDashboard:
    _publisher: GearswapPublisher
    _adopt: GearswapAdopt
    _rating: GearswapRating
    _history: GearswapVersionHistory

    def _adopts_in_window(
        self, publish_ids: set[str], now: int, day_window: int,
    ) -> int:
        if day_window <= 0:
            return 0
        cutoff = now - (day_window * _SECONDS_PER_DAY)
        n = 0
        for record in self._adopt._adoptions.values():
            if record.publish_id not in publish_ids:
                continue
            if record.adopted_at >= cutoff:
                n += 1
        return n

    def for_author(
        self, *, author_id: str, now: int, day_window: int = 7,
    ) -> t.Optional[AuthorDashboard]:
        if not author_id:
            return None
        all_entries = self._publisher.by_author(
            author_id=author_id,
        )
        if not all_entries:
            return None
        # display name from the first entry (publisher
        # treats it as immutable per author once set)
        display_name = all_entries[0].author_display_name

        per_lua: list[PerLuaStats] = []
        total_adopts = 0
        net_thumbs = 0
        total_reports = 0
        live_count = 0
        for entry in all_entries:
            adopts = self._adopt.adopters_count(
                publish_id=entry.publish_id,
            )
            summary = self._rating.summary(
                publish_id=entry.publish_id,
            )
            rev = self._history.revision_count(
                publish_id=entry.publish_id,
            )
            per_lua.append(PerLuaStats(
                publish_id=entry.publish_id,
                addon_id=entry.addon_id, job=entry.job,
                status=entry.status.value,
                adopt_count=adopts,
                thumbs_up=summary.thumbs_up,
                thumbs_down=summary.thumbs_down,
                report_count=summary.report_count,
                revision_count=rev,
                published_at=entry.published_at,
            ))
            total_adopts += adopts
            net_thumbs += summary.thumbs_up - summary.thumbs_down
            total_reports += summary.report_count
            if entry.status == PublishStatus.PUBLISHED:
                live_count += 1
        # Sort luas by adopt count desc — UI shows the hit
        # at the top
        per_lua.sort(key=lambda s: -s.adopt_count)
        publish_ids = {e.publish_id for e in all_entries}
        adopts_window = self._adopts_in_window(
            publish_ids, now, day_window,
        )
        return AuthorDashboard(
            author_id=author_id,
            author_display_name=display_name,
            total_publishes=len(all_entries),
            live_publishes=live_count,
            total_adopts=total_adopts,
            net_thumbs=net_thumbs,
            total_reports=total_reports,
            adopts_in_window=adopts_window,
            luas=per_lua,
        )


__all__ = [
    "PerLuaStats", "AuthorDashboard",
    "GearswapAuthorDashboard",
]
