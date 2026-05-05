"""Beastman courier dailies — daily fetch quests.

Each beastman city posts a small board of DAILY COURIER tasks
(deliver X to NPC Y in zone Z, fetch N samples of item Q,
escort caravan to outpost W). Each task has:
  - reward gil + sparks
  - difficulty grade (EASY / NORMAL / HARD)
  - daily slot cap (3 per player default)

Tasks RESET at the daily clock boundary (default 86_400 s).
A player may BANK up to 5 unstarted tasks across days; once
banked the slot is reserved and won't drop on rollover, but
they STILL count against the player's "active or banked" cap.

Public surface
--------------
    Difficulty enum   EASY / NORMAL / HARD
    CourierTask dataclass
    BeastmanCourierDailies
        .register_task(task_id, difficulty, gil, sparks)
        .accept(player_id, task_id, now_seconds)
        .bank(player_id, task_id)
        .complete(player_id, task_id)
        .roll_over_day(player_id, now_seconds)
        .active_count(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Difficulty(str, enum.Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


class TaskState(str, enum.Enum):
    ACTIVE = "active"
    BANKED = "banked"
    COMPLETED = "completed"


_PER_DAY_CAP = 3
_BANK_HARD_CAP = 5
_DAY_SECONDS = 86_400


@dataclasses.dataclass(frozen=True)
class CourierTask:
    task_id: str
    difficulty: Difficulty
    gil_reward: int
    sparks_reward: int


@dataclasses.dataclass
class _Acceptance:
    task_id: str
    state: TaskState
    accepted_at: int


@dataclasses.dataclass(frozen=True)
class AcceptResult:
    accepted: bool
    task_id: str
    state: TaskState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CompleteResult:
    accepted: bool
    task_id: str
    gil_awarded: int
    sparks_awarded: int
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanCourierDailies:
    _tasks: dict[str, CourierTask] = dataclasses.field(
        default_factory=dict,
    )
    # Per-player records of acceptances (active + banked + completed today)
    _accepted: dict[
        tuple[str, str], _Acceptance,
    ] = dataclasses.field(default_factory=dict)

    def register_task(
        self, *, task_id: str,
        difficulty: Difficulty,
        gil_reward: int,
        sparks_reward: int,
    ) -> t.Optional[CourierTask]:
        if task_id in self._tasks:
            return None
        if gil_reward < 0 or sparks_reward < 0:
            return None
        if gil_reward == 0 and sparks_reward == 0:
            return None
        ct = CourierTask(
            task_id=task_id,
            difficulty=difficulty,
            gil_reward=gil_reward,
            sparks_reward=sparks_reward,
        )
        self._tasks[task_id] = ct
        return ct

    def _player_acceptances(
        self, player_id: str,
    ) -> list[_Acceptance]:
        return [
            a for (pid, _tid), a in self._accepted.items()
            if pid == player_id
        ]

    def _active_or_banked_count(
        self, player_id: str,
    ) -> int:
        return sum(
            1 for a in self._player_acceptances(player_id)
            if a.state in (TaskState.ACTIVE, TaskState.BANKED)
        )

    def accept(
        self, *, player_id: str,
        task_id: str,
        now_seconds: int,
    ) -> AcceptResult:
        ct = self._tasks.get(task_id)
        if ct is None:
            return AcceptResult(
                False, task_id, TaskState.COMPLETED,
                reason="unknown task",
            )
        key = (player_id, task_id)
        if key in self._accepted:
            return AcceptResult(
                False, task_id, TaskState.COMPLETED,
                reason="already accepted",
            )
        # Cap per-day: count ACTIVE only (banked carry over and don't
        # consume the daily slot)
        active = sum(
            1 for a in self._player_acceptances(player_id)
            if a.state == TaskState.ACTIVE
        )
        if active >= _PER_DAY_CAP:
            return AcceptResult(
                False, task_id, TaskState.ACTIVE,
                reason="daily slot cap reached",
            )
        self._accepted[key] = _Acceptance(
            task_id=task_id,
            state=TaskState.ACTIVE,
            accepted_at=now_seconds,
        )
        return AcceptResult(
            accepted=True,
            task_id=task_id,
            state=TaskState.ACTIVE,
        )

    def bank(
        self, *, player_id: str, task_id: str,
    ) -> AcceptResult:
        a = self._accepted.get((player_id, task_id))
        if a is None:
            return AcceptResult(
                False, task_id, TaskState.COMPLETED,
                reason="not accepted",
            )
        if a.state != TaskState.ACTIVE:
            return AcceptResult(
                False, task_id, a.state,
                reason="not in active state",
            )
        # Hard cap on banked across player
        banked = sum(
            1 for x in self._player_acceptances(player_id)
            if x.state == TaskState.BANKED
        )
        if banked >= _BANK_HARD_CAP:
            return AcceptResult(
                False, task_id, a.state,
                reason="bank cap reached",
            )
        a.state = TaskState.BANKED
        return AcceptResult(
            accepted=True, task_id=task_id, state=a.state,
        )

    def complete(
        self, *, player_id: str, task_id: str,
    ) -> CompleteResult:
        a = self._accepted.get((player_id, task_id))
        if a is None:
            return CompleteResult(
                False, task_id, 0, 0,
                reason="not accepted",
            )
        if a.state == TaskState.COMPLETED:
            return CompleteResult(
                False, task_id, 0, 0,
                reason="already completed",
            )
        ct = self._tasks[task_id]
        a.state = TaskState.COMPLETED
        return CompleteResult(
            accepted=True,
            task_id=task_id,
            gil_awarded=ct.gil_reward,
            sparks_awarded=ct.sparks_reward,
        )

    def roll_over_day(
        self, *, player_id: str, now_seconds: int,
    ) -> int:
        """Drops ACTIVE tasks whose accepted_at is more than one day
        ago. BANKED + COMPLETED are preserved. Returns count rolled."""
        keys_to_drop: list[tuple[str, str]] = []
        for (pid, tid), a in self._accepted.items():
            if pid != player_id:
                continue
            if a.state == TaskState.ACTIVE:
                if now_seconds - a.accepted_at >= _DAY_SECONDS:
                    keys_to_drop.append((pid, tid))
        for k in keys_to_drop:
            del self._accepted[k]
        return len(keys_to_drop)

    def active_count(
        self, *, player_id: str,
    ) -> int:
        return sum(
            1 for a in self._player_acceptances(player_id)
            if a.state == TaskState.ACTIVE
        )

    def banked_count(
        self, *, player_id: str,
    ) -> int:
        return sum(
            1 for a in self._player_acceptances(player_id)
            if a.state == TaskState.BANKED
        )

    def total_tasks(self) -> int:
        return len(self._tasks)


__all__ = [
    "Difficulty", "TaskState",
    "CourierTask",
    "AcceptResult", "CompleteResult",
    "BeastmanCourierDailies",
]
