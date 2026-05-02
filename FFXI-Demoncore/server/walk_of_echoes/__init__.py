"""Walk of Echoes — instanced random encounter battles.

WotG-era bonus content: party enters a Walk of Echoes wing,
fights waves of randomized opponents pulled from the era's
mob pools, and is rewarded based on clear time + party size.

Composes on top of instance_engine and rng_pool.

Public surface
--------------
    EchoTier enum (TIER_1 ... TIER_3)
    WoeWaveSpec dataclass
    spawn_wave(tier, party_size, rng) -> tuple[WoeOpponent, ...]
    compute_reward(tier, clear_time_s, party_size) -> WoeReward
"""
from __future__ import annotations

import dataclasses
import enum

from server.rng_pool import RngPool, STREAM_BOSS_CRITIC


class EchoTier(str, enum.Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


# Sample mob pools per tier
_MOB_POOL: dict[EchoTier, tuple[str, ...]] = {
    EchoTier.TIER_1: (
        "abyss_worm", "shadow_minion_t1", "phantom_yagudo",
        "spectral_orc", "ghastly_quadav",
    ),
    EchoTier.TIER_2: (
        "abyss_dragon_t2", "shadow_lord_t2", "phantom_archmage",
        "spectral_warmonger", "ghastly_chieftain",
    ),
    EchoTier.TIER_3: (
        "primordial_terror", "echo_dread", "void_chimera",
        "echo_lord_himself",
    ),
}


_LEVEL_PER_TIER: dict[EchoTier, int] = {
    EchoTier.TIER_1: 75,
    EchoTier.TIER_2: 85,
    EchoTier.TIER_3: 99,
}


WAVE_SIZE_BY_TIER: dict[EchoTier, int] = {
    EchoTier.TIER_1: 3,
    EchoTier.TIER_2: 5,
    EchoTier.TIER_3: 7,
}


@dataclasses.dataclass(frozen=True)
class WoeOpponent:
    mob_id: str
    level: int


@dataclasses.dataclass(frozen=True)
class WoeReward:
    cruor: int
    riftborn_boulder: int
    riftdross: int


def spawn_wave(*, tier: EchoTier, party_size: int,
                rng_pool: RngPool) -> tuple[WoeOpponent, ...]:
    """Roll a wave of mobs from the tier pool. Wave size scales
    with party size (1 mob extra per 2 players above 3)."""
    pool = _MOB_POOL[tier]
    base_size = WAVE_SIZE_BY_TIER[tier]
    bonus = max(0, (party_size - 3) // 2)
    size = base_size + bonus
    out: list[WoeOpponent] = []
    level = _LEVEL_PER_TIER[tier]
    for i in range(size):
        idx = rng_pool.randint(STREAM_BOSS_CRITIC, 0, len(pool) - 1)
        # Slight per-mob level variance: +/-2
        var = rng_pool.randint(STREAM_BOSS_CRITIC, -2, 2)
        out.append(WoeOpponent(
            mob_id=pool[idx], level=max(1, level + var),
        ))
    return tuple(out)


def compute_reward(*, tier: EchoTier, clear_time_s: float,
                    party_size: int) -> WoeReward:
    """Faster clears yield more cruor + a chance at riftborn pieces."""
    base_cruor = {
        EchoTier.TIER_1: 1500,
        EchoTier.TIER_2: 3000,
        EchoTier.TIER_3: 5000,
    }[tier]
    # Time bonus: <5min = 1.5x; 5-10min = 1.0x; >10min = 0.6x
    if clear_time_s < 5 * 60:
        mult = 1.5
    elif clear_time_s < 10 * 60:
        mult = 1.0
    else:
        mult = 0.6
    # Big party splits the cruor a bit
    party_factor = max(0.5, 1.0 - 0.05 * max(0, party_size - 3))
    cruor = int(base_cruor * mult * party_factor)
    boulder = 1 if (tier != EchoTier.TIER_1
                     and clear_time_s < 8 * 60) else 0
    dross = 1 if tier == EchoTier.TIER_3 and clear_time_s < 6 * 60 else 0
    return WoeReward(cruor=cruor, riftborn_boulder=boulder,
                      riftdross=dross)


__all__ = [
    "EchoTier", "WAVE_SIZE_BY_TIER",
    "WoeOpponent", "WoeReward",
    "spawn_wave", "compute_reward",
]
