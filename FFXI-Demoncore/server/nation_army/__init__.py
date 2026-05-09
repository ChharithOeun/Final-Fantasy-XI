"""Nation army — standing military force composition.

Each nation maintains a STANDING ARMY: a registry of
combat units (regiments, battalions, special forces),
each with a commander, troop strength, and READINESS
state. Units can be DEPLOYED to zones for siege/
campaign duty (the actual combat is delegated to
siege_system); deployment depletes readiness, recall +
rest restore it.

Unit kinds:
    INFANTRY            line troops
    HEAVY_INFANTRY      shock troops, slow
    LIGHT_CAVALRY       skirmishers, scouting
    HEAVY_CAVALRY       shock cavalry
    ARTILLERY           ballistae, catapults
    ENGINEERS           siege construction
    MEDICS              field hospital
    SPECIAL_FORCES      elite raiders
    AUXILIARY           levied militia (cheap, weak)

Readiness:
    READY               at full strength, can deploy
    DEPLOYED            in the field
    REGROUPING          back at base, recovering
    UNDERSTRENGTH       below 50% troops, needs
                        reinforcement
    DISBANDED           unit dissolved

Public surface
--------------
    UnitKind enum
    Readiness enum
    Unit dataclass (frozen)
    NationArmySystem
        .raise_unit(nation_id, unit_id, kind,
                    commander_id, strength,
                    raised_day) -> bool
        .deploy(unit_id, zone_id, now_day) -> bool
        .recall(unit_id, now_day) -> bool
        .take_casualties(unit_id, lost) -> bool
        .reinforce(unit_id, troops) -> bool
        .promote_commander(unit_id,
                           new_commander) -> bool
        .disband(unit_id, now_day) -> bool
        .tick(now_day) ->
                          list[(unit_id, Readiness)]
        .unit(unit_id) -> Optional[Unit]
        .units_for(nation_id) -> list[Unit]
        .deployed_in(zone_id) -> list[Unit]
        .total_strength(nation_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_REGROUP_DAYS = 5
_UNDERSTRENGTH_PCT = 50


class UnitKind(str, enum.Enum):
    INFANTRY = "infantry"
    HEAVY_INFANTRY = "heavy_infantry"
    LIGHT_CAVALRY = "light_cavalry"
    HEAVY_CAVALRY = "heavy_cavalry"
    ARTILLERY = "artillery"
    ENGINEERS = "engineers"
    MEDICS = "medics"
    SPECIAL_FORCES = "special_forces"
    AUXILIARY = "auxiliary"


class Readiness(str, enum.Enum):
    READY = "ready"
    DEPLOYED = "deployed"
    REGROUPING = "regrouping"
    UNDERSTRENGTH = "understrength"
    DISBANDED = "disbanded"


@dataclasses.dataclass(frozen=True)
class Unit:
    unit_id: str
    nation_id: str
    kind: UnitKind
    commander_id: str
    strength: int
    base_strength: int
    raised_day: int
    deployed_zone: str
    deployed_day: t.Optional[int]
    recalled_day: t.Optional[int]
    state: Readiness


@dataclasses.dataclass
class NationArmySystem:
    _units: dict[str, Unit] = dataclasses.field(
        default_factory=dict,
    )

    def raise_unit(
        self, *, nation_id: str, unit_id: str,
        kind: UnitKind, commander_id: str,
        strength: int, raised_day: int,
    ) -> bool:
        if not nation_id or not unit_id:
            return False
        if not commander_id:
            return False
        if strength <= 0 or raised_day < 0:
            return False
        if unit_id in self._units:
            return False
        self._units[unit_id] = Unit(
            unit_id=unit_id, nation_id=nation_id,
            kind=kind, commander_id=commander_id,
            strength=strength,
            base_strength=strength,
            raised_day=raised_day,
            deployed_zone="", deployed_day=None,
            recalled_day=None,
            state=Readiness.READY,
        )
        return True

    def _refresh_state(
        self, unit_id: str,
    ) -> None:
        u = self._units[unit_id]
        if u.state in (
            Readiness.DISBANDED, Readiness.DEPLOYED,
            Readiness.REGROUPING,
        ):
            return
        pct = u.strength * 100 // max(
            1, u.base_strength,
        )
        if pct < _UNDERSTRENGTH_PCT:
            self._units[unit_id] = (
                dataclasses.replace(
                    u, state=Readiness.UNDERSTRENGTH,
                )
            )
        else:
            self._units[unit_id] = (
                dataclasses.replace(
                    u, state=Readiness.READY,
                )
            )

    def deploy(
        self, *, unit_id: str, zone_id: str,
        now_day: int,
    ) -> bool:
        if unit_id not in self._units:
            return False
        if not zone_id:
            return False
        u = self._units[unit_id]
        if u.state != Readiness.READY:
            return False
        self._units[unit_id] = dataclasses.replace(
            u, deployed_zone=zone_id,
            deployed_day=now_day,
            state=Readiness.DEPLOYED,
        )
        return True

    def recall(
        self, *, unit_id: str, now_day: int,
    ) -> bool:
        if unit_id not in self._units:
            return False
        u = self._units[unit_id]
        if u.state != Readiness.DEPLOYED:
            return False
        self._units[unit_id] = dataclasses.replace(
            u, recalled_day=now_day,
            state=Readiness.REGROUPING,
        )
        return True

    def take_casualties(
        self, *, unit_id: str, lost: int,
    ) -> bool:
        if unit_id not in self._units:
            return False
        if lost <= 0:
            return False
        u = self._units[unit_id]
        if u.state == Readiness.DISBANDED:
            return False
        new_strength = max(0, u.strength - lost)
        self._units[unit_id] = dataclasses.replace(
            u, strength=new_strength,
        )
        # If wiped out, mark disbanded
        if new_strength == 0:
            self._units[unit_id] = (
                dataclasses.replace(
                    self._units[unit_id],
                    state=Readiness.DISBANDED,
                )
            )
        else:
            self._refresh_state(unit_id)
        return True

    def reinforce(
        self, *, unit_id: str, troops: int,
    ) -> bool:
        if unit_id not in self._units:
            return False
        if troops <= 0:
            return False
        u = self._units[unit_id]
        if u.state == Readiness.DISBANDED:
            return False
        new_strength = min(
            u.base_strength, u.strength + troops,
        )
        self._units[unit_id] = dataclasses.replace(
            u, strength=new_strength,
        )
        self._refresh_state(unit_id)
        return True

    def promote_commander(
        self, *, unit_id: str, new_commander: str,
    ) -> bool:
        if unit_id not in self._units:
            return False
        if not new_commander:
            return False
        u = self._units[unit_id]
        if u.state == Readiness.DISBANDED:
            return False
        self._units[unit_id] = dataclasses.replace(
            u, commander_id=new_commander,
        )
        return True

    def disband(
        self, *, unit_id: str, now_day: int,
    ) -> bool:
        if unit_id not in self._units:
            return False
        u = self._units[unit_id]
        if u.state == Readiness.DISBANDED:
            return False
        self._units[unit_id] = dataclasses.replace(
            u, state=Readiness.DISBANDED,
        )
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, Readiness]]:
        changes: list[tuple[str, Readiness]] = []
        for uid, u in list(self._units.items()):
            if u.state != Readiness.REGROUPING:
                continue
            if u.recalled_day is None:
                continue
            if (now_day - u.recalled_day
                    < _REGROUP_DAYS):
                continue
            # Done regrouping
            self._units[uid] = dataclasses.replace(
                u, deployed_zone="", deployed_day=None,
                recalled_day=None,
                state=Readiness.READY,
            )
            self._refresh_state(uid)
            changes.append((uid, self._units[uid].state))
        return changes

    def unit(
        self, *, unit_id: str,
    ) -> t.Optional[Unit]:
        return self._units.get(unit_id)

    def units_for(
        self, *, nation_id: str,
    ) -> list[Unit]:
        return [
            u for u in self._units.values()
            if u.nation_id == nation_id
        ]

    def deployed_in(
        self, *, zone_id: str,
    ) -> list[Unit]:
        return [
            u for u in self._units.values()
            if (u.state == Readiness.DEPLOYED
                and u.deployed_zone == zone_id)
        ]

    def total_strength(
        self, *, nation_id: str,
    ) -> int:
        return sum(
            u.strength
            for u in self._units.values()
            if (u.nation_id == nation_id
                and u.state != Readiness.DISBANDED)
        )


__all__ = [
    "UnitKind", "Readiness", "Unit",
    "NationArmySystem",
]
