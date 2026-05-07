"""GearSwap version history — author updates + adopter notice.

A published lua isn't frozen. Authors keep tuning gear,
patches change item names, BiS changes when relics drop.
This module lets the author push a new revision under the
same publish_id, keeps the old revisions immutable, and
flags adopters that they're behind so they can review
the diff and choose to upgrade.

Each revision is an immutable snapshot:
    revision_no   monotonic from 1
    lua_source    full text (we don't store deltas; luas
                  are tiny and storage is cheap)
    content_hash  sha256 for change detection
    notes         optional one-line changelog
    published_at  timestamp

The CURRENT revision is always the highest revision_no.
Adopters compare their adopted_at hash against the
current hash to know whether to prompt for upgrade.

We deliberately separate this from gearswap_publisher
because publishing the FIRST version is the social
"I'm ready to share this" moment (gated by mentor
status + hours), while pushing a v2 is the routine
maintenance moment (no extra gate, just author identity).

Public surface
--------------
    Revision dataclass (frozen)
    GearswapVersionHistory
        .seed_initial(publish_id, lua_source,
                      content_hash, published_at) -> Revision
        .push_revision(author_id, publish_id, lua_source,
                       notes, published_at)
            -> Optional[Revision]
        .current(publish_id) -> Optional[Revision]
        .history(publish_id) -> list[Revision]
        .revision_count(publish_id) -> int
        .has_update(publish_id, adopted_hash) -> bool
        .diff_to_current(publish_id, adopted_hash)
            -> Optional[tuple[int, int]]   # (from_rev, to_rev)
"""
from __future__ import annotations

import dataclasses
import hashlib
import typing as t

from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)


_MAX_NOTES_LEN = 200


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclasses.dataclass(frozen=True)
class Revision:
    publish_id: str
    revision_no: int
    lua_source: str
    content_hash: str
    notes: str
    published_at: int


@dataclasses.dataclass
class GearswapVersionHistory:
    _publisher: GearswapPublisher
    # publish_id → ordered revisions (oldest → newest)
    _history: dict[str, list[Revision]] = dataclasses.field(
        default_factory=dict,
    )

    def seed_initial(
        self, *, publish_id: str, lua_source: str,
        content_hash: str, published_at: int,
    ) -> t.Optional[Revision]:
        """Called by the publisher right after the initial
        publish so revision 1 lines up with what's in the
        publisher store. Idempotent — only seeds once."""
        if publish_id in self._history:
            return None
        rev = Revision(
            publish_id=publish_id, revision_no=1,
            lua_source=lua_source, content_hash=content_hash,
            notes="initial publish", published_at=published_at,
        )
        self._history[publish_id] = [rev]
        return rev

    def push_revision(
        self, *, author_id: str, publish_id: str,
        lua_source: str, notes: str, published_at: int,
    ) -> t.Optional[Revision]:
        if not lua_source or len(notes) > _MAX_NOTES_LEN:
            return None
        entry = self._publisher.lookup(publish_id=publish_id)
        if entry is None:
            return None
        # Only the author can push revisions, and only on
        # PUBLISHED or UNLISTED entries (not REVOKED).
        if entry.author_id != author_id:
            return None
        if entry.status == PublishStatus.REVOKED:
            return None
        revs = self._history.setdefault(publish_id, [])
        new_hash = _hash(lua_source)
        # No-op if nothing changed
        if revs and revs[-1].content_hash == new_hash:
            return None
        rev = Revision(
            publish_id=publish_id,
            revision_no=len(revs) + 1,
            lua_source=lua_source, content_hash=new_hash,
            notes=notes, published_at=published_at,
        )
        revs.append(rev)
        return rev

    def current(
        self, *, publish_id: str,
    ) -> t.Optional[Revision]:
        revs = self._history.get(publish_id)
        if not revs:
            return None
        return revs[-1]

    def history(
        self, *, publish_id: str,
    ) -> list[Revision]:
        return list(self._history.get(publish_id, []))

    def revision_count(self, *, publish_id: str) -> int:
        return len(self._history.get(publish_id, []))

    def has_update(
        self, *, publish_id: str, adopted_hash: str,
    ) -> bool:
        cur = self.current(publish_id=publish_id)
        if cur is None:
            return False
        return cur.content_hash != adopted_hash

    def diff_to_current(
        self, *, publish_id: str, adopted_hash: str,
    ) -> t.Optional[tuple[int, int]]:
        revs = self._history.get(publish_id)
        if not revs:
            return None
        cur = revs[-1]
        if cur.content_hash == adopted_hash:
            return None
        # find the revision the adopter is on
        for r in revs:
            if r.content_hash == adopted_hash:
                return (r.revision_no, cur.revision_no)
        # adopter's hash isn't in our history (e.g. was
        # adopted from a snapshot we don't track) — still
        # report the current rev so UI can prompt
        return (0, cur.revision_no)

    def total_revisions(self) -> int:
        return sum(len(v) for v in self._history.values())


__all__ = [
    "Revision", "GearswapVersionHistory",
]
