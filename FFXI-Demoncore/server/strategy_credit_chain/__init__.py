"""Strategy credit chain — derivative guides cite their roots.

Forks (in GS) clone source. Strategy guides are different
— they're prose, not code, and the natural relationship
is "I learned this from Chharith's guide and tweaked
it for my BLM context." That's a CITATION, not a fork.

A guide can cite up to 5 inspirations (other guide_ids).
Citations are public; the gallery card lists "Inspired
by: Chharith's Maat (BST) and Rival's Maat (RDM)".

Citations are validated: cited guide must exist and not
be REVOKED (revoked guides shouldn't be promoted by
citations). UNLISTED is OK — the citing author saw it
when it was up; UI can render the cited guide name
even if the link no longer leads anywhere.

Cited authors get an aggregate "cited_count" stat on
their dashboard — "your guide has inspired 7 others"
is a quieter form of fame than direct adoption but
arguably more meaningful: someone studied your work
deeply enough to write their own.

Self-citation is allowed (the author building on their
own earlier guide). Cycles are detected (A cites B
cites A) — both stand, but resolve_lineage() shortcuts
to avoid infinite loops.

Public surface
--------------
    Citation dataclass (frozen)
    StrategyCreditChain
        .cite(citing_guide_id, cited_guide_ids, ...) -> bool
        .citations_of(citing_guide_id) -> list[str]
        .citations_to(cited_guide_id) -> list[str]
        .cited_count(author_id, _publisher) -> int
        .resolve_lineage(guide_id) -> list[str]
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.strategy_publisher import (
    GuideStatus, StrategyPublisher,
)


_MAX_CITATIONS_PER_GUIDE = 5


@dataclasses.dataclass(frozen=True)
class Citation:
    citing_guide_id: str
    cited_guide_id: str
    cited_at: int


@dataclasses.dataclass
class StrategyCreditChain:
    _publisher: StrategyPublisher
    _citations: list[Citation] = dataclasses.field(
        default_factory=list,
    )

    def cite(
        self, *, citing_guide_id: str,
        cited_guide_ids: list[str], cited_at: int,
    ) -> bool:
        if not citing_guide_id:
            return False
        if not cited_guide_ids:
            return False
        if len(cited_guide_ids) > _MAX_CITATIONS_PER_GUIDE:
            return False
        # Citing guide must exist
        if self._publisher.lookup(
            guide_id=citing_guide_id,
        ) is None:
            return False
        # Validate ALL cited guides exist and aren't revoked
        for cid in cited_guide_ids:
            if not cid:
                return False
            cited = self._publisher.lookup(guide_id=cid)
            if cited is None:
                return False
            if cited.status == GuideStatus.REVOKED:
                return False
        # Avoid duplicates within this single citation call
        if len(set(cited_guide_ids)) != len(cited_guide_ids):
            return False
        # Reject if this citing guide already has citations
        # (citations are set-once, immutable — like a
        # paper's references)
        if self.citations_of(
            citing_guide_id=citing_guide_id,
        ):
            return False
        for cid in cited_guide_ids:
            self._citations.append(Citation(
                citing_guide_id=citing_guide_id,
                cited_guide_id=cid, cited_at=cited_at,
            ))
        return True

    def citations_of(
        self, *, citing_guide_id: str,
    ) -> list[str]:
        return [
            c.cited_guide_id for c in self._citations
            if c.citing_guide_id == citing_guide_id
        ]

    def citations_to(
        self, *, cited_guide_id: str,
    ) -> list[str]:
        return [
            c.citing_guide_id for c in self._citations
            if c.cited_guide_id == cited_guide_id
        ]

    def cited_count(
        self, *, author_id: str,
    ) -> int:
        own_guides = {
            g.guide_id for g in self._publisher.by_author(
                author_id=author_id,
            )
        }
        # Unique citing guides that point at any of this
        # author's guides
        citers: set[str] = set()
        for c in self._citations:
            if c.cited_guide_id in own_guides:
                citers.add(c.citing_guide_id)
        return len(citers)

    def resolve_lineage(
        self, *, guide_id: str,
    ) -> list[str]:
        """BFS through citations starting from guide_id;
        returns the guide and all transitively-cited
        ancestors. Cycle-safe: each id appears once.
        Order is BFS (citing → cited → grandcited)."""
        seen: list[str] = [guide_id]
        seen_set = {guide_id}
        frontier = [guide_id]
        while frontier:
            nxt: list[str] = []
            for cur in frontier:
                for cited in self.citations_of(
                    citing_guide_id=cur,
                ):
                    if cited not in seen_set:
                        seen.append(cited)
                        seen_set.add(cited)
                        nxt.append(cited)
            frontier = nxt
        return seen

    def total_citations(self) -> int:
        return len(self._citations)


__all__ = [
    "Citation", "StrategyCreditChain",
]
