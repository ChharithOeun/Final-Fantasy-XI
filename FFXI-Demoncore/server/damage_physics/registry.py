"""StructureRegistry — per-zone collection of HealingStructures.

Backs the SQL pair from DAMAGE_PHYSICS_HEALING.md:
    - zone_structures        (static design data: positions, presets)
    - zone_structures_state  (live HP per server)

In-memory implementation here — persistence is the caller's job. The
registry exposes:
    spawn_structure(zone_id, kind, position) -> HealingStructure
    structures_in_zone(zone_id) -> list
    structures_in_radius(zone_id, point, radius) -> list
    iter_all() -> iterator
    tick_all(now, dt, broadcast_only=True) -> list[HealEvent]
    snapshot() / restore(...)               # persistence helpers
"""
from __future__ import annotations

import dataclasses
import math
import typing as t
import uuid

from .heal_tick import HealEvent, filter_broadcastable, heal_tick_many
from .structure_kinds import STRUCTURE_PRESETS, get_preset
from .structure_state import HealingStructure, VisibleState


@dataclasses.dataclass(frozen=True)
class StructureSnapshot:
    """Serializable shape of one structure for persistence."""
    structure_id: str
    zone_id: str
    kind: str
    position: tuple[float, float, float]
    hp_current: int
    visible_state: str
    last_hit_at: t.Optional[float]
    permanent: bool


class StructureRegistry:
    """In-memory home for every HealingStructure in the world.

    The pretty terminal print of this code module is intentionally
    minimal — each structure is one row, each tick is the same loop,
    and the test suite doesn't need surprises.
    """

    def __init__(self) -> None:
        self._structures: dict[str, HealingStructure] = {}
        # zone_id -> set of structure_ids
        self._by_zone: dict[str, set[str]] = {}

    # ------------------------------------------------------------------
    # Spawn / lookup
    # ------------------------------------------------------------------

    def spawn_structure(
        self,
        *,
        zone_id: str,
        kind: str,
        position: tuple[float, float, float],
        structure_id: t.Optional[str] = None,
    ) -> HealingStructure:
        preset = get_preset(kind)
        if preset is None:
            raise ValueError(f"unknown structure kind '{kind}'")
        sid = structure_id or f"struct_{uuid.uuid4().hex[:12]}"
        if sid in self._structures:
            raise ValueError(f"structure id '{sid}' already exists")
        s = HealingStructure.from_preset(
            structure_id=sid, zone_id=zone_id,
            position=position, preset=preset,
        )
        self._structures[sid] = s
        self._by_zone.setdefault(zone_id, set()).add(sid)
        return s

    def get(self, structure_id: str) -> t.Optional[HealingStructure]:
        return self._structures.get(structure_id)

    def structures_in_zone(self, zone_id: str) -> list[HealingStructure]:
        sids = self._by_zone.get(zone_id, set())
        return [self._structures[s] for s in sids
                  if s in self._structures]

    def iter_all(self) -> t.Iterator[HealingStructure]:
        return iter(self._structures.values())

    def __len__(self) -> int:
        return len(self._structures)

    def remove(self, structure_id: str) -> bool:
        s = self._structures.pop(structure_id, None)
        if s is None:
            return False
        self._by_zone.get(s.zone_id, set()).discard(structure_id)
        return True

    # ------------------------------------------------------------------
    # Spatial query
    # ------------------------------------------------------------------

    def structures_in_radius(
        self,
        *,
        zone_id: str,
        point: tuple[float, float, float],
        radius: float,
    ) -> list[HealingStructure]:
        if radius < 0:
            raise ValueError("radius must be non-negative")
        out: list[HealingStructure] = []
        for s in self.structures_in_zone(zone_id):
            dx = s.position[0] - point[0]
            dy = s.position[1] - point[1]
            dz = s.position[2] - point[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            if d <= radius:
                out.append(s)
        return out

    # ------------------------------------------------------------------
    # World tick
    # ------------------------------------------------------------------

    def tick_all(
        self,
        *,
        now: float,
        dt: float,
        broadcast_only: bool = True,
    ) -> list[HealEvent]:
        """Run heal_tick on every structure. By default returns only
        events where the visible state stage changed (the only ones
        LSB broadcasts to clients).
        """
        events = heal_tick_many(self.iter_all(), now=now, dt=dt)
        if broadcast_only:
            return filter_broadcastable(events)
        return events

    def tick_zone(
        self,
        *,
        zone_id: str,
        now: float,
        dt: float,
        broadcast_only: bool = True,
    ) -> list[HealEvent]:
        events = heal_tick_many(self.structures_in_zone(zone_id),
                                  now=now, dt=dt)
        if broadcast_only:
            return filter_broadcastable(events)
        return events

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def snapshot(self) -> list[StructureSnapshot]:
        """Serialize for zone_structures_state persistence."""
        return [
            StructureSnapshot(
                structure_id=s.structure_id,
                zone_id=s.zone_id,
                kind=s.kind,
                position=s.position,
                hp_current=s.hp_current,
                visible_state=s.visible_state.value,
                last_hit_at=s.last_hit_at,
                permanent=s.permanent,
            )
            for s in self._structures.values()
        ]

    def restore(self, snapshots: t.Iterable[StructureSnapshot]) -> int:
        """Rehydrate from persisted snapshots. Returns count restored.

        Per the doc: 'On server restart we reload the state — partial
        damage persists across server restarts, so a wall hit in last
        night's siege is still visibly damaged in the morning while
        it heals.'
        """
        count = 0
        for snap in snapshots:
            preset = get_preset(snap.kind)
            if preset is None:
                continue   # unknown kind, skip
            s = HealingStructure(
                structure_id=snap.structure_id,
                zone_id=snap.zone_id,
                kind=snap.kind,
                position=snap.position,
                hp_max=preset.hp_max,
                heal_rate=preset.heal_rate,
                heal_delay_s=preset.heal_delay_s,
                permanent_threshold=preset.permanent_threshold,
                hp_current=snap.hp_current,
                visible_state=VisibleState(snap.visible_state),
                last_hit_at=snap.last_hit_at,
                permanent=snap.permanent,
            )
            self._structures[s.structure_id] = s
            self._by_zone.setdefault(s.zone_id, set()).add(s.structure_id)
            count += 1
        return count


# Module-level singleton convenience.
_GLOBAL_REGISTRY = StructureRegistry()


def global_registry() -> StructureRegistry:
    return _GLOBAL_REGISTRY


def reset_global_registry() -> None:
    """For tests."""
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = StructureRegistry()
