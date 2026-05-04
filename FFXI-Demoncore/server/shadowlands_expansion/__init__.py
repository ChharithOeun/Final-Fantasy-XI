"""Shadowlands expansion — Demoncore custom expansion registry.

Introduces playable BEASTMEN races with their own MSQ that
RUNS PARALLEL AND INVERSE to the canonical Hume/Elvaan/Mithra/
Taru thread. Mechanically:

* New ZONES — Yagudo Highlands, Quadav Foundry, Lamia Sea-Hold,
  Orc Iron Cradle, plus shared Shadowland transitional zones.
* New beastman CITIES (handled in beastman_cities).
* Per-race MSQ chapters (inverse_msq_engine).
* Gear ladders that line up tier-for-tier with hume canon
  (beastman_gear_progression).

This module owns the EXPANSION-LEVEL state: ownership flag per
player, zone unlock graph, chapter prerequisites, expansion
status (PRE_RELEASE / OPEN / SUNSET).

Public surface
--------------
    ZoneKind enum        SHADOWLAND_HUB / YAGUDO / QUADAV /
                         LAMIA / ORC / TRANSITIONAL
    ExpansionStatus enum
    ShadowlandZone dataclass
    ShadowlandsExpansion
        .register_zone(zone_id, kind, prereq_zones, level_gate)
        .grant_ownership(player_id) — unlocks the expansion
        .has_ownership(player_id)
        .can_enter(player_id, zone_id, completed_zones, level)
        .mark_status(status)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ZoneKind(str, enum.Enum):
    SHADOWLAND_HUB = "shadowland_hub"
    YAGUDO = "yagudo"
    QUADAV = "quadav"
    LAMIA = "lamia"
    ORC = "orc"
    TRANSITIONAL = "transitional"


class ExpansionStatus(str, enum.Enum):
    PRE_RELEASE = "pre_release"
    OPEN = "open"
    EVENT_LIMITED = "event_limited"
    SUNSET = "sunset"


@dataclasses.dataclass(frozen=True)
class ShadowlandZone:
    zone_id: str
    kind: ZoneKind
    label: str
    level_gate: int
    prereq_zone_ids: tuple[str, ...]
    is_starter: bool = False


@dataclasses.dataclass(frozen=True)
class EntryCheckResult:
    accepted: bool
    zone_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class ShadowlandsExpansion:
    status: ExpansionStatus = ExpansionStatus.PRE_RELEASE
    _zones: dict[str, ShadowlandZone] = dataclasses.field(
        default_factory=dict,
    )
    _ownership: set[str] = dataclasses.field(
        default_factory=set,
    )

    def register_zone(
        self, *, zone_id: str, kind: ZoneKind,
        label: str, level_gate: int = 1,
        prereq_zone_ids: tuple[str, ...] = (),
        is_starter: bool = False,
    ) -> t.Optional[ShadowlandZone]:
        if zone_id in self._zones:
            return None
        if level_gate < 1:
            return None
        # Validate prereqs exist
        for p in prereq_zone_ids:
            if p not in self._zones:
                return None
        z = ShadowlandZone(
            zone_id=zone_id, kind=kind, label=label,
            level_gate=level_gate,
            prereq_zone_ids=prereq_zone_ids,
            is_starter=is_starter,
        )
        self._zones[zone_id] = z
        return z

    def zone(self, zone_id: str) -> t.Optional[ShadowlandZone]:
        return self._zones.get(zone_id)

    def grant_ownership(
        self, *, player_id: str,
    ) -> bool:
        if player_id in self._ownership:
            return False
        self._ownership.add(player_id)
        return True

    def revoke_ownership(
        self, *, player_id: str,
    ) -> bool:
        if player_id not in self._ownership:
            return False
        self._ownership.remove(player_id)
        return True

    def has_ownership(
        self, *, player_id: str,
    ) -> bool:
        return player_id in self._ownership

    def mark_status(
        self, *, status: ExpansionStatus,
    ) -> ExpansionStatus:
        self.status = status
        return self.status

    def can_enter(
        self, *, player_id: str, zone_id: str,
        completed_zone_ids: t.Iterable[str] = (),
        player_level: int = 1,
    ) -> EntryCheckResult:
        if self.status == ExpansionStatus.PRE_RELEASE:
            return EntryCheckResult(
                False, zone_id=zone_id,
                reason="expansion not yet released",
            )
        if self.status == ExpansionStatus.SUNSET:
            return EntryCheckResult(
                False, zone_id=zone_id,
                reason="expansion sunset",
            )
        z = self._zones.get(zone_id)
        if z is None:
            return EntryCheckResult(
                False, zone_id=zone_id,
                reason="no such zone",
            )
        if not self.has_ownership(player_id=player_id):
            return EntryCheckResult(
                False, zone_id=zone_id,
                reason="expansion not owned",
            )
        if player_level < z.level_gate:
            return EntryCheckResult(
                False, zone_id=zone_id,
                reason=f"level < {z.level_gate}",
            )
        completed = set(completed_zone_ids)
        for p in z.prereq_zone_ids:
            if p not in completed:
                return EntryCheckResult(
                    False, zone_id=zone_id,
                    reason=f"missing prereq {p}",
                )
        return EntryCheckResult(
            accepted=True, zone_id=zone_id,
        )

    def starter_zones(
        self, kind: ZoneKind,
    ) -> tuple[ShadowlandZone, ...]:
        return tuple(
            z for z in self._zones.values()
            if z.kind == kind and z.is_starter
        )

    def total_zones(self) -> int:
        return len(self._zones)

    def total_owners(self) -> int:
        return len(self._ownership)


__all__ = [
    "ZoneKind", "ExpansionStatus",
    "ShadowlandZone", "EntryCheckResult",
    "ShadowlandsExpansion",
]
