"""Guild archive — LS-internal records of past members,
internal events, and historical decisions.

Where server_chronicle is the public memory of major
world events, and dynasty_annals is family-scope, the
guild_archive sits at LS-scope: it tracks the
linkshell's INTERNAL HISTORY — every past member,
every leadership change, every internal proclamation,
every member that left or was expelled. It's the LS's
own version of personnel records + minutes.

Archives are sealed against editing. Adding a record
is the only mutation. Even if a player rejoins after
expulsion, their original expulsion record stays
visible.

Record kinds:
    MEMBER_JOINED          new pearl issued
    MEMBER_LEFT_VOLUNTARY  member quit
    MEMBER_EXPELLED        kicked
    MEMBER_PROMOTED        rank up
    MEMBER_DEMOTED         rank down
    LEADER_CHANGED         leader swap
    PROCLAMATION           leader-issued message
    HALL_PURCHASED         GuildHall purchased
    HALL_FORFEITED         GuildHall lapsed
    AT_WAR_DECLARED        formal war started
    AT_WAR_ENDED           formal war ended
    HONOR_RECEIVED         LS earned a server-wide
                           honor
    DISBANDED              LS dissolved

Public surface
--------------
    ArchiveKind enum
    ArchiveEntry dataclass (frozen)
    GuildArchiveSystem
        .open_archive(ls_id) -> bool
        .record(ls_id, kind, subject, body, day,
                witnesses) -> Optional[str]
        .entries(ls_id) -> list[ArchiveEntry]
        .entries_of_kind(ls_id, kind) -> list[ArchiveEntry]
        .entries_about(ls_id, subject) -> list[ArchiveEntry]
        .count(ls_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ArchiveKind(str, enum.Enum):
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT_VOLUNTARY = "member_left_voluntary"
    MEMBER_EXPELLED = "member_expelled"
    MEMBER_PROMOTED = "member_promoted"
    MEMBER_DEMOTED = "member_demoted"
    LEADER_CHANGED = "leader_changed"
    PROCLAMATION = "proclamation"
    HALL_PURCHASED = "hall_purchased"
    HALL_FORFEITED = "hall_forfeited"
    AT_WAR_DECLARED = "at_war_declared"
    AT_WAR_ENDED = "at_war_ended"
    HONOR_RECEIVED = "honor_received"
    DISBANDED = "disbanded"


@dataclasses.dataclass(frozen=True)
class ArchiveEntry:
    entry_id: str
    ls_id: str
    kind: ArchiveKind
    subject: str        # member_id or "" if not member
    body: str
    day: int
    witnesses: tuple[str, ...]


@dataclasses.dataclass
class GuildArchiveSystem:
    _archives: dict[str, list[ArchiveEntry]] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def open_archive(self, *, ls_id: str) -> bool:
        if not ls_id:
            return False
        if ls_id in self._archives:
            return False
        self._archives[ls_id] = []
        return True

    def record(
        self, *, ls_id: str, kind: ArchiveKind,
        subject: str, body: str, day: int,
        witnesses: t.Sequence[str] = (),
    ) -> t.Optional[str]:
        if ls_id not in self._archives:
            return None
        if not body or day < 0:
            return None
        eid = f"arch_{self._next_id}"
        self._next_id += 1
        entry = ArchiveEntry(
            entry_id=eid, ls_id=ls_id, kind=kind,
            subject=subject, body=body, day=day,
            witnesses=tuple(witnesses),
        )
        self._archives[ls_id].append(entry)
        return eid

    def entries(
        self, *, ls_id: str,
    ) -> list[ArchiveEntry]:
        return list(self._archives.get(ls_id, ()))

    def entries_of_kind(
        self, *, ls_id: str, kind: ArchiveKind,
    ) -> list[ArchiveEntry]:
        return [
            e for e in self._archives.get(ls_id, ())
            if e.kind == kind
        ]

    def entries_about(
        self, *, ls_id: str, subject: str,
    ) -> list[ArchiveEntry]:
        return [
            e for e in self._archives.get(ls_id, ())
            if e.subject == subject
        ]

    def count(self, *, ls_id: str) -> int:
        return len(self._archives.get(ls_id, ()))


__all__ = [
    "ArchiveKind", "ArchiveEntry",
    "GuildArchiveSystem",
]
