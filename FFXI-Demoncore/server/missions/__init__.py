"""Missions — nation + expansion mission lines.

Different from quests: missions are linear (you can only have one
active in a line at a time), gate access by rank, and progressing
through them advances your rank within that line. Three nation
lines (Bastok/Sandy/Windy) plus expansion lines (ZM, CoP, ToAU,
WotG, etc.) — each independent.

Public surface
--------------
    MissionLine enum
    Mission immutable spec
    MissionState enum
    PlayerMissions per-player tracker
        .start(line, mission_id)
        .complete(line, mission_id) -> advances rank within line
        .current(line)
        .rank_in(line)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MissionLine(str, enum.Enum):
    BASTOK = "bastok_nation"
    SANDY = "sandy_nation"
    WINDY = "windy_nation"
    ZILART = "zilart"
    PROMATHIA = "promathia"
    AHT_URHGAN = "aht_urhgan"
    WINGS_OF_GODDESS = "wings_of_goddess"


class MissionState(str, enum.Enum):
    NOT_AVAILABLE = "not_available"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass(frozen=True)
class Mission:
    mission_id: str
    line: MissionLine
    label: str
    rank_required: int          # rank you need to start
    rank_after: int             # rank you become after completing
    description: str = ""


# Sample catalog (the canonical FFXI rank 1 -> rank 10 lines)
MISSION_CATALOG: tuple[Mission, ...] = (
    # Bastok rank 1 missions
    Mission("bastok_1_1", MissionLine.BASTOK,
            "Smash the Orcish Scouts!",
            rank_required=1, rank_after=1),
    Mission("bastok_1_2", MissionLine.BASTOK,
            "The Zeruhn Report",
            rank_required=1, rank_after=2),
    Mission("bastok_2_1", MissionLine.BASTOK,
            "The Crystal Spring",
            rank_required=2, rank_after=2),
    Mission("bastok_2_2", MissionLine.BASTOK,
            "The Emissary",
            rank_required=2, rank_after=3),
    Mission("bastok_3_1", MissionLine.BASTOK,
            "Ranperre's Final Rest",
            rank_required=3, rank_after=4),
    # Sandy rank 1 missions
    Mission("sandy_1_1", MissionLine.SANDY,
            "Smash the Orcish Scouts!",
            rank_required=1, rank_after=1),
    Mission("sandy_1_2", MissionLine.SANDY,
            "Save the Children",
            rank_required=1, rank_after=2),
    # Windy rank 1 missions
    Mission("windy_1_1", MissionLine.WINDY,
            "Recover the Orb",
            rank_required=1, rank_after=1),
    Mission("windy_1_2", MissionLine.WINDY,
            "The Heart of the Matter",
            rank_required=1, rank_after=2),
    # ZM line
    Mission("zm_1", MissionLine.ZILART,
            "The New Frontier",
            rank_required=6, rank_after=1),
    Mission("zm_2", MissionLine.ZILART,
            "Headstone Pilgrimage",
            rank_required=1, rank_after=2),
)


MISSION_BY_ID: dict[str, Mission] = {
    m.mission_id: m for m in MISSION_CATALOG
}


def missions_in_line(line: MissionLine) -> tuple[Mission, ...]:
    return tuple(m for m in MISSION_CATALOG if m.line == line)


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    mission_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _LineProgress:
    rank: int = 1                       # all lines start at rank 1
    in_progress: t.Optional[str] = None
    completed: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class PlayerMissions:
    player_id: str
    _by_line: dict[MissionLine, _LineProgress] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def _line(self, line: MissionLine) -> _LineProgress:
        return self._by_line.setdefault(line, _LineProgress())

    def rank_in(self, line: MissionLine) -> int:
        return self._line(line).rank

    def state_of(self, mission_id: str) -> MissionState:
        m = MISSION_BY_ID.get(mission_id)
        if m is None:
            return MissionState.NOT_AVAILABLE
        line = self._line(m.line)
        if mission_id in line.completed:
            return MissionState.COMPLETE
        if line.in_progress == mission_id:
            return MissionState.IN_PROGRESS
        if line.rank >= m.rank_required:
            return MissionState.AVAILABLE
        return MissionState.NOT_AVAILABLE

    def start(self, *, mission_id: str) -> StartResult:
        m = MISSION_BY_ID.get(mission_id)
        if m is None:
            return StartResult(False, mission_id, "unknown mission")
        line = self._line(m.line)
        if line.in_progress is not None:
            return StartResult(False, mission_id,
                               f"line busy with {line.in_progress}")
        if mission_id in line.completed:
            return StartResult(False, mission_id, "already completed")
        if line.rank < m.rank_required:
            return StartResult(
                False, mission_id,
                f"need rank {m.rank_required}, have {line.rank}",
            )
        line.in_progress = mission_id
        return StartResult(True, mission_id)

    def complete(self, *, mission_id: str) -> bool:
        m = MISSION_BY_ID.get(mission_id)
        if m is None:
            return False
        line = self._line(m.line)
        if line.in_progress != mission_id:
            return False
        line.in_progress = None
        line.completed.add(mission_id)
        # Advance rank if mission grants it
        if m.rank_after > line.rank:
            line.rank = m.rank_after
        return True

    def is_complete(self, mission_id: str) -> bool:
        return self.state_of(mission_id) == MissionState.COMPLETE

    def current(self, line: MissionLine) -> t.Optional[str]:
        return self._line(line).in_progress


__all__ = [
    "MissionLine", "MissionState", "Mission",
    "MISSION_CATALOG", "MISSION_BY_ID",
    "missions_in_line",
    "StartResult",
    "PlayerMissions",
]
