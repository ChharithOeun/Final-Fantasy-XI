"""Quest log MSQ tracker — main story / mission / expansion arcs.

Two tracks live in the new quest log:
* SIDE QUESTS (handled by quest_engine + side_quest_clue_system) —
  authored to be cryptic; the log shows them only when a
  fragment is captured.
* MSQ / MISSIONS / EXPANSION ARCS — fully tracked. Players
  should never get lost in side content while a main thread
  is open.

This module is the MSQ track. For each player, for each
expansion, for each chapter mission they have started, we know:
  * current_step (numbered)
  * next_step description (one line)
  * who_to_talk_to (NPC id)
  * waypoint (zone + x,y,z)
  * required_keyitems / required_jobs / required_levels

Public surface
--------------
    Expansion enum
    StepKind enum
    MissionStep dataclass
    PlayerMSQProgress dataclass
    QuestLogMSQTracker
        .register_mission(expansion, mission_id, steps)
        .start_mission(player_id, mission_id)
        .complete_step(player_id, mission_id) -> next step
        .progress_for(player_id, mission_id)
        .next_for(player_id) -> the steered "do this next" hint
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Expansion(str, enum.Enum):
    BASE = "base"
    RISE_OF_THE_ZILART = "rotz"
    CHAINS_OF_PROMATHIA = "cop"
    TREASURES_OF_AHT_URHGAN = "toau"
    WINGS_OF_THE_GODDESS = "wotg"
    SEEKERS_OF_ADOULIN = "soa"
    RHAPSODIES = "rov"
    DEMONCORE = "demoncore"      # native Demoncore arc


class StepKind(str, enum.Enum):
    TALK = "talk"
    KILL = "kill"
    DELIVER = "deliver"
    DISCOVER = "discover"
    DEFEAT_BOSS = "defeat_boss"
    CUTSCENE = "cutscene"


class MissionStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclasses.dataclass(frozen=True)
class WaypointPos:
    zone_id: str
    x: float
    y: float
    z: float = 0.0


@dataclasses.dataclass(frozen=True)
class MissionStep:
    step_index: int
    kind: StepKind
    description: str
    who_to_talk_to: t.Optional[str] = None
    waypoint: t.Optional[WaypointPos] = None
    required_level: int = 1
    required_keyitems: tuple[str, ...] = ()
    required_jobs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class Mission:
    mission_id: str
    expansion: Expansion
    chapter_index: int
    title: str
    steps: tuple[MissionStep, ...]


@dataclasses.dataclass
class PlayerMSQProgress:
    player_id: str
    mission_id: str
    current_step_index: int = 0
    status: MissionStatus = MissionStatus.NOT_STARTED
    started_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None


@dataclasses.dataclass(frozen=True)
class NextStepHint:
    """The 'go do this' card rendered in the new quest log."""
    mission_id: str
    expansion: Expansion
    chapter_index: int
    step_index: int
    description: str
    who_to_talk_to: t.Optional[str]
    waypoint: t.Optional[WaypointPos]
    required_level: int


@dataclasses.dataclass
class QuestLogMSQTracker:
    _missions: dict[str, Mission] = dataclasses.field(
        default_factory=dict,
    )
    _progress: dict[
        tuple[str, str], PlayerMSQProgress,
    ] = dataclasses.field(default_factory=dict)

    def register_mission(
        self, *, mission_id: str,
        expansion: Expansion, chapter_index: int,
        title: str, steps: tuple[MissionStep, ...],
    ) -> t.Optional[Mission]:
        if mission_id in self._missions:
            return None
        if not steps:
            return None
        # Verify steps are 0-indexed contiguous
        for i, step in enumerate(steps):
            if step.step_index != i:
                return None
        m = Mission(
            mission_id=mission_id, expansion=expansion,
            chapter_index=chapter_index,
            title=title, steps=steps,
        )
        self._missions[mission_id] = m
        return m

    def mission(
        self, mission_id: str,
    ) -> t.Optional[Mission]:
        return self._missions.get(mission_id)

    def start_mission(
        self, *, player_id: str, mission_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[PlayerMSQProgress]:
        m = self._missions.get(mission_id)
        if m is None:
            return None
        key = (player_id, mission_id)
        if key in self._progress:
            return None
        prog = PlayerMSQProgress(
            player_id=player_id, mission_id=mission_id,
            current_step_index=0,
            status=MissionStatus.IN_PROGRESS,
            started_at_seconds=now_seconds,
        )
        self._progress[key] = prog
        return prog

    def progress_for(
        self, *, player_id: str, mission_id: str,
    ) -> t.Optional[PlayerMSQProgress]:
        return self._progress.get((player_id, mission_id))

    def complete_step(
        self, *, player_id: str, mission_id: str,
        now_seconds: float = 0.0,
    ) -> t.Optional[NextStepHint]:
        m = self._missions.get(mission_id)
        prog = self._progress.get((player_id, mission_id))
        if m is None or prog is None:
            return None
        if prog.status != MissionStatus.IN_PROGRESS:
            return None
        next_idx = prog.current_step_index + 1
        if next_idx >= len(m.steps):
            prog.status = MissionStatus.COMPLETE
            prog.completed_at_seconds = now_seconds
            return None
        prog.current_step_index = next_idx
        step = m.steps[next_idx]
        return NextStepHint(
            mission_id=mission_id,
            expansion=m.expansion,
            chapter_index=m.chapter_index,
            step_index=step.step_index,
            description=step.description,
            who_to_talk_to=step.who_to_talk_to,
            waypoint=step.waypoint,
            required_level=step.required_level,
        )

    def next_for_mission(
        self, *, player_id: str, mission_id: str,
    ) -> t.Optional[NextStepHint]:
        """Render the current 'do this next' card."""
        m = self._missions.get(mission_id)
        prog = self._progress.get((player_id, mission_id))
        if m is None or prog is None:
            return None
        if prog.status != MissionStatus.IN_PROGRESS:
            return None
        step = m.steps[prog.current_step_index]
        return NextStepHint(
            mission_id=mission_id,
            expansion=m.expansion,
            chapter_index=m.chapter_index,
            step_index=step.step_index,
            description=step.description,
            who_to_talk_to=step.who_to_talk_to,
            waypoint=step.waypoint,
            required_level=step.required_level,
        )

    def active_msqs_for(
        self, player_id: str,
    ) -> tuple[NextStepHint, ...]:
        """All in-progress MSQ cards for this player. Sorted
        by expansion enum order then chapter — keeps the active
        story arc front-and-center in the quest log."""
        out: list[NextStepHint] = []
        for (pid, mid), prog in self._progress.items():
            if pid != player_id:
                continue
            if prog.status != MissionStatus.IN_PROGRESS:
                continue
            hint = self.next_for_mission(
                player_id=player_id, mission_id=mid,
            )
            if hint is not None:
                out.append(hint)
        out.sort(
            key=lambda h: (h.expansion.value, h.chapter_index),
        )
        return tuple(out)

    def total_missions(self) -> int:
        return len(self._missions)


__all__ = [
    "Expansion", "StepKind", "MissionStatus",
    "WaypointPos", "MissionStep", "Mission",
    "PlayerMSQProgress", "NextStepHint",
    "QuestLogMSQTracker",
]
