"""Player travelogue — narrative explorer journal.

A traveler keeps a travelogue: a chronological journal of
zones visited and short prose entries about each. Other
players can read published travelogues and like them; a
travelogue with many likes builds the writer's reputation
as a chronicler. Travelogues stay in DRAFT until the
writer publishes them — once published they are immutable.
A traveler can later AMEND a published travelogue with a
postscript, but cannot rewrite earlier entries.

Lifecycle (travelogue)
    DRAFT         in progress; entries can be added/edited
    PUBLISHED     released; entries locked, postscripts ok
    ARCHIVED      writer retired the travelogue

Public surface
--------------
    TravelogueState enum
    Travelogue dataclass (frozen)
    JournalEntry dataclass (frozen)
    PlayerTravelogueSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TravelogueState(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclasses.dataclass(frozen=True)
class Travelogue:
    travelogue_id: str
    writer_id: str
    title: str
    state: TravelogueState
    entry_count: int
    likes: int


@dataclasses.dataclass(frozen=True)
class JournalEntry:
    entry_index: int
    zone: str
    day: int
    prose: str
    is_postscript: bool


@dataclasses.dataclass
class _TState:
    spec: Travelogue
    entries: list[JournalEntry] = dataclasses.field(
        default_factory=list,
    )
    likers: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerTravelogueSystem:
    _logs: dict[str, _TState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def begin(
        self, *, writer_id: str, title: str,
    ) -> t.Optional[str]:
        if not writer_id or not title:
            return None
        tid = f"trav_{self._next}"
        self._next += 1
        self._logs[tid] = _TState(
            spec=Travelogue(
                travelogue_id=tid,
                writer_id=writer_id, title=title,
                state=TravelogueState.DRAFT,
                entry_count=0, likes=0,
            ),
        )
        return tid

    def add_entry(
        self, *, travelogue_id: str, writer_id: str,
        zone: str, day: int, prose: str,
    ) -> bool:
        if travelogue_id not in self._logs:
            return False
        st = self._logs[travelogue_id]
        if st.spec.writer_id != writer_id:
            return False
        if st.spec.state != TravelogueState.DRAFT:
            return False
        if not zone or not prose:
            return False
        if day < 0:
            return False
        # Entries must be chronologically non-decreasing
        if (
            st.entries
            and day < st.entries[-1].day
        ):
            return False
        st.entries.append(JournalEntry(
            entry_index=len(st.entries),
            zone=zone, day=day, prose=prose,
            is_postscript=False,
        ))
        st.spec = dataclasses.replace(
            st.spec, entry_count=len(st.entries),
        )
        return True

    def publish(
        self, *, travelogue_id: str, writer_id: str,
    ) -> bool:
        if travelogue_id not in self._logs:
            return False
        st = self._logs[travelogue_id]
        if st.spec.writer_id != writer_id:
            return False
        if st.spec.state != TravelogueState.DRAFT:
            return False
        if not st.entries:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=TravelogueState.PUBLISHED,
        )
        return True

    def add_postscript(
        self, *, travelogue_id: str, writer_id: str,
        zone: str, day: int, prose: str,
    ) -> bool:
        if travelogue_id not in self._logs:
            return False
        st = self._logs[travelogue_id]
        if st.spec.writer_id != writer_id:
            return False
        if st.spec.state != TravelogueState.PUBLISHED:
            return False
        if not zone or not prose:
            return False
        if (
            st.entries
            and day < st.entries[-1].day
        ):
            return False
        st.entries.append(JournalEntry(
            entry_index=len(st.entries),
            zone=zone, day=day, prose=prose,
            is_postscript=True,
        ))
        st.spec = dataclasses.replace(
            st.spec, entry_count=len(st.entries),
        )
        return True

    def like(
        self, *, travelogue_id: str, reader_id: str,
    ) -> bool:
        if travelogue_id not in self._logs:
            return False
        st = self._logs[travelogue_id]
        if st.spec.state != TravelogueState.PUBLISHED:
            return False
        if not reader_id:
            return False
        if reader_id == st.spec.writer_id:
            return False
        if reader_id in st.likers:
            return False
        st.likers.add(reader_id)
        st.spec = dataclasses.replace(
            st.spec, likes=len(st.likers),
        )
        return True

    def archive(
        self, *, travelogue_id: str, writer_id: str,
    ) -> bool:
        if travelogue_id not in self._logs:
            return False
        st = self._logs[travelogue_id]
        if st.spec.writer_id != writer_id:
            return False
        if st.spec.state == TravelogueState.ARCHIVED:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=TravelogueState.ARCHIVED,
        )
        return True

    def travelogue(
        self, *, travelogue_id: str,
    ) -> t.Optional[Travelogue]:
        st = self._logs.get(travelogue_id)
        return st.spec if st else None

    def entries(
        self, *, travelogue_id: str,
    ) -> list[JournalEntry]:
        st = self._logs.get(travelogue_id)
        if st is None:
            return []
        return list(st.entries)

    def by_writer(
        self, *, writer_id: str,
    ) -> list[Travelogue]:
        return [
            st.spec for st in self._logs.values()
            if st.spec.writer_id == writer_id
        ]


__all__ = [
    "TravelogueState", "Travelogue", "JournalEntry",
    "PlayerTravelogueSystem",
]
