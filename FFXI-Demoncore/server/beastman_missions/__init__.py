"""Beastman missions — city-mission chain + ranks.

Mirroring the canon nation mission structure: each beastman
city has a TIERED mission chain a player advances through to
earn city-specific RANKS. Mission progress per (player, city)
is independent — a Yagudo player might be Bishop's Acolyte in
Oztroja and Stranger in the Quadav Foundry on the same
character. Ranks gate teleports, gear shops, and final-boss
access.

Public surface
--------------
    CityRank enum    NEWCOMER -> ACOLYTE -> CHAMPION ->
                     CAPTAIN -> ELDER -> SOVEREIGN
    MissionDef dataclass
    PlayerMissionState dataclass
    BeastmanMissions
        .register_mission(city_id, mission_id, rank_required,
                          rewards_rank)
        .start_mission(player_id, city_id, mission_id)
        .complete_mission(player_id, city_id, mission_id)
        .rank_in(player_id, city_id) -> CityRank
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CityRank(str, enum.Enum):
    NEWCOMER = "newcomer"
    ACOLYTE = "acolyte"
    CHAMPION = "champion"
    CAPTAIN = "captain"
    ELDER = "elder"
    SOVEREIGN = "sovereign"


_RANK_ORDER: tuple[CityRank, ...] = tuple(CityRank)
_RANK_INDEX: dict[CityRank, int] = {
    R: i for i, R in enumerate(_RANK_ORDER)
}


@dataclasses.dataclass(frozen=True)
class MissionDef:
    mission_id: str
    city_id: str
    rank_required: CityRank
    rewards_rank: t.Optional[CityRank]
    label: str


@dataclasses.dataclass
class PlayerMissionState:
    player_id: str
    city_id: str
    rank: CityRank = CityRank.NEWCOMER
    in_progress: t.Optional[str] = None    # mission_id
    completed: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    mission_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    mission_id: str
    new_rank: t.Optional[CityRank] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanMissions:
    _missions: dict[str, MissionDef] = dataclasses.field(
        default_factory=dict,
    )
    _states: dict[
        tuple[str, str], PlayerMissionState,
    ] = dataclasses.field(default_factory=dict)

    def register_mission(
        self, *, mission_id: str, city_id: str,
        rank_required: CityRank,
        rewards_rank: t.Optional[CityRank],
        label: str,
    ) -> t.Optional[MissionDef]:
        if not mission_id or not city_id:
            return None
        if not label:
            return None
        if mission_id in self._missions:
            return None
        # rewards_rank, if set, must outrank rank_required
        if rewards_rank is not None:
            if (
                _RANK_INDEX[rewards_rank]
                <= _RANK_INDEX[rank_required]
            ):
                return None
        m = MissionDef(
            mission_id=mission_id, city_id=city_id,
            rank_required=rank_required,
            rewards_rank=rewards_rank,
            label=label,
        )
        self._missions[mission_id] = m
        return m

    def get_mission(
        self, mission_id: str,
    ) -> t.Optional[MissionDef]:
        return self._missions.get(mission_id)

    def _state(
        self, player_id: str, city_id: str,
    ) -> PlayerMissionState:
        key = (player_id, city_id)
        st = self._states.get(key)
        if st is None:
            st = PlayerMissionState(
                player_id=player_id, city_id=city_id,
            )
            self._states[key] = st
        return st

    def rank_in(
        self, *, player_id: str, city_id: str,
    ) -> CityRank:
        return self._state(player_id, city_id).rank

    def start_mission(
        self, *, player_id: str,
        city_id: str, mission_id: str,
    ) -> StartResult:
        m = self._missions.get(mission_id)
        if m is None:
            return StartResult(
                False, mission_id=mission_id,
                reason="no such mission",
            )
        if m.city_id != city_id:
            return StartResult(
                False, mission_id=mission_id,
                reason="wrong city",
            )
        st = self._state(player_id, city_id)
        if st.in_progress is not None:
            return StartResult(
                False, mission_id=mission_id,
                reason="another mission in progress",
            )
        if mission_id in st.completed:
            return StartResult(
                False, mission_id=mission_id,
                reason="already completed",
            )
        if (
            _RANK_INDEX[st.rank]
            < _RANK_INDEX[m.rank_required]
        ):
            return StartResult(
                False, mission_id=mission_id,
                reason="rank too low",
            )
        st.in_progress = mission_id
        return StartResult(
            accepted=True, mission_id=mission_id,
        )

    def complete_mission(
        self, *, player_id: str,
        city_id: str, mission_id: str,
    ) -> CompleteResult:
        m = self._missions.get(mission_id)
        if m is None:
            return CompleteResult(
                False, mission_id=mission_id,
                reason="no such mission",
            )
        st = self._state(player_id, city_id)
        if st.in_progress != mission_id:
            return CompleteResult(
                False, mission_id=mission_id,
                reason="not the active mission",
            )
        st.in_progress = None
        st.completed.add(mission_id)
        new_rank = None
        if m.rewards_rank is not None:
            if (
                _RANK_INDEX[m.rewards_rank]
                > _RANK_INDEX[st.rank]
            ):
                st.rank = m.rewards_rank
                new_rank = m.rewards_rank
        return CompleteResult(
            accepted=True, mission_id=mission_id,
            new_rank=new_rank,
        )

    def in_progress_for(
        self, *, player_id: str, city_id: str,
    ) -> t.Optional[str]:
        return self._state(
            player_id, city_id,
        ).in_progress

    def completed_for(
        self, *, player_id: str, city_id: str,
    ) -> tuple[str, ...]:
        return tuple(sorted(
            self._state(
                player_id, city_id,
            ).completed,
        ))

    def total_missions(self) -> int:
        return len(self._missions)


__all__ = [
    "CityRank",
    "MissionDef", "PlayerMissionState",
    "StartResult", "CompleteResult",
    "BeastmanMissions",
]
