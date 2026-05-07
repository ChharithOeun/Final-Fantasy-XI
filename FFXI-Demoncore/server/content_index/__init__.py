"""Content index — unified search across all 3
publishing systems.

Three publishing systems now exist (gearswap, strategy,
recipe). The natural question is "what has Chharith
published, period?" — across all of them. This module
is the unified search/discovery layer.

The index is a thin aggregator over the three publishers'
read-side APIs. It owns no data of its own; lookup goes
through whichever underlying publisher matches the
ContentKind. The indexer is per-instance; the caller
constructs it with references to all three publishers
they have running.

Public surface
--------------
    ContentKind enum
    ContentEntry dataclass (frozen)
    ContentIndex
        .by_author(author_id) -> list[ContentEntry]
        .search(query, kind, limit) -> list[ContentEntry]
        .total_by_kind() -> dict[ContentKind, int]
        .browse_recent(now, day_window, limit)
            -> list[ContentEntry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)
from server.recipe_publisher import (
    RecipePublisher, RecipeStatus,
)
from server.strategy_publisher import (
    GuideStatus, StrategyPublisher,
)


_SECONDS_PER_DAY = 86400


class ContentKind(str, enum.Enum):
    GEARSWAP = "gearswap"
    STRATEGY = "strategy"
    RECIPE = "recipe"


@dataclasses.dataclass(frozen=True)
class ContentEntry:
    kind: ContentKind
    content_id: str          # publish_id / guide_id / recipe_id
    author_id: str
    author_display_name: str
    title: str               # addon_id / title / title
    secondary: str           # job / encounter_display / discipline
    published_at: int


@dataclasses.dataclass
class ContentIndex:
    _gearswap: t.Optional[GearswapPublisher] = None
    _strategy: t.Optional[StrategyPublisher] = None
    _recipe: t.Optional[RecipePublisher] = None

    def _gearswap_entries(
        self, *, author_filter: str = "",
    ) -> list[ContentEntry]:
        out: list[ContentEntry] = []
        if self._gearswap is None:
            return out
        for e in self._gearswap._published.values():
            if e.status != PublishStatus.PUBLISHED:
                continue
            if author_filter and e.author_id != author_filter:
                continue
            out.append(ContentEntry(
                kind=ContentKind.GEARSWAP,
                content_id=e.publish_id,
                author_id=e.author_id,
                author_display_name=e.author_display_name,
                title=e.addon_id, secondary=e.job,
                published_at=e.published_at,
            ))
        return out

    def _strategy_entries(
        self, *, author_filter: str = "",
    ) -> list[ContentEntry]:
        out: list[ContentEntry] = []
        if self._strategy is None:
            return out
        for g in self._strategy._guides.values():
            if g.status != GuideStatus.PUBLISHED:
                continue
            if author_filter and g.author_id != author_filter:
                continue
            out.append(ContentEntry(
                kind=ContentKind.STRATEGY,
                content_id=g.guide_id,
                author_id=g.author_id,
                author_display_name=g.author_display_name,
                title=g.title,
                secondary=g.encounter.display_name,
                published_at=g.published_at,
            ))
        return out

    def _recipe_entries(
        self, *, author_filter: str = "",
    ) -> list[ContentEntry]:
        out: list[ContentEntry] = []
        if self._recipe is None:
            return out
        for r in self._recipe._recipes.values():
            if r.status != RecipeStatus.PUBLISHED:
                continue
            if author_filter and r.author_id != author_filter:
                continue
            out.append(ContentEntry(
                kind=ContentKind.RECIPE,
                content_id=r.recipe_id,
                author_id=r.author_id,
                author_display_name=r.author_display_name,
                title=r.title,
                secondary=r.discipline.value,
                published_at=r.published_at,
            ))
        return out

    def by_author(
        self, *, author_id: str,
    ) -> list[ContentEntry]:
        if not author_id:
            return []
        out = (
            self._gearswap_entries(author_filter=author_id)
            + self._strategy_entries(
                author_filter=author_id,
            )
            + self._recipe_entries(author_filter=author_id)
        )
        out.sort(key=lambda e: -e.published_at)
        return out

    def search(
        self, *, query: str,
        kind: t.Optional[ContentKind] = None,
        limit: int = 25,
    ) -> list[ContentEntry]:
        if not query or limit <= 0:
            return []
        q = query.lower()
        all_entries: list[ContentEntry] = []
        if kind is None or kind == ContentKind.GEARSWAP:
            all_entries.extend(self._gearswap_entries())
        if kind is None or kind == ContentKind.STRATEGY:
            all_entries.extend(self._strategy_entries())
        if kind is None or kind == ContentKind.RECIPE:
            all_entries.extend(self._recipe_entries())
        out = []
        for e in all_entries:
            haystack = (
                e.title.lower() + " "
                + e.author_display_name.lower() + " "
                + e.secondary.lower()
            )
            if q in haystack:
                out.append(e)
        out.sort(key=lambda e: -e.published_at)
        return out[:limit]

    def total_by_kind(self) -> dict[ContentKind, int]:
        return {
            ContentKind.GEARSWAP: len(self._gearswap_entries()),
            ContentKind.STRATEGY: len(self._strategy_entries()),
            ContentKind.RECIPE: len(self._recipe_entries()),
        }

    def browse_recent(
        self, *, now: int, day_window: int,
        limit: int = 25,
    ) -> list[ContentEntry]:
        if day_window <= 0 or limit <= 0:
            return []
        cutoff = now - (day_window * _SECONDS_PER_DAY)
        out = (
            self._gearswap_entries()
            + self._strategy_entries()
            + self._recipe_entries()
        )
        out = [e for e in out if e.published_at >= cutoff]
        out.sort(key=lambda e: -e.published_at)
        return out[:limit]


__all__ = [
    "ContentKind", "ContentEntry", "ContentIndex",
]
