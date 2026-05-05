"""Airship combat — dogfighting between dirigibles.

Three engagement modes mirror surface_ship_combat but the
geometry is different:

  CANNON_VOLLEY  — long range, lateral; damage scales with
                   gun_count and crew_skill. Same band only
                   (cannons can't elevate enough to cross a
                   band on a moving ship).
  RAM            — closes to zero range; massive damage but
                   60% self-damage (like sub ramming).
  GRAPPLE_BOARD  — hooks to the enemy ship; ends combat
                   movement and starts a boarding party.
                   Requires speed-gap < 1.0 and same-band.

Climb/dive are free actions outside combat but cost a turn
in combat (you can dodge a cannon volley by changing band
mid-action; the volley misses).

Public surface
--------------
    AirshipClass enum (SKIFF / GUNBOAT / DREADNOUGHT)
    AirshipProfile dataclass (frozen)
    EngageResult dataclass (frozen)
    AirshipCombat
        .register(ship_id, ship_class, hp, band, speed,
                  gun_count, crew_skill)
        .change_band(ship_id, new_band) -> bool
        .cannon_volley(attacker, target) -> EngageResult
        .ram(attacker, target) -> EngageResult
        .grapple(attacker, target) -> EngageResult
        .hp_of(ship_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AirshipClass(str, enum.Enum):
    SKIFF = "skiff"
    GUNBOAT = "gunboat"
    DREADNOUGHT = "dreadnought"


CLASS_HP_MAX: dict[AirshipClass, int] = {
    AirshipClass.SKIFF: 200,
    AirshipClass.GUNBOAT: 600,
    AirshipClass.DREADNOUGHT: 1500,
}
CLASS_DAMAGE_RESIST_PCT: dict[AirshipClass, int] = {
    AirshipClass.SKIFF: 0,
    AirshipClass.GUNBOAT: 15,
    AirshipClass.DREADNOUGHT: 30,
}

# base damage per cannon volley = guns * BASE
VOLLEY_BASE = 8
# crew skill bonus: +1% per skill point, capped
VOLLEY_SKILL_CAP_PCT = 50
# ram base damage scales with attacker class
RAM_BASE: dict[AirshipClass, int] = {
    AirshipClass.SKIFF: 80,
    AirshipClass.GUNBOAT: 200,
    AirshipClass.DREADNOUGHT: 500,
}
RAM_SELF_DAMAGE_PCT = 60
GRAPPLE_SPEED_GAP_MAX = 1.0


@dataclasses.dataclass
class _Ship:
    ship_id: str
    ship_class: AirshipClass
    hp: int
    band: int
    speed: float
    gun_count: int
    crew_skill: int


@dataclasses.dataclass(frozen=True)
class EngageResult:
    accepted: bool
    damage_dealt: int = 0
    self_damage: int = 0
    target_hp_after: int = 0
    attacker_hp_after: int = 0
    grappled: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class AirshipCombat:
    _ships: dict[str, _Ship] = dataclasses.field(default_factory=dict)
    _grapples: set[tuple[str, str]] = dataclasses.field(default_factory=set)

    def register(
        self, *, ship_id: str,
        ship_class: AirshipClass,
        hp: t.Optional[int] = None,
        band: int = 2, speed: float = 1.0,
        gun_count: int = 4, crew_skill: int = 0,
    ) -> bool:
        if not ship_id or ship_id in self._ships:
            return False
        actual_hp = hp if hp is not None else CLASS_HP_MAX[ship_class]
        self._ships[ship_id] = _Ship(
            ship_id=ship_id, ship_class=ship_class,
            hp=actual_hp, band=band, speed=speed,
            gun_count=max(0, gun_count),
            crew_skill=max(0, crew_skill),
        )
        return True

    def change_band(
        self, *, ship_id: str, new_band: int,
    ) -> bool:
        s = self._ships.get(ship_id)
        if s is None:
            return False
        s.band = new_band
        return True

    def cannon_volley(
        self, *, attacker_id: str, target_id: str,
    ) -> EngageResult:
        a = self._ships.get(attacker_id)
        t_ship = self._ships.get(target_id)
        if a is None or t_ship is None:
            return EngageResult(False, reason="unknown ship")
        if a.band != t_ship.band:
            return EngageResult(False, reason="band mismatch")
        if a.gun_count <= 0:
            return EngageResult(False, reason="no guns")
        skill_bonus = min(a.crew_skill, VOLLEY_SKILL_CAP_PCT)
        raw = a.gun_count * VOLLEY_BASE
        scaled = raw * (100 + skill_bonus) // 100
        resist = CLASS_DAMAGE_RESIST_PCT[t_ship.ship_class]
        dmg = scaled * (100 - resist) // 100
        t_ship.hp = max(0, t_ship.hp - dmg)
        return EngageResult(
            accepted=True,
            damage_dealt=dmg,
            target_hp_after=t_ship.hp,
            attacker_hp_after=a.hp,
        )

    def ram(
        self, *, attacker_id: str, target_id: str,
    ) -> EngageResult:
        a = self._ships.get(attacker_id)
        t_ship = self._ships.get(target_id)
        if a is None or t_ship is None:
            return EngageResult(False, reason="unknown ship")
        if a.band != t_ship.band:
            return EngageResult(False, reason="band mismatch")
        base = RAM_BASE[a.ship_class]
        resist = CLASS_DAMAGE_RESIST_PCT[t_ship.ship_class]
        dmg = base * (100 - resist) // 100
        t_ship.hp = max(0, t_ship.hp - dmg)
        # attacker also takes hits
        self_dmg = base * RAM_SELF_DAMAGE_PCT // 100
        a.hp = max(0, a.hp - self_dmg)
        return EngageResult(
            accepted=True,
            damage_dealt=dmg,
            self_damage=self_dmg,
            target_hp_after=t_ship.hp,
            attacker_hp_after=a.hp,
        )

    def grapple(
        self, *, attacker_id: str, target_id: str,
    ) -> EngageResult:
        a = self._ships.get(attacker_id)
        t_ship = self._ships.get(target_id)
        if a is None or t_ship is None:
            return EngageResult(False, reason="unknown ship")
        if a.band != t_ship.band:
            return EngageResult(False, reason="band mismatch")
        speed_gap = abs(a.speed - t_ship.speed)
        if speed_gap >= GRAPPLE_SPEED_GAP_MAX:
            return EngageResult(False, reason="speed gap too wide")
        self._grapples.add((attacker_id, target_id))
        return EngageResult(
            accepted=True, grappled=True,
            target_hp_after=t_ship.hp,
            attacker_hp_after=a.hp,
        )

    def hp_of(self, *, ship_id: str) -> int:
        s = self._ships.get(ship_id)
        return s.hp if s else 0


__all__ = [
    "AirshipClass", "EngageResult", "AirshipCombat",
    "CLASS_HP_MAX", "CLASS_DAMAGE_RESIST_PCT",
    "VOLLEY_BASE", "VOLLEY_SKILL_CAP_PCT",
    "RAM_BASE", "RAM_SELF_DAMAGE_PCT",
    "GRAPPLE_SPEED_GAP_MAX",
]
