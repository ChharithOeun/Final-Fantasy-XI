"""Tests for NPC hierarchical goal stacks."""
from __future__ import annotations

import pytest

from server.npc_goals import (
    GOAL_LEVEL_ORDER,
    Goal,
    GoalLevel,
    GoalStatus,
    NPCGoalRegistry,
    NPCGoalStack,
)


def test_goal_progress_validation():
    with pytest.raises(ValueError):
        Goal(
            level=GoalLevel.NEAR_TERM_TASK, label="x",
            progress=200,
        )


def test_goal_level_order():
    assert GOAL_LEVEL_ORDER[0] == GoalLevel.LIFETIME_AMBITION
    assert GOAL_LEVEL_ORDER[-1] == GoalLevel.CURRENT_INTENT


def test_set_and_get_goal():
    s = NPCGoalStack(npc_id="dabihook")
    g = s.set(
        level=GoalLevel.LIFETIME_AMBITION,
        label="open a forge",
    )
    assert g.label == "open a forge"
    assert s.get(GoalLevel.LIFETIME_AMBITION) is g


def test_setting_higher_cancels_active_lower():
    """Setting a new MID_TERM_PLAN cancels active NEAR_TERM_TASK
    and CURRENT_INTENT — they were spawned by the prior plan."""
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.MID_TERM_PLAN, label="save 100k gil")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell stock")
    s.set(level=GoalLevel.CURRENT_INTENT, label="greet customer")
    # Replace the plan
    s.set(level=GoalLevel.MID_TERM_PLAN, label="apprentice instead")
    assert s.get(
        GoalLevel.NEAR_TERM_TASK,
    ).status == GoalStatus.CANCELLED
    assert s.get(
        GoalLevel.CURRENT_INTENT,
    ).status == GoalStatus.CANCELLED


def test_setting_lower_does_not_cancel_higher():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(
        level=GoalLevel.LIFETIME_AMBITION, label="open a forge",
    )
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell stock")
    assert s.get(
        GoalLevel.LIFETIME_AMBITION,
    ).status == GoalStatus.ACTIVE


def test_progress_increments_and_completes():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell stock")
    assert s.progress(level=GoalLevel.NEAR_TERM_TASK, delta=50)
    assert s.get(GoalLevel.NEAR_TERM_TASK).progress == 50
    s.progress(level=GoalLevel.NEAR_TERM_TASK, delta=60)
    g = s.get(GoalLevel.NEAR_TERM_TASK)
    assert g.progress == 100
    assert g.status == GoalStatus.COMPLETED


def test_progress_unknown_level_returns_false():
    s = NPCGoalStack(npc_id="dabihook")
    assert not s.progress(
        level=GoalLevel.NEAR_TERM_TASK, delta=10,
    )


def test_progress_blocked_goal_rejected():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell")
    s.block(level=GoalLevel.NEAR_TERM_TASK, reason="store closed")
    assert not s.progress(
        level=GoalLevel.NEAR_TERM_TASK, delta=10,
    )


def test_progress_propagates_to_parent_quarter():
    """Progress on a NEAR_TERM_TASK rolls 25% upward to MID_TERM."""
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.MID_TERM_PLAN, label="save gil")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell stock")
    s.progress(level=GoalLevel.NEAR_TERM_TASK, delta=80)
    # Parent should bump by 80//4 = 20
    assert s.get(GoalLevel.MID_TERM_PLAN).progress == 20


def test_progress_does_not_propagate_above_top():
    """LIFETIME_AMBITION has no parent."""
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.LIFETIME_AMBITION, label="forge")
    s.progress(level=GoalLevel.LIFETIME_AMBITION, delta=50)
    assert s.get(GoalLevel.LIFETIME_AMBITION).progress == 50


def test_complete_sets_progress_to_100():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell")
    s.complete(level=GoalLevel.NEAR_TERM_TASK)
    g = s.get(GoalLevel.NEAR_TERM_TASK)
    assert g.progress == 100
    assert g.status == GoalStatus.COMPLETED


def test_cancel_propagates_downward():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.MID_TERM_PLAN, label="save gil")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell")
    s.set(level=GoalLevel.CURRENT_INTENT, label="greet")
    s.cancel(level=GoalLevel.MID_TERM_PLAN)
    assert s.get(
        GoalLevel.NEAR_TERM_TASK,
    ).status == GoalStatus.CANCELLED
    assert s.get(
        GoalLevel.CURRENT_INTENT,
    ).status == GoalStatus.CANCELLED


def test_cancel_unknown_returns_false():
    s = NPCGoalStack(npc_id="dabihook")
    assert not s.cancel(level=GoalLevel.NEAR_TERM_TASK)


def test_block_and_unblock():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell")
    assert s.block(
        level=GoalLevel.NEAR_TERM_TASK, reason="store closed",
    )
    assert s.get(
        GoalLevel.NEAR_TERM_TASK,
    ).status == GoalStatus.BLOCKED
    assert "closed" in s.get(GoalLevel.NEAR_TERM_TASK).notes
    assert s.unblock(level=GoalLevel.NEAR_TERM_TASK)
    assert s.get(
        GoalLevel.NEAR_TERM_TASK,
    ).status == GoalStatus.ACTIVE


def test_unblock_active_goal_returns_false():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell")
    assert not s.unblock(level=GoalLevel.NEAR_TERM_TASK)


def test_aggregate_progress_lists_all_levels():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(
        level=GoalLevel.LIFETIME_AMBITION,
        label="forge", progress=10,
    )
    s.set(
        level=GoalLevel.MID_TERM_PLAN,
        label="save", progress=40,
    )
    agg = s.aggregate_progress()
    assert agg[GoalLevel.LIFETIME_AMBITION] == 10
    assert agg[GoalLevel.MID_TERM_PLAN] == 40


def test_summary_for_prompt_renders_levels():
    s = NPCGoalStack(npc_id="dabihook")
    s.set(
        level=GoalLevel.LIFETIME_AMBITION, label="open a forge",
    )
    s.set(level=GoalLevel.MID_TERM_PLAN, label="save 100k")
    summary = s.summary_for_prompt()
    assert "lifetime_ambition" in summary
    assert "mid_term_plan" in summary
    assert "open a forge" in summary


def test_registry_lazy_creates_stack():
    reg = NPCGoalRegistry()
    s = reg.stack_for("dabihook")
    assert s.npc_id == "dabihook"
    s2 = reg.stack_for("dabihook")
    assert s is s2
    assert reg.total() == 1


def test_registry_has_check():
    reg = NPCGoalRegistry()
    assert not reg.has("ghost")
    reg.stack_for("ghost")
    assert reg.has("ghost")


def test_full_lifecycle_npc_pursues_dream():
    """Dabihook wants to open a forge. Plans to save gil. Today's
    task: sell stock. Each customer interaction is a current
    intent. As tasks complete, plan progress rolls up."""
    s = NPCGoalStack(npc_id="dabihook")
    s.set(
        level=GoalLevel.LIFETIME_AMBITION, label="open a forge",
    )
    s.set(level=GoalLevel.MID_TERM_PLAN, label="save 100k gil")
    s.set(level=GoalLevel.NEAR_TERM_TASK, label="sell today's stock")
    s.set(level=GoalLevel.CURRENT_INTENT, label="greet customer")
    # Day's tasks complete
    s.progress(level=GoalLevel.NEAR_TERM_TASK, delta=100)
    # Task done, plan bumped 25%
    assert s.get(
        GoalLevel.NEAR_TERM_TASK,
    ).status == GoalStatus.COMPLETED
    assert s.get(GoalLevel.MID_TERM_PLAN).progress >= 20
    # New task for next day
    s.set(
        level=GoalLevel.NEAR_TERM_TASK,
        label="restock from caravan",
    )
    new = s.get(GoalLevel.NEAR_TERM_TASK)
    assert new.status == GoalStatus.ACTIVE
    assert new.progress == 0
