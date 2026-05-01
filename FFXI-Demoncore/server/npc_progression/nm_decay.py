"""NM time-decay buffs — power scales with time-since-last-death.

Per NPC_PROGRESSION.md: 'A low-tier NM unkilled for a month becomes
notably harder than its baseline — new abilities unlock, HP scales up,
drop rate goes up to compensate (the longer it's been alive, the
more it has to give).'

Creates the NM hunting metagame: do you kill the leveled-up NM (harder
fight, better drops) or wait it out (gets scarier; might miss the
window).
"""
from __future__ import annotations

import dataclasses
import typing as t


# Buff thresholds: time-since-last-death (real seconds) -> bonus tier
# Tier 0 baseline, tier 1 at 3 days, tier 2 at 1 week, tier 3 at 2 weeks,
# tier 4 at 1 month
DECAY_TIER_THRESHOLDS_SECONDS = {
    1: 3 * 86400,
    2: 7 * 86400,
    3: 14 * 86400,
    4: 30 * 86400,
}

# HP multiplier per tier (compounds gently)
HP_MULTIPLIER_BY_TIER = {0: 1.0, 1: 1.10, 2: 1.25, 3: 1.45, 4: 1.70}

# Drop-rate multiplier per tier (compensates the player for the harder fight)
DROP_RATE_MULTIPLIER_BY_TIER = {0: 1.0, 1: 1.20, 2: 1.50, 3: 1.85, 4: 2.30}

# Per-tier ability unlocks (additive list of ability_ids)
ABILITY_UNLOCKS_BY_TIER: dict[int, tuple[str, ...]] = {
    0: (),
    1: ("rage",),
    2: ("rage", "berserk"),
    3: ("rage", "berserk", "summon_adds"),
    4: ("rage", "berserk", "summon_adds", "apex_signature_move"),
}


@dataclasses.dataclass
class NmSnapshot:
    """Per-NM persistent memory."""
    nm_id: str
    name: str
    base_level: int
    zone: str
    base_hp: int
    last_killed_at: t.Optional[float] = None    # None = never killed
    base_drop_rate: float = 1.0                  # 1.0 = catalog default


def time_decay_buff(state: NmSnapshot, *, now: float) -> int:
    """Return the current decay tier (0..4) based on time-since-last-death."""
    if state.last_killed_at is None:
        # Never killed: counts as fully decayed (server-old NM)
        return 4
    elapsed = now - state.last_killed_at
    tier = 0
    for t_, threshold in DECAY_TIER_THRESHOLDS_SECONDS.items():
        if elapsed >= threshold:
            tier = t_
        else:
            break
    return tier


def nm_hp_scaling(state: NmSnapshot, *, now: float) -> int:
    """Effective HP of the NM at its current decay tier."""
    tier = time_decay_buff(state, now=now)
    return int(state.base_hp * HP_MULTIPLIER_BY_TIER[tier])


def drop_rate_for(state: NmSnapshot, *, now: float) -> float:
    """Effective drop rate multiplier."""
    tier = time_decay_buff(state, now=now)
    return state.base_drop_rate * DROP_RATE_MULTIPLIER_BY_TIER[tier]


def unlocks_ability(state: NmSnapshot, ability_id: str,
                     *, now: float) -> bool:
    """Has the NM unlocked this ability at its current decay tier?"""
    tier = time_decay_buff(state, now=now)
    return ability_id in ABILITY_UNLOCKS_BY_TIER[tier]


def notify_killed(state: NmSnapshot, *, now: float) -> None:
    """Reset the decay clock — NM was killed."""
    state.last_killed_at = now
