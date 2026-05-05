"""Depth band atlas — 3D pathing for underwater zones.

zone_atlas knows which zones connect to which on the
surface map. Underwater that's not enough — within a zone
you might transit between SHALLOW and DEEP, and the
ascend/descend route might go through a vent shaft, a
trench drop, a kelp tunnel, or a zone-line that just
happens to dump you out at MID instead of SURFACE.

A node here is (zone_id, band). Edges are typed:
  ASCEND     - upward within a zone
  DESCEND    - downward within a zone
  ZONE_LINE  - to a different zone (any band)

Some edges require a key item (depth gear, pearl,
diving suit). The pathfinder takes a set of keys the
player owns and skips gated edges they can't unlock.

BFS gives the shortest hop count — same approach as
zone_atlas, just over a 3D node space.

Public surface
--------------
    TransitionKind enum
    BandTransition dataclass (frozen)
    DepthBandAtlas
        .register_zone(zone_id, available_bands)
        .add_transition(from_zone, from_band, to_zone, to_band,
                        kind, gate_key_item=None)
        .bands_in(zone_id) -> tuple[int, ...]
        .path(start_zone, start_band, end_zone, end_band,
              available_keys) -> list[(zone, band)] or None
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


class TransitionKind(str, enum.Enum):
    ASCEND = "ascend"
    DESCEND = "descend"
    ZONE_LINE = "zone_line"


@dataclasses.dataclass(frozen=True)
class BandTransition:
    from_zone: str
    from_band: int
    to_zone: str
    to_band: int
    kind: TransitionKind
    gate_key_item: t.Optional[str] = None


_Node = tuple[str, int]


@dataclasses.dataclass
class DepthBandAtlas:
    _bands_by_zone: dict[str, set[int]] = dataclasses.field(
        default_factory=dict,
    )
    # adjacency: node -> list[BandTransition]
    _edges: dict[_Node, list[BandTransition]] = dataclasses.field(
        default_factory=dict,
    )

    def register_zone(
        self, *, zone_id: str,
        available_bands: t.Iterable[int],
    ) -> bool:
        if not zone_id:
            return False
        self._bands_by_zone[zone_id] = set(available_bands)
        return True

    def add_transition(
        self, *, from_zone: str, from_band: int,
        to_zone: str, to_band: int,
        kind: TransitionKind,
        gate_key_item: t.Optional[str] = None,
    ) -> bool:
        if from_zone not in self._bands_by_zone:
            return False
        if to_zone not in self._bands_by_zone:
            return False
        if from_band not in self._bands_by_zone[from_zone]:
            return False
        if to_band not in self._bands_by_zone[to_zone]:
            return False
        edge = BandTransition(
            from_zone=from_zone, from_band=from_band,
            to_zone=to_zone, to_band=to_band,
            kind=kind, gate_key_item=gate_key_item,
        )
        self._edges.setdefault(
            (from_zone, from_band), [],
        ).append(edge)
        return True

    def bands_in(
        self, *, zone_id: str,
    ) -> tuple[int, ...]:
        return tuple(sorted(self._bands_by_zone.get(zone_id, set())))

    def path(
        self, *, start_zone: str, start_band: int,
        end_zone: str, end_band: int,
        available_keys: t.Optional[t.Iterable[str]] = None,
    ) -> t.Optional[list[_Node]]:
        keys = set(available_keys or [])
        start: _Node = (start_zone, start_band)
        end: _Node = (end_zone, end_band)
        if start_zone not in self._bands_by_zone:
            return None
        if start_band not in self._bands_by_zone[start_zone]:
            return None
        if end_zone not in self._bands_by_zone:
            return None
        if end_band not in self._bands_by_zone[end_zone]:
            return None
        if start == end:
            return [start]
        # BFS
        prev: dict[_Node, _Node] = {}
        visited = {start}
        q: collections.deque[_Node] = collections.deque([start])
        while q:
            cur = q.popleft()
            for edge in self._edges.get(cur, []):
                if (
                    edge.gate_key_item is not None
                    and edge.gate_key_item not in keys
                ):
                    continue
                nxt: _Node = (edge.to_zone, edge.to_band)
                if nxt in visited:
                    continue
                visited.add(nxt)
                prev[nxt] = cur
                if nxt == end:
                    # reconstruct
                    path: list[_Node] = [end]
                    while path[-1] != start:
                        path.append(prev[path[-1]])
                    path.reverse()
                    return path
                q.append(nxt)
        return None


__all__ = [
    "TransitionKind", "BandTransition", "DepthBandAtlas",
]
