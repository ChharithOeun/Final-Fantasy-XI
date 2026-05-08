"""Dynasty annals — per-family chronicle of accomplishments.

family_lineage tracks WHO is in a family. dynasty_annals
tracks WHAT THE FAMILY HAS DONE. Per-family ledger:
births, deaths, marriages, achievements, infamy. The
heir of a generation can READ the family's full history
back to the founder. NPCs reference it in dialogue
("you are of House Stoneforge — your great-grandfather
slew the wyvern of Boyahda").

Annal entries:
    BIRTH                a new generation entered the
                         line (heir designation +
                         permadeath of parent fires this)
    MARRIAGE             marriage_legacy.marry()
    PERMADEATH           a member died permanently
    ACHIEVEMENT          notable accomplishment (HNM
                         kill, level cap, master rank,
                         etc.)
    INFAMY               outlaw act, public_works
                         betrayal, broken treaty
                         signature
    HONOR_BESTOWED       title earned by a family member
    DESCENDANT_FIRST     a server-first by a descendant

Plus annal_score — derived from entry counts weighted by
kind. Other modules read this for "fame of house"
modifiers (npc_dialogue, mob_personality respect, etc.)

Public surface
--------------
    AnnalKind enum
    AnnalEntry dataclass (frozen)
    DynastyAnnals
        .open_dynasty(family_name) -> bool
        .record(family_name, kind, member_id, summary,
                day) -> Optional[str]
        .entries_for(family_name) -> list[AnnalEntry]
        .annal_score(family_name) -> int
        .members_listed(family_name) -> list[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AnnalKind(str, enum.Enum):
    BIRTH = "birth"
    MARRIAGE = "marriage"
    PERMADEATH = "permadeath"
    ACHIEVEMENT = "achievement"
    INFAMY = "infamy"
    HONOR_BESTOWED = "honor_bestowed"
    DESCENDANT_FIRST = "descendant_first"


_KIND_SCORE = {
    AnnalKind.BIRTH: 1,
    AnnalKind.MARRIAGE: 3,
    AnnalKind.PERMADEATH: 5,
    AnnalKind.ACHIEVEMENT: 5,
    AnnalKind.INFAMY: -8,
    AnnalKind.HONOR_BESTOWED: 7,
    AnnalKind.DESCENDANT_FIRST: 15,
}


@dataclasses.dataclass(frozen=True)
class AnnalEntry:
    entry_id: str
    family_name: str
    kind: AnnalKind
    member_id: str
    summary: str
    day: int


@dataclasses.dataclass
class DynastyAnnals:
    _families: set[str] = dataclasses.field(
        default_factory=set,
    )
    _entries: dict[str, list[AnnalEntry]] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def open_dynasty(self, *, family_name: str) -> bool:
        if not family_name:
            return False
        if family_name in self._families:
            return False
        self._families.add(family_name)
        self._entries[family_name] = []
        return True

    def record(
        self, *, family_name: str, kind: AnnalKind,
        member_id: str, summary: str, day: int,
    ) -> t.Optional[str]:
        if family_name not in self._families:
            return None
        if not member_id or not summary:
            return None
        if day < 0:
            return None
        entry_id = f"annal_{self._next_id}"
        self._next_id += 1
        self._entries[family_name].append(AnnalEntry(
            entry_id=entry_id, family_name=family_name,
            kind=kind, member_id=member_id,
            summary=summary, day=day,
        ))
        return entry_id

    def entries_for(
        self, *, family_name: str,
    ) -> list[AnnalEntry]:
        if family_name not in self._families:
            return []
        return sorted(
            self._entries[family_name],
            key=lambda e: e.day,
        )

    def entries_of_kind(
        self, *, family_name: str, kind: AnnalKind,
    ) -> list[AnnalEntry]:
        return [
            e for e in self.entries_for(
                family_name=family_name,
            )
            if e.kind == kind
        ]

    def annal_score(self, *, family_name: str) -> int:
        if family_name not in self._families:
            return 0
        return sum(
            _KIND_SCORE[e.kind]
            for e in self._entries[family_name]
        )

    def members_listed(
        self, *, family_name: str,
    ) -> list[str]:
        if family_name not in self._families:
            return []
        members = {e.member_id for e in self._entries[family_name]}
        return sorted(members)


__all__ = [
    "AnnalKind", "AnnalEntry", "DynastyAnnals",
]
