"""GearSwap publisher — mentor-gated publish flow.

A player who has reached MENTOR status (chunk 320's
mentor_system) AND has an established reputation can
publish their job-specific GearSwap to the public
gallery for other players to adopt.

The eligibility gate has three layers:
  1. is_mentor flag from mentor_system
  2. reputation_at_publish snapshot from honor_reputation
     — both positive AND negative reputations qualify;
     the gallery surfaces both so adopters can decide
     whose builds to trust
  3. job-specific play time minimum (you can't publish
     a WHM build if you only ever played WHM for 3 hours)

Each published lua is signed with the author_id and a
content hash so adopters can prove provenance — anyone
can claim "this is Chharith's RDM lua", but the hash on
the gallery entry is the canonical one.

Public surface
--------------
    PublishStatus enum (DRAFT/PUBLISHED/UNLISTED/REVOKED)
    PublishEligibility dataclass (frozen)
    PublishedAddon dataclass (frozen)
    GearswapPublisher
        .check_eligibility(author_id, job, hours_played)
            -> PublishEligibility
        .publish(author_id, job, addon_id, lua_source,
                 reputation_snapshot, hours_played) -> Optional[str]
        .unlist(author_id, publish_id) -> bool
        .revoke(publish_id, by_moderator) -> bool
        .lookup(publish_id) -> Optional[PublishedAddon]
        .by_author(author_id) -> list[PublishedAddon]
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import typing as t


class PublishStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNLISTED = "unlisted"     # author hid it; not in gallery
    REVOKED = "revoked"       # moderator removed it; immutable


@dataclasses.dataclass(frozen=True)
class PublishEligibility:
    eligible: bool
    is_mentor: bool
    reputation_seen: int
    hours_played: int
    failure_reason: str       # "" if eligible


@dataclasses.dataclass(frozen=True)
class PublishedAddon:
    publish_id: str
    author_id: str
    author_display_name: str
    job: str
    addon_id: str
    lua_source: str
    content_hash: str          # sha256 of lua_source
    reputation_at_publish: int  # signed; negative = infamous
    hours_played_at_publish: int
    published_at: int
    status: PublishStatus
    revoke_reason: str         # "" if not REVOKED


# Minimum hours-on-job required to publish for that job.
# A mentor with 800 hours total but 5 hours on RDM can't
# publish a "trusted" RDM build.
_MIN_HOURS_ON_JOB = 200


def _content_hash(lua_source: str) -> str:
    return hashlib.sha256(lua_source.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class GearswapPublisher:
    _published: dict[str, PublishedAddon] = dataclasses.field(
        default_factory=dict,
    )
    # author_id → set of publish_ids
    _by_author: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # author_id → is_mentor (caller-injected from mentor_system)
    _mentor_flags: dict[str, bool] = dataclasses.field(
        default_factory=dict,
    )
    # author_id → display_name (caller-injected)
    _display_names: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _next_seq: int = 1

    def set_mentor_status(
        self, *, author_id: str, is_mentor: bool,
        display_name: str = "",
    ) -> bool:
        if not author_id:
            return False
        self._mentor_flags[author_id] = is_mentor
        if display_name:
            self._display_names[author_id] = display_name
        return True

    def check_eligibility(
        self, *, author_id: str, job: str,
        hours_played_on_job: int,
        reputation_snapshot: int,
    ) -> PublishEligibility:
        if not author_id:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                reputation_seen=0, hours_played=0,
                failure_reason="author_id_required",
            )
        is_mentor = self._mentor_flags.get(author_id, False)
        if not is_mentor:
            return PublishEligibility(
                eligible=False, is_mentor=False,
                reputation_seen=reputation_snapshot,
                hours_played=hours_played_on_job,
                failure_reason="not_mentor",
            )
        if hours_played_on_job < _MIN_HOURS_ON_JOB:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                reputation_seen=reputation_snapshot,
                hours_played=hours_played_on_job,
                failure_reason="insufficient_hours_on_job",
            )
        if not job:
            return PublishEligibility(
                eligible=False, is_mentor=True,
                reputation_seen=reputation_snapshot,
                hours_played=hours_played_on_job,
                failure_reason="job_required",
            )
        return PublishEligibility(
            eligible=True, is_mentor=True,
            reputation_seen=reputation_snapshot,
            hours_played=hours_played_on_job,
            failure_reason="",
        )

    def publish(
        self, *, author_id: str, job: str,
        addon_id: str, lua_source: str,
        reputation_snapshot: int,
        hours_played_on_job: int,
        published_at: int,
    ) -> t.Optional[str]:
        elig = self.check_eligibility(
            author_id=author_id, job=job,
            hours_played_on_job=hours_played_on_job,
            reputation_snapshot=reputation_snapshot,
        )
        if not elig.eligible:
            return None
        if not addon_id or not lua_source:
            return None
        publish_id = f"pub_{self._next_seq:06d}"
        self._next_seq += 1
        entry = PublishedAddon(
            publish_id=publish_id,
            author_id=author_id,
            author_display_name=self._display_names.get(
                author_id, author_id,
            ),
            job=job, addon_id=addon_id,
            lua_source=lua_source,
            content_hash=_content_hash(lua_source),
            reputation_at_publish=reputation_snapshot,
            hours_played_at_publish=hours_played_on_job,
            published_at=published_at,
            status=PublishStatus.PUBLISHED,
            revoke_reason="",
        )
        self._published[publish_id] = entry
        self._by_author.setdefault(author_id, set()).add(publish_id)
        return publish_id

    def unlist(
        self, *, author_id: str, publish_id: str,
    ) -> bool:
        entry = self._published.get(publish_id)
        if entry is None:
            return False
        if entry.author_id != author_id:
            return False
        if entry.status == PublishStatus.REVOKED:
            return False
        new_entry = dataclasses.replace(
            entry, status=PublishStatus.UNLISTED,
        )
        self._published[publish_id] = new_entry
        return True

    def relist(
        self, *, author_id: str, publish_id: str,
    ) -> bool:
        entry = self._published.get(publish_id)
        if entry is None:
            return False
        if entry.author_id != author_id:
            return False
        if entry.status != PublishStatus.UNLISTED:
            return False
        new_entry = dataclasses.replace(
            entry, status=PublishStatus.PUBLISHED,
        )
        self._published[publish_id] = new_entry
        return True

    def revoke(
        self, *, publish_id: str, reason: str,
    ) -> bool:
        entry = self._published.get(publish_id)
        if entry is None:
            return False
        if not reason:
            return False
        # REVOKED is terminal — even author can't undo it.
        new_entry = dataclasses.replace(
            entry, status=PublishStatus.REVOKED,
            revoke_reason=reason,
        )
        self._published[publish_id] = new_entry
        return True

    def lookup(
        self, *, publish_id: str,
    ) -> t.Optional[PublishedAddon]:
        return self._published.get(publish_id)

    def by_author(
        self, *, author_id: str,
    ) -> list[PublishedAddon]:
        ids = self._by_author.get(author_id, set())
        return [self._published[pid] for pid in sorted(ids)]

    def total_published(self) -> int:
        return sum(
            1 for e in self._published.values()
            if e.status == PublishStatus.PUBLISHED
        )

    def total_entries(self) -> int:
        return len(self._published)


__all__ = [
    "PublishStatus", "PublishEligibility", "PublishedAddon",
    "GearswapPublisher",
]
