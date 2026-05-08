"""Server chronicle — permanent ledger of major events.

Beyond the rolling combat_log and zone_bulletin_board,
the server has a CHRONICLE — a permanent, append-only,
human-readable record of major events. First server-
first kill of an HNM. The sealing of a major treaty.
The fall of a famous outlaw linkshell. The election of
a new president. The completion of a public_works
bridge.

A chronicle ENTRY has:
    entry_id
    event_kind         enum
    title              short headline
    body               full description
    witnesses          list of player_ids who were there
    location           zone_id where it happened (None
                       for server-wide events)
    importance         MINOR / NOTABLE / MAJOR / EPIC
    chronicled_at_ms

Append-only — entries cannot be edited or deleted. The
chronicle is the SERVER'S MEMORY.

Public surface
--------------
    EventKind enum
    Importance enum
    ChronicleEntry dataclass (frozen)
    ServerChronicle
        .record(kind, title, body, witnesses, location,
                importance, now_ms) -> str
        .entries_in_range(start_ms, end_ms) -> list
        .entries_about(witness_id) -> list
        .entries_in_zone(zone_id) -> list
        .entries_at_importance(importance) -> list
        .entry(entry_id) -> Optional[ChronicleEntry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventKind(str, enum.Enum):
    SERVER_FIRST_KILL = "server_first_kill"
    HNM_FELLED = "hnm_felled"
    TREATY_SIGNED = "treaty_signed"
    TREATY_TERMINATED = "treaty_terminated"
    OFFICE_ELECTION = "office_election"
    EDICT_PASSED = "edict_passed"
    PUBLIC_WORKS_COMPLETE = "public_works_complete"
    LS_FORMED = "ls_formed"
    LS_OUTLAWED = "ls_outlawed"
    PERMADEATH = "permadeath"
    DYNASTY_FOUNDED = "dynasty_founded"
    DISCOVERY = "discovery"
    FESTIVAL = "festival"
    WORLD_RECORD = "world_record"


class Importance(str, enum.Enum):
    MINOR = "minor"
    NOTABLE = "notable"
    MAJOR = "major"
    EPIC = "epic"


@dataclasses.dataclass(frozen=True)
class ChronicleEntry:
    entry_id: str
    event_kind: EventKind
    title: str
    body: str
    witnesses: tuple[str, ...]
    location: t.Optional[str]
    importance: Importance
    chronicled_at_ms: int


@dataclasses.dataclass
class ServerChronicle:
    _entries: list[ChronicleEntry] = dataclasses.field(
        default_factory=list,
    )
    _by_id: dict[str, ChronicleEntry] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def record(
        self, *, event_kind: EventKind, title: str,
        body: str,
        witnesses: t.Iterable[str],
        location: t.Optional[str],
        importance: Importance,
        now_ms: int,
    ) -> t.Optional[str]:
        if not title or not body:
            return None
        if now_ms < 0:
            return None
        ws = tuple(sorted(set(w for w in witnesses if w)))
        entry_id = f"chron_{self._next_id}"
        self._next_id += 1
        entry = ChronicleEntry(
            entry_id=entry_id, event_kind=event_kind,
            title=title, body=body,
            witnesses=ws, location=location,
            importance=importance,
            chronicled_at_ms=now_ms,
        )
        self._entries.append(entry)
        self._by_id[entry_id] = entry
        return entry_id

    def entries_in_range(
        self, *, start_ms: int, end_ms: int,
    ) -> list[ChronicleEntry]:
        return [
            e for e in self._entries
            if start_ms <= e.chronicled_at_ms <= end_ms
        ]

    def entries_about(
        self, *, witness_id: str,
    ) -> list[ChronicleEntry]:
        return [
            e for e in self._entries
            if witness_id in e.witnesses
        ]

    def entries_in_zone(
        self, *, zone_id: str,
    ) -> list[ChronicleEntry]:
        return [
            e for e in self._entries
            if e.location == zone_id
        ]

    def entries_at_importance(
        self, *, importance: Importance,
    ) -> list[ChronicleEntry]:
        return [
            e for e in self._entries
            if e.importance == importance
        ]

    def entry(
        self, *, entry_id: str,
    ) -> t.Optional[ChronicleEntry]:
        return self._by_id.get(entry_id)

    def total(self) -> int:
        return len(self._entries)


__all__ = [
    "EventKind", "Importance", "ChronicleEntry",
    "ServerChronicle",
]
