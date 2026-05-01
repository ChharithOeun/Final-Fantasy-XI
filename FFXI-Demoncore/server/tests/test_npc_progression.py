"""Tests for NPC progression: civilians + economic agents + mob memory
+ NM decay + boss policy pool + world tick.

Run:  python -m pytest server/tests/test_npc_progression.py -v
"""
import pathlib
import random
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from npc_progression import (
    BossPolicy,
    BossPolicyPool,
    EconomicAgent,
    LEVEL_CAP_BY_ROLE,
    MOB_LEVEL_SCALING_CAP,
    MarketListing,
    MobSnapshot,
    NmSnapshot,
    NpcRole,
    NpcSnapshot,
    POLICY_POOL_SIZE,
    POOL_REFRESH_INTERVAL_DAYS,
    award_xp,
    can_afford,
    choose_purchase,
    drop_rate_for,
    earn_gil_for_role,
    increment_kill_count,
    mob_level,
    nm_hp_scaling,
    promote_heir,
    ready_to_retire,
    reset_on_death,
    retire_npc,
    time_decay_buff,
    unlocks_ability,
    witness_event,
    world_tick,
)
from npc_progression.boss_policy import (
    needs_refresh,
    record_fight,
    refresh_pool,
    sample_policy_for_fight,
)
from npc_progression.civilian import (
    EVENT_XP_BURSTS,
    PLAYER_INTERACTION_XP,
    xp_required_for_level,
)
from npc_progression.nm_decay import notify_killed


# ----------------------------------------------------------------------
# Civilian XP + leveling
# ----------------------------------------------------------------------

def _zaldon() -> NpcSnapshot:
    """The doc's headline example NPC — Bastok shopkeeper."""
    return NpcSnapshot(
        npc_id="zaldon", name="Zaldon",
        role=NpcRole.SHOPKEEPER, zone="bastok_markets",
    )


def test_new_npc_starts_level_1():
    z = _zaldon()
    assert z.level == 1
    assert z.gil == 0


def test_ambient_xp_accumulates():
    z = _zaldon()
    # Shopkeeper ambient = 0.20 XP/tick; lvl 2 needs 200 XP -> 1000 ticks
    for _ in range(1100):
        award_xp(z, kind="ambient_tick", now=0)
    assert z.level >= 2


def test_witness_event_grants_burst():
    z = _zaldon()
    assert z.level == 1
    witness_event(z, event_kind="fomor_invasion_repelled", now=0)
    # 200 XP into a curve where lvl 2 needs 200: should hit lvl 2 exactly
    assert z.level == 2


def test_player_interaction_xp_modest():
    z = _zaldon()
    award_xp(z, kind="purchase_completed", now=0)
    # 0.5 XP — not enough to level
    assert z.level == 1
    assert z.xp_into_level == 0.5


def test_xp_history_records_event():
    z = _zaldon()
    witness_event(z, event_kind="fomor_invasion_witnessed",
                    now=42, detail="east gate")
    assert len(z.xp_history) == 1
    assert z.xp_history[0].timestamp == 42
    assert "fomor_invasion_witnessed" in z.xp_history[0].source


def test_levels_cap_at_role_max():
    z = _zaldon()
    # Force massive XP — should cap at SHOPKEEPER cap (65)
    for _ in range(10000):
        witness_event(z, event_kind="fomor_invasion_repelled", now=0)
    assert z.level == LEVEL_CAP_BY_ROLE[NpcRole.SHOPKEEPER]


def test_role_caps_match_doc():
    """Guards reach 75; ambient townfolk plateau at 30."""
    assert LEVEL_CAP_BY_ROLE[NpcRole.GUARD] == 75
    assert LEVEL_CAP_BY_ROLE[NpcRole.AMBIENT_TOWNFOLK] == 30
    assert LEVEL_CAP_BY_ROLE[NpcRole.GUILD_MASTER] == 85


# ----------------------------------------------------------------------
# Retirement + heir succession
# ----------------------------------------------------------------------

def test_not_ready_to_retire_below_cap():
    z = _zaldon()
    z.level = 60
    z.gil = 10_000_000
    assert ready_to_retire(z) is False


def test_not_ready_below_savings_goal():
    z = _zaldon()
    z.level = 65
    z.gil = 100_000
    assert ready_to_retire(z) is False


def test_ready_at_cap_and_savings():
    z = _zaldon()
    z.level = 65
    z.gil = 5_000_000
    assert ready_to_retire(z) is True


def test_retire_marks_state():
    z = _zaldon()
    z.level = 65
    z.gil = 5_000_000
    assert retire_npc(z, heir_npc_id="zaldon_jr") is True
    assert z.is_retired is True
    assert z.heir_npc_id == "zaldon_jr"


def test_retired_npc_no_more_xp():
    z = _zaldon()
    z.level = 65
    z.gil = 5_000_000
    retire_npc(z, heir_npc_id="zaldon_jr")
    award_xp(z, kind="purchase_completed", now=0)
    assert z.xp_into_level == 0.0


def test_promote_heir_inherits_role_and_zone():
    z = _zaldon()
    z.level = 65
    z.gil = 5_000_000
    retire_npc(z, heir_npc_id="zaldon_jr")
    heir = promote_heir(retiring=z, heir_id="zaldon_jr",
                          heir_name="Zaldon Jr.")
    assert heir.role == NpcRole.SHOPKEEPER
    assert heir.zone == "bastok_markets"
    assert heir.level == 1   # fresh start


# ----------------------------------------------------------------------
# Economic agent — wallet + decision loop
# ----------------------------------------------------------------------

def test_earn_gil_scales_with_role_and_level():
    z = _zaldon()
    z.level = 50
    earned = earn_gil_for_role(z, hours_elapsed=10)
    # base 200 * (1 + 50/30) * 10 = 200 * 2.667 * 10 ~= 5333
    assert earned > 4000
    assert z.gil == earned


def test_retired_npc_no_gil_earnings():
    z = _zaldon()
    z.is_retired = True
    earned = earn_gil_for_role(z, hours_elapsed=24)
    assert earned == 0


def _bronze_listing() -> MarketListing:
    return MarketListing(
        item_id="head_bronze_cap", seller_id="vendor1",
        price=500, item_tier=5,
        item_role_fit={NpcRole.SHOPKEEPER: 0.6, NpcRole.GUARD: 0.9},
        stats_score=10.0,
    )


def _mythril_listing() -> MarketListing:
    return MarketListing(
        item_id="head_mythril_sallet", seller_id="vendor1",
        price=8000, item_tier=30,
        item_role_fit={NpcRole.SHOPKEEPER: 0.5, NpcRole.GUARD: 0.95},
        stats_score=45.0,
    )


def test_can_afford_with_buffer():
    z = _zaldon()
    z.gil = 10_000
    # 20% buffer → 8000 spending cap. The 8000 mythril item is at the limit.
    listing = _mythril_listing()
    # Equal to cap is affordable (price == cap)
    assert can_afford(z, listing) is True
    z.gil = 9000   # cap is now 7200; 8000 doesn't fit
    assert can_afford(z, listing) is False


def test_choose_purchase_picks_best_affordable():
    z = _zaldon()
    z.gil = 100_000
    listings = [_bronze_listing(), _mythril_listing()]
    pick = choose_purchase(z, listings=listings, current_gear={})
    # Mythril sallet has higher stats_score; affordable; better
    assert pick is not None
    assert pick.item_id == "head_mythril_sallet"


def test_choose_purchase_skips_unaffordable():
    z = _zaldon()
    z.gil = 1000   # spending cap 800
    pick = choose_purchase(z,
                            listings=[_mythril_listing(), _bronze_listing()],
                            current_gear={})
    # Mythril at 8000 unaffordable; bronze at 500 is affordable
    assert pick is not None
    assert pick.item_id == "head_bronze_cap"


def test_choose_purchase_skips_low_role_fit():
    """A listing with role_fit < 0.5 is filtered out."""
    z = _zaldon()
    z.gil = 100_000
    bad_fit = MarketListing(
        item_id="head_paladin_helmet", seller_id="v1",
        price=2000, item_tier=40,
        item_role_fit={NpcRole.SHOPKEEPER: 0.20},
        stats_score=80.0,
    )
    pick = choose_purchase(z, listings=[bad_fit], current_gear={})
    assert pick is None


def test_economic_agent_tick_buys_and_deducts():
    z = _zaldon()
    z.gil = 0   # start broke
    agent = EconomicAgent(state=z)
    # Get rich-ish over many hours
    earn_gil_for_role(z, hours_elapsed=1000)
    mythril = _mythril_listing()
    purchase = agent.tick(
        hours_elapsed=1.0, listings=[mythril], now=0,
    )
    assert purchase is not None
    assert "head" in agent.current_gear
    assert agent.current_gear["head"].item_id == "head_mythril_sallet"


def test_economic_agent_tick_no_op_when_already_well_geared():
    z = _zaldon()
    z.gil = 100_000
    agent = EconomicAgent(state=z)
    # Pre-equip a better item
    agent.current_gear["head"] = MarketListing.__new__(MarketListing)   # placeholder
    from npc_progression.economic_agent import EquippedItem
    agent.current_gear["head"] = EquippedItem(
        item_id="head_relic_circlet", item_tier=99, stats_score=200.0,
        role_fit=1.0,
    )
    purchase = agent.tick(
        hours_elapsed=1.0,
        listings=[_mythril_listing()],
        now=0,
    )
    assert purchase is None


# ----------------------------------------------------------------------
# Mob memory + level scaling
# ----------------------------------------------------------------------

def test_fresh_mob_at_base_level():
    m = MobSnapshot(spawn_id="gob_1", base_level=7,
                     zone="ronfaure_west", species="goblin")
    assert mob_level(m) == 7


def test_three_kills_plus_one():
    m = MobSnapshot(spawn_id="gob_1", base_level=7,
                     zone="ronfaure_west", species="goblin")
    increment_kill_count(m, count=3)
    assert mob_level(m) == 8


def test_ten_kills_plus_two():
    m = MobSnapshot(spawn_id="gob_1", base_level=7,
                     zone="ronfaure_west", species="goblin")
    increment_kill_count(m, count=10)
    assert mob_level(m) == 9


def test_max_kill_scaling_caps_at_plus_5():
    m = MobSnapshot(spawn_id="gob_1", base_level=7,
                     zone="ronfaure_west", species="goblin")
    increment_kill_count(m, count=200)   # way past all thresholds
    assert mob_level(m) == 7 + MOB_LEVEL_SCALING_CAP   # 12


def test_death_resets_scaling():
    m = MobSnapshot(spawn_id="gob_1", base_level=7,
                     zone="ronfaure_west", species="goblin")
    increment_kill_count(m, count=50)
    reset_on_death(m)
    assert mob_level(m) == 7
    assert m.kill_count == 0


# ----------------------------------------------------------------------
# NM time-decay buffs
# ----------------------------------------------------------------------

def _leaping_lizzy() -> NmSnapshot:
    return NmSnapshot(
        nm_id="leaping_lizzy", name="Leaping Lizzy",
        base_level=27, zone="la_theine_plateau",
        base_hp=8000,
    )


def test_recently_killed_nm_at_baseline():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    assert time_decay_buff(nm, now=3600) == 0
    assert nm_hp_scaling(nm, now=3600) == 8000
    assert drop_rate_for(nm, now=3600) == pytest.approx(1.0)


def test_three_day_decay_tier_1():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    tier = time_decay_buff(nm, now=3 * 86400 + 1)
    assert tier == 1
    assert nm_hp_scaling(nm, now=3 * 86400 + 1) == int(8000 * 1.10)


def test_one_week_tier_2():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    assert time_decay_buff(nm, now=7 * 86400) == 2


def test_one_month_apex_tier_4():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    assert time_decay_buff(nm, now=30 * 86400) == 4
    assert drop_rate_for(nm, now=30 * 86400) == pytest.approx(2.30)


def test_never_killed_nm_treated_as_fully_decayed():
    """An NM that's never been killed counts as max-decay tier."""
    nm = _leaping_lizzy()
    nm.last_killed_at = None
    assert time_decay_buff(nm, now=0) == 4


def test_ability_unlocks_progression():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    assert unlocks_ability(nm, "rage", now=4 * 86400) is True
    assert unlocks_ability(nm, "berserk", now=4 * 86400) is False
    assert unlocks_ability(nm, "berserk", now=8 * 86400) is True
    assert unlocks_ability(nm, "apex_signature_move",
                              now=30 * 86400) is True


def test_killing_nm_resets_decay():
    nm = _leaping_lizzy()
    nm.last_killed_at = 0
    # 30 days uncampted: tier 4
    assert time_decay_buff(nm, now=30 * 86400) == 4
    # Killed: timer resets
    notify_killed(nm, now=30 * 86400)
    # 1 hour later: back to baseline
    assert time_decay_buff(nm, now=30 * 86400 + 3600) == 0


# ----------------------------------------------------------------------
# Boss policy pool
# ----------------------------------------------------------------------

def test_pool_size_constant():
    assert POLICY_POOL_SIZE == 10


def test_refresh_interval_constant():
    assert POOL_REFRESH_INTERVAL_DAYS == 30


def test_empty_pool_returns_none():
    pool = BossPolicyPool(boss_id="maat")
    assert sample_policy_for_fight(pool) is None


def test_sample_returns_one_of_pool():
    pool = BossPolicyPool(boss_id="maat", policies=[
        BossPolicy("p1", "maat"),
        BossPolicy("p2", "maat"),
        BossPolicy("p3", "maat"),
    ])
    pick = sample_policy_for_fight(pool, rng=random.Random(0))
    assert pick is not None
    assert pick.policy_id in {"p1", "p2", "p3"}


def test_weighted_sampling():
    """A heavily-weighted policy gets picked more often."""
    pool = BossPolicyPool(boss_id="maat", policies=[
        BossPolicy("p_rare", "maat", weight=0.01),
        BossPolicy("p_common", "maat", weight=99.0),
    ])
    rng = random.Random(42)
    counts = {"p_rare": 0, "p_common": 0}
    for _ in range(200):
        pick = sample_policy_for_fight(pool, rng=rng)
        counts[pick.policy_id] += 1
    assert counts["p_common"] > counts["p_rare"] * 10


def test_refresh_pool_replaces_policies():
    pool = BossPolicyPool(boss_id="maat", policies=[
        BossPolicy("old1", "maat"),
        BossPolicy("old2", "maat"),
    ])
    refresh_pool(pool, new_policies=[
        BossPolicy(f"new{i}", "maat") for i in range(15)
    ], now=100)
    # Pool capped at POLICY_POOL_SIZE
    assert len(pool.policies) == POLICY_POOL_SIZE
    assert pool.policies[0].policy_id == "new0"


def test_needs_refresh_when_never_refreshed():
    pool = BossPolicyPool(boss_id="maat")
    assert needs_refresh(pool, now=0) is True


def test_needs_refresh_after_30_days():
    """A pool refreshed at t=100 stays valid for 30 days; needs refresh
    after that. (Pools with last_refresh_at == 0 are treated as
    never-refreshed by needs_refresh, which is correct.)"""
    pool = BossPolicyPool(boss_id="maat", last_refresh_at=100,
                            policies=[BossPolicy("p", "maat")])
    assert needs_refresh(pool, now=100 + 29 * 86400) is False
    assert needs_refresh(pool, now=100 + 31 * 86400) is True


def test_record_fight_stamps_policy():
    pool = BossPolicyPool(boss_id="maat",
                            policies=[BossPolicy("p_a", "maat")])
    policy = sample_policy_for_fight(pool, rng=random.Random(0))
    log = record_fight(
        fight_id="f_1", pool=pool, policy=policy,
        party_composition=("WAR", "WHM", "BLM", "RDM", "NIN", "DRG"),
        started_at=100,
    )
    assert log.boss_id == "maat"
    assert log.policy_id == policy.policy_id
    assert log.started_at == 100


# ----------------------------------------------------------------------
# Integration: world tick coordinator
# ----------------------------------------------------------------------

def test_world_tick_processes_active_npcs():
    z = _zaldon()
    z.gil = 100_000
    agent = EconomicAgent(state=z)
    result = world_tick(
        economic_agents=[agent],
        market_listings=[_mythril_listing()],
        hours_elapsed=1.0, now=0,
    )
    assert result.npcs_processed == 1
    # Mythril sallet bought
    assert result.npcs_purchases == 1
    assert result.npcs_total_gil_spent == 8000


def test_world_tick_skips_retired_npcs():
    z = _zaldon()
    z.is_retired = True
    agent = EconomicAgent(state=z)
    result = world_tick(
        economic_agents=[agent],
        market_listings=[_mythril_listing()],
        hours_elapsed=1.0, now=0,
    )
    assert result.npcs_processed == 0


def test_world_tick_flags_retirement_ready_npc():
    z = _zaldon()
    z.level = 65
    z.gil = 5_500_000
    agent = EconomicAgent(state=z)
    result = world_tick(
        economic_agents=[agent],
        market_listings=[],
        hours_elapsed=1.0, now=0,
    )
    assert "zaldon" in result.npcs_ready_to_retire


def test_world_tick_grants_level_up_when_xp_crosses():
    """Many ambient ticks should level the NPC up at least once."""
    z = _zaldon()
    z.level = 1
    z.xp_into_level = 199.0   # 1 XP from level 2
    agent = EconomicAgent(state=z)
    result = world_tick(
        economic_agents=[agent],
        market_listings=[],
        hours_elapsed=10.0, now=0,
    )
    assert result.npcs_levelled_up == 1


# ----------------------------------------------------------------------
# Constants sanity
# ----------------------------------------------------------------------

def test_event_xp_burst_table_present():
    for required in ("fomor_invasion_repelled", "siege_repelled",
                       "boss_kill_witnessed", "outlaw_executed"):
        assert required in EVENT_XP_BURSTS


def test_player_interaction_xp_table_present():
    for required in ("purchase_completed", "quest_completed_by_player",
                       "advice_given_player_succeeded"):
        assert required in PLAYER_INTERACTION_XP


def test_xp_curve_simple_linear():
    """100 * level cumulative."""
    assert xp_required_for_level(1) == 100
    assert xp_required_for_level(10) == 1000
