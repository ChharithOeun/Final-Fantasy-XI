"""Sahagin resistance cells — pocket bases all over the sea.

The Kingdom is small. The Resistance is everywhere.

Each cell is a hidden Sahagin base in territory the
kingdom has no real claim to — a gutted shipwreck refit,
a flooded sea cave, a coral grotto. Cells specialize:

    SMUGGLERS_DEN      - moves cargo for the Kingdom; kill
                         to disrupt sahagin economy
    ASSASSINS_ROOST    - launches ASSASSINATION raids; kill
                         to remove that raid type from
                         the zone for a week
    SCOUT_HIDE         - feeds intel to other cells; kill
                         to make raids in the area dumber
    SABOTEURS_CACHE    - launches SABOTAGE/DESECRATION;
                         kill to protect mermaid sites
    WAR_FORGE          - manufactures weapons; kill to lower
                         all sahagin damage in the zone

Each cell has hp_remaining; players (or mermaid Trusts)
can damage them. At 0 hp the cell is WIPED OUT — permanent.
The Kingdom may build new cells over time, but a wiped
cell at a specific location stays gone.

Public surface
--------------
    CellKind enum
    CellStatus enum
    ResistanceCell dataclass
    SahaginResistanceCells
        .establish(cell_id, kind, zone_id, band, hp_max,
                   bounty_on_kill)
        .damage(cell_id, amount, attacker_id, now_seconds)
            -> WipeResult
        .status_of(cell_id) -> CellStatus
        .cells_in(zone_id) -> tuple[ResistanceCell, ...]
        .active_kinds_in(zone_id) -> frozenset[CellKind]
        .wiped_count() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CellKind(str, enum.Enum):
    SMUGGLERS_DEN = "smugglers_den"
    ASSASSINS_ROOST = "assassins_roost"
    SCOUT_HIDE = "scout_hide"
    SABOTEURS_CACHE = "saboteurs_cache"
    WAR_FORGE = "war_forge"


class CellStatus(str, enum.Enum):
    ACTIVE = "active"
    DAMAGED = "damaged"      # < 50% hp
    WIPED = "wiped"          # 0 hp; permanent


# threshold for DAMAGED status (fraction of hp_max)
DAMAGED_HP_THRESHOLD = 0.5


@dataclasses.dataclass
class ResistanceCell:
    cell_id: str
    kind: CellKind
    zone_id: str
    band: int
    hp_max: int
    hp_remaining: int
    bounty_on_kill: int
    status: CellStatus = CellStatus.ACTIVE
    wiped_at: t.Optional[int] = None
    last_attacker: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class WipeResult:
    accepted: bool
    cell_wiped: bool = False
    bounty_paid: int = 0
    hp_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SahaginResistanceCells:
    _cells: dict[str, ResistanceCell] = dataclasses.field(default_factory=dict)

    def establish(
        self, *, cell_id: str,
        kind: CellKind,
        zone_id: str, band: int,
        hp_max: int,
        bounty_on_kill: int,
    ) -> bool:
        if not cell_id or cell_id in self._cells:
            return False
        if not zone_id or hp_max <= 0 or bounty_on_kill < 0:
            return False
        self._cells[cell_id] = ResistanceCell(
            cell_id=cell_id, kind=kind,
            zone_id=zone_id, band=band,
            hp_max=hp_max, hp_remaining=hp_max,
            bounty_on_kill=bounty_on_kill,
        )
        return True

    def damage(
        self, *, cell_id: str,
        amount: int,
        attacker_id: str,
        now_seconds: int,
    ) -> WipeResult:
        c = self._cells.get(cell_id)
        if c is None:
            return WipeResult(False, reason="unknown cell")
        if c.status == CellStatus.WIPED:
            return WipeResult(
                False, reason="already wiped",
                hp_remaining=0,
            )
        if amount <= 0:
            return WipeResult(False, reason="bad damage")
        c.hp_remaining = max(0, c.hp_remaining - amount)
        c.last_attacker = attacker_id
        if c.hp_remaining == 0:
            c.status = CellStatus.WIPED
            c.wiped_at = now_seconds
            return WipeResult(
                accepted=True, cell_wiped=True,
                bounty_paid=c.bounty_on_kill,
                hp_remaining=0,
            )
        if c.hp_remaining < int(c.hp_max * DAMAGED_HP_THRESHOLD):
            c.status = CellStatus.DAMAGED
        return WipeResult(
            accepted=True, cell_wiped=False,
            hp_remaining=c.hp_remaining,
        )

    def status_of(self, *, cell_id: str) -> t.Optional[CellStatus]:
        c = self._cells.get(cell_id)
        return c.status if c else None

    def cells_in(
        self, *, zone_id: str,
    ) -> tuple[ResistanceCell, ...]:
        return tuple(
            c for c in self._cells.values()
            if c.zone_id == zone_id
        )

    def active_kinds_in(
        self, *, zone_id: str,
    ) -> frozenset[CellKind]:
        return frozenset(
            c.kind for c in self._cells.values()
            if c.zone_id == zone_id
            and c.status != CellStatus.WIPED
        )

    def wiped_count(self) -> int:
        return sum(
            1 for c in self._cells.values()
            if c.status == CellStatus.WIPED
        )


__all__ = [
    "CellKind", "CellStatus", "ResistanceCell",
    "WipeResult", "SahaginResistanceCells",
    "DAMAGED_HP_THRESHOLD",
]
