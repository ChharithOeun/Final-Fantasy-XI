"""Minimap engine — 3D-pop minimap entity registry.

The classic Windower minimap plugin had movable/resizable
positioning and pinned dots. Demoncore goes further: a 3D-pop
HUD that tracks party members, other players (different color),
and visible mobs in radius — but explicitly excludes FOMORS
(spectral pursuers tracked elsewhere; we don't want their dots
blowing the player's cover).

This module is the DATA LAYER. UI rendering happens in UE5/HUD;
this module answers "what dots should the minimap show right
now for player X?". It pulls live position+role data from the
caller and emits a snapshot of dot records the renderer paints.

Public surface
--------------
    DotKind enum          PARTY_MEMBER / SELF / OTHER_PLAYER
                          / MOB_HOSTILE / MOB_NEUTRAL /
                          MOB_FRIENDLY / NPC
    DotColor enum
    EntityRecord dataclass
    MinimapDot dataclass
    MinimapSnapshot dataclass
    MinimapEngine
        .register_entity(entity_id, kind, position, ...)
        .update_position(entity_id, x, y, z)
        .mark_fomor(entity_id) — entities marked Fomor never appear
        .clear_entity(entity_id)
        .snapshot_for(viewer_id, radius) -> MinimapSnapshot
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# Default radius around viewer for inclusion (game units).
DEFAULT_VIEW_RADIUS = 100.0
MAX_DOTS_PER_SNAPSHOT = 64


class DotKind(str, enum.Enum):
    SELF = "self"
    PARTY_MEMBER = "party_member"
    OTHER_PLAYER = "other_player"
    MOB_HOSTILE = "mob_hostile"
    MOB_NEUTRAL = "mob_neutral"
    MOB_FRIENDLY = "mob_friendly"
    NPC = "npc"


class DotColor(str, enum.Enum):
    """Distinct, accessible palette for the 3D-pop renderer."""
    BLUE = "blue"          # self
    CYAN = "cyan"          # party member
    GREEN = "green"        # friendly mob (charmed pet, trust)
    YELLOW = "yellow"      # other player (different color)
    RED = "red"            # hostile mob
    GRAY = "gray"          # neutral mob
    WHITE = "white"        # NPC


_DOT_COLOR_BY_KIND: dict[DotKind, DotColor] = {
    DotKind.SELF: DotColor.BLUE,
    DotKind.PARTY_MEMBER: DotColor.CYAN,
    DotKind.OTHER_PLAYER: DotColor.YELLOW,
    DotKind.MOB_HOSTILE: DotColor.RED,
    DotKind.MOB_NEUTRAL: DotColor.GRAY,
    DotKind.MOB_FRIENDLY: DotColor.GREEN,
    DotKind.NPC: DotColor.WHITE,
}


@dataclasses.dataclass
class EntityRecord:
    entity_id: str
    kind: DotKind
    zone_id: str
    x: float
    y: float
    z: float = 0.0
    display_name: str = ""
    is_fomor: bool = False
    last_updated_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class MinimapDot:
    entity_id: str
    kind: DotKind
    color: DotColor
    relative_x: float       # entity.x - viewer.x
    relative_y: float       # entity.y - viewer.y
    relative_z: float       # entity.z - viewer.z (height pop)
    distance: float
    display_name: str
    clickable: bool


@dataclasses.dataclass(frozen=True)
class MinimapSnapshot:
    viewer_id: str
    zone_id: str
    radius: float
    dots: tuple[MinimapDot, ...]
    excluded_fomors: int = 0
    truncated: int = 0


@dataclasses.dataclass
class MinimapEngine:
    default_radius: float = DEFAULT_VIEW_RADIUS
    max_dots: int = MAX_DOTS_PER_SNAPSHOT
    _entities: dict[str, EntityRecord] = dataclasses.field(
        default_factory=dict,
    )
    _party_members_of: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_entity(
        self, *, entity_id: str, kind: DotKind,
        zone_id: str, x: float, y: float, z: float = 0.0,
        display_name: str = "",
        now_seconds: float = 0.0,
    ) -> t.Optional[EntityRecord]:
        if entity_id in self._entities:
            return None
        rec = EntityRecord(
            entity_id=entity_id, kind=kind, zone_id=zone_id,
            x=x, y=y, z=z, display_name=display_name,
            last_updated_seconds=now_seconds,
        )
        self._entities[entity_id] = rec
        return rec

    def update_position(
        self, *, entity_id: str,
        x: float, y: float, z: float = 0.0,
        zone_id: t.Optional[str] = None,
        now_seconds: float = 0.0,
    ) -> bool:
        rec = self._entities.get(entity_id)
        if rec is None:
            return False
        rec.x = x
        rec.y = y
        rec.z = z
        if zone_id is not None:
            rec.zone_id = zone_id
        rec.last_updated_seconds = now_seconds
        return True

    def mark_fomor(self, *, entity_id: str) -> bool:
        rec = self._entities.get(entity_id)
        if rec is None:
            return False
        rec.is_fomor = True
        return True

    def clear_entity(self, *, entity_id: str) -> bool:
        return self._entities.pop(entity_id, None) is not None

    def declare_party(
        self, *, leader_id: str,
        member_ids: t.Iterable[str],
    ) -> bool:
        ids = set(member_ids) | {leader_id}
        for pid in ids:
            self._party_members_of[pid] = ids
        return True

    def disband_party(self, *, leader_id: str) -> bool:
        ids = self._party_members_of.get(leader_id)
        if ids is None:
            return False
        for pid in ids:
            self._party_members_of.pop(pid, None)
        return True

    def _classify_for_viewer(
        self, *, viewer_id: str, rec: EntityRecord,
    ) -> DotKind:
        """Promote OTHER_PLAYER → PARTY_MEMBER when the viewer
        and entity share a party, and PARTY_MEMBER → SELF for
        the viewer's own dot."""
        if rec.entity_id == viewer_id:
            return DotKind.SELF
        party = self._party_members_of.get(viewer_id)
        if party and rec.entity_id in party:
            # Even if originally registered as OTHER_PLAYER,
            # show as PARTY_MEMBER on this viewer's map.
            if rec.kind in (
                DotKind.OTHER_PLAYER, DotKind.PARTY_MEMBER,
            ):
                return DotKind.PARTY_MEMBER
        return rec.kind

    def snapshot_for(
        self, *, viewer_id: str,
        radius: t.Optional[float] = None,
    ) -> t.Optional[MinimapSnapshot]:
        viewer = self._entities.get(viewer_id)
        if viewer is None:
            return None
        r = radius if radius is not None else self.default_radius

        candidates: list[tuple[float, EntityRecord, DotKind]] = []
        excluded_fomors = 0
        for rec in self._entities.values():
            if rec.zone_id != viewer.zone_id:
                continue
            if rec.is_fomor:
                excluded_fomors += 1
                continue
            dx = rec.x - viewer.x
            dy = rec.y - viewer.y
            dz = rec.z - viewer.z
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist > r and rec.entity_id != viewer_id:
                continue
            kind = self._classify_for_viewer(
                viewer_id=viewer_id, rec=rec,
            )
            candidates.append((dist, rec, kind))

        # Closest first
        candidates.sort(key=lambda t_: t_[0])
        truncated = 0
        if len(candidates) > self.max_dots:
            truncated = len(candidates) - self.max_dots
            candidates = candidates[: self.max_dots]

        dots: list[MinimapDot] = []
        for dist, rec, kind in candidates:
            color = _DOT_COLOR_BY_KIND[kind]
            clickable = kind in (
                DotKind.OTHER_PLAYER, DotKind.PARTY_MEMBER,
                DotKind.MOB_HOSTILE, DotKind.MOB_NEUTRAL,
                DotKind.MOB_FRIENDLY, DotKind.NPC,
            )
            dots.append(MinimapDot(
                entity_id=rec.entity_id, kind=kind,
                color=color,
                relative_x=rec.x - viewer.x,
                relative_y=rec.y - viewer.y,
                relative_z=rec.z - viewer.z,
                distance=dist,
                display_name=rec.display_name,
                clickable=clickable,
            ))

        return MinimapSnapshot(
            viewer_id=viewer_id, zone_id=viewer.zone_id,
            radius=r, dots=tuple(dots),
            excluded_fomors=excluded_fomors,
            truncated=truncated,
        )

    def total_entities(self) -> int:
        return len(self._entities)


__all__ = [
    "DEFAULT_VIEW_RADIUS", "MAX_DOTS_PER_SNAPSHOT",
    "DotKind", "DotColor",
    "EntityRecord", "MinimapDot", "MinimapSnapshot",
    "MinimapEngine",
]
