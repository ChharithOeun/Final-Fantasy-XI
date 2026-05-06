"""Exploration journal — per-player log of unique discoveries.

Each player carries a small leather journal. New zones,
new landmarks, new secret passages, new boss-zone entries
all go in. The journal is automatically populated; players
don't write to it themselves. Pages are timestamped and
ordered by discovery time.

EntryKind reflects what was discovered:
    ZONE_FIRST_VISIT    walking into a zone for the first time
    LANDMARK_FOUND      first time touching a registered landmark
    PASSAGE_DISCOVERED  triggering a SecretPassage
    BOSS_FIRST_SIGHTING first laying eyes on a named boss
    PILGRIMAGE_DONE     finishing a pilgrimage_route

The journal is also queryable by zone, kind, since-time.

Public surface
--------------
    EntryKind enum
    JournalEntry dataclass (frozen)
    ExplorationJournal
        .record(player_id, kind, ref_id, zone_id,
                discovered_at) -> bool
        .entries_for(player_id) -> tuple[JournalEntry, ...]
        .entries_for_zone(player_id, zone_id) -> tuple[...]
        .entries_of_kind(player_id, kind) -> tuple[...]
        .has_seen(player_id, kind, ref_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EntryKind(str, enum.Enum):
    ZONE_FIRST_VISIT = "zone_first_visit"
    LANDMARK_FOUND = "landmark_found"
    PASSAGE_DISCOVERED = "passage_discovered"
    BOSS_FIRST_SIGHTING = "boss_first_sighting"
    PILGRIMAGE_DONE = "pilgrimage_done"


@dataclasses.dataclass(frozen=True)
class JournalEntry:
    entry_id: str
    player_id: str
    kind: EntryKind
    ref_id: str          # the zone/landmark/passage/boss/route id
    zone_id: str
    discovered_at: int


@dataclasses.dataclass
class ExplorationJournal:
    _entries: list[JournalEntry] = dataclasses.field(
        default_factory=list,
    )
    _next_id: int = 0
    # (player_id, kind, ref_id) -> True
    _seen: set[tuple[str, EntryKind, str]] = dataclasses.field(
        default_factory=set,
    )
    _by_player: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )

    def record(
        self, *, player_id: str, kind: EntryKind,
        ref_id: str, zone_id: str,
        discovered_at: int,
    ) -> bool:
        if not player_id or not ref_id or not zone_id:
            return False
        key = (player_id, kind, ref_id)
        if key in self._seen:
            return False
        self._seen.add(key)
        self._next_id += 1
        eid = f"jentry_{self._next_id}"
        entry = JournalEntry(
            entry_id=eid, player_id=player_id,
            kind=kind, ref_id=ref_id, zone_id=zone_id,
            discovered_at=discovered_at,
        )
        idx = len(self._entries)
        self._entries.append(entry)
        self._by_player.setdefault(player_id, []).append(idx)
        return True

    def entries_for(
        self, *, player_id: str,
    ) -> tuple[JournalEntry, ...]:
        idxs = self._by_player.get(player_id, [])
        return tuple(self._entries[i] for i in idxs)

    def entries_for_zone(
        self, *, player_id: str, zone_id: str,
    ) -> tuple[JournalEntry, ...]:
        return tuple(
            e for e in self.entries_for(player_id=player_id)
            if e.zone_id == zone_id
        )

    def entries_of_kind(
        self, *, player_id: str, kind: EntryKind,
    ) -> tuple[JournalEntry, ...]:
        return tuple(
            e for e in self.entries_for(player_id=player_id)
            if e.kind == kind
        )

    def has_seen(
        self, *, player_id: str, kind: EntryKind, ref_id: str,
    ) -> bool:
        return (player_id, kind, ref_id) in self._seen

    def total_entries(self) -> int:
        return len(self._entries)


__all__ = ["EntryKind", "JournalEntry", "ExplorationJournal"]
