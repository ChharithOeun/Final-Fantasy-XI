"""Beastman field of valor — training regimens for beastman.

Beastman-side analog to FFXI's Field of Valor. A REGIMEN is a
small kill-list (3-5 mob types) tied to a zone, with an XP +
gil + tabs reward on completion. Players accept ONE regimen
at a time; finishing it is mandatory before accepting another
in the same zone.

Three regimen TIERS govern the reward magnitude:
  TRAINEE  — small XP, low tab payout, levels 1-30
  WARRIOR  — mid XP, mid tabs,        levels 30-60
  ELITE    — high XP, high tabs,      levels 60-99

Public surface
--------------
    RegimenTier enum
    Regimen dataclass
    BeastmanFieldOfValor
        .register_regimen(regimen_id, zone_id, tier, mob_kills,
                          xp_reward, gil_reward, tabs_reward)
        .accept(player_id, regimen_id)
        .record_kill(player_id, regimen_id, mob_id)
        .complete(player_id, regimen_id)
        .active_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RegimenTier(str, enum.Enum):
    TRAINEE = "trainee"
    WARRIOR = "warrior"
    ELITE = "elite"


@dataclasses.dataclass(frozen=True)
class Regimen:
    regimen_id: str
    zone_id: str
    tier: RegimenTier
    mob_kills: dict[str, int]   # mob_id -> required count
    xp_reward: int
    gil_reward: int
    tabs_reward: int


@dataclasses.dataclass
class _Acceptance:
    regimen_id: str
    progress: dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class AcceptResult:
    accepted: bool
    regimen_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class KillResult:
    accepted: bool
    regimen_id: str
    mob_id: str
    progress: int
    target: int
    completed_overall: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    regimen_id: str
    xp_awarded: int = 0
    gil_awarded: int = 0
    tabs_awarded: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanFieldOfValor:
    _regimens: dict[str, Regimen] = dataclasses.field(
        default_factory=dict,
    )
    _accepted: dict[str, _Acceptance] = dataclasses.field(
        default_factory=dict,
    )

    def register_regimen(
        self, *, regimen_id: str,
        zone_id: str,
        tier: RegimenTier,
        mob_kills: dict[str, int],
        xp_reward: int,
        gil_reward: int,
        tabs_reward: int,
    ) -> t.Optional[Regimen]:
        if regimen_id in self._regimens:
            return None
        if not mob_kills:
            return None
        for _, n in mob_kills.items():
            if n <= 0:
                return None
        if xp_reward < 0 or gil_reward < 0 or tabs_reward < 0:
            return None
        r = Regimen(
            regimen_id=regimen_id,
            zone_id=zone_id, tier=tier,
            mob_kills=dict(mob_kills),
            xp_reward=xp_reward,
            gil_reward=gil_reward,
            tabs_reward=tabs_reward,
        )
        self._regimens[regimen_id] = r
        return r

    def accept(
        self, *, player_id: str, regimen_id: str,
    ) -> AcceptResult:
        r = self._regimens.get(regimen_id)
        if r is None:
            return AcceptResult(
                False, regimen_id, reason="unknown regimen",
            )
        if player_id in self._accepted:
            return AcceptResult(
                False, regimen_id,
                reason="another regimen already active",
            )
        self._accepted[player_id] = _Acceptance(regimen_id=regimen_id)
        return AcceptResult(accepted=True, regimen_id=regimen_id)

    def record_kill(
        self, *, player_id: str,
        regimen_id: str,
        mob_id: str,
    ) -> KillResult:
        acc = self._accepted.get(player_id)
        if acc is None or acc.regimen_id != regimen_id:
            return KillResult(
                False, regimen_id, mob_id, 0, 0, False,
                reason="regimen not active for player",
            )
        r = self._regimens[regimen_id]
        if mob_id not in r.mob_kills:
            return KillResult(
                False, regimen_id, mob_id,
                progress=acc.progress.get(mob_id, 0),
                target=0,
                completed_overall=False,
                reason="mob not in regimen",
            )
        target = r.mob_kills[mob_id]
        cur = acc.progress.get(mob_id, 0)
        if cur >= target:
            return KillResult(
                accepted=True, regimen_id=regimen_id,
                mob_id=mob_id,
                progress=cur, target=target,
                completed_overall=self._all_done(acc, r),
                reason="quota already met",
            )
        acc.progress[mob_id] = cur + 1
        return KillResult(
            accepted=True, regimen_id=regimen_id,
            mob_id=mob_id,
            progress=acc.progress[mob_id],
            target=target,
            completed_overall=self._all_done(acc, r),
        )

    def _all_done(
        self, acc: _Acceptance, r: Regimen,
    ) -> bool:
        for mob_id, target in r.mob_kills.items():
            if acc.progress.get(mob_id, 0) < target:
                return False
        return True

    def complete(
        self, *, player_id: str, regimen_id: str,
    ) -> CompleteResult:
        acc = self._accepted.get(player_id)
        if acc is None or acc.regimen_id != regimen_id:
            return CompleteResult(
                False, regimen_id, reason="not active",
            )
        r = self._regimens[regimen_id]
        if not self._all_done(acc, r):
            return CompleteResult(
                False, regimen_id, reason="not all kills done",
            )
        del self._accepted[player_id]
        return CompleteResult(
            accepted=True, regimen_id=regimen_id,
            xp_awarded=r.xp_reward,
            gil_awarded=r.gil_reward,
            tabs_awarded=r.tabs_reward,
        )

    def active_for(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        acc = self._accepted.get(player_id)
        if acc is None:
            return None
        return acc.regimen_id

    def total_regimens(self) -> int:
        return len(self._regimens)


__all__ = [
    "RegimenTier", "Regimen",
    "AcceptResult", "KillResult", "CompleteResult",
    "BeastmanFieldOfValor",
]
