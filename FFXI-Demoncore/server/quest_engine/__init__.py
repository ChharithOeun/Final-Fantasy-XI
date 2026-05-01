"""Quest engine — state machine + prereq DAG.

Quests have a lifecycle: NOT_STARTED -> IN_PROGRESS (at some stage) ->
COMPLETE. Some quests have prereqs (must complete X first); the
engine validates the DAG topology when starting a quest.

Public surface
--------------
    QuestState      enum
    Quest           dataclass: id, name, prereq_ids, stages
    QuestLog        per-player progress
    StartResult / AdvanceResult
    register_quest / get_quest / quests_unlocked_for
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class QuestState(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True)
class Quest:
    quest_id: str
    name: str
    description: str = ""
    prereq_ids: tuple[str, ...] = ()       # all must be COMPLETE
    stages: tuple[str, ...] = ()           # ordered stage labels
    nation: str = "neutral"                # bastok / sandy / windy / neutral

    @property
    def stage_count(self) -> int:
        return len(self.stages)


@dataclasses.dataclass(frozen=True)
class StartResult:
    accepted: bool
    quest_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class AdvanceResult:
    accepted: bool
    quest_id: str
    new_stage: t.Optional[str] = None
    final_state: QuestState = QuestState.IN_PROGRESS
    reason: t.Optional[str] = None


@dataclasses.dataclass
class QuestProgress:
    quest_id: str
    state: QuestState = QuestState.NOT_STARTED
    current_stage_index: int = -1     # -1 means not started
    started_tick: t.Optional[int] = None
    completed_tick: t.Optional[int] = None


@dataclasses.dataclass
class QuestLog:
    """Per-player quest log."""
    player_id: str
    _entries: dict[str, QuestProgress] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def state_of(self, quest_id: str) -> QuestState:
        e = self._entries.get(quest_id)
        return e.state if e else QuestState.NOT_STARTED

    def progress_of(self, quest_id: str) -> t.Optional[QuestProgress]:
        return self._entries.get(quest_id)

    def is_complete(self, quest_id: str) -> bool:
        return self.state_of(quest_id) == QuestState.COMPLETE

    def all_complete(self) -> tuple[str, ...]:
        return tuple(
            qid for qid, e in self._entries.items()
            if e.state == QuestState.COMPLETE
        )


# Quest registry. Designers add to this catalog.
_QUESTS: dict[str, Quest] = {}


def register_quest(q: Quest) -> None:
    if q.quest_id in _QUESTS:
        raise ValueError(f"quest {q.quest_id} already registered")
    _QUESTS[q.quest_id] = q


def get_quest(quest_id: str) -> Quest:
    return _QUESTS[quest_id]


def all_registered_quest_ids() -> tuple[str, ...]:
    return tuple(_QUESTS.keys())


def reset_registry() -> None:
    """Test helper: clear the global registry."""
    _QUESTS.clear()


def _prereqs_satisfied(
    quest: Quest, log: QuestLog,
) -> tuple[bool, t.Optional[str]]:
    for pid in quest.prereq_ids:
        if not log.is_complete(pid):
            return False, f"prereq {pid} not complete"
    return True, None


def start_quest(
    *, log: QuestLog, quest_id: str, now_tick: int,
) -> StartResult:
    if quest_id not in _QUESTS:
        return StartResult(False, quest_id, "unknown quest")
    quest = _QUESTS[quest_id]
    if log.state_of(quest_id) != QuestState.NOT_STARTED:
        return StartResult(
            False, quest_id,
            f"already in state {log.state_of(quest_id).value}",
        )
    ok, reason = _prereqs_satisfied(quest, log)
    if not ok:
        return StartResult(False, quest_id, reason)

    log._entries[quest_id] = QuestProgress(
        quest_id=quest_id,
        state=QuestState.IN_PROGRESS,
        current_stage_index=0,
        started_tick=now_tick,
    )
    return StartResult(True, quest_id)


def advance_quest(
    *, log: QuestLog, quest_id: str, now_tick: int,
) -> AdvanceResult:
    """Advance to next stage; if past the last stage, complete."""
    progress = log._entries.get(quest_id)
    if progress is None or progress.state != QuestState.IN_PROGRESS:
        return AdvanceResult(
            False, quest_id, reason="not in progress",
        )
    quest = _QUESTS[quest_id]
    next_idx = progress.current_stage_index + 1
    if next_idx >= quest.stage_count:
        # Final advance -> complete
        progress.state = QuestState.COMPLETE
        progress.completed_tick = now_tick
        return AdvanceResult(
            True, quest_id,
            new_stage=None,
            final_state=QuestState.COMPLETE,
        )
    progress.current_stage_index = next_idx
    return AdvanceResult(
        True, quest_id,
        new_stage=quest.stages[next_idx],
        final_state=QuestState.IN_PROGRESS,
    )


def fail_quest(
    *, log: QuestLog, quest_id: str, now_tick: int,
) -> bool:
    progress = log._entries.get(quest_id)
    if progress is None:
        return False
    if progress.state != QuestState.IN_PROGRESS:
        return False
    progress.state = QuestState.FAILED
    progress.completed_tick = now_tick
    return True


def quests_unlocked_for(
    log: QuestLog,
) -> tuple[str, ...]:
    """All registered quest_ids whose prereqs are complete and that
    aren't already started/complete for this player."""
    out: list[str] = []
    for qid, q in _QUESTS.items():
        if log.state_of(qid) != QuestState.NOT_STARTED:
            continue
        ok, _ = _prereqs_satisfied(q, log)
        if ok:
            out.append(qid)
    return tuple(out)


__all__ = [
    "QuestState", "Quest",
    "QuestProgress", "QuestLog",
    "StartResult", "AdvanceResult",
    "register_quest", "get_quest",
    "all_registered_quest_ids", "reset_registry",
    "start_quest", "advance_quest", "fail_quest",
    "quests_unlocked_for",
]
