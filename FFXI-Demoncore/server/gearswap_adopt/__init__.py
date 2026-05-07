"""GearSwap adopt — one-click adopt a published lua.

A player browsing the gallery hits "Adopt" on a published
build. Two outcomes:

    USE_AS_IS     install the lua directly into the player's
                  addon set; can run immediately
    CLONE_TO_DRAFT  copy the source to the player's draft so
                    they can customize before installing

Each adopt is recorded against (player_id, publish_id) so
repeat-adopts are no-ops (no double-counting in the
gallery's adopt count). Players can un-adopt to remove
the addon and decrement the counter.

The module also tracks the "adopted_at" snapshot so when
the author publishes a new version, the player's UI
shows "this is v1.2; you have v1.0" and prompts to
upgrade — handed off to gearswap_version_history.

Public surface
--------------
    AdoptMode enum (USE_AS_IS/CLONE_TO_DRAFT)
    AdoptionRecord dataclass (frozen)
    GearswapAdopt
        .adopt(player_id, publish_id, mode, adopted_at)
            -> Optional[AdoptionRecord]
        .un_adopt(player_id, publish_id) -> bool
        .has_adopted(player_id, publish_id) -> bool
        .adoptions_for(player_id) -> list[AdoptionRecord]
        .adopters_count(publish_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_publisher import (
    GearswapPublisher, PublishStatus,
)


class AdoptMode(str, enum.Enum):
    USE_AS_IS = "use_as_is"
    CLONE_TO_DRAFT = "clone_to_draft"


@dataclasses.dataclass(frozen=True)
class AdoptionRecord:
    player_id: str
    publish_id: str
    mode: AdoptMode
    adopted_at: int
    content_hash_at_adopt: str    # for "you have an old version" check


@dataclasses.dataclass
class GearswapAdopt:
    _publisher: GearswapPublisher
    # (player_id, publish_id) → record
    _adoptions: dict[
        tuple[str, str], AdoptionRecord,
    ] = dataclasses.field(default_factory=dict)

    def adopt(
        self, *, player_id: str, publish_id: str,
        mode: AdoptMode, adopted_at: int,
    ) -> t.Optional[AdoptionRecord]:
        if not player_id:
            return None
        entry = self._publisher.lookup(publish_id=publish_id)
        if entry is None:
            return None
        # REVOKED entries can never be adopted; UNLISTED can't
        # be newly adopted (existing adopters keep theirs).
        if entry.status != PublishStatus.PUBLISHED:
            return None
        key = (player_id, publish_id)
        if key in self._adoptions:
            return None   # already adopted; no double-count
        record = AdoptionRecord(
            player_id=player_id, publish_id=publish_id,
            mode=mode, adopted_at=adopted_at,
            content_hash_at_adopt=entry.content_hash,
        )
        self._adoptions[key] = record
        return record

    def un_adopt(
        self, *, player_id: str, publish_id: str,
    ) -> bool:
        key = (player_id, publish_id)
        if key not in self._adoptions:
            return False
        del self._adoptions[key]
        return True

    def has_adopted(
        self, *, player_id: str, publish_id: str,
    ) -> bool:
        return (player_id, publish_id) in self._adoptions

    def adoptions_for(
        self, *, player_id: str,
    ) -> list[AdoptionRecord]:
        out = [
            r for (pid, _), r in self._adoptions.items()
            if pid == player_id
        ]
        out.sort(key=lambda r: r.adopted_at)
        return out

    def adopters_count(
        self, *, publish_id: str,
    ) -> int:
        return sum(
            1 for (_pid, pubid) in self._adoptions
            if pubid == publish_id
        )

    def has_outdated_version(
        self, *, player_id: str, publish_id: str,
    ) -> bool:
        """True if the published content has changed since
        the player adopted (i.e. author shipped an update)."""
        record = self._adoptions.get((player_id, publish_id))
        if record is None:
            return False
        entry = self._publisher.lookup(publish_id=publish_id)
        if entry is None:
            return False
        return entry.content_hash != record.content_hash_at_adopt

    def total_adoptions(self) -> int:
        return len(self._adoptions)


__all__ = [
    "AdoptMode", "AdoptionRecord", "GearswapAdopt",
]
