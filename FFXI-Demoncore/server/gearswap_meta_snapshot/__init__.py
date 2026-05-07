"""GearSwap meta snapshot — server-wide "the meta" read.

Famous players publish builds; thousands of players adopt
them. The meta is what emerges. This module periodically
samples adoption + thumb data and produces a snapshot
per job: which builds dominate, what the average net-thumb
score looks like, how concentrated the top is.

A snapshot answers questions like:
    "Right now on this server, what does the average
     lvl-99 RDM run?"
    "Is the RDM scene healthy (many viable builds) or
     stagnant (one build owns 80% of adopters)?"

The Gini-style concentration ratio — top1 share over
total adopters in a job — is the canonical "is one
author dominating" signal. Live ops can spot a stagnant
job by watching this trend up over weeks. (We don't
balance based on it; we just expose it so the community
sees it.)

The snapshot is taken on demand and stored. Old snapshots
are kept for trend lines; the keep-history cap is 200.

Public surface
--------------
    JobMeta dataclass (frozen)
    MetaSnapshot dataclass (frozen)
    GearswapMetaSnapshot
        .take_snapshot(now) -> MetaSnapshot
        .latest() -> Optional[MetaSnapshot]
        .history(limit) -> list[MetaSnapshot]
        .meta_for_job(snapshot, job) -> Optional[JobMeta]
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)
from server.gearswap_rating import GearswapRating


_HISTORY_CAP = 200


@dataclasses.dataclass(frozen=True)
class JobMeta:
    job: str
    publish_count: int
    total_adopters: int
    top_publish_id: str            # most-adopted live publish
    top_addon_id: str
    top_author_display_name: str
    top_adopt_count: int
    top_share: float               # top_adopt_count / total_adopters
    avg_net_thumbs: float          # mean across this job
    health: str                    # "healthy" / "concentrated" / "quiet"


@dataclasses.dataclass(frozen=True)
class MetaSnapshot:
    snapshot_at: int
    jobs: list[JobMeta]


@dataclasses.dataclass
class GearswapMetaSnapshot:
    _publisher: GearswapPublisher
    _adopt: GearswapAdopt
    _rating: GearswapRating
    _history: list[MetaSnapshot] = dataclasses.field(
        default_factory=list,
    )

    def _job_meta(self, job: str) -> JobMeta:
        publish_count = 0
        total_adopters = 0
        net_thumbs_sum = 0
        top_pid = ""
        top_addon = ""
        top_name = ""
        top_count = 0
        for entry in self._publisher._published.values():
            if entry.status != PublishStatus.PUBLISHED:
                continue
            if entry.job != job:
                continue
            publish_count += 1
            count = self._adopt.adopters_count(
                publish_id=entry.publish_id,
            )
            total_adopters += count
            s = self._rating.summary(
                publish_id=entry.publish_id,
            )
            net_thumbs_sum += s.thumbs_up - s.thumbs_down
            if count > top_count:
                top_count = count
                top_pid = entry.publish_id
                top_addon = entry.addon_id
                top_name = entry.author_display_name
        avg_net = (
            net_thumbs_sum / publish_count
            if publish_count else 0.0
        )
        share = (
            top_count / total_adopters
            if total_adopters else 0.0
        )
        if total_adopters < 10:
            health = "quiet"
        elif share > 0.6:
            health = "concentrated"
        else:
            health = "healthy"
        return JobMeta(
            job=job, publish_count=publish_count,
            total_adopters=total_adopters,
            top_publish_id=top_pid,
            top_addon_id=top_addon,
            top_author_display_name=top_name,
            top_adopt_count=top_count,
            top_share=share, avg_net_thumbs=avg_net,
            health=health,
        )

    def take_snapshot(self, *, now: int) -> MetaSnapshot:
        # Collect every distinct job that has at least
        # one PUBLISHED entry.
        jobs: set[str] = set()
        for entry in self._publisher._published.values():
            if entry.status == PublishStatus.PUBLISHED:
                jobs.add(entry.job)
        metas = [self._job_meta(j) for j in sorted(jobs)]
        snap = MetaSnapshot(snapshot_at=now, jobs=metas)
        self._history.append(snap)
        if len(self._history) > _HISTORY_CAP:
            del self._history[0]
        return snap

    def latest(self) -> t.Optional[MetaSnapshot]:
        return self._history[-1] if self._history else None

    def history(
        self, *, limit: int = 50,
    ) -> list[MetaSnapshot]:
        if limit <= 0:
            return []
        return list(self._history[-limit:])

    @staticmethod
    def meta_for_job(
        snapshot: MetaSnapshot, *, job: str,
    ) -> t.Optional[JobMeta]:
        for jm in snapshot.jobs:
            if jm.job == job:
                return jm
        return None

    def total_snapshots(self) -> int:
        return len(self._history)


__all__ = [
    "JobMeta", "MetaSnapshot", "GearswapMetaSnapshot",
]
