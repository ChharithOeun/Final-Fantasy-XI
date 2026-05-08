"""Guild legacy — preserve LS identity post-dissolution.

When a linkshell DISBANDS, the natural reflex is to drop
all data and free the namespace. Demoncore takes the
opposite stance: the LS's identity is enshrined in a
LEGACY RECORD, an immutable monument to its existence.
The pearl color, the leadership lineage, the major
honors, the famous fights — all preserved.

Why? Because reputation matters. A famous LS that ran
hard for 5 years deserves to leave a mark in Vana'diel.
A new LS founded years later cannot reuse the same
name; the legacy registry blocks it (a "namespace
graveyard"). NPC dialogue can reference past LS — the
old guard remembers.

A LegacyRecord is created via `seal()` once, on
disband. It carries:
    legacy_id
    ls_id (original)
    name (original)
    pearl_color
    founded_day
    sealed_day
    founder_id
    final_leader_id
    member_count_at_seal
    notable_honors        list of honor strings
    cause                 enum: VOLUNTARY / FORFEITED /
                          OUTLAWED_DISSOLVED / EXTINCT

After sealing, the LS name is forever marked as
"sealed" — a future LS attempting that name is
rejected. The system tracks an "honor_score" derived
from len(notable_honors) so NPCs can rank legacies.

Public surface
--------------
    DisbandCause enum
    LegacyRecord dataclass (frozen)
    GuildLegacySystem
        .seal(...) -> Optional[str]
        .name_is_sealed(name) -> bool
        .legacy(legacy_id) -> Optional[LegacyRecord]
        .legacy_for_ls(ls_id) -> Optional[LegacyRecord]
        .top_legacies(limit) -> list[LegacyRecord]
        .all_legacies() -> list[LegacyRecord]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DisbandCause(str, enum.Enum):
    VOLUNTARY = "voluntary"
    FORFEITED = "forfeited"
    OUTLAWED_DISSOLVED = "outlawed_dissolved"
    EXTINCT = "extinct"


@dataclasses.dataclass(frozen=True)
class LegacyRecord:
    legacy_id: str
    ls_id: str
    name: str
    pearl_color: str
    founded_day: int
    sealed_day: int
    founder_id: str
    final_leader_id: str
    member_count_at_seal: int
    notable_honors: tuple[str, ...]
    cause: DisbandCause

    @property
    def honor_score(self) -> int:
        return len(self.notable_honors)


@dataclasses.dataclass
class GuildLegacySystem:
    _legacies: dict[str, LegacyRecord] = dataclasses.field(
        default_factory=dict,
    )
    _ls_to_legacy: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _sealed_names: set[str] = dataclasses.field(
        default_factory=set,
    )
    _next_id: int = 1

    def seal(
        self, *, ls_id: str, name: str,
        pearl_color: str, founded_day: int,
        sealed_day: int, founder_id: str,
        final_leader_id: str,
        member_count_at_seal: int,
        notable_honors: t.Sequence[str] = (),
        cause: DisbandCause = DisbandCause.VOLUNTARY,
    ) -> t.Optional[str]:
        if not ls_id or not name:
            return None
        if not pearl_color:
            return None
        if founded_day < 0 or sealed_day < founded_day:
            return None
        if not founder_id or not final_leader_id:
            return None
        if member_count_at_seal < 0:
            return None
        if ls_id in self._ls_to_legacy:
            return None
        legacy_id = f"leg_{self._next_id}"
        self._next_id += 1
        rec = LegacyRecord(
            legacy_id=legacy_id, ls_id=ls_id, name=name,
            pearl_color=pearl_color,
            founded_day=founded_day,
            sealed_day=sealed_day,
            founder_id=founder_id,
            final_leader_id=final_leader_id,
            member_count_at_seal=member_count_at_seal,
            notable_honors=tuple(notable_honors),
            cause=cause,
        )
        self._legacies[legacy_id] = rec
        self._ls_to_legacy[ls_id] = legacy_id
        self._sealed_names.add(name.lower())
        return legacy_id

    def name_is_sealed(self, *, name: str) -> bool:
        return name.lower() in self._sealed_names

    def legacy(
        self, *, legacy_id: str,
    ) -> t.Optional[LegacyRecord]:
        return self._legacies.get(legacy_id)

    def legacy_for_ls(
        self, *, ls_id: str,
    ) -> t.Optional[LegacyRecord]:
        if ls_id not in self._ls_to_legacy:
            return None
        return self._legacies[self._ls_to_legacy[ls_id]]

    def top_legacies(
        self, *, limit: int,
    ) -> list[LegacyRecord]:
        if limit <= 0:
            return []
        ordered = sorted(
            self._legacies.values(),
            key=lambda r: (-r.honor_score,
                           r.sealed_day),
        )
        return ordered[:limit]

    def all_legacies(self) -> list[LegacyRecord]:
        return list(self._legacies.values())


__all__ = [
    "DisbandCause", "LegacyRecord",
    "GuildLegacySystem",
]
