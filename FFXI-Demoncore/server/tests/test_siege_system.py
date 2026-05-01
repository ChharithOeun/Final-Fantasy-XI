"""Tests for siege + campaign macro-warfare layer.

Run:  python -m pytest server/tests/test_siege_system.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from siege_system import (
    BASE_HOURLY_RATE,
    DEFENSE_MEDAL_BASE,
    DeploymentRecommendation,
    MILITARY_RESPAWN_SECONDS,
    MilitaryDeploymentPlanner,
    MilitaryNpcManager,
    MilitaryNpcSnapshot,
    NATION_MILITARY_COMPOSITIONS,
    PER_NATION_DEPLOYMENT_CAP,
    RaidComposer,
    RaidComposition,
    RaidReward,
    RaidRewardDistributor,
    RaidSize,
    SiegeProbabilityCalculator,
    ZoneMetrics,
    ZoneRankingComputer,
    ZoneStatus,
)
from siege_system.zone_rankings import compute_control_percentage


# ----------------------------------------------------------------------
# Zone classification
# ----------------------------------------------------------------------

def test_high_control_classifies_stable():
    metrics = ZoneMetrics(
        zone="ronfaure_east", beastman_activity=10,
        player_presence_hours=100, nation_interest=80,
        control_percentage=85,
    )
    rc = ZoneRankingComputer()
    assert rc.classify(metrics) == ZoneStatus.STABLE


def test_mid_control_classifies_contested():
    metrics = ZoneMetrics(
        zone="pashhow_marshlands", beastman_activity=400,
        player_presence_hours=50, nation_interest=60,
        control_percentage=50,
    )
    rc = ZoneRankingComputer()
    assert rc.classify(metrics) == ZoneStatus.CONTESTED


def test_low_control_classifies_beastman_dominant():
    metrics = ZoneMetrics(
        zone="davoi", beastman_activity=900,
        player_presence_hours=5, nation_interest=70,
        control_percentage=15,
    )
    rc = ZoneRankingComputer()
    assert rc.classify(metrics) == ZoneStatus.BEASTMAN_DOMINANT


def test_compute_control_dominated_by_kill_ratio():
    """When the kill ratio favors the nation strongly, control rises."""
    pct = compute_control_percentage(
        nation_kills=900, beastman_kills=100,
        player_presence_hours=10, nation_interest=50,
    )
    # kill_axis = 90; presence = 20; interest = 50
    # 90*0.6 + 20*0.25 + 50*0.15 = 54 + 5 + 7.5 = 66.5
    assert pct == pytest.approx(66.5, abs=0.5)


def test_compute_control_handles_no_combat():
    pct = compute_control_percentage(
        nation_kills=0, beastman_kills=0,
        player_presence_hours=0, nation_interest=50,
    )
    assert 30 <= pct <= 70   # falls in CONTESTED band by design


def test_ranking_sorts_most_vulnerable_first():
    rc = ZoneRankingComputer()
    a = ZoneMetrics(zone="a", beastman_activity=0,
                     player_presence_hours=0, nation_interest=50,
                     control_percentage=85)
    b = ZoneMetrics(zone="b", beastman_activity=0,
                     player_presence_hours=0, nation_interest=80,
                     control_percentage=20)
    c = ZoneMetrics(zone="c", beastman_activity=0,
                     player_presence_hours=0, nation_interest=50,
                     control_percentage=50)
    ranked = rc.rank_zones([a, b, c])
    # b (lowest control + high interest) should rank first
    assert ranked[0][0] == "b"
    assert ranked[0][1] == ZoneStatus.BEASTMAN_DOMINANT


# ----------------------------------------------------------------------
# Deployment planner
# ----------------------------------------------------------------------

def test_deploy_to_stable_uses_low_band():
    planner = MilitaryDeploymentPlanner(nation="bastok")
    recs = planner.plan([
        ("ronfaure_east", ZoneStatus.STABLE),
    ])
    assert len(recs) == 1
    assert recs[0].npc_count == 10   # upper of 5-10 stable band


def test_deploy_to_beastman_dominant_uses_high_band():
    planner = MilitaryDeploymentPlanner(nation="bastok")
    recs = planner.plan([
        ("pashhow_marshlands", ZoneStatus.BEASTMAN_DOMINANT),
    ])
    assert recs[0].npc_count == 100   # upper of 50-100 band


def test_deployment_respects_cap():
    """Many BEASTMAN_DOMINANT zones can't all get 100 NPCs each —
    the cap forces truncation."""
    planner = MilitaryDeploymentPlanner(nation="bastok", cap=300)
    recs = planner.plan([
        (f"zone_{i}", ZoneStatus.BEASTMAN_DOMINANT) for i in range(10)
    ])
    total = sum(r.npc_count for r in recs)
    assert total <= 300


def test_unknown_nation_raises():
    with pytest.raises(ValueError, match="unknown nation"):
        MilitaryDeploymentPlanner(nation="atlantis")


def test_composition_roles_match_nation():
    planner = MilitaryDeploymentPlanner(nation="sandoria")
    recs = planner.plan([
        ("la_theine_plateau", ZoneStatus.CONTESTED),
    ])
    composition = recs[0].composition
    assert "cavalry" in composition
    assert "paladin_captain" in composition
    # Total of role counts equals npc_count
    assert sum(composition.values()) == recs[0].npc_count


def test_composition_zero_count_is_empty():
    planner = MilitaryDeploymentPlanner(nation="bastok", cap=10)
    # First zone consumes the cap; second zone gets 0
    recs = planner.plan([
        ("a", ZoneStatus.BEASTMAN_DOMINANT),   # would want 100, capped
        ("b", ZoneStatus.STABLE),
    ])
    assert recs[0].npc_count <= 10
    # Second rec might be 0 or capped
    second_count = recs[1].npc_count
    if second_count == 0:
        assert recs[1].composition == {}


def test_each_nation_has_distinct_composition():
    bastok = NATION_MILITARY_COMPOSITIONS["bastok"]
    sandy = NATION_MILITARY_COMPOSITIONS["sandoria"]
    assert "heavy_infantry" in bastok
    assert "cavalry" in sandy
    assert "heavy_infantry" not in sandy


# ----------------------------------------------------------------------
# Military NPC lifecycle
# ----------------------------------------------------------------------

def test_military_kill_starts_8h_respawn():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="rg_1", nation="bastok", role="heavy_infantry",
        zone="pashhow_marshlands", level=40,
    ))
    mgr.notify_killed("rg_1", now=100)

    # Not eligible yet
    assert "rg_1" not in mgr.respawn_eligible(now=100 + 4 * 3600)
    # 8+ hours later: eligible
    assert "rg_1" in mgr.respawn_eligible(
        now=100 + MILITARY_RESPAWN_SECONDS + 1)


def test_respawn_brings_npc_back_at_full_level():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="rg_1", nation="bastok", role="heavy_infantry",
        zone="pashhow_marshlands", level=55,
    ))
    mgr.notify_killed("rg_1", now=0)
    mgr.respawn("rg_1")

    npc = mgr.get("rg_1")
    assert npc is not None
    assert npc.is_alive is True
    assert npc.level == 55         # progression preserved


def test_grant_xp_levels_up():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="rg_1", nation="bastok", role="heavy_infantry",
        zone="ronfaure_east", level=1,
    ))
    # 1->2 needs 1000 xp; 2->3 needs 2000; 3->4 needs 3000.
    # 6000 XP exact = level 4
    new_level = mgr.grant_xp("rg_1", xp=6000)
    assert new_level == 4


def test_dead_npc_does_not_gain_xp():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="rg_1", nation="bastok", role="heavy_infantry",
        zone="ronfaure_east", level=1,
    ))
    mgr.notify_killed("rg_1", now=0)
    new_level = mgr.grant_xp("rg_1", xp=10000)
    assert new_level == 0   # dead = no level reported


def test_alive_in_zone_only_returns_alive():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="a", nation="bastok", role="r",
        zone="z", level=1, is_alive=True,
    ))
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="b", nation="bastok", role="r",
        zone="z", level=1, is_alive=False,
    ))
    alive = mgr.alive_in_zone("z")
    assert len(alive) == 1
    assert alive[0].npc_id == "a"


def test_flag_bearer_death_drops_squad_effectiveness():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="standard", nation="bastok", role="standard_bearer",
        zone="z", level=40, is_flag_bearer=True,
    ))
    assert mgr.squad_effectiveness(zone="z", nation="bastok") == 1.0
    mgr.notify_killed("standard", now=100)
    assert mgr.squad_effectiveness(zone="z", nation="bastok") == 0.9


def test_zone_with_no_flag_bearer_is_full_effectiveness():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="grunt", nation="bastok", role="heavy_infantry",
        zone="z", level=20,
    ))
    assert mgr.squad_effectiveness(zone="z", nation="bastok") == 1.0


def test_time_until_respawn():
    mgr = MilitaryNpcManager()
    mgr.deploy(MilitaryNpcSnapshot(
        npc_id="rg_1", nation="bastok", role="r",
        zone="z", level=20,
    ))
    mgr.notify_killed("rg_1", now=0)
    # 4 hours in
    remaining = mgr.time_until_respawn("rg_1", now=4 * 3600)
    assert remaining == pytest.approx(4 * 3600.0)
    # After respawn time
    assert mgr.time_until_respawn("rg_1", now=10 * 3600) == 0.0


# ----------------------------------------------------------------------
# Siege probability
# ----------------------------------------------------------------------

def test_attack_chance_zero_when_no_beastmen():
    calc = SiegeProbabilityCalculator()
    chance = calc.attack_chance(
        beastman_strength=0.0, nation_strength=1.0,
        hours_since_last_attack=0,
    )
    assert chance == 0.0


def test_attack_chance_grows_with_time_since_attack():
    calc = SiegeProbabilityCalculator()
    fresh = calc.attack_chance(
        beastman_strength=1.0, nation_strength=1.0,
        hours_since_last_attack=0,
    )
    week_old = calc.attack_chance(
        beastman_strength=1.0, nation_strength=1.0,
        hours_since_last_attack=168,
    )
    # 1 week = 2x the chance
    assert week_old == pytest.approx(2 * fresh)


def test_attack_chance_drops_with_strong_nation():
    calc = SiegeProbabilityCalculator()
    weak = calc.attack_chance(
        beastman_strength=1.0, nation_strength=0.5,
        hours_since_last_attack=0,
    )
    strong = calc.attack_chance(
        beastman_strength=1.0, nation_strength=2.0,
        hours_since_last_attack=0,
    )
    assert weak > strong


def test_should_trigger_uses_rng():
    """RNG returning < chance triggers."""
    calc = SiegeProbabilityCalculator()
    rng_low = random.Random()
    rng_low.random = lambda: 0.0   # always trigger
    rng_high = random.Random()
    rng_high.random = lambda: 0.99   # never trigger

    assert calc.should_trigger(
        beastman_strength=1.0, nation_strength=1.0,
        hours_since_last_attack=0, rng=rng_low,
    ) is True
    assert calc.should_trigger(
        beastman_strength=1.0, nation_strength=1.0,
        hours_since_last_attack=0, rng=rng_high,
    ) is False


def test_attack_chance_clamps_to_one():
    calc = SiegeProbabilityCalculator()
    chance = calc.attack_chance(
        beastman_strength=1000.0, nation_strength=0.001,
        hours_since_last_attack=10000,
    )
    assert chance == 1.0


# ----------------------------------------------------------------------
# Raid composition
# ----------------------------------------------------------------------

def test_low_vulnerability_yields_small_raid():
    comp = RaidComposer().compose(vulnerability_score=20)
    assert comp.raid_size == RaidSize.SMALL
    assert comp.has_boss is False
    assert 50 <= comp.beastmen_count <= 100


def test_mid_vulnerability_yields_medium_raid():
    comp = RaidComposer().compose(vulnerability_score=50)
    assert comp.raid_size == RaidSize.MEDIUM
    assert 200 <= comp.beastmen_count <= 400
    assert comp.nm_count >= 2


def test_high_vulnerability_yields_major_raid():
    comp = RaidComposer().compose(vulnerability_score=85)
    assert comp.raid_size == RaidSize.MAJOR
    assert comp.beastmen_count >= 500
    assert comp.has_boss is True
    assert comp.duration_minutes >= 90


def test_compose_clamps_extreme_inputs():
    comp_low = RaidComposer().compose(vulnerability_score=-100)
    comp_high = RaidComposer().compose(vulnerability_score=999)
    assert comp_low.raid_size == RaidSize.SMALL
    assert comp_high.raid_size == RaidSize.MAJOR


# ----------------------------------------------------------------------
# Reward distribution
# ----------------------------------------------------------------------

def test_low_contribution_no_honor_gain():
    distrib = RaidRewardDistributor()
    reward = distrib.reward_defender(
        raid_size=RaidSize.MEDIUM,
        beastmen_killed=10, nm_killed=0,
        contribution_pct=0.05,
    )
    assert reward.honor_gain == 0


def test_high_contribution_grants_honor():
    distrib = RaidRewardDistributor()
    reward = distrib.reward_defender(
        raid_size=RaidSize.MAJOR,
        beastmen_killed=200, nm_killed=3,
        contribution_pct=0.40,
    )
    assert reward.honor_gain > 0
    assert reward.defense_medals > DEFENSE_MEDAL_BASE[RaidSize.MAJOR]


def test_xp_scales_with_kills_and_contribution():
    distrib = RaidRewardDistributor()
    high = distrib.reward_defender(
        raid_size=RaidSize.MEDIUM,
        beastmen_killed=100, nm_killed=2,
        contribution_pct=1.0,
    )
    low = distrib.reward_defender(
        raid_size=RaidSize.MEDIUM,
        beastmen_killed=100, nm_killed=2,
        contribution_pct=0.10,
    )
    assert high.xp == 10 * low.xp


def test_reward_includes_rep_gain_for_nation():
    distrib = RaidRewardDistributor()
    reward = distrib.reward_defender(
        raid_size=RaidSize.MAJOR,
        beastmen_killed=100, nm_killed=2,
        contribution_pct=0.50,
    )
    assert reward.nation_rep_gain >= 200


def test_major_raid_has_higher_drop_chance():
    distrib = RaidRewardDistributor()
    small = distrib.reward_defender(
        raid_size=RaidSize.SMALL, beastmen_killed=10, nm_killed=0,
        contribution_pct=1.0,
    )
    major = distrib.reward_defender(
        raid_size=RaidSize.MAJOR, beastmen_killed=10, nm_killed=0,
        contribution_pct=1.0,
    )
    assert major.bonus_drop_chance > small.bonus_drop_chance
