"""Salvage / Assault — instanced mercenary missions.

ToAU's mercenary system: form a 6-player static, hand a tag at the
mercenary recruiter, get teleported into a 30-minute instanced map,
clear objectives, exit. Imperial Standing reward + Salvage cells
(used for Salvage gear upgrades). Different from Dynamis (timed
raid) — these are crafted-objective puzzles.

Public surface
--------------
    AssaultRank enum (rank gates)
    AssaultMission catalog
    AssaultInstance lifecycle
        .start_objectives(now_tick)
        .complete_objective(name, now_tick)
        .conclude(now_tick) -> ResultRecord
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AssaultRank(int, enum.Enum):
    """Imperial Mercenary rank tiers."""
    PRIVATE = 1
    PRIVATE_FIRST_CLASS = 2
    SUPERIOR_PRIVATE = 3
    LANCE_CORPORAL = 4
    CORPORAL = 5
    SERGEANT = 6
    SERGEANT_MAJOR = 7
    CHIEF_SERGEANT = 8
    SECOND_LIEUTENANT = 9
    FIRST_LIEUTENANT = 10
    CAPTAIN = 11


@dataclasses.dataclass(frozen=True)
class AssaultMission:
    mission_id: str
    label: str
    rank_required: AssaultRank
    objectives: tuple[str, ...]
    timer_seconds: int = 30 * 60
    imperial_standing_reward: int = 600
    salvage_cell_reward: int = 0


# Sample catalog (Aht Urhgan canonical assault missions)
ASSAULT_CATALOG: tuple[AssaultMission, ...] = (
    AssaultMission(
        mission_id="lebros_supplies",
        label="Lebros Supplies",
        rank_required=AssaultRank.PRIVATE,
        objectives=("retrieve_supplies", "exit_zone"),
        imperial_standing_reward=600,
    ),
    AssaultMission(
        mission_id="orichalcum_survey",
        label="Orichalcum Survey",
        rank_required=AssaultRank.PRIVATE_FIRST_CLASS,
        objectives=("scan_node_a", "scan_node_b",
                    "scan_node_c", "exit_zone"),
        imperial_standing_reward=800,
    ),
    AssaultMission(
        mission_id="azure_experiments",
        label="Azure Experiments",
        rank_required=AssaultRank.CORPORAL,
        objectives=("collect_azure_essence",
                    "defeat_naga_warden", "exit_zone"),
        imperial_standing_reward=1200,
        salvage_cell_reward=2,
    ),
    AssaultMission(
        mission_id="mamool_breach",
        label="Mamool Ja Breach",
        rank_required=AssaultRank.SERGEANT_MAJOR,
        objectives=("breach_outer_wall", "kill_warleader",
                    "extract_intel", "exit_zone"),
        imperial_standing_reward=1500,
        salvage_cell_reward=3,
    ),
    AssaultMission(
        mission_id="apkallu_breeding",
        label="Apkallu Breeding",
        rank_required=AssaultRank.CHIEF_SERGEANT,
        objectives=("retrieve_apkallu_egg_x3", "exit_zone"),
        imperial_standing_reward=1800,
        salvage_cell_reward=3,
    ),
    AssaultMission(
        mission_id="periqia_lockdown",
        label="Periqia Lockdown",
        rank_required=AssaultRank.CAPTAIN,
        objectives=("breach_armory", "defeat_warden_a",
                    "defeat_warden_b", "extract_prisoners",
                    "exit_zone"),
        timer_seconds=45 * 60,
        imperial_standing_reward=2400,
        salvage_cell_reward=5,
    ),
)

MISSION_BY_ID: dict[str, AssaultMission] = {
    m.mission_id: m for m in ASSAULT_CATALOG
}


@dataclasses.dataclass
class AssaultInstance:
    instance_id: str
    mission_id: str
    party_ids: tuple[str, ...]
    started_at_tick: int
    expires_at_tick: int
    completed_objectives: set[str] = dataclasses.field(
        default_factory=set,
    )
    failed: bool = False
    concluded: bool = False

    @property
    def mission(self) -> AssaultMission:
        return MISSION_BY_ID[self.mission_id]


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    objective: str
    all_complete: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ConcludeResult:
    accepted: bool
    instance_id: str
    objectives_completed: int
    success: bool
    imperial_standing_awarded: int
    salvage_cells_awarded: int
    reason: t.Optional[str] = None


def open_assault(
    *, instance_id: str, mission_id: str,
    party_ids: t.Sequence[str], leader_rank: AssaultRank,
    now_tick: int,
) -> t.Optional[AssaultInstance]:
    """Open an instance if leader rank suffices and party isn't empty."""
    mission = MISSION_BY_ID.get(mission_id)
    if mission is None:
        return None
    if not party_ids:
        return None
    if leader_rank.value < mission.rank_required.value:
        return None
    return AssaultInstance(
        instance_id=instance_id,
        mission_id=mission_id,
        party_ids=tuple(party_ids),
        started_at_tick=now_tick,
        expires_at_tick=now_tick + mission.timer_seconds,
    )


def complete_objective(
    instance: AssaultInstance, *, objective: str, now_tick: int,
) -> CompleteResult:
    if instance.concluded:
        return CompleteResult(False, objective, reason="concluded")
    if now_tick >= instance.expires_at_tick:
        instance.failed = True
        return CompleteResult(False, objective, reason="time expired")
    mission = instance.mission
    if objective not in mission.objectives:
        return CompleteResult(False, objective,
                              reason="not an objective")
    if objective in instance.completed_objectives:
        return CompleteResult(False, objective,
                              reason="already complete")
    instance.completed_objectives.add(objective)
    all_done = (
        len(instance.completed_objectives) == len(mission.objectives)
    )
    return CompleteResult(True, objective, all_complete=all_done)


def conclude(
    instance: AssaultInstance, *, now_tick: int,
) -> ConcludeResult:
    instance.concluded = True
    mission = instance.mission
    success = (
        len(instance.completed_objectives) == len(mission.objectives)
        and not instance.failed
    )
    if not success:
        return ConcludeResult(
            accepted=True, instance_id=instance.instance_id,
            objectives_completed=len(instance.completed_objectives),
            success=False,
            imperial_standing_awarded=0,
            salvage_cells_awarded=0,
        )
    return ConcludeResult(
        accepted=True, instance_id=instance.instance_id,
        objectives_completed=len(instance.completed_objectives),
        success=True,
        imperial_standing_awarded=mission.imperial_standing_reward,
        salvage_cells_awarded=mission.salvage_cell_reward,
    )


__all__ = [
    "AssaultRank", "AssaultMission",
    "ASSAULT_CATALOG", "MISSION_BY_ID",
    "AssaultInstance",
    "CompleteResult", "ConcludeResult",
    "open_assault", "complete_objective", "conclude",
]
