"""Tests for dynamic quest generation."""
from __future__ import annotations

import pytest

from server.dynamic_quest_gen import (
    GENERATION_THRESHOLD,
    NEED_STALE_SECONDS,
    RESOLVED_THRESHOLD,
    NeedKind,
    NeedSnapshot,
    ObjectiveKind,
    QuestEngine,
    QuestReward,
)
from server.npc_daily_routines import (
    NPCRoutineRegistry,
    shopkeeper_schedule,
)


def test_need_snapshot_validates_urgency():
    with pytest.raises(ValueError):
        NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=200,
        )


def test_publish_low_urgency_no_quest():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="woodsman", kind=NeedKind.LUMBER_LOW,
            urgency=30, target_id="oak_log", target_count=10,
        ),
        now_seconds=0.0,
    )
    eng.tick(now_seconds=0.0)
    assert eng.total_quests() == 0


def test_publish_high_urgency_generates_quest():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="woodsman", kind=NeedKind.LUMBER_LOW,
            urgency=80, target_id="oak_log", target_count=10,
        ),
        now_seconds=0.0,
    )
    counters = eng.tick(now_seconds=0.0)
    assert counters["generated"] == 1
    open_q = eng.open_quests_for(npc_id="woodsman")
    assert len(open_q) == 1
    q = open_q[0]
    assert q.objectives[0].kind == ObjectiveKind.GATHER_ITEM


def test_quest_objective_kind_matches_need():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="captain", kind=NeedKind.BEASTMEN_PRESSURE,
            urgency=85, target_id="orc_warrior", target_count=8,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="captain")[0]
    assert q.objectives[0].kind == ObjectiveKind.KILL_COUNT


def test_one_quest_per_need_kind():
    """Multiple urgency publishes for the same need don't spawn
    duplicates."""
    eng = QuestEngine()
    for _ in range(3):
        eng.publish_need(
            snapshot=NeedSnapshot(
                npc_id="woodsman", kind=NeedKind.LUMBER_LOW,
                urgency=70,
            ),
        )
        eng.tick(now_seconds=0.0)
    assert eng.total_quests() == 1


def test_resolution_auto_closes_quest():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="woodsman", kind=NeedKind.LUMBER_LOW,
            urgency=80,
        ),
        now_seconds=0.0,
    )
    eng.tick(now_seconds=0.0)
    # Need was resolved by the world (someone else stockpiled)
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="woodsman", kind=NeedKind.LUMBER_LOW,
            urgency=10,
        ),
        now_seconds=10.0,
    )
    counters = eng.tick(now_seconds=10.0)
    assert counters["closed_resolved"] >= 1


def test_quest_expires_when_npc_silent():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
        ),
        now_seconds=0.0,
    )
    eng.tick(now_seconds=0.0)
    # Long silence
    counters = eng.tick(now_seconds=NEED_STALE_SECONDS + 1)
    assert counters["expired"] >= 1


def test_player_accept_quest():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    assert eng.player_accept(player_id="bob", quest_id=q.quest_id)
    assert q.accepted_by == "bob"


def test_player_accept_already_taken_blocks_others():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    eng.player_accept(player_id="bob", quest_id=q.quest_id)
    assert not eng.player_accept(
        player_id="charlie", quest_id=q.quest_id,
    )


def test_player_progress_not_accepted_rejected():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
            target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    # Bob hasn't accepted yet
    assert not eng.player_progress(
        player_id="bob", quest_id=q.quest_id, objective_idx=0,
    )


def test_player_progress_caps_at_target():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
            target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    eng.player_accept(player_id="bob", quest_id=q.quest_id)
    eng.player_progress(
        player_id="bob", quest_id=q.quest_id,
        objective_idx=0, delta=10,
    )
    assert q.objectives[0].progress == 5


def test_turn_in_incomplete_rejected():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
            target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    eng.player_accept(player_id="bob", quest_id=q.quest_id)
    res = eng.player_turn_in(player_id="bob", quest_id=q.quest_id)
    assert not res.accepted
    assert "incomplete" in res.reason


def test_turn_in_complete_succeeds():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.LUMBER_LOW, urgency=80,
            target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    eng.player_accept(player_id="bob", quest_id=q.quest_id)
    eng.player_progress(
        player_id="bob", quest_id=q.quest_id,
        objective_idx=0, delta=5,
    )
    res = eng.player_turn_in(player_id="bob", quest_id=q.quest_id)
    assert res.accepted
    assert res.reward.gil > 0


def test_reward_scales_with_urgency():
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="urgent", kind=NeedKind.BEASTMEN_PRESSURE,
            urgency=95, target_count=1, target_id="orc_warlord",
        ),
    )
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="mild", kind=NeedKind.BEASTMEN_PRESSURE,
            urgency=GENERATION_THRESHOLD,
            target_count=1, target_id="orc_grunt",
        ),
    )
    eng.tick(now_seconds=0.0)
    urgent_q = eng.open_quests_for(npc_id="urgent")[0]
    mild_q = eng.open_quests_for(npc_id="mild")[0]
    assert urgent_q.reward.gil > mild_q.reward.gil


def _shop_registry() -> NPCRoutineRegistry:
    """A routine registry with one shopkeeper schedule."""
    reg = NPCRoutineRegistry()
    reg.register(schedule=shopkeeper_schedule(
        npc_id="dabihook",
        shop_waypoint="bastok_market_stall_3",
        home_waypoint="bastok_residence_3",
        tavern_waypoint="bastok_galkan_tavern",
    ))
    return reg


def test_quest_reward_rejects_xp():
    """XP doctrine: rewards must not carry XP."""
    with pytest.raises(ValueError):
        QuestReward(gil=500, xp=200)


def test_quest_reward_default_has_zero_xp():
    r = QuestReward(gil=500)
    assert r.xp == 0


def test_giver_waypoint_returns_active_location():
    eng = QuestEngine(routine_registry=_shop_registry())
    # 10am — shopkeeper is at the market stall
    wp = eng.giver_waypoint(npc_id="dabihook", hour=10)
    assert wp == "bastok_market_stall_3"
    # 3am — sleeping at home
    wp_night = eng.giver_waypoint(npc_id="dabihook", hour=3)
    assert wp_night == "bastok_residence_3"


def test_giver_waypoint_none_when_registry_unwired():
    eng = QuestEngine()
    assert eng.giver_waypoint(npc_id="dabihook", hour=10) is None


def test_player_accept_requires_correct_waypoint():
    eng = QuestEngine(routine_registry=_shop_registry())
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="dabihook", kind=NeedKind.LUMBER_LOW,
            urgency=80, target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="dabihook")[0]
    # Player at the wrong place at 10am
    assert not eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_residence_3", now_hour=10,
    )
    # Player at the right place at 10am (stall)
    assert eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=10,
    )


def test_player_accept_at_night_requires_finding_npc_at_home():
    eng = QuestEngine(routine_registry=_shop_registry())
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="dabihook", kind=NeedKind.LUMBER_LOW,
            urgency=80, target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="dabihook")[0]
    # 3am — shopkeeper is asleep at home
    # Looking at the stall finds an empty stall
    assert not eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=3,
    )
    # Knocking on the door at home — actual NPC is there
    assert eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_residence_3", now_hour=3,
    )


def test_player_accept_missing_args_when_registry_set():
    """If registry is wired but caller forgets to pass location/hour,
    accept fails — the player can't just hand-wave the schedule."""
    eng = QuestEngine(routine_registry=_shop_registry())
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="dabihook", kind=NeedKind.LUMBER_LOW, urgency=80,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="dabihook")[0]
    assert not eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
    )


def test_turn_in_requires_correct_waypoint():
    eng = QuestEngine(routine_registry=_shop_registry())
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="dabihook", kind=NeedKind.LUMBER_LOW,
            urgency=80, target_count=5,
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="dabihook")[0]
    # Accept at the right place
    eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=10,
    )
    # Complete the objective
    eng.player_progress(
        player_id="bob", quest_id=q.quest_id,
        objective_idx=0, delta=5,
    )
    # Try to turn in at the wrong place
    bad = eng.player_turn_in(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_galkan_tavern", now_hour=10,
    )
    assert not bad.accepted
    # Right place (he's still at the stall at 10am)
    good = eng.player_turn_in(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=10,
    )
    assert good.accepted
    # Reward has no XP
    assert good.reward.xp == 0
    assert good.reward.gil > 0


def test_turn_in_after_npc_changes_routine():
    """Player completes objective during shop hours but tries to
    turn in at 22h when the NPC is at the tavern. Wrong place
    -> rejected. Find the NPC at the tavern instead."""
    eng = QuestEngine(routine_registry=_shop_registry())
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="dabihook", kind=NeedKind.LUMBER_LOW,
            urgency=80, target_count=1, target_id="oak_log",
        ),
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="dabihook")[0]
    eng.player_accept(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=10,
    )
    eng.player_progress(
        player_id="bob", quest_id=q.quest_id,
        objective_idx=0, delta=1,
    )
    # 21h — shopkeeper is at the tavern.
    bad = eng.player_turn_in(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_market_stall_3", now_hour=21,
    )
    assert not bad.accepted
    good = eng.player_turn_in(
        player_id="bob", quest_id=q.quest_id,
        player_at_waypoint="bastok_galkan_tavern", now_hour=21,
    )
    assert good.accepted


def test_full_lifecycle_world_resolution_cancels_quest():
    """NPC publishes high urgency. Quest spawns. World resolves
    the underlying need. Quest auto-cancels even if a player had
    accepted it."""
    eng = QuestEngine()
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.PEST_INFESTATION,
            urgency=80, target_count=10, target_id="rat",
        ),
        now_seconds=0.0,
    )
    eng.tick(now_seconds=0.0)
    q = eng.open_quests_for(npc_id="alice")[0]
    eng.player_accept(player_id="bob", quest_id=q.quest_id)
    # World resolution: rats migrated elsewhere
    eng.publish_need(
        snapshot=NeedSnapshot(
            npc_id="alice", kind=NeedKind.PEST_INFESTATION,
            urgency=RESOLVED_THRESHOLD - 5,
        ),
        now_seconds=100.0,
    )
    eng.tick(now_seconds=100.0)
    # Bob can't turn it in
    res = eng.player_turn_in(player_id="bob", quest_id=q.quest_id)
    assert not res.accepted
    assert "cancelled" in res.reason
