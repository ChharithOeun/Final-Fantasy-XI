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
