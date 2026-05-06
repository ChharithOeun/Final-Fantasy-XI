"""Biome transition zones — points where surface / deep / sky meet.

Each TransitionZone is a tagged location at a specific
(zone, band) where a player can move from one biome to
another. Examples:

  Bastok Harbor       — SURFACE_LAND <-> SURFACE_SEA
  Pearl Diving Pier   — SURFACE_SEA  <-> SHALLOW
  Norg Sub Bay        — SURFACE_SEA  <-> DEEP   (gated: sub)
  Cloud City Port     — SURFACE_LAND <-> MID    (gated: airship_pass)
  Wyvern Aerie        — MID          <-> STRAT  (gated: wyvern_rep)

Transit can be one-way (e.g. dragon-only ascent) or
bidirectional. Each transit may be GATED on a key item or
reputation threshold; ungated transits are public.

Public surface
--------------
    BiomeKind enum
    TransitionZone dataclass (frozen)
    GateKind enum
    BiomeTransitionZones
        .register(transit_id, name, zone_id, band,
                  from_biome, to_biome, bidirectional,
                  gate_kind, gate_key)
        .transitions_at(zone_id, band)
            -> tuple[TransitionZone, ...]
        .can_transit(player_keys, faction_reps, transit_id)
            -> (bool, reason)
        .find_path_across_biomes(start_biome, end_biome)
            -> tuple[TransitionZone, ...]  (BFS one-hop only)
"""
from __future__ import annotations

import collections
import dataclasses
import enum
import typing as t


class BiomeKind(str, enum.Enum):
    SURFACE_LAND = "surface_land"
    SURFACE_SEA = "surface_sea"
    SHALLOW = "shallow"
    DEEP = "deep"
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    STRATOSPHERE = "stratosphere"


class GateKind(str, enum.Enum):
    NONE = "none"
    KEY_ITEM = "key_item"
    FACTION_REP = "faction_rep"


@dataclasses.dataclass(frozen=True)
class TransitionZone:
    transit_id: str
    name: str
    zone_id: str
    band: int
    from_biome: BiomeKind
    to_biome: BiomeKind
    bidirectional: bool
    gate_kind: GateKind
    gate_key: t.Optional[str] = None
    gate_threshold: int = 0


@dataclasses.dataclass
class BiomeTransitionZones:
    _transits: dict[str, TransitionZone] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, transit_id: str, name: str,
        zone_id: str, band: int,
        from_biome: BiomeKind, to_biome: BiomeKind,
        bidirectional: bool = True,
        gate_kind: GateKind = GateKind.NONE,
        gate_key: t.Optional[str] = None,
        gate_threshold: int = 0,
    ) -> bool:
        if not transit_id or transit_id in self._transits:
            return False
        if not name or not zone_id:
            return False
        if from_biome == to_biome:
            return False
        self._transits[transit_id] = TransitionZone(
            transit_id=transit_id, name=name,
            zone_id=zone_id, band=band,
            from_biome=from_biome, to_biome=to_biome,
            bidirectional=bidirectional,
            gate_kind=gate_kind,
            gate_key=gate_key,
            gate_threshold=gate_threshold,
        )
        return True

    def transitions_at(
        self, *, zone_id: str, band: int,
    ) -> tuple[TransitionZone, ...]:
        out = [
            t for t in self._transits.values()
            if t.zone_id == zone_id and t.band == band
        ]
        return tuple(out)

    def can_transit(
        self, *, transit_id: str,
        player_keys: t.Optional[t.Iterable[str]] = None,
        faction_reps: t.Optional[dict[str, int]] = None,
    ) -> tuple[bool, t.Optional[str]]:
        t_ = self._transits.get(transit_id)
        if t_ is None:
            return False, "unknown transit"
        if t_.gate_kind == GateKind.NONE:
            return True, None
        keys = set(player_keys or [])
        reps = faction_reps or {}
        if t_.gate_kind == GateKind.KEY_ITEM:
            if t_.gate_key and t_.gate_key in keys:
                return True, None
            return False, "missing key item"
        if t_.gate_kind == GateKind.FACTION_REP:
            if t_.gate_key is None:
                return True, None
            if reps.get(t_.gate_key, 0) >= t_.gate_threshold:
                return True, None
            return False, "faction rep too low"
        return False, "unknown gate"

    def find_path_across_biomes(
        self, *, start_biome: BiomeKind,
        end_biome: BiomeKind,
    ) -> t.Optional[tuple[TransitionZone, ...]]:
        if start_biome == end_biome:
            return ()
        # build adjacency: biome -> [(transit, neighbor_biome), ...]
        adj: dict[BiomeKind, list[tuple[TransitionZone, BiomeKind]]] = (
            collections.defaultdict(list)
        )
        for t_ in self._transits.values():
            adj[t_.from_biome].append((t_, t_.to_biome))
            if t_.bidirectional:
                adj[t_.to_biome].append((t_, t_.from_biome))
        # BFS
        prev: dict[BiomeKind, tuple[BiomeKind, TransitionZone]] = {}
        q: collections.deque[BiomeKind] = collections.deque([start_biome])
        visited = {start_biome}
        while q:
            cur = q.popleft()
            if cur == end_biome:
                # reconstruct path of transits
                path: list[TransitionZone] = []
                node = cur
                while node in prev:
                    parent, t_ = prev[node]
                    path.append(t_)
                    node = parent
                path.reverse()
                return tuple(path)
            for t_, nxt in adj.get(cur, []):
                if nxt in visited:
                    continue
                visited.add(nxt)
                prev[nxt] = (cur, t_)
                q.append(nxt)
        return None


__all__ = [
    "BiomeKind", "GateKind", "TransitionZone",
    "BiomeTransitionZones",
]
