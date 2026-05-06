"""Server history log — permanent record of legendary moments.

Most MMOs forget. Players come and go, world-firsts blur,
the great fights become rumors. This module keeps the
ledger: an APPEND-ONLY chronological record of every
meaningful event the server cares to remember.

Event kinds
-----------
    WORLD_FIRST_KILL    first time anyone on the server
                        defeats a NM/boss/world boss
    SECOND_KILL         second-firsts get noted too —
                        the team that broke the strategy
                        deserves remembering
    PERFECT_RUN         a fight cleared with no deaths
                        on first attempt
    SPEED_RECORD        fastest kill of a tracked boss
    NEW_RECORD          generic record (longest fishing
                        catch, biggest auction sale,
                        100k SC closes, etc.)
    PERMADEATH          a level-30+ player permadied;
                        becomes part of the chronicle
    LEGENDARY_DUEL      a recorded ML-tier duel between
                        two notable players
    NATION_VICTORY      a region captured/defended by
                        nation forces
    EXPANSION_UNLOCK    server unlocks a new expansion's
                        endgame zone

The log is a SOURCE OF TRUTH. Other modules (hero_titles,
world_chronicle, bardic_renown) read from it to build
their interfaces. Once an entry is written it is NEVER
modified — only marked for review if disputed.

Public surface
--------------
    EventKind enum
    HistoryEntry dataclass (frozen)
    QueryFilter dataclass (frozen)
    ServerHistoryLog
        .record_event(kind, summary, participants,
                      boss_id, value, recorded_at)
            -> entry_id
        .get(entry_id) -> Optional[HistoryEntry]
        .query(filter) -> tuple[HistoryEntry, ...]
        .events_for_player(player_id) -> tuple[HistoryEntry, ...]
        .events_for_boss(boss_id) -> tuple[HistoryEntry, ...]
        .total_entries() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventKind(str, enum.Enum):
    WORLD_FIRST_KILL = "world_first_kill"
    SECOND_KILL = "second_kill"
    PERFECT_RUN = "perfect_run"
    SPEED_RECORD = "speed_record"
    NEW_RECORD = "new_record"
    PERMADEATH = "permadeath"
    LEGENDARY_DUEL = "legendary_duel"
    NATION_VICTORY = "nation_victory"
    EXPANSION_UNLOCK = "expansion_unlock"


@dataclasses.dataclass(frozen=True)
class HistoryEntry:
    entry_id: str
    kind: EventKind
    summary: str
    participants: tuple[str, ...]   # player_ids
    recorded_at: int
    boss_id: t.Optional[str] = None
    value: t.Optional[int] = None     # speed seconds, sale price, etc.
    region_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class QueryFilter:
    kinds: tuple[EventKind, ...] = ()
    boss_id: t.Optional[str] = None
    participant_id: t.Optional[str] = None
    region_id: t.Optional[str] = None
    since_seconds: t.Optional[int] = None


@dataclasses.dataclass
class ServerHistoryLog:
    _entries: list[HistoryEntry] = dataclasses.field(default_factory=list)
    _next_id: int = 0
    # secondary indexes for fast lookup
    _by_player: dict[str, list[int]] = dataclasses.field(default_factory=dict)
    _by_boss: dict[str, list[int]] = dataclasses.field(default_factory=dict)

    def record_event(
        self, *, kind: EventKind, summary: str,
        participants: t.Iterable[str],
        recorded_at: int,
        boss_id: t.Optional[str] = None,
        value: t.Optional[int] = None,
        region_id: t.Optional[str] = None,
    ) -> str:
        if not summary:
            return ""
        parts = tuple(p for p in participants if p)
        if not parts and kind not in (
            EventKind.NATION_VICTORY,
            EventKind.EXPANSION_UNLOCK,
        ):
            return ""
        self._next_id += 1
        eid = f"hist_{self._next_id}"
        entry = HistoryEntry(
            entry_id=eid, kind=kind, summary=summary,
            participants=parts, recorded_at=recorded_at,
            boss_id=boss_id, value=value, region_id=region_id,
        )
        idx = len(self._entries)
        self._entries.append(entry)
        for p in parts:
            self._by_player.setdefault(p, []).append(idx)
        if boss_id:
            self._by_boss.setdefault(boss_id, []).append(idx)
        return eid

    def get(self, *, entry_id: str) -> t.Optional[HistoryEntry]:
        for e in self._entries:
            if e.entry_id == entry_id:
                return e
        return None

    def events_for_player(
        self, *, player_id: str,
    ) -> tuple[HistoryEntry, ...]:
        idxs = self._by_player.get(player_id, [])
        return tuple(self._entries[i] for i in idxs)

    def events_for_boss(
        self, *, boss_id: str,
    ) -> tuple[HistoryEntry, ...]:
        idxs = self._by_boss.get(boss_id, [])
        return tuple(self._entries[i] for i in idxs)

    def query(self, *, qf: QueryFilter) -> tuple[HistoryEntry, ...]:
        out: list[HistoryEntry] = []
        for e in self._entries:
            if qf.kinds and e.kind not in qf.kinds:
                continue
            if qf.boss_id is not None and e.boss_id != qf.boss_id:
                continue
            if qf.participant_id is not None and (
                qf.participant_id not in e.participants
            ):
                continue
            if qf.region_id is not None and e.region_id != qf.region_id:
                continue
            if qf.since_seconds is not None and (
                e.recorded_at < qf.since_seconds
            ):
                continue
            out.append(e)
        return tuple(out)

    def total_entries(self) -> int:
        return len(self._entries)

    def world_firsts(self) -> tuple[HistoryEntry, ...]:
        return tuple(
            e for e in self._entries
            if e.kind == EventKind.WORLD_FIRST_KILL
        )


__all__ = [
    "EventKind", "HistoryEntry", "QueryFilter",
    "ServerHistoryLog",
]
