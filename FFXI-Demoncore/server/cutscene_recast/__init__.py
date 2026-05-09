"""Cutscene recast — keep cutscene NPCs in their right faction.

Cutscenes that featured an NPC in their original
faction need to reflect the NPC's CURRENT allegiance
when re-played. If a cutscene shows Volker in Bastok
guard armor delivering a Bastok-loyalist line, but
Volker has since defected to Windurst, the cutscene
needs to be FLAGGED as STALE and the caller can either
re-render it (with the recast variant) or substitute
a text overlay/prefix explaining the time-shift.

Each cutscene declares ROLES (similar to quest_anchor)
and the system walks the bindings against the NPCs'
current factions to detect mismatches.

Resolution mode per cutscene:
    LIVE_RECAST     re-render with current faction
                    (assets must exist in
                    recast_pool)
    HISTORICAL_LOCK pretend it's a flashback; play
                    as-is but add a "long ago"
                    overlay
    SKIP            don't play it at all anymore (the
                    casting is just too broken)

Public surface
--------------
    Resolution enum
    StaleReason enum (per-role mismatch reason)
    CutsceneRole dataclass (frozen)
    Cutscene dataclass (frozen)
    StaleReport dataclass (frozen)
    CutsceneRecastSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Resolution(str, enum.Enum):
    LIVE_RECAST = "live_recast"
    HISTORICAL_LOCK = "historical_lock"
    SKIP = "skip"


class StaleReason(str, enum.Enum):
    NPC_DEFECTED = "npc_defected"
    NPC_DECEASED = "npc_deceased"
    NPC_RETIRED = "npc_retired"
    NPC_MISSING = "npc_missing"


@dataclasses.dataclass(frozen=True)
class CutsceneRole:
    cutscene_id: str
    role: str
    npc_id: str
    expected_faction: str


@dataclasses.dataclass(frozen=True)
class Cutscene:
    cutscene_id: str
    title: str
    resolution: Resolution
    roles: tuple[CutsceneRole, ...]
    has_recast_assets: bool


@dataclasses.dataclass(frozen=True)
class StaleReport:
    cutscene_id: str
    role: str
    npc_id: str
    expected_faction: str
    current_faction: str
    reason: StaleReason


@dataclasses.dataclass
class CutsceneRecastSystem:
    _cutscenes: dict[str, Cutscene] = (
        dataclasses.field(default_factory=dict)
    )

    def register(
        self, *, cutscene_id: str, title: str,
        resolution: Resolution,
        has_recast_assets: bool = False,
    ) -> bool:
        if not cutscene_id or not title:
            return False
        if cutscene_id in self._cutscenes:
            return False
        self._cutscenes[cutscene_id] = Cutscene(
            cutscene_id=cutscene_id, title=title,
            resolution=resolution, roles=(),
            has_recast_assets=has_recast_assets,
        )
        return True

    def add_role(
        self, *, cutscene_id: str, role: str,
        npc_id: str, expected_faction: str,
    ) -> bool:
        if cutscene_id not in self._cutscenes:
            return False
        if not role or not npc_id:
            return False
        if not expected_faction:
            return False
        c = self._cutscenes[cutscene_id]
        # Replace existing same-role binding
        new_roles = tuple(
            r for r in c.roles if r.role != role
        ) + (CutsceneRole(
            cutscene_id=cutscene_id, role=role,
            npc_id=npc_id,
            expected_faction=expected_faction,
        ),)
        self._cutscenes[cutscene_id] = (
            dataclasses.replace(c, roles=new_roles)
        )
        return True

    def set_resolution(
        self, *, cutscene_id: str,
        resolution: Resolution,
    ) -> bool:
        if cutscene_id not in self._cutscenes:
            return False
        c = self._cutscenes[cutscene_id]
        self._cutscenes[cutscene_id] = (
            dataclasses.replace(
                c, resolution=resolution,
            )
        )
        return True

    def stale_roles(
        self, *, cutscene_id: str,
        npc_factions: t.Mapping[str, str],
        npc_statuses: t.Mapping[str, str] = (
            None  # type: ignore
        ),
    ) -> list[StaleReport]:
        if cutscene_id not in self._cutscenes:
            return []
        statuses = npc_statuses or {}
        c = self._cutscenes[cutscene_id]
        out: list[StaleReport] = []
        for r in c.roles:
            cur_status = statuses.get(r.npc_id, "")
            cur_faction = npc_factions.get(r.npc_id)
            if cur_status == "deceased":
                out.append(StaleReport(
                    cutscene_id=cutscene_id,
                    role=r.role, npc_id=r.npc_id,
                    expected_faction=(
                        r.expected_faction
                    ),
                    current_faction=(
                        cur_faction or ""
                    ),
                    reason=StaleReason.NPC_DECEASED,
                ))
                continue
            if cur_status == "retired":
                out.append(StaleReport(
                    cutscene_id=cutscene_id,
                    role=r.role, npc_id=r.npc_id,
                    expected_faction=(
                        r.expected_faction
                    ),
                    current_faction=(
                        cur_faction or ""
                    ),
                    reason=StaleReason.NPC_RETIRED,
                ))
                continue
            if cur_faction is None:
                out.append(StaleReport(
                    cutscene_id=cutscene_id,
                    role=r.role, npc_id=r.npc_id,
                    expected_faction=(
                        r.expected_faction
                    ),
                    current_faction="",
                    reason=StaleReason.NPC_MISSING,
                ))
                continue
            if cur_faction != r.expected_faction:
                out.append(StaleReport(
                    cutscene_id=cutscene_id,
                    role=r.role, npc_id=r.npc_id,
                    expected_faction=(
                        r.expected_faction
                    ),
                    current_faction=cur_faction,
                    reason=StaleReason.NPC_DEFECTED,
                ))
        return out

    def is_playable(
        self, *, cutscene_id: str,
        npc_factions: t.Mapping[str, str],
        npc_statuses: t.Mapping[str, str] = (
            None  # type: ignore
        ),
    ) -> bool:
        """A cutscene is playable if:
        - resolution=HISTORICAL_LOCK (always plays),
        - resolution=LIVE_RECAST and has_recast_assets,
        - resolution=SKIP -> never playable,
        - if no stale_roles, always playable.
        """
        if cutscene_id not in self._cutscenes:
            return False
        c = self._cutscenes[cutscene_id]
        if c.resolution == Resolution.SKIP:
            return False
        stale = self.stale_roles(
            cutscene_id=cutscene_id,
            npc_factions=npc_factions,
            npc_statuses=npc_statuses,
        )
        if not stale:
            return True
        if c.resolution == Resolution.HISTORICAL_LOCK:
            return True
        # LIVE_RECAST: only playable if we have the
        # assets to render the new casting.
        return c.has_recast_assets

    def cutscene(
        self, *, cutscene_id: str,
    ) -> t.Optional[Cutscene]:
        return self._cutscenes.get(cutscene_id)

    def all_cutscenes(self) -> list[Cutscene]:
        return list(self._cutscenes.values())


__all__ = [
    "Resolution", "StaleReason", "CutsceneRole",
    "Cutscene", "StaleReport",
    "CutsceneRecastSystem",
]
