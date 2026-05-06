"""Title appraiser — predicate-driven hero-title grants.

Players don't ask for titles; titles find them. The
appraiser reads server_history_log and runs a set of
predicates (rules) against every history entry. Each
predicate maps to a title_id; matching entries trigger
a grant call against HeroTitleRegistry.

Built-in predicates (composed declaratively):
    HasKindPredicate(EventKind.WORLD_FIRST_KILL)
    HasKindAndBossPredicate(EventKind.SPEED_RECORD,
                            "vorrak", under_seconds=300)
    PermadeathSurvivorPredicate(after_seconds=N)

The appraiser is idempotent: running it 3 times produces
the same grant set as running it once.

Public surface
--------------
    TitlePredicate (Protocol-like base)
    HasKindPredicate, HasKindAndBossPredicate,
        SpeedRecordUnderPredicate, NationVictoryPredicate
    TitleAppraiser
        .register_rule(predicate, title_id) -> bool
        .appraise(history_log, title_registry,
                  now_seconds) -> int   (count of new grants)
        .registered_count() -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.server_history_log import (
    EventKind,
    HistoryEntry,
    ServerHistoryLog,
)
from server.hero_titles import HeroTitleRegistry


class TitlePredicate(t.Protocol):
    def matches(self, entry: HistoryEntry) -> bool: ...


@dataclasses.dataclass(frozen=True)
class HasKindPredicate:
    kind: EventKind

    def matches(self, entry: HistoryEntry) -> bool:
        return entry.kind == self.kind


@dataclasses.dataclass(frozen=True)
class HasKindAndBossPredicate:
    kind: EventKind
    boss_id: str

    def matches(self, entry: HistoryEntry) -> bool:
        return (
            entry.kind == self.kind
            and entry.boss_id == self.boss_id
        )


@dataclasses.dataclass(frozen=True)
class SpeedRecordUnderPredicate:
    boss_id: str
    under_seconds: int

    def matches(self, entry: HistoryEntry) -> bool:
        if entry.kind != EventKind.SPEED_RECORD:
            return False
        if entry.boss_id != self.boss_id:
            return False
        if entry.value is None:
            return False
        return entry.value < self.under_seconds


@dataclasses.dataclass(frozen=True)
class NationVictoryPredicate:
    region_id: str

    def matches(self, entry: HistoryEntry) -> bool:
        return (
            entry.kind == EventKind.NATION_VICTORY
            and entry.region_id == self.region_id
        )


@dataclasses.dataclass
class _Rule:
    predicate: TitlePredicate
    title_id: str


@dataclasses.dataclass
class TitleAppraiser:
    _rules: list[_Rule] = dataclasses.field(default_factory=list)

    def register_rule(
        self, *, predicate: TitlePredicate, title_id: str,
    ) -> bool:
        if not title_id:
            return False
        self._rules.append(_Rule(
            predicate=predicate, title_id=title_id,
        ))
        return True

    def appraise(
        self, *,
        history_log: ServerHistoryLog,
        title_registry: HeroTitleRegistry,
        now_seconds: int,
    ) -> int:
        granted = 0
        # iterate every entry in the ledger; for each rule
        # whose predicate matches, attempt a grant for each
        # participant (HeroTitleRegistry de-dups silently)
        # Use the public query API to keep coupling thin.
        from server.server_history_log import QueryFilter
        all_entries = history_log.query(qf=QueryFilter())
        for entry in all_entries:
            for rule in self._rules:
                if not rule.predicate.matches(entry):
                    continue
                for pid in entry.participants:
                    ok = title_registry.grant_title(
                        title_id=rule.title_id,
                        player_id=pid,
                        granted_at=now_seconds,
                        source_entry_id=entry.entry_id,
                    )
                    if ok:
                        granted += 1
        return granted

    def registered_count(self) -> int:
        return len(self._rules)


__all__ = [
    "TitlePredicate",
    "HasKindPredicate",
    "HasKindAndBossPredicate",
    "SpeedRecordUnderPredicate",
    "NationVictoryPredicate",
    "TitleAppraiser",
]
