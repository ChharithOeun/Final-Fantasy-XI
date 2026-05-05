"""Surface ship combat — broadside cannons + boarding hooks.

Surface ships (the ones from sea_pirate_factions and the
airship_ferry — yes, sea ferries too) can fight each other
with broadsides + grappling hooks. We model SHIP CLASS,
HULL HP, and ARMAMENT.

Ship classes:
  SLOOP        - small, fast, light cannons (4 guns/side)
  FRIGATE      - medium, balanced (8 guns/side)
  GALLEON      - heavy, slow, big broadsides (12 guns/side)
  IRONCLAD     - rare; 4 guns + 50% damage_resist

Combat actions:
  BROADSIDE     - fire one full row of cannons; depends on
                  position (port or starboard). Damage scales
                  with gun count + crew_skill.
  GRAPPLE       - fire a hook to lock the ship in place;
                  blocks evasion next round, enables
                  boarding_party_pvp.
  EVADE         - +30% chance to dodge next broadside;
                  consumes the round.

Position rule: a broadside only hits if attacker's facing
is broadside_to_target (we model this as a boolean flag
the caller passes).

Public surface
--------------
    ShipClass enum
    Action enum
    BroadsideResult / GrappleResult dataclasses
    SurfaceShipCombat
        .ship_profile(class) -> ShipProfile
        .resolve_broadside(attacker_class, attacker_crew_skill,
                           target_class, target_evading,
                           broadside_lined_up, target_hp)
        .resolve_grapple(attacker_class, target_class,
                         attacker_crew_skill, target_crew_skill)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShipClass(str, enum.Enum):
    SLOOP = "sloop"
    FRIGATE = "frigate"
    GALLEON = "galleon"
    IRONCLAD = "ironclad"


class Action(str, enum.Enum):
    BROADSIDE = "broadside"
    GRAPPLE = "grapple"
    EVADE = "evade"


@dataclasses.dataclass(frozen=True)
class ShipProfile:
    ship_class: ShipClass
    hp_max: int
    guns_per_side: int
    base_speed: float
    damage_resist_pct: int


_PROFILES: dict[ShipClass, ShipProfile] = {
    ShipClass.SLOOP: ShipProfile(
        ship_class=ShipClass.SLOOP,
        hp_max=1_500, guns_per_side=4,
        base_speed=1.5, damage_resist_pct=0,
    ),
    ShipClass.FRIGATE: ShipProfile(
        ship_class=ShipClass.FRIGATE,
        hp_max=3_000, guns_per_side=8,
        base_speed=1.0, damage_resist_pct=10,
    ),
    ShipClass.GALLEON: ShipProfile(
        ship_class=ShipClass.GALLEON,
        hp_max=5_500, guns_per_side=12,
        base_speed=0.7, damage_resist_pct=20,
    ),
    ShipClass.IRONCLAD: ShipProfile(
        ship_class=ShipClass.IRONCLAD,
        hp_max=4_000, guns_per_side=4,
        base_speed=0.6, damage_resist_pct=50,
    ),
}

_DAMAGE_PER_GUN = 60
_EVADE_DAMAGE_REDUCTION_PCT = 30


@dataclasses.dataclass(frozen=True)
class BroadsideResult:
    accepted: bool
    damage_dealt: int = 0
    target_hp_after: int = 0
    target_sunk: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class GrappleResult:
    accepted: bool
    locked: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SurfaceShipCombat:
    @staticmethod
    def ship_profile(*, ship_class: ShipClass) -> t.Optional[ShipProfile]:
        return _PROFILES.get(ship_class)

    def resolve_broadside(
        self, *, attacker_class: ShipClass,
        attacker_crew_skill: int,
        target_class: ShipClass,
        target_evading: bool,
        broadside_lined_up: bool,
        target_hp: int,
    ) -> BroadsideResult:
        atk = _PROFILES.get(attacker_class)
        tgt = _PROFILES.get(target_class)
        if atk is None or tgt is None:
            return BroadsideResult(False, reason="unknown class")
        if attacker_crew_skill < 0:
            return BroadsideResult(False, reason="bad skill")
        if target_hp <= 0:
            return BroadsideResult(False, reason="target sunk")
        if not broadside_lined_up:
            return BroadsideResult(
                False, reason="broadside not aligned",
            )
        # base damage from gun count
        base = atk.guns_per_side * _DAMAGE_PER_GUN
        # crew skill: +1% per skill point, max +50%
        skill_mod = 1.0 + min(attacker_crew_skill, 50) / 100.0
        damage = int(base * skill_mod)
        # target damage resist
        damage = int(damage * (100 - tgt.damage_resist_pct) / 100)
        # evasion
        if target_evading:
            damage = int(
                damage * (100 - _EVADE_DAMAGE_REDUCTION_PCT) / 100,
            )
        new_hp = max(0, target_hp - damage)
        return BroadsideResult(
            accepted=True,
            damage_dealt=damage,
            target_hp_after=new_hp,
            target_sunk=(new_hp == 0),
        )

    def resolve_grapple(
        self, *, attacker_class: ShipClass,
        target_class: ShipClass,
        attacker_crew_skill: int,
        target_crew_skill: int,
    ) -> GrappleResult:
        atk = _PROFILES.get(attacker_class)
        tgt = _PROFILES.get(target_class)
        if atk is None or tgt is None:
            return GrappleResult(False, reason="unknown class")
        if (
            attacker_crew_skill < 0
            or target_crew_skill < 0
        ):
            return GrappleResult(False, reason="bad skill")
        # grapple succeeds when attacker_skill > target_skill
        # AND target is not faster by more than 1.0
        speed_gap = tgt.base_speed - atk.base_speed
        if speed_gap >= 1.0:
            return GrappleResult(
                False, reason="target too fast",
            )
        if attacker_crew_skill <= target_crew_skill:
            return GrappleResult(
                False, locked=False, reason="failed roll",
            )
        return GrappleResult(accepted=True, locked=True)


__all__ = [
    "ShipClass", "Action", "ShipProfile",
    "BroadsideResult", "GrappleResult",
    "SurfaceShipCombat",
]
