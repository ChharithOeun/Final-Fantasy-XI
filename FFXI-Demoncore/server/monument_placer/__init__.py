"""Monument placer — physical stone monuments at the sites
of legendary events.

When something extraordinary happens at a specific spot
in the world — a world-first kill, a heroic last-stand,
a place where a famous duel was fought — the world should
remember it physically. The monument_placer is where that
remembrance becomes geometry.

Each monument has:
    - a position (zone_id + x, y, z)
    - a kind (which determines mesh + decoration palette)
    - an inscription (engraved text players can read)
    - a source_entry_id back to server_history_log
    - vandalism_resistance (some monuments are weatherproof
      and cannot be defaced; others can degrade)

MonumentKind
    OBELISK         tall stone shaft, world-firsts
    CAIRN           pile of stones, permadeath sites
    SHRINE          religious — for nation_victory
    STATUE          full figure, named hero only
    PLAQUE          flat memorial, attached to walls
    BURIAL_PILLAR   permadeath grave + epitaph

Public surface
--------------
    MonumentKind enum
    Monument dataclass (mutable; vandalism is mutable)
    MonumentPlacer
        .place_monument(zone_id, position, kind,
                        inscription, source_entry_id,
                        placed_at,
                        vandalism_resistant=False)
            -> monument_id
        .get(monument_id) -> Optional[Monument]
        .deface(monument_id, defaced_at) -> bool
        .repair(monument_id, repaired_at) -> bool
        .monuments_in_zone(zone_id) -> tuple[Monument, ...]
        .monuments_for_event(source_entry_id)
            -> tuple[Monument, ...]
        .total_placed() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MonumentKind(str, enum.Enum):
    OBELISK = "obelisk"
    CAIRN = "cairn"
    SHRINE = "shrine"
    STATUE = "statue"
    PLAQUE = "plaque"
    BURIAL_PILLAR = "burial_pillar"


@dataclasses.dataclass
class Monument:
    monument_id: str
    zone_id: str
    position: tuple[float, float, float]
    kind: MonumentKind
    inscription: str
    source_entry_id: t.Optional[str]
    placed_at: int
    vandalism_resistant: bool = False
    defaced: bool = False
    last_repaired_at: t.Optional[int] = None


@dataclasses.dataclass
class MonumentPlacer:
    _monuments: dict[str, Monument] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0
    _by_zone: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    _by_event: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )

    def place_monument(
        self, *, zone_id: str,
        position: tuple[float, float, float],
        kind: MonumentKind, inscription: str,
        source_entry_id: t.Optional[str],
        placed_at: int,
        vandalism_resistant: bool = False,
    ) -> str:
        if not zone_id or not inscription:
            return ""
        self._next_id += 1
        mid = f"mon_{self._next_id}"
        m = Monument(
            monument_id=mid, zone_id=zone_id,
            position=position, kind=kind,
            inscription=inscription,
            source_entry_id=source_entry_id,
            placed_at=placed_at,
            vandalism_resistant=vandalism_resistant,
        )
        self._monuments[mid] = m
        self._by_zone.setdefault(zone_id, []).append(mid)
        if source_entry_id:
            self._by_event.setdefault(source_entry_id, []).append(mid)
        return mid

    def get(self, *, monument_id: str) -> t.Optional[Monument]:
        return self._monuments.get(monument_id)

    def deface(
        self, *, monument_id: str, defaced_at: int,
    ) -> bool:
        m = self._monuments.get(monument_id)
        if m is None:
            return False
        if m.vandalism_resistant:
            return False
        if m.defaced:
            return False
        m.defaced = True
        return True

    def repair(
        self, *, monument_id: str, repaired_at: int,
    ) -> bool:
        m = self._monuments.get(monument_id)
        if m is None:
            return False
        if not m.defaced:
            return False
        m.defaced = False
        m.last_repaired_at = repaired_at
        return True

    def monuments_in_zone(
        self, *, zone_id: str,
    ) -> tuple[Monument, ...]:
        ids = self._by_zone.get(zone_id, [])
        return tuple(self._monuments[i] for i in ids)

    def monuments_for_event(
        self, *, source_entry_id: str,
    ) -> tuple[Monument, ...]:
        ids = self._by_event.get(source_entry_id, [])
        return tuple(self._monuments[i] for i in ids)

    def total_placed(self) -> int:
        return len(self._monuments)


__all__ = ["MonumentKind", "Monument", "MonumentPlacer"]
