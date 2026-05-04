"""Tests for beastman PvP rules."""
from __future__ import annotations

from server.beastman_pvp_rules import (
    BeastmanPvPRules,
    CIVILIAN_KILL_BOUNTY_PER,
    COMBATANT_KILL_BOUNTY_PER,
    DEFENDER_REWARD_GIL,
    InvaderSide,
    RaidObjective,
    RaidStatus,
    SUCCESS_BOUNTY_GIL,
)


def test_declare_raid():
    p = BeastmanPvPRules()
    r = p.declare_raid(
        invader_id="brokenfang",
        invader_side=InvaderSide.BEASTMAN,
        target_zone_id="bastok_markets",
        objective=RaidObjective.LOOT_TREASURY,
    )
    assert r is not None
    assert r.status == RaidStatus.DECLARED


def test_declare_invalid_invader_rejected():
    p = BeastmanPvPRules()
    assert p.declare_raid(
        invader_id="",
        invader_side=InvaderSide.BEASTMAN,
        target_zone_id="x",
        objective=RaidObjective.BURN_LANDMARK,
    ) is None


def test_declare_invalid_zone_rejected():
    p = BeastmanPvPRules()
    assert p.declare_raid(
        invader_id="x",
        invader_side=InvaderSide.BEASTMAN,
        target_zone_id="",
        objective=RaidObjective.BURN_LANDMARK,
    ) is None


def test_declare_double_active_rejected():
    p = BeastmanPvPRules()
    p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.CAPTURE_LEADER,
    )
    res = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="palborough",
        objective=RaidObjective.LOOT_TREASURY,
    )
    assert res is None


def test_record_combatant_kill():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.CAPTURE_LEADER,
    )
    assert p.record_combat_kill(
        raid_id=raid.raid_id,
        killer_id="alice",
        victim_id="orc_guard_a",
    )
    r = p.get(raid.raid_id)
    assert r.combatant_kills == 1
    assert r.bounty_accrued == COMBATANT_KILL_BOUNTY_PER


def test_record_civilian_kill_higher_penalty():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.CAPTURE_LEADER,
    )
    p.record_combat_kill(
        raid_id=raid.raid_id,
        killer_id="alice",
        victim_id="orc_civilian_a",
        is_civilian=True,
    )
    r = p.get(raid.raid_id)
    assert r.civilian_kills == 1
    assert r.bounty_accrued == CIVILIAN_KILL_BOUNTY_PER


def test_record_kill_unknown_raid():
    p = BeastmanPvPRules()
    assert not p.record_combat_kill(
        raid_id="ghost",
        killer_id="alice", victim_id="bob",
    )


def test_record_kill_self_rejected():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
    )
    assert not p.record_combat_kill(
        raid_id=raid.raid_id,
        killer_id="alice", victim_id="alice",
    )


def test_record_kill_only_invader_counts():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
    )
    res = p.record_combat_kill(
        raid_id=raid.raid_id,
        killer_id="defender_a",
        victim_id="alice",
    )
    assert not res


def test_resolve_success():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    p.record_combat_kill(
        raid_id=raid.raid_id,
        killer_id="alice", victim_id="guard_a",
    )
    res = p.resolve_raid(
        raid_id=raid.raid_id, success=True,
        now_seconds=10.0,
    )
    assert res.success
    assert res.bounty_owed_by_invader == (
        COMBATANT_KILL_BOUNTY_PER + SUCCESS_BOUNTY_GIL
    )
    assert res.defender_reward_gil == 0


def test_resolve_repelled():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    res = p.resolve_raid(
        raid_id=raid.raid_id, success=False,
        now_seconds=10.0,
    )
    assert not res.success
    assert res.defender_reward_gil == DEFENDER_REWARD_GIL


def test_resolve_unknown():
    p = BeastmanPvPRules()
    assert p.resolve_raid(
        raid_id="ghost", success=True,
    ) is None


def test_resolve_already_resolved():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    p.resolve_raid(
        raid_id=raid.raid_id, success=True,
        now_seconds=10.0,
    )
    assert p.resolve_raid(
        raid_id=raid.raid_id, success=False,
        now_seconds=20.0,
    ) is None


def test_resolve_after_window_returns_none():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    res = p.resolve_raid(
        raid_id=raid.raid_id, success=True,
        now_seconds=99999.0,
    )
    assert res is None


def test_tick_auto_resolves_overdue():
    p = BeastmanPvPRules()
    raid = p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    auto = p.tick(now_seconds=99999.0)
    assert raid.raid_id in auto
    assert (
        p.get(raid.raid_id).status
        == RaidStatus.AUTO_RESOLVED
    )


def test_tick_keeps_active():
    p = BeastmanPvPRules()
    p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
        now_seconds=0.0,
    )
    auto = p.tick(now_seconds=10.0)
    assert auto == ()


def test_raids_in_zone_filters():
    p = BeastmanPvPRules()
    p.declare_raid(
        invader_id="a",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
    )
    p.declare_raid(
        invader_id="b",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="palborough",
        objective=RaidObjective.LOOT_TREASURY,
    )
    in_oztroja = p.raids_in_zone("oztroja")
    assert len(in_oztroja) == 1


def test_active_raid_for_lookup():
    p = BeastmanPvPRules()
    p.declare_raid(
        invader_id="alice",
        invader_side=InvaderSide.HUME_NATIONS,
        target_zone_id="oztroja",
        objective=RaidObjective.LOOT_TREASURY,
    )
    r = p.active_raid_for(invader_id="alice")
    assert r is not None
    assert r.invader_id == "alice"


def test_active_raid_for_unknown():
    p = BeastmanPvPRules()
    assert p.active_raid_for(
        invader_id="ghost",
    ) is None


def test_total_raids():
    p = BeastmanPvPRules()
    p.declare_raid(
        invader_id="a",
        invader_side=InvaderSide.BEASTMAN,
        target_zone_id="bastok_markets",
        objective=RaidObjective.LOOT_TREASURY,
    )
    p.declare_raid(
        invader_id="b",
        invader_side=InvaderSide.BEASTMAN,
        target_zone_id="windurst_walls",
        objective=RaidObjective.BURN_LANDMARK,
    )
    assert p.total_raids() == 2
