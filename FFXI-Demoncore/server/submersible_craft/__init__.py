"""Submersible craft — craftable diving bells & subs.

Diving with just a body works fine to MID_DEPTH but past
that, players want HULLS. Submersibles are crafted craft
that protect divers from pressure and breath drain entirely
while inside, at the cost of mobility and a vulnerable hull.

Submersible classes:
  DIVING_BELL    - 1-person, depth cap 200, slow, cheap
  SCOUT_SUB      - 2-person, depth cap 350, medium speed
  CORSAIR_SUB    - 4-person, depth cap 500, well-armed
  ABYSSAL_RIG    - 6-person, depth cap 1000, slow, fragile
                   (the only craft that goes past the trench
                   floor, but pirates rip it apart easily)

Each sub has:
  hp_max         - hull HP. Mob attacks while submerged
                   damage the hull, not the occupants.
  crew_capacity  - max occupants
  depth_cap      - hard limit; sub refuses deeper
  speed_bonus    - swim speed multiplier vs body-diving

A SubmersibleSession tracks a deployed sub: occupants,
current_hp, current_depth_yalms. Damage events route through
take_damage; HP at 0 means HULL_BREACH and all occupants
are dumped at current depth, taking the underwater_swim
pressure ramp from there.

Public surface
--------------
    SubClass enum
    SubProfile dataclass
    SubmersibleSession dataclass
    SubmersibleCraft
        .deploy(sub_id, sub_class, occupants, now_seconds)
        .descend(sub_id, target_depth_yalms)
        .take_damage(sub_id, dmg) -> RouteResult
        .occupants(sub_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SubClass(str, enum.Enum):
    DIVING_BELL = "diving_bell"
    SCOUT_SUB = "scout_sub"
    CORSAIR_SUB = "corsair_sub"
    ABYSSAL_RIG = "abyssal_rig"


@dataclasses.dataclass(frozen=True)
class SubProfile:
    sub_class: SubClass
    hp_max: int
    crew_capacity: int
    depth_cap_yalms: int
    speed_bonus: float


_PROFILES: dict[SubClass, SubProfile] = {
    SubClass.DIVING_BELL: SubProfile(
        sub_class=SubClass.DIVING_BELL,
        hp_max=400,
        crew_capacity=1,
        depth_cap_yalms=200,
        speed_bonus=0.7,
    ),
    SubClass.SCOUT_SUB: SubProfile(
        sub_class=SubClass.SCOUT_SUB,
        hp_max=900,
        crew_capacity=2,
        depth_cap_yalms=350,
        speed_bonus=1.1,
    ),
    SubClass.CORSAIR_SUB: SubProfile(
        sub_class=SubClass.CORSAIR_SUB,
        hp_max=2_000,
        crew_capacity=4,
        depth_cap_yalms=500,
        speed_bonus=1.0,
    ),
    SubClass.ABYSSAL_RIG: SubProfile(
        sub_class=SubClass.ABYSSAL_RIG,
        hp_max=2_800,
        crew_capacity=6,
        depth_cap_yalms=1_000,
        speed_bonus=0.5,
    ),
}


@dataclasses.dataclass
class SubmersibleSession:
    sub_id: str
    sub_class: SubClass
    occupants: tuple[str, ...]
    current_hp: int
    current_depth_yalms: int = 0
    deployed_at: int = 0
    breached: bool = False


@dataclasses.dataclass(frozen=True)
class DescendResult:
    accepted: bool
    new_depth: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class DamageResult:
    accepted: bool
    hp_remaining: int = 0
    breached: bool = False
    dumped_at_depth: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SubmersibleCraft:
    _sessions: dict[str, SubmersibleSession] = dataclasses.field(
        default_factory=dict,
    )

    @staticmethod
    def profile_for(*, sub_class: SubClass) -> t.Optional[SubProfile]:
        return _PROFILES.get(sub_class)

    def deploy(
        self, *, sub_id: str,
        sub_class: SubClass,
        occupants: tuple[str, ...],
        now_seconds: int,
    ) -> bool:
        if not sub_id or sub_id in self._sessions:
            return False
        prof = _PROFILES.get(sub_class)
        if prof is None:
            return False
        if not occupants or len(occupants) > prof.crew_capacity:
            return False
        if len(set(occupants)) != len(occupants):
            return False
        self._sessions[sub_id] = SubmersibleSession(
            sub_id=sub_id,
            sub_class=sub_class,
            occupants=tuple(occupants),
            current_hp=prof.hp_max,
            deployed_at=now_seconds,
        )
        return True

    def descend(
        self, *, sub_id: str,
        target_depth_yalms: int,
    ) -> DescendResult:
        sess = self._sessions.get(sub_id)
        if sess is None:
            return DescendResult(False, reason="unknown sub")
        if sess.breached:
            return DescendResult(False, reason="hull breached")
        if target_depth_yalms < 0:
            return DescendResult(False, reason="bad depth")
        prof = _PROFILES[sess.sub_class]
        if target_depth_yalms > prof.depth_cap_yalms:
            return DescendResult(
                False, reason="exceeds depth cap",
            )
        sess.current_depth_yalms = target_depth_yalms
        return DescendResult(
            accepted=True, new_depth=target_depth_yalms,
        )

    def take_damage(
        self, *, sub_id: str, dmg: int,
    ) -> DamageResult:
        sess = self._sessions.get(sub_id)
        if sess is None:
            return DamageResult(False, reason="unknown sub")
        if dmg < 0:
            return DamageResult(False, reason="bad damage")
        if sess.breached:
            return DamageResult(
                accepted=True, hp_remaining=0,
                breached=True,
                dumped_at_depth=sess.current_depth_yalms,
            )
        sess.current_hp = max(0, sess.current_hp - dmg)
        if sess.current_hp == 0:
            sess.breached = True
            return DamageResult(
                accepted=True, hp_remaining=0,
                breached=True,
                dumped_at_depth=sess.current_depth_yalms,
            )
        return DamageResult(
            accepted=True, hp_remaining=sess.current_hp,
        )

    def occupants(self, *, sub_id: str) -> tuple[str, ...]:
        sess = self._sessions.get(sub_id)
        return sess.occupants if sess else ()

    def total_classes(self) -> int:
        return len(_PROFILES)


__all__ = [
    "SubClass", "SubProfile",
    "SubmersibleSession",
    "DescendResult", "DamageResult",
    "SubmersibleCraft",
]
