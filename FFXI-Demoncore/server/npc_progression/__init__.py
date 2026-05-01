"""NPC Progression — every entity in the world levels up.

Per NPC_PROGRESSION.md: NPCs aren't static fixtures. Civilians earn
XP from doing their jobs, save gil, buy gear, eventually retire and
pass their stalls to heirs. Mobs accumulate kill counts and level
up. NMs gain power proportional to time-since-last-death. Bosses
remember every fight and adapt.

Four progression classes:
    civilian.py       - 5 roles (shopkeeper/guild_master/guard/
                        ambient_townfolk/quest_giver) with role-tuned
                        XP + retirement + heir succession
    economic_agent.py - per-NPC wallet + observe-market + purchase
                        decision loop
    mob_memory.py     - per-spawn kill_count + level scaling
                        (base + 5 cap, resets on death)
    nm_decay.py       - time-since-last-death buffs (HP / abilities /
                        drop rate up)
    boss_policy.py    - 10-policy pool sampled at fight start, locked
                        for fight, monthly refresh
    world_tick.py     - per-Vana'diel-hour cron coordinator

Public surface (re-exports):
    NpcRole, NpcSnapshot, NpcXpEvent
    award_xp, witness_event, complete_player_interaction
    retire_npc, ready_to_retire
    EconomicAgent, MarketListing, can_afford, choose_purchase
    MobSnapshot, increment_kill_count, mob_level
    NmSnapshot, time_decay_buff, drop_rate_for
    BossPolicyPool, sample_policy_for_fight, refresh_pool
    world_tick (the coordinator)
"""
from .boss_policy import (
    BossPolicy,
    BossPolicyPool,
    POOL_REFRESH_INTERVAL_DAYS,
    POLICY_POOL_SIZE,
)
from .civilian import (
    LEVEL_CAP_BY_ROLE,
    NpcRole,
    NpcSnapshot,
    NpcXpEvent,
    award_xp,
    promote_heir,
    ready_to_retire,
    retire_npc,
    witness_event,
)
from .economic_agent import (
    EconomicAgent,
    MarketListing,
    can_afford,
    choose_purchase,
    earn_gil_for_role,
)
from .mob_memory import (
    MOB_LEVEL_SCALING_CAP,
    MobSnapshot,
    increment_kill_count,
    mob_level,
    reset_on_death,
)
from .nm_decay import (
    NmSnapshot,
    drop_rate_for,
    nm_hp_scaling,
    time_decay_buff,
    unlocks_ability,
)
from .world_tick import (
    world_tick,
    WorldTickResult,
)

__all__ = [
    # Civilian
    "NpcRole",
    "NpcSnapshot",
    "NpcXpEvent",
    "LEVEL_CAP_BY_ROLE",
    "award_xp",
    "witness_event",
    "ready_to_retire",
    "retire_npc",
    "promote_heir",
    # Economic agent
    "EconomicAgent",
    "MarketListing",
    "can_afford",
    "choose_purchase",
    "earn_gil_for_role",
    # Mob
    "MobSnapshot",
    "MOB_LEVEL_SCALING_CAP",
    "increment_kill_count",
    "mob_level",
    "reset_on_death",
    # NM
    "NmSnapshot",
    "time_decay_buff",
    "nm_hp_scaling",
    "drop_rate_for",
    "unlocks_ability",
    # Boss
    "BossPolicy",
    "BossPolicyPool",
    "POOL_REFRESH_INTERVAL_DAYS",
    "POLICY_POOL_SIZE",
    # World tick
    "world_tick",
    "WorldTickResult",
]
