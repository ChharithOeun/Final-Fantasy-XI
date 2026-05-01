"""Boss policy pool — sampled at fight start, locked for fight,
monthly refresh.

Per NPC_PROGRESSION.md anti-degenerate-strat:
    A boss that learns from every fight will eventually counter every
    popular strategy. To keep the meta moving but not unwinnable:

    - Sampled at fight start from a pool of ~10 trained policies
    - Locked for the duration of that fight
    - Pool refreshes monthly based on what's been working

Strategy works for a fight; LS-meta-strategies stay viable for weeks;
world-meta-strategies (everyone uses tanker-X) shift over months.
"""
from __future__ import annotations

import dataclasses
import random
import typing as t


POLICY_POOL_SIZE = 10
POOL_REFRESH_INTERVAL_DAYS = 30
POOL_REFRESH_INTERVAL_SECONDS = POOL_REFRESH_INTERVAL_DAYS * 86400


@dataclasses.dataclass(frozen=True)
class BossPolicy:
    """One trained RL policy + metadata."""
    policy_id: str
    boss_id: str
    weight: float = 1.0          # sampling weight; higher = more often
    description: str = ""        # patch-notes hint for players
    trained_against_meta: str = ""    # 'tank-2dps-healer' / etc.


@dataclasses.dataclass
class BossPolicyPool:
    """Per-boss sampling pool. Refreshes every 30 days."""
    boss_id: str
    policies: list[BossPolicy] = dataclasses.field(default_factory=list)
    last_refresh_at: float = 0.0


def sample_policy_for_fight(pool: BossPolicyPool,
                              *,
                              rng: t.Optional[random.Random] = None,
                              ) -> t.Optional[BossPolicy]:
    """Pick the policy this fight will use. Locked for the fight's
    duration; the caller stores the chosen policy_id alongside the
    fight log so post-mortem readers know which variant they faced."""
    rng = rng or random.Random()
    if not pool.policies:
        return None

    weights = [p.weight for p in pool.policies]
    total = sum(weights)
    if total <= 0:
        return rng.choice(pool.policies)
    roll = rng.random() * total
    running = 0.0
    for policy, weight in zip(pool.policies, weights):
        running += weight
        if roll <= running:
            return policy
    return pool.policies[-1]


def needs_refresh(pool: BossPolicyPool, *, now: float) -> bool:
    """True if the 30-day refresh window has elapsed."""
    if pool.last_refresh_at == 0.0:
        return True
    return (now - pool.last_refresh_at) >= POOL_REFRESH_INTERVAL_SECONDS


def refresh_pool(pool: BossPolicyPool,
                  *,
                  new_policies: list[BossPolicy],
                  now: float) -> int:
    """Replace the pool with `new_policies` (typically 10) and stamp
    last_refresh_at. Returns the number of policies installed."""
    pool.policies = list(new_policies)[:POLICY_POOL_SIZE]
    pool.last_refresh_at = now
    return len(pool.policies)


@dataclasses.dataclass
class FightLog:
    """Records which policy was used in a given fight, for player
    post-mortem and pool-refresh signal."""
    fight_id: str
    boss_id: str
    policy_id: str
    started_at: float
    ended_at: t.Optional[float] = None
    party_won: t.Optional[bool] = None
    party_composition: tuple[str, ...] = ()


def record_fight(*,
                  fight_id: str,
                  pool: BossPolicyPool,
                  policy: BossPolicy,
                  party_composition: tuple[str, ...],
                  started_at: float) -> FightLog:
    """Stamp the fight start. The orchestrator updates ended_at +
    party_won when the fight resolves."""
    return FightLog(
        fight_id=fight_id,
        boss_id=pool.boss_id,
        policy_id=policy.policy_id,
        started_at=started_at,
        party_composition=party_composition,
    )
