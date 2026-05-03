"""NPC goal stacks — hierarchical agency for AI entities.

A real person doesn't act on whim moment to moment; they have a
LIFETIME ambition, a multi-week PLAN that serves it, day-scale
TASKS, and a current INTENT. Demoncore's NPCs need the same
structure or they'll feel like glorified vending machines.

Goal levels
-----------
    LIFETIME_AMBITION   — "Open my own forge in the Metalworks."
                          Years of game-time. Rarely changes.
    MID_TERM_PLAN       — "Save 100,000 gil." Weeks. Updated as
                          the world shifts.
    NEAR_TERM_TASK      — "Sell today's stock by sundown." A day.
    CURRENT_INTENT      — "Greet the next customer warmly."
                          Minutes. Mostly emergent from
                          npc_dialogue_system + npc_daily_routines.

The stack flows top-down: ambitions birth plans, plans birth
tasks, tasks birth intents. Progress on a lower level feeds back
upward (a NEAR_TERM_TASK completed bumps the MID_TERM_PLAN's
progress meter).

What this module owns
---------------------
A `NPCGoalStack` per NPC, exposing:
* set / replace at any level
* get current goal at level
* progress(level, delta)
* compute aggregate progress on plans / ambitions
* tear-down propagation: cancel a plan, dependent tasks cancel

The orchestrator's prompt assembly pulls "current top of each
level" into the AI agent's context so the LLM stays
goal-aware.

Public surface
--------------
    GoalLevel enum
    GoalStatus enum
    Goal dataclass — level, label, progress 0..100, status
    NPCGoalStack
        .set(npc_id, level, goal)
        .get(npc_id, level) / .stack_for(npc_id) -> dict
        .progress(npc_id, level, delta) -> bool
        .complete(npc_id, level) / .cancel(npc_id, level)
        .summary_for_prompt(npc_id) -> str
    NPCGoalRegistry  — global registry holding stacks
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


PROGRESS_MIN = 0
PROGRESS_MAX = 100


class GoalLevel(str, enum.Enum):
    LIFETIME_AMBITION = "lifetime_ambition"
    MID_TERM_PLAN = "mid_term_plan"
    NEAR_TERM_TASK = "near_term_task"
    CURRENT_INTENT = "current_intent"


# Order from highest to lowest. Cancel-propagation walks downward.
GOAL_LEVEL_ORDER: tuple[GoalLevel, ...] = (
    GoalLevel.LIFETIME_AMBITION,
    GoalLevel.MID_TERM_PLAN,
    GoalLevel.NEAR_TERM_TASK,
    GoalLevel.CURRENT_INTENT,
)


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


@dataclasses.dataclass
class Goal:
    level: GoalLevel
    label: str
    progress: int = 0
    status: GoalStatus = GoalStatus.ACTIVE
    notes: str = ""
    set_at_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not (PROGRESS_MIN <= self.progress <= PROGRESS_MAX):
            raise ValueError(
                f"progress {self.progress} out of range",
            )


@dataclasses.dataclass
class NPCGoalStack:
    npc_id: str
    _by_level: dict[GoalLevel, Goal] = dataclasses.field(
        default_factory=dict,
    )

    def set(
        self, *, level: GoalLevel, label: str,
        progress: int = 0, notes: str = "",
        now_seconds: float = 0.0,
    ) -> Goal:
        g = Goal(
            level=level, label=label,
            progress=progress, notes=notes,
            set_at_seconds=now_seconds,
        )
        # Setting a higher-level goal cancels the active lower-
        # level goals — they were spawned by the prior plan and
        # no longer apply.
        idx = GOAL_LEVEL_ORDER.index(level)
        for lower in GOAL_LEVEL_ORDER[idx + 1:]:
            existing = self._by_level.get(lower)
            if existing is not None and existing.status == GoalStatus.ACTIVE:
                existing.status = GoalStatus.CANCELLED
        self._by_level[level] = g
        return g

    def get(self, level: GoalLevel) -> t.Optional[Goal]:
        return self._by_level.get(level)

    def stack(self) -> dict[GoalLevel, Goal]:
        return dict(self._by_level)

    def progress(
        self, *, level: GoalLevel, delta: int,
    ) -> bool:
        g = self._by_level.get(level)
        if g is None or g.status != GoalStatus.ACTIVE:
            return False
        g.progress = min(
            PROGRESS_MAX, max(PROGRESS_MIN, g.progress + delta),
        )
        if g.progress >= PROGRESS_MAX:
            g.status = GoalStatus.COMPLETED
        # Propagate a small fraction of progress UPWARD: completing
        # a NEAR_TERM_TASK bumps the MID_TERM_PLAN.
        idx = GOAL_LEVEL_ORDER.index(level)
        if idx > 0:
            parent_level = GOAL_LEVEL_ORDER[idx - 1]
            parent = self._by_level.get(parent_level)
            if parent is not None and parent.status == GoalStatus.ACTIVE:
                # Roll up 1/4 of the delta toward parent.
                parent.progress = min(
                    PROGRESS_MAX,
                    max(PROGRESS_MIN, parent.progress + delta // 4),
                )
                if parent.progress >= PROGRESS_MAX:
                    parent.status = GoalStatus.COMPLETED
        return True

    def complete(self, *, level: GoalLevel) -> bool:
        g = self._by_level.get(level)
        if g is None:
            return False
        g.status = GoalStatus.COMPLETED
        g.progress = PROGRESS_MAX
        return True

    def cancel(self, *, level: GoalLevel) -> bool:
        """Cancel a goal and all dependent lower-level goals."""
        g = self._by_level.get(level)
        if g is None:
            return False
        g.status = GoalStatus.CANCELLED
        idx = GOAL_LEVEL_ORDER.index(level)
        for lower in GOAL_LEVEL_ORDER[idx + 1:]:
            sub = self._by_level.get(lower)
            if sub is not None and sub.status == GoalStatus.ACTIVE:
                sub.status = GoalStatus.CANCELLED
        return True

    def block(self, *, level: GoalLevel, reason: str = "") -> bool:
        g = self._by_level.get(level)
        if g is None:
            return False
        g.status = GoalStatus.BLOCKED
        if reason:
            g.notes = reason
        return True

    def unblock(self, *, level: GoalLevel) -> bool:
        g = self._by_level.get(level)
        if g is None or g.status != GoalStatus.BLOCKED:
            return False
        g.status = GoalStatus.ACTIVE
        return True

    def aggregate_progress(self) -> dict[GoalLevel, int]:
        return {
            lvl: g.progress
            for lvl, g in self._by_level.items()
        }

    def summary_for_prompt(self) -> str:
        """Compact line per level for the orchestrator's prompt."""
        lines: list[str] = []
        for lvl in GOAL_LEVEL_ORDER:
            g = self._by_level.get(lvl)
            if g is None:
                continue
            lines.append(
                f"{lvl.value}: {g.label} "
                f"[{g.status.value}, {g.progress}%]"
            )
        return "\n".join(lines)


@dataclasses.dataclass
class NPCGoalRegistry:
    _stacks: dict[str, NPCGoalStack] = dataclasses.field(
        default_factory=dict,
    )

    def stack_for(self, npc_id: str) -> NPCGoalStack:
        s = self._stacks.get(npc_id)
        if s is None:
            s = NPCGoalStack(npc_id=npc_id)
            self._stacks[npc_id] = s
        return s

    def has(self, npc_id: str) -> bool:
        return npc_id in self._stacks

    def total(self) -> int:
        return len(self._stacks)


__all__ = [
    "PROGRESS_MIN", "PROGRESS_MAX",
    "GoalLevel", "GOAL_LEVEL_ORDER", "GoalStatus",
    "Goal", "NPCGoalStack", "NPCGoalRegistry",
]
