"""GearSwap gallery — public catalog of published luas.

Players browse the gallery by job, by author, or by
popularity. Filters narrow by reputation tier (so a
brand-new player can pre-filter to "POSITIVE reputation
authors only" if they want safer picks; veterans might
prefer to see everything including the infamous to make
their own call).

Sort modes:
    NEWEST      most recently published first
    POPULAR     most adopted (adopt count from gearswap_adopt)
    REPUTATION  highest author reputation first

The gallery does NOT publish — it READS from the
gearswap_publisher store via injection. It also does NOT
own the rating data — that lives in gearswap_rating. The
gallery is the read-side API.

Public surface
--------------
    SortMode enum
    ReputationFilter enum (ANY/POSITIVE_ONLY/NEUTRAL_OR_BETTER)
    GalleryListing dataclass (frozen)
    GearswapGallery
        .browse(job, sort, reputation_filter, limit)
            -> list[GalleryListing]
        .by_author_listing(author_id) -> list[GalleryListing]
        .search(query, job, limit) -> list[GalleryListing]
        .set_adopt_count(publish_id, count) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_publisher import (
    GearswapPublisher, PublishedAddon, PublishStatus,
)


class SortMode(str, enum.Enum):
    NEWEST = "newest"
    POPULAR = "popular"
    REPUTATION = "reputation"


class ReputationFilter(str, enum.Enum):
    ANY = "any"
    POSITIVE_ONLY = "positive_only"      # rep > 0
    NEUTRAL_OR_BETTER = "neutral_or_better"  # rep >= 0


@dataclasses.dataclass(frozen=True)
class GalleryListing:
    publish_id: str
    addon_id: str
    author_id: str
    author_display_name: str
    job: str
    reputation: int
    adopt_count: int
    published_at: int


@dataclasses.dataclass
class GearswapGallery:
    _publisher: GearswapPublisher
    # publish_id → adopt count (driven by gearswap_adopt)
    _adopt_counts: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def set_adopt_count(
        self, *, publish_id: str, count: int,
    ) -> bool:
        if count < 0:
            return False
        if self._publisher.lookup(publish_id=publish_id) is None:
            return False
        self._adopt_counts[publish_id] = count
        return True

    def _to_listing(
        self, entry: PublishedAddon,
    ) -> GalleryListing:
        return GalleryListing(
            publish_id=entry.publish_id,
            addon_id=entry.addon_id,
            author_id=entry.author_id,
            author_display_name=entry.author_display_name,
            job=entry.job,
            reputation=entry.reputation_at_publish,
            adopt_count=self._adopt_counts.get(
                entry.publish_id, 0,
            ),
            published_at=entry.published_at,
        )

    def _passes_rep_filter(
        self, entry: PublishedAddon,
        rep_filter: ReputationFilter,
    ) -> bool:
        if rep_filter == ReputationFilter.ANY:
            return True
        if rep_filter == ReputationFilter.POSITIVE_ONLY:
            return entry.reputation_at_publish > 0
        if rep_filter == ReputationFilter.NEUTRAL_OR_BETTER:
            return entry.reputation_at_publish >= 0
        return True

    def _all_published(self) -> list[PublishedAddon]:
        return [
            e for e in self._publisher._published.values()
            if e.status == PublishStatus.PUBLISHED
        ]

    def browse(
        self, *, job: str = "",
        sort: SortMode = SortMode.NEWEST,
        reputation_filter: ReputationFilter = ReputationFilter.ANY,
        limit: int = 25,
    ) -> list[GalleryListing]:
        if limit <= 0:
            return []
        filtered: list[PublishedAddon] = []
        for entry in self._all_published():
            if job and entry.job != job:
                continue
            if not self._passes_rep_filter(entry, reputation_filter):
                continue
            filtered.append(entry)
        if sort == SortMode.NEWEST:
            filtered.sort(
                key=lambda e: -e.published_at,
            )
        elif sort == SortMode.POPULAR:
            filtered.sort(
                key=lambda e: -self._adopt_counts.get(
                    e.publish_id, 0,
                ),
            )
        elif sort == SortMode.REPUTATION:
            filtered.sort(
                key=lambda e: -e.reputation_at_publish,
            )
        return [self._to_listing(e) for e in filtered[:limit]]

    def by_author_listing(
        self, *, author_id: str,
    ) -> list[GalleryListing]:
        out: list[GalleryListing] = []
        for entry in self._publisher.by_author(author_id=author_id):
            if entry.status == PublishStatus.PUBLISHED:
                out.append(self._to_listing(entry))
        return out

    def search(
        self, *, query: str, job: str = "",
        limit: int = 25,
    ) -> list[GalleryListing]:
        if not query or limit <= 0:
            return []
        q = query.lower()
        out: list[GalleryListing] = []
        for entry in self._all_published():
            if job and entry.job != job:
                continue
            # Match against addon_id, author display, or job
            haystack = (
                entry.addon_id.lower()
                + " " + entry.author_display_name.lower()
                + " " + entry.job.lower()
            )
            if q in haystack:
                out.append(self._to_listing(entry))
        # Default ordering: newest first within search results
        out.sort(key=lambda l: -l.published_at)
        return out[:limit]


__all__ = [
    "SortMode", "ReputationFilter", "GalleryListing",
    "GearswapGallery",
]
