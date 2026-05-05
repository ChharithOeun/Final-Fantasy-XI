"""Submersible dock — sub fuel/repair/storage between dives.

Subs from submersible_craft don't auto-restore between
expeditions. Each port has a DOCK that:
  * STORES idle subs across log-out
  * REPAIRS hull damage at a per-port gil rate
  * REFUELS fuel cells (subs run a cell over distance — we
    track cells abstractly as a fuel pool)
  * RESPOOLS the sub's CREW manifest from the player's
    party_system roster

Each dock has a class_compatibility roster — the smallest
fishing port can't dock an ABYSSAL_RIG. CORSAIR_SUB and
ABYSSAL_RIG only dock at deep-water ports.

Per-port pricing tiers:
  hull_repair_gil_per_hp - varies by port
  fuel_gil_per_cell      - varies by port

Public surface
--------------
    DockProfile dataclass
    DockedSub dataclass
    SubmersibleDock
        .register_port(port_id, allowed_classes,
                       repair_rate, fuel_rate)
        .stow(sub_id, port_id, current_hp, hp_max,
              fuel_remaining)
        .retrieve(sub_id, port_id)
        .repair(sub_id, port_id, gil_paid) -> RepairResult
        .refuel(sub_id, port_id, gil_paid) -> RefuelResult
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.submersible_craft import SubClass


@dataclasses.dataclass(frozen=True)
class DockProfile:
    port_id: str
    allowed_classes: tuple[SubClass, ...]
    repair_rate_gil_per_hp: int
    fuel_rate_gil_per_cell: int


@dataclasses.dataclass
class DockedSub:
    sub_id: str
    sub_class: SubClass
    port_id: str
    current_hp: int
    hp_max: int
    fuel_remaining: int


@dataclasses.dataclass(frozen=True)
class StowResult:
    accepted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class RepairResult:
    accepted: bool
    hp_restored: int = 0
    new_hp: int = 0
    gil_consumed: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class RefuelResult:
    accepted: bool
    cells_added: int = 0
    new_fuel: int = 0
    gil_consumed: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SubmersibleDock:
    _ports: dict[str, DockProfile] = dataclasses.field(default_factory=dict)
    _stowed: dict[str, DockedSub] = dataclasses.field(default_factory=dict)

    def register_port(
        self, *, port_id: str,
        allowed_classes: tuple[SubClass, ...],
        repair_rate_gil_per_hp: int,
        fuel_rate_gil_per_cell: int,
    ) -> bool:
        if not port_id or port_id in self._ports:
            return False
        if not allowed_classes:
            return False
        if (
            repair_rate_gil_per_hp <= 0
            or fuel_rate_gil_per_cell <= 0
        ):
            return False
        self._ports[port_id] = DockProfile(
            port_id=port_id,
            allowed_classes=tuple(allowed_classes),
            repair_rate_gil_per_hp=repair_rate_gil_per_hp,
            fuel_rate_gil_per_cell=fuel_rate_gil_per_cell,
        )
        return True

    def stow(
        self, *, sub_id: str,
        sub_class: SubClass,
        port_id: str,
        current_hp: int,
        hp_max: int,
        fuel_remaining: int,
    ) -> StowResult:
        port = self._ports.get(port_id)
        if port is None:
            return StowResult(False, reason="unknown port")
        if sub_class not in port.allowed_classes:
            return StowResult(
                False, reason="port does not service this class",
            )
        if not sub_id or sub_id in self._stowed:
            return StowResult(False, reason="already stowed")
        if current_hp < 0 or hp_max <= 0 or fuel_remaining < 0:
            return StowResult(False, reason="bad metrics")
        self._stowed[sub_id] = DockedSub(
            sub_id=sub_id,
            sub_class=sub_class,
            port_id=port_id,
            current_hp=min(current_hp, hp_max),
            hp_max=hp_max,
            fuel_remaining=fuel_remaining,
        )
        return StowResult(True)

    def retrieve(
        self, *, sub_id: str, port_id: str,
    ) -> t.Optional[DockedSub]:
        sub = self._stowed.get(sub_id)
        if sub is None or sub.port_id != port_id:
            return None
        del self._stowed[sub_id]
        return sub

    def repair(
        self, *, sub_id: str,
        port_id: str,
        gil_paid: int,
    ) -> RepairResult:
        sub = self._stowed.get(sub_id)
        if sub is None or sub.port_id != port_id:
            return RepairResult(False, reason="not stowed here")
        if gil_paid <= 0:
            return RepairResult(False, reason="bad gil")
        port = self._ports[port_id]
        rate = port.repair_rate_gil_per_hp
        affordable_hp = gil_paid // rate
        needed = sub.hp_max - sub.current_hp
        repair_hp = min(affordable_hp, needed)
        if repair_hp <= 0:
            return RepairResult(
                accepted=True,
                hp_restored=0,
                new_hp=sub.current_hp,
                gil_consumed=0,
                reason="already at max",
            )
        sub.current_hp += repair_hp
        return RepairResult(
            accepted=True,
            hp_restored=repair_hp,
            new_hp=sub.current_hp,
            gil_consumed=repair_hp * rate,
        )

    def refuel(
        self, *, sub_id: str,
        port_id: str,
        gil_paid: int,
    ) -> RefuelResult:
        sub = self._stowed.get(sub_id)
        if sub is None or sub.port_id != port_id:
            return RefuelResult(False, reason="not stowed here")
        if gil_paid <= 0:
            return RefuelResult(False, reason="bad gil")
        port = self._ports[port_id]
        cells = gil_paid // port.fuel_rate_gil_per_cell
        if cells <= 0:
            return RefuelResult(
                False, reason="not enough gil for one cell",
            )
        sub.fuel_remaining += cells
        return RefuelResult(
            accepted=True,
            cells_added=cells,
            new_fuel=sub.fuel_remaining,
            gil_consumed=cells * port.fuel_rate_gil_per_cell,
        )

    def status(self, *, sub_id: str) -> t.Optional[DockedSub]:
        return self._stowed.get(sub_id)


__all__ = [
    "DockProfile", "DockedSub",
    "StowResult", "RepairResult", "RefuelResult",
    "SubmersibleDock",
]
