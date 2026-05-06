"""Wayfarer titles — auto-granted from exploration milestones.

Reads the exploration_journal and grants matching
hero_titles when a player crosses a milestone threshold.

Built-in milestones (configurable):
    "well_traveled"      visited 10 distinct zones
    "cartographer"       visited 25 distinct zones
    "sea_dog"            visited 5 ocean zones (zone_id startswith
                         "ocean_" or in OCEAN_ZONES)
    "spelunker"          5 LANDMARK_FOUND in cave-class zones
    "secret_keeper"      discovered 3 secret passages
    "pilgrim"            completed 1 pilgrimage
    "perfect_pilgrim"    completed 5 pilgrimages

The appraiser is idempotent: re-running awards no
duplicates (HeroTitleRegistry already de-dupes; this
module ensures the predicate is well-defined).

Public surface
--------------
    WayfarerMilestone dataclass (frozen)
    WayfarerTitleAppraiser
        .register_milestone(title_id, predicate, name) -> bool
        .appraise(player_id, journal, title_registry,
                  now_seconds) -> int   (count of new grants)
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.exploration_journal import EntryKind, ExplorationJournal
from server.hero_titles import HeroTitleRegistry


# Predicate signature: (entries) -> bool
# entries is a tuple of JournalEntry for the target player
JournalPredicate = t.Callable[[tuple[t.Any, ...]], bool]


@dataclasses.dataclass(frozen=True)
class WayfarerMilestone:
    title_id: str
    name: str
    predicate: JournalPredicate


# --- canonical predicates ---------------------------------

def _distinct_zones_predicate(threshold: int) -> JournalPredicate:
    def pred(entries: tuple[t.Any, ...]) -> bool:
        zones = {
            e.zone_id for e in entries
            if e.kind == EntryKind.ZONE_FIRST_VISIT
        }
        return len(zones) >= threshold
    return pred


def _kind_count_predicate(
    kind: EntryKind, threshold: int,
) -> JournalPredicate:
    def pred(entries: tuple[t.Any, ...]) -> bool:
        n = sum(1 for e in entries if e.kind == kind)
        return n >= threshold
    return pred


def _zone_prefix_predicate(
    prefix: str, threshold: int,
) -> JournalPredicate:
    def pred(entries: tuple[t.Any, ...]) -> bool:
        zones = {
            e.zone_id for e in entries
            if e.kind == EntryKind.ZONE_FIRST_VISIT
            and e.zone_id.startswith(prefix)
        }
        return len(zones) >= threshold
    return pred


@dataclasses.dataclass
class WayfarerTitleAppraiser:
    _milestones: list[WayfarerMilestone] = dataclasses.field(
        default_factory=list,
    )

    def register_milestone(
        self, *, title_id: str, name: str,
        predicate: JournalPredicate,
    ) -> bool:
        if not title_id or not name:
            return False
        self._milestones.append(WayfarerMilestone(
            title_id=title_id, name=name, predicate=predicate,
        ))
        return True

    def appraise(
        self, *, player_id: str,
        journal: ExplorationJournal,
        title_registry: HeroTitleRegistry,
        now_seconds: int,
    ) -> int:
        if not player_id:
            return 0
        entries = journal.entries_for(player_id=player_id)
        granted = 0
        for ms in self._milestones:
            if not ms.predicate(entries):
                continue
            ok = title_registry.grant_title(
                title_id=ms.title_id, player_id=player_id,
                granted_at=now_seconds,
            )
            if ok:
                granted += 1
        return granted

    def total_milestones(self) -> int:
        return len(self._milestones)


# --- helpers for canonical predicates --------------------

def predicate_distinct_zones(threshold: int) -> JournalPredicate:
    return _distinct_zones_predicate(threshold)


def predicate_kind_count(
    kind: EntryKind, threshold: int,
) -> JournalPredicate:
    return _kind_count_predicate(kind, threshold)


def predicate_zone_prefix(
    prefix: str, threshold: int,
) -> JournalPredicate:
    return _zone_prefix_predicate(prefix, threshold)


__all__ = [
    "WayfarerMilestone", "WayfarerTitleAppraiser",
    "predicate_distinct_zones", "predicate_kind_count",
    "predicate_zone_prefix",
]
