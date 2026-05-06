"""Hall of Heroes — physical building of statues for title-holders.

Each nation has one. Walk inside and the world's heroes
look back at you. Statues are arranged by tier into
alcoves; the floor matters; lighting matters; the same
architectural grammar that makes a real hall feel sacred.

Hall layout:
    foyer       quiet entrance, COMMON statues if shown
    nave        long room, NOTED + EPIC alcoves
    chancel     bright, REVERED alcoves
    sanctum     vault, MYTHIC statues only

Statues are placed via curate_statue() which records
provenance: which title earned the statue, who carved it,
when it was unveiled. A hall has visit_count for
analytics — how many players have walked through.

Public surface
--------------
    HallSection enum
    Statue dataclass (frozen)
    Hall dataclass (mutable)
    HallOfHeroes
        .register_hall(hall_id, zone_id, region_id)
        .curate_statue(hall_id, title_id, player_id,
                       sculptor_id, unveiled_at,
                       section) -> statue_id
        .remove_statue(statue_id) -> bool
        .visit(hall_id, visitor_id, visited_at) -> bool
        .statues_in_section(hall_id, section)
            -> tuple[Statue, ...]
        .statues_for_player(player_id)
            -> tuple[Statue, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HallSection(str, enum.Enum):
    FOYER = "foyer"        # COMMON
    NAVE = "nave"          # NOTED + EPIC
    CHANCEL = "chancel"    # REVERED
    SANCTUM = "sanctum"    # MYTHIC


@dataclasses.dataclass(frozen=True)
class Statue:
    statue_id: str
    hall_id: str
    section: HallSection
    title_id: str
    player_id: str
    sculptor_id: str
    unveiled_at: int


@dataclasses.dataclass
class Hall:
    hall_id: str
    zone_id: str
    region_id: str
    visit_count: int = 0
    statue_ids: tuple[str, ...] = ()


@dataclasses.dataclass
class HallOfHeroes:
    _halls: dict[str, Hall] = dataclasses.field(default_factory=dict)
    _statues: dict[str, Statue] = dataclasses.field(default_factory=dict)
    _next_id: int = 0
    _by_player: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_hall(
        self, *, hall_id: str, zone_id: str, region_id: str,
    ) -> bool:
        if not hall_id or not zone_id:
            return False
        if hall_id in self._halls:
            return False
        self._halls[hall_id] = Hall(
            hall_id=hall_id, zone_id=zone_id, region_id=region_id,
        )
        return True

    def get_hall(self, *, hall_id: str) -> t.Optional[Hall]:
        return self._halls.get(hall_id)

    def curate_statue(
        self, *, hall_id: str, title_id: str, player_id: str,
        sculptor_id: str, unveiled_at: int,
        section: HallSection,
    ) -> str:
        h = self._halls.get(hall_id)
        if h is None:
            return ""
        if not title_id or not player_id or not sculptor_id:
            return ""
        # one statue per (hall, title, player) triple
        for sid in h.statue_ids:
            s = self._statues.get(sid)
            if s and s.title_id == title_id and s.player_id == player_id:
                return ""
        self._next_id += 1
        statue_id = f"statue_{self._next_id}"
        s = Statue(
            statue_id=statue_id, hall_id=hall_id,
            section=section, title_id=title_id,
            player_id=player_id, sculptor_id=sculptor_id,
            unveiled_at=unveiled_at,
        )
        self._statues[statue_id] = s
        h.statue_ids = h.statue_ids + (statue_id,)
        self._by_player.setdefault(player_id, []).append(statue_id)
        return statue_id

    def remove_statue(self, *, statue_id: str) -> bool:
        s = self._statues.get(statue_id)
        if s is None:
            return False
        h = self._halls.get(s.hall_id)
        if h is None:
            return False
        h.statue_ids = tuple(
            sid for sid in h.statue_ids if sid != statue_id
        )
        self._by_player.get(s.player_id, []).remove(statue_id)
        del self._statues[statue_id]
        return True

    def visit(
        self, *, hall_id: str, visitor_id: str,
        visited_at: int,
    ) -> bool:
        h = self._halls.get(hall_id)
        if h is None or not visitor_id:
            return False
        h.visit_count += 1
        return True

    def statues_in_section(
        self, *, hall_id: str, section: HallSection,
    ) -> tuple[Statue, ...]:
        h = self._halls.get(hall_id)
        if h is None:
            return ()
        return tuple(
            self._statues[sid] for sid in h.statue_ids
            if sid in self._statues
            and self._statues[sid].section == section
        )

    def statues_for_player(
        self, *, player_id: str,
    ) -> tuple[Statue, ...]:
        ids = self._by_player.get(player_id, [])
        return tuple(self._statues[i] for i in ids if i in self._statues)

    def total_statues(self) -> int:
        return len(self._statues)


__all__ = [
    "HallSection", "Statue", "Hall", "HallOfHeroes",
]
