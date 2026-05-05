"""Sub vs sub combat — torpedo / depth-charge / ramming.

Submersibles from submersible_craft can fight each other.
Three weapon kinds with different trade-offs:
  TORPEDO       - long-range, mid-damage, fixed cooldown,
                  evasion check vs sub speed_bonus
  DEPTH_CHARGE  - short-range explosive; AOE 3 subs at once;
                  best vs slow targets
  RAMMING       - melee; massive damage but DAMAGES THE
                  RAMMER too (60% of dealt)

Targeting rules:
  * Both subs must be in the same zone
  * Both must be at "engaged depth" — the deeper sub takes
    a 25% damage penalty trying to hit the shallower one
    (you can't shoot up easily)
  * Hull breach (current_hp <= 0) is the same dump-the-crew
    semantics from submersible_craft

Public surface
--------------
    WeaponKind enum
    EngagementResult dataclass
    SubVsSubCombat
        .can_engage(attacker_id, defender_id, attacker_zone,
                    defender_zone)
        .resolve_attack(attacker_id, defender_id, weapon,
                        attacker_speed_bonus,
                        defender_speed_bonus,
                        attacker_depth, defender_depth,
                        attacker_hp, defender_hp)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WeaponKind(str, enum.Enum):
    TORPEDO = "torpedo"
    DEPTH_CHARGE = "depth_charge"
    RAMMING = "ramming"


@dataclasses.dataclass(frozen=True)
class WeaponProfile:
    weapon: WeaponKind
    base_damage: int
    is_aoe: bool
    self_damage_pct: int       # how much damage RAMMER takes
    long_range: bool


_PROFILES: dict[WeaponKind, WeaponProfile] = {
    WeaponKind.TORPEDO: WeaponProfile(
        weapon=WeaponKind.TORPEDO,
        base_damage=350,
        is_aoe=False,
        self_damage_pct=0,
        long_range=True,
    ),
    WeaponKind.DEPTH_CHARGE: WeaponProfile(
        weapon=WeaponKind.DEPTH_CHARGE,
        base_damage=250,
        is_aoe=True,
        self_damage_pct=0,
        long_range=False,
    ),
    WeaponKind.RAMMING: WeaponProfile(
        weapon=WeaponKind.RAMMING,
        base_damage=900,
        is_aoe=False,
        self_damage_pct=60,
        long_range=False,
    ),
}

# damage penalty when shooting a sub above you (positive = penalty)
_SHOOTING_UP_PENALTY_PCT = 25


@dataclasses.dataclass(frozen=True)
class EngagementResult:
    accepted: bool
    weapon: t.Optional[WeaponKind] = None
    damage_dealt: int = 0
    self_damage: int = 0
    attacker_hp_after: int = 0
    defender_hp_after: int = 0
    defender_breached: bool = False
    attacker_breached: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SubVsSubCombat:
    @staticmethod
    def can_engage(
        *, attacker_id: str, defender_id: str,
        attacker_zone: str, defender_zone: str,
    ) -> bool:
        if not attacker_id or not defender_id:
            return False
        if attacker_id == defender_id:
            return False
        if attacker_zone != defender_zone:
            return False
        return True

    def resolve_attack(
        self, *, attacker_id: str,
        defender_id: str,
        weapon: WeaponKind,
        attacker_speed_bonus: float,
        defender_speed_bonus: float,
        attacker_depth: int,
        defender_depth: int,
        attacker_hp: int,
        defender_hp: int,
    ) -> EngagementResult:
        if not attacker_id or not defender_id:
            return EngagementResult(False, reason="bad ids")
        if attacker_id == defender_id:
            return EngagementResult(False, reason="self target")
        prof = _PROFILES.get(weapon)
        if prof is None:
            return EngagementResult(False, reason="unknown weapon")
        if attacker_hp <= 0 or defender_hp <= 0:
            return EngagementResult(False, reason="dead sub")
        # evasion: torpedoes can be dodged
        if prof.weapon == WeaponKind.TORPEDO:
            # higher defender speed -> better dodge chance.
            # we don't roll; we just clip damage by relative speed.
            # if defender_speed > attacker_speed, defender takes
            # 50% damage; equal = 100%; lower = 100%.
            speed_ratio = (
                defender_speed_bonus / attacker_speed_bonus
                if attacker_speed_bonus > 0 else 1.0
            )
            damage_mod = 1.0 if speed_ratio <= 1.0 else 0.5
        else:
            damage_mod = 1.0
        # depth penalty: shooting at someone shallower gets a
        # penalty (current is "below" the target)
        if attacker_depth > defender_depth:
            damage_mod *= (100 - _SHOOTING_UP_PENALTY_PCT) / 100.0
        damage = int(prof.base_damage * damage_mod)
        # self damage for ramming
        self_dmg = (damage * prof.self_damage_pct) // 100
        new_def_hp = max(0, defender_hp - damage)
        new_att_hp = max(0, attacker_hp - self_dmg)
        return EngagementResult(
            accepted=True,
            weapon=weapon,
            damage_dealt=damage,
            self_damage=self_dmg,
            attacker_hp_after=new_att_hp,
            defender_hp_after=new_def_hp,
            defender_breached=(new_def_hp == 0),
            attacker_breached=(new_att_hp == 0),
        )

    @staticmethod
    def profile_for(*, weapon: WeaponKind) -> t.Optional[WeaponProfile]:
        return _PROFILES.get(weapon)


__all__ = [
    "WeaponKind", "WeaponProfile",
    "EngagementResult", "SubVsSubCombat",
]
