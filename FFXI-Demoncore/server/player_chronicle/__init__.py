"""Player chronicle — auto-recorded journal of significant events.

The world records what each player has done. Significant events
get auto-logged into the player's chronicle:

* NM kills + boss kills
* Faction-rep band changes (Friendly -> Allied)
* Mission steps completed
* Permadeaths witnessed
* Level-ups (every 5 levels)
* Quest chain completions
* Lore set unlocks

The chronicle is browseable in-game (read your story) and
shareable (post excerpts to a linkshell). AI NPCs can READ from
the chronicle to greet the player with context-aware lines:
"I heard you slew Zerde at the Crag of Mea — quite a feat."

Public surface
--------------
    ChronicleEventKind enum
    ChronicleEntry dataclass
    PlayerChronicle dataclass
    ChronicleRegistry
        .record(player_id, kind, summary, details, now)
        .for_player(player_id) -> tuple[ChronicleEntry]
        .last_n(player_id, n) / .by_kind(player_id, kind)
        .recent_summary(player_id, top_n) -> str  for AI prompts
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ChronicleEventKind(str, enum.Enum):
    NM_KILL = "nm_kill"
    BOSS_KILL = "boss_kill"
    FACTION_BAND_UP = "faction_band_up"
    FACTION_BAND_DOWN = "faction_band_down"
    MISSION_STEP = "mission_step"
    QUEST_CHAIN_COMPLETE = "quest_chain_complete"
    LORE_SET_COMPLETE = "lore_set_complete"
    LEVEL_MILESTONE = "level_milestone"      # every 5 levels
    PERMADEATH = "permadeath"
    PARTY_WIPE = "party_wipe"
    NEW_TITLE = "new_title"
    JOB_UNLOCK = "job_unlock"
    LANDMARK_DISCOVERED = "landmark_discovered"
    SERVER_FIRST = "server_first"


@dataclasses.dataclass(frozen=True)
class ChronicleEntry:
    entry_id: str
    player_id: str
    kind: ChronicleEventKind
    summary: str
    details: str = ""
    recorded_at_seconds: float = 0.0
    notes: str = ""


@dataclasses.dataclass
class _PlayerChronicleStore:
    entries: list[ChronicleEntry] = dataclasses.field(
        default_factory=list,
    )
    next_id: int = 0


@dataclasses.dataclass
class ChronicleRegistry:
    _stores: dict[
        str, _PlayerChronicleStore,
    ] = dataclasses.field(default_factory=dict)

    def _store(self, player_id: str) -> _PlayerChronicleStore:
        s = self._stores.get(player_id)
        if s is None:
            s = _PlayerChronicleStore()
            self._stores[player_id] = s
        return s

    def record(
        self, *, player_id: str,
        kind: ChronicleEventKind,
        summary: str, details: str = "",
        now_seconds: float = 0.0,
    ) -> ChronicleEntry:
        s = self._store(player_id)
        eid = f"chron_{player_id}_{s.next_id}"
        s.next_id += 1
        entry = ChronicleEntry(
            entry_id=eid, player_id=player_id,
            kind=kind, summary=summary, details=details,
            recorded_at_seconds=now_seconds,
        )
        s.entries.append(entry)
        return entry

    def for_player(
        self, player_id: str,
    ) -> tuple[ChronicleEntry, ...]:
        return tuple(self._store(player_id).entries)

    def by_kind(
        self, *, player_id: str,
        kind: ChronicleEventKind,
    ) -> tuple[ChronicleEntry, ...]:
        return tuple(
            e for e in self._store(player_id).entries
            if e.kind == kind
        )

    def last_n(
        self, *, player_id: str, n: int,
    ) -> tuple[ChronicleEntry, ...]:
        if n <= 0:
            return ()
        entries = self._store(player_id).entries
        return tuple(entries[-n:])

    def total(self, player_id: str) -> int:
        return len(self._store(player_id).entries)

    def recent_summary(
        self, *, player_id: str, top_n: int = 5,
    ) -> str:
        """Compact text suitable for the orchestrator's prompt."""
        recent = self.last_n(player_id=player_id, n=top_n)
        if not recent:
            return "(no recorded deeds)"
        lines = [
            f"- [{e.kind.value}] {e.summary}"
            for e in recent
        ]
        return "\n".join(lines)

    def has_event_kind(
        self, *, player_id: str,
        kind: ChronicleEventKind,
    ) -> bool:
        return bool(self.by_kind(
            player_id=player_id, kind=kind,
        ))


__all__ = [
    "ChronicleEventKind", "ChronicleEntry",
    "ChronicleRegistry",
]
