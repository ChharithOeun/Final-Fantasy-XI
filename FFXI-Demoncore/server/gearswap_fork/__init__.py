"""GearSwap fork — clone an existing publish, keep the
attribution chain.

When Bob adopts in CLONE_TO_DRAFT mode and tweaks
Chharith's RDM build, he might want to publish his tuned
version. Today that just creates an unrelated new publish
— Chharith gets no credit and Bob's listing has no
"based on Chharith".

A fork preserves the lineage. Forking creates a brand-new
publish (must clear the publisher's normal eligibility +
hours gate just like any other publish), but the new
record carries an `original_publish_id` reference. The
gallery card can then render "Bob — RDM (forked from
Chharith's rdm_chharith)".

Forks count toward the original author's "influence":
total adopters across THEIR descendants. That's the
"my style spread across the server" metric. It's a
softer fame signal than direct adoption (and doesn't
pay author_rewards — the fork's adopters belong to the
fork's author for reward purposes).

We allow fork-of-fork chains (Bob forks Chharith → Cara
forks Bob). The chain is walked to find the root, and
influence credit is attributed at every level of the
chain (Chharith gets credit for Cara's adopts too, two
levels deep).

Fork-of-yourself is allowed (you're refactoring your own
build into a v2 lineage). UNLISTED forks-OF do not block
new forks (people who already adopted the source can
still publish their tweak even if the source author
parked it). REVOKED do block — there's no innocent
reason to fork an exploit.

Public surface
--------------
    ForkRecord dataclass (frozen)
    GearswapFork
        .fork(forker_id, source_publish_id, job, addon_id,
              lua_source, hours_played_on_job,
              reputation_snapshot, published_at)
            -> Optional[str]   # new publish_id
        .fork_of(publish_id) -> Optional[str]
        .fork_chain(publish_id) -> list[str]
        .descendants(publish_id) -> list[str]
        .influence_count(author_id, _adopt) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)


@dataclasses.dataclass(frozen=True)
class ForkRecord:
    fork_publish_id: str
    source_publish_id: str
    forker_id: str
    forked_at: int


@dataclasses.dataclass
class GearswapFork:
    _publisher: GearswapPublisher
    # publish_id of the FORK -> ForkRecord
    _forks: dict[str, ForkRecord] = dataclasses.field(
        default_factory=dict,
    )

    def fork(
        self, *, forker_id: str, source_publish_id: str,
        job: str, addon_id: str, lua_source: str,
        hours_played_on_job: int,
        reputation_snapshot: int, published_at: int,
    ) -> t.Optional[str]:
        source = self._publisher.lookup(
            publish_id=source_publish_id,
        )
        if source is None:
            return None
        if source.status == PublishStatus.REVOKED:
            return None
        new_pid = self._publisher.publish(
            author_id=forker_id, job=job, addon_id=addon_id,
            lua_source=lua_source,
            reputation_snapshot=reputation_snapshot,
            hours_played_on_job=hours_played_on_job,
            published_at=published_at,
        )
        if new_pid is None:
            return None
        self._forks[new_pid] = ForkRecord(
            fork_publish_id=new_pid,
            source_publish_id=source_publish_id,
            forker_id=forker_id, forked_at=published_at,
        )
        return new_pid

    def fork_of(
        self, *, publish_id: str,
    ) -> t.Optional[str]:
        rec = self._forks.get(publish_id)
        return rec.source_publish_id if rec else None

    def fork_chain(
        self, *, publish_id: str,
    ) -> list[str]:
        """Returns [publish_id, parent, grandparent, ...
        root] walking the fork lineage backward."""
        chain = [publish_id]
        cur = publish_id
        seen = {publish_id}
        while True:
            rec = self._forks.get(cur)
            if rec is None:
                break
            parent = rec.source_publish_id
            if parent in seen:
                break   # defensive — should never happen
            chain.append(parent)
            seen.add(parent)
            cur = parent
        return chain

    def descendants(
        self, *, publish_id: str,
    ) -> list[str]:
        """All publish_ids in the fork tree rooted at
        publish_id (transitively, sorted)."""
        out: set[str] = set()
        # BFS
        frontier = {publish_id}
        while frontier:
            nxt: set[str] = set()
            for fork_pid, rec in self._forks.items():
                if rec.source_publish_id in frontier:
                    if fork_pid not in out:
                        out.add(fork_pid)
                        nxt.add(fork_pid)
            frontier = nxt
        return sorted(out)

    def influence_count(
        self, *, author_id: str, _adopt: GearswapAdopt,
    ) -> int:
        """Total adopters of any publish that descends
        from one of author_id's published luas. Excludes
        direct adopts on the author's own luas — those
        are already in their adopt count. Pure
        downstream signal."""
        # Find the author's own publish_ids
        own = {
            e.publish_id for e in self._publisher.by_author(
                author_id=author_id,
            )
        }
        total = 0
        for pid in own:
            for desc in self.descendants(publish_id=pid):
                total += _adopt.adopters_count(
                    publish_id=desc,
                )
        return total

    def total_forks(self) -> int:
        return len(self._forks)


__all__ = ["ForkRecord", "GearswapFork"]
