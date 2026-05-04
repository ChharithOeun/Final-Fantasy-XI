"""Beastman assault companies — beastman-side mercenary squads.

Parallel to the hume Salvage/Assault model: small fireteams (3-6
players) take on time-bound MERCENARY MISSIONS issued by the
beastman war juntas. Each mission has a TARGET (zone+objective),
a TIMER (default 30 minutes), MERCENARY POINT payout, and a
RANK gate.

Squads are persistent rosters with a MERC RANK that grows with
completed missions, unlocking higher-difficulty issuances.

Public surface
--------------
    MercRank enum     PRIVATE → CORPORAL → SERGEANT →
                      LIEUTENANT → CAPTAIN → COMMANDER
    ObjectiveKind enum
    MissionStatus enum
    AssaultMission dataclass
    Squad dataclass
    BeastmanAssaultCompanies
        .form_squad(squad_id, members)
        .register_mission(mission_id, kind, zone_id,
                          rank_required, timer_seconds,
                          merc_payout)
        .deploy(squad_id, mission_id, now_seconds)
        .complete(squad_id, mission_id, now_seconds)
        .fail(squad_id, mission_id, reason)
        .squad_rank(squad_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MercRank(str, enum.Enum):
    PRIVATE = "private"
    CORPORAL = "corporal"
    SERGEANT = "sergeant"
    LIEUTENANT = "lieutenant"
    CAPTAIN = "captain"
    COMMANDER = "commander"


_RANK_ORDER: list[MercRank] = [
    MercRank.PRIVATE, MercRank.CORPORAL, MercRank.SERGEANT,
    MercRank.LIEUTENANT, MercRank.CAPTAIN, MercRank.COMMANDER,
]

_RANK_PROMOTION_THRESHOLDS: dict[MercRank, int] = {
    MercRank.CORPORAL: 5,
    MercRank.SERGEANT: 15,
    MercRank.LIEUTENANT: 35,
    MercRank.CAPTAIN: 70,
    MercRank.COMMANDER: 120,
}


class ObjectiveKind(str, enum.Enum):
    ASSASSINATE = "assassinate"
    DEMOLISH = "demolish"
    EXTRACT_INTEL = "extract_intel"
    ESCORT_PRISONER = "escort_prisoner"
    SABOTAGE_SUPPLY = "sabotage_supply"
    HOLD_GROUND = "hold_ground"


class MissionStatus(str, enum.Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class AssaultMission:
    mission_id: str
    kind: ObjectiveKind
    zone_id: str
    rank_required: MercRank
    timer_seconds: int
    merc_payout: int


@dataclasses.dataclass
class Squad:
    squad_id: str
    members: tuple[str, ...]
    rank: MercRank = MercRank.PRIVATE
    missions_completed: int = 0


@dataclasses.dataclass
class _Deployment:
    squad_id: str
    mission_id: str
    started_at: int
    status: MissionStatus = MissionStatus.ACTIVE


@dataclasses.dataclass(frozen=True)
class DeployResult:
    accepted: bool
    squad_id: str
    mission_id: str
    deadline: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    squad_id: str
    mission_id: str
    merc_awarded: int
    new_rank: MercRank
    promoted: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanAssaultCompanies:
    _missions: dict[str, AssaultMission] = dataclasses.field(
        default_factory=dict,
    )
    _squads: dict[str, Squad] = dataclasses.field(default_factory=dict)
    _deployments: dict[str, _Deployment] = dataclasses.field(
        default_factory=dict,
    )

    def form_squad(
        self, *, squad_id: str,
        members: tuple[str, ...],
    ) -> t.Optional[Squad]:
        if squad_id in self._squads:
            return None
        if not (3 <= len(members) <= 6):
            return None
        if len(set(members)) != len(members):
            return None
        s = Squad(squad_id=squad_id, members=tuple(members))
        self._squads[squad_id] = s
        return s

    def register_mission(
        self, *, mission_id: str,
        kind: ObjectiveKind,
        zone_id: str,
        rank_required: MercRank,
        timer_seconds: int,
        merc_payout: int,
    ) -> t.Optional[AssaultMission]:
        if mission_id in self._missions:
            return None
        if timer_seconds <= 0 or merc_payout <= 0:
            return None
        m = AssaultMission(
            mission_id=mission_id,
            kind=kind, zone_id=zone_id,
            rank_required=rank_required,
            timer_seconds=timer_seconds,
            merc_payout=merc_payout,
        )
        self._missions[mission_id] = m
        return m

    def _rank_meets(
        self, squad_rank: MercRank, required: MercRank,
    ) -> bool:
        return (
            _RANK_ORDER.index(squad_rank)
            >= _RANK_ORDER.index(required)
        )

    def deploy(
        self, *, squad_id: str,
        mission_id: str,
        now_seconds: int,
    ) -> DeployResult:
        squad = self._squads.get(squad_id)
        mission = self._missions.get(mission_id)
        if squad is None or mission is None:
            return DeployResult(
                False, squad_id, mission_id, 0,
                reason="unknown squad or mission",
            )
        if squad_id in self._deployments:
            return DeployResult(
                False, squad_id, mission_id, 0,
                reason="squad already deployed",
            )
        if not self._rank_meets(squad.rank, mission.rank_required):
            return DeployResult(
                False, squad_id, mission_id, 0,
                reason="squad rank too low",
            )
        self._deployments[squad_id] = _Deployment(
            squad_id=squad_id,
            mission_id=mission_id,
            started_at=now_seconds,
        )
        return DeployResult(
            accepted=True,
            squad_id=squad_id, mission_id=mission_id,
            deadline=now_seconds + mission.timer_seconds,
        )

    def complete(
        self, *, squad_id: str,
        mission_id: str,
        now_seconds: int,
    ) -> CompleteResult:
        squad = self._squads.get(squad_id)
        mission = self._missions.get(mission_id)
        if squad is None or mission is None:
            return CompleteResult(
                False, squad_id, mission_id, 0,
                MercRank.PRIVATE, False,
                reason="unknown squad or mission",
            )
        deployment = self._deployments.get(squad_id)
        if deployment is None or deployment.mission_id != mission_id:
            return CompleteResult(
                False, squad_id, mission_id, 0,
                squad.rank, False,
                reason="squad not on this mission",
            )
        if (
            now_seconds - deployment.started_at
            > mission.timer_seconds
        ):
            self._deployments.pop(squad_id, None)
            return CompleteResult(
                False, squad_id, mission_id, 0,
                squad.rank, False,
                reason="timer expired",
            )
        squad.missions_completed += 1
        promoted = self._maybe_promote(squad)
        self._deployments.pop(squad_id, None)
        return CompleteResult(
            accepted=True,
            squad_id=squad_id, mission_id=mission_id,
            merc_awarded=mission.merc_payout,
            new_rank=squad.rank,
            promoted=promoted,
        )

    def _maybe_promote(self, squad: Squad) -> bool:
        idx = _RANK_ORDER.index(squad.rank)
        promoted = False
        # Walk up tiers as long as missions_completed meets next floor
        while idx < len(_RANK_ORDER) - 1:
            next_rank = _RANK_ORDER[idx + 1]
            threshold = _RANK_PROMOTION_THRESHOLDS[next_rank]
            if squad.missions_completed >= threshold:
                squad.rank = next_rank
                idx += 1
                promoted = True
            else:
                break
        return promoted

    def fail(
        self, *, squad_id: str, mission_id: str, reason: str,
    ) -> bool:
        deployment = self._deployments.get(squad_id)
        if deployment is None or deployment.mission_id != mission_id:
            return False
        self._deployments.pop(squad_id, None)
        return True

    def squad_rank(
        self, *, squad_id: str,
    ) -> t.Optional[MercRank]:
        s = self._squads.get(squad_id)
        if s is None:
            return None
        return s.rank

    def total_squads(self) -> int:
        return len(self._squads)

    def total_missions(self) -> int:
        return len(self._missions)


__all__ = [
    "MercRank", "ObjectiveKind", "MissionStatus",
    "AssaultMission", "Squad",
    "DeployResult", "CompleteResult",
    "BeastmanAssaultCompanies",
]
