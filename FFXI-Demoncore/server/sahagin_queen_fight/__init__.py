"""Sahagin Queen fight — SMN/WHM/RDM, dual-cast, royal guard summons.

MIRAHNA THE TIDE-HAG — Queen of the Sahagin. She fights as
SMN/WHM/RDM with permanent DUAL CAST (every spell goes
off twice). She can keep up to 3 avatars active at once
(typically Leviathan + Diabolos + a rotated 3rd) and
pulses heals to her royals between casts.

Every 5 game-minutes she calls forth a ROYAL GUARD party
of 5 — a balanced FFXI comp pulled at random from a
weighted pool: TANK + HEALER + SUPPORT + 2x DPS. The
guard is the key to surviving the fight: a royal guard
killed by a DOUBLE MAGIC BURST (the killing blow itself
must be a 2-stage MB) drops a 30-yalm AOE OXYGEN TANK
that grants +5 minutes of underwater breathing to every
player in range.

Public surface
--------------
    GuardRole enum
    OxygenTankDrop dataclass (frozen)
    GuardSummonResult dataclass (frozen)
    SahaginQueenFight
        .start(fight_id, hp_max, now_seconds)
        .tick_guard_summons(fight_id, now_seconds)
            -> Optional[GuardSummonResult]
        .active_avatar_count(fight_id) -> int
        .summon_avatar(fight_id, avatar_id) -> bool
        .dispel_avatar(fight_id, avatar_id) -> bool
        .dual_cast(fight_id, spell_id, now_seconds)
            -> tuple[str, str]
        .royal_guard_killed(fight_id, guard_id,
                            magic_burst_count,
                            killing_blow_was_double_mb,
                            now_seconds)
            -> Optional[OxygenTankDrop]
        .damage_queen(fight_id, amount, now_seconds)
        .queen_hp(fight_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


class GuardRole(str, enum.Enum):
    TANK = "tank"
    HEALER = "healer"
    SUPPORT = "support"
    DPS = "dps"


GUARD_PARTY_COMP: tuple[GuardRole, ...] = (
    GuardRole.TANK,
    GuardRole.HEALER,
    GuardRole.SUPPORT,
    GuardRole.DPS,
    GuardRole.DPS,
)
GUARD_SUMMON_INTERVAL_SECONDS = 5 * 60
MAX_ACTIVE_AVATARS = 3
OXYGEN_TANK_RADIUS_YALMS = 30
OXYGEN_TANK_BONUS_SECONDS = 5 * 60


@dataclasses.dataclass
class _Guard:
    guard_id: str
    role: GuardRole
    summoned_at: int


@dataclasses.dataclass
class _QueenFightState:
    fight_id: str
    hp_max: int
    hp: int
    started_at: int
    last_guard_summon_at: int
    active_avatars: set[str] = dataclasses.field(default_factory=set)
    active_guards: dict[str, _Guard] = dataclasses.field(default_factory=dict)
    summon_count: int = 0
    rng: random.Random = dataclasses.field(
        default_factory=lambda: random.Random(0),
    )


@dataclasses.dataclass(frozen=True)
class GuardSummonResult:
    summoned: bool
    guard_ids: tuple[str, ...] = ()
    roles: tuple[GuardRole, ...] = ()


@dataclasses.dataclass(frozen=True)
class OxygenTankDrop:
    dropped: bool
    radius_yalms: int = 0
    bonus_seconds: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SahaginQueenFight:
    _fights: dict[str, _QueenFightState] = dataclasses.field(
        default_factory=dict,
    )

    def start(
        self, *, fight_id: str, hp_max: int, now_seconds: int,
        rng_seed: int = 0,
    ) -> bool:
        if not fight_id or fight_id in self._fights:
            return False
        if hp_max <= 0:
            return False
        self._fights[fight_id] = _QueenFightState(
            fight_id=fight_id,
            hp_max=hp_max, hp=hp_max,
            started_at=now_seconds,
            last_guard_summon_at=now_seconds,
            rng=random.Random(rng_seed),
        )
        return True

    def tick_guard_summons(
        self, *, fight_id: str, now_seconds: int,
    ) -> t.Optional[GuardSummonResult]:
        f = self._fights.get(fight_id)
        if f is None or f.hp == 0:
            return None
        if (now_seconds - f.last_guard_summon_at) < GUARD_SUMMON_INTERVAL_SECONDS:
            return GuardSummonResult(summoned=False)
        f.last_guard_summon_at = now_seconds
        f.summon_count += 1
        guard_ids: list[str] = []
        roles: list[GuardRole] = []
        for i, role in enumerate(GUARD_PARTY_COMP):
            gid = f"{fight_id}_g{f.summon_count}_{i}_{role.value}"
            f.active_guards[gid] = _Guard(
                guard_id=gid, role=role, summoned_at=now_seconds,
            )
            guard_ids.append(gid)
            roles.append(role)
        return GuardSummonResult(
            summoned=True,
            guard_ids=tuple(guard_ids),
            roles=tuple(roles),
        )

    def summon_avatar(
        self, *, fight_id: str, avatar_id: str,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None or not avatar_id:
            return False
        if avatar_id in f.active_avatars:
            return False
        if len(f.active_avatars) >= MAX_ACTIVE_AVATARS:
            return False
        f.active_avatars.add(avatar_id)
        return True

    def dispel_avatar(
        self, *, fight_id: str, avatar_id: str,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None:
            return False
        return f.active_avatars.discard(avatar_id) is None and (
            avatar_id not in f.active_avatars
        )

    def active_avatar_count(self, *, fight_id: str) -> int:
        f = self._fights.get(fight_id)
        return len(f.active_avatars) if f else 0

    def dual_cast(
        self, *, fight_id: str, spell_id: str,
        now_seconds: int,
    ) -> tuple[str, str]:
        """Queen casts the same spell twice in a single action."""
        f = self._fights.get(fight_id)
        if f is None or not spell_id:
            return ("", "")
        return (spell_id, spell_id)

    def royal_guard_killed(
        self, *, fight_id: str, guard_id: str,
        magic_burst_count: int,
        killing_blow_was_double_mb: bool,
        now_seconds: int,
    ) -> t.Optional[OxygenTankDrop]:
        f = self._fights.get(fight_id)
        if f is None or guard_id not in f.active_guards:
            return None
        # remove guard
        del f.active_guards[guard_id]
        # tank drops only if killing blow was a double magic burst
        if not killing_blow_was_double_mb:
            return OxygenTankDrop(
                dropped=False, reason="killing blow not double MB",
            )
        if magic_burst_count < 2:
            return OxygenTankDrop(
                dropped=False, reason="MB count below 2",
            )
        return OxygenTankDrop(
            dropped=True,
            radius_yalms=OXYGEN_TANK_RADIUS_YALMS,
            bonus_seconds=OXYGEN_TANK_BONUS_SECONDS,
        )

    def damage_queen(
        self, *, fight_id: str, amount: int, now_seconds: int,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None or f.hp == 0 or amount <= 0:
            return False
        f.hp = max(0, f.hp - amount)
        return True

    def queen_hp(self, *, fight_id: str) -> int:
        f = self._fights.get(fight_id)
        return f.hp if f else 0


__all__ = [
    "GuardRole", "OxygenTankDrop", "GuardSummonResult",
    "SahaginQueenFight",
    "GUARD_PARTY_COMP", "GUARD_SUMMON_INTERVAL_SECONDS",
    "MAX_ACTIVE_AVATARS",
    "OXYGEN_TANK_RADIUS_YALMS", "OXYGEN_TANK_BONUS_SECONDS",
]
