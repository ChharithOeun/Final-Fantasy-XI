"""Mob tier classifier — the 'tier the mobs' mitigation for 10x density.

Per COMBAT_TEMPO.md the doc lists three tiers:

    Hero   (current target, 1 per player)   full RL policy + anim + audio
    Active (2-15 in combat radius)          scripted+RL hybrid + full anim
    Ambient (everything else)                patrol-only, low-tick, no audio

When a player approaches an Ambient mob it gets promoted to Active.
When they leave combat range it demotes back. A mob is only Hero
when it's the player's CURRENT TARGET.

This is distinct from server.ai_density.AiTier (REACTIVE / SCRIPTED_BARK
/ REFLECTION / HERO / RL_POLICY) — that taxonomy is about WHAT KIND
of brain runs the agent. This taxonomy is about HOW MUCH compute we
spend on it RIGHT NOW based on player proximity.
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


class MobTempoTier(str, enum.Enum):
    """Per-frame compute budget tier (proximity-driven)."""
    HERO = "hero"
    ACTIVE = "active"
    AMBIENT = "ambient"


@dataclasses.dataclass(frozen=True)
class TierProfile:
    """What a tier costs and what it gets."""
    tier: MobTempoTier
    has_full_animation: bool
    has_full_audio: bool
    ai_policy_kind: str        # "rl" | "rl_scripted_hybrid" | "patrol_only"
    tick_hz: float             # AI ticks per second
    relative_compute_cost: float  # 1.0 = hero baseline


TIER_PROFILES: dict[MobTempoTier, TierProfile] = {
    MobTempoTier.HERO: TierProfile(
        tier=MobTempoTier.HERO,
        has_full_animation=True,
        has_full_audio=True,
        ai_policy_kind="rl",
        tick_hz=10.0,
        relative_compute_cost=1.0,
    ),
    MobTempoTier.ACTIVE: TierProfile(
        tier=MobTempoTier.ACTIVE,
        has_full_animation=True,
        has_full_audio=False,           # 'partial audio' per doc
        ai_policy_kind="rl_scripted_hybrid",
        tick_hz=5.0,
        relative_compute_cost=0.40,
    ),
    MobTempoTier.AMBIENT: TierProfile(
        tier=MobTempoTier.AMBIENT,
        has_full_animation=False,       # animation LOD'd
        has_full_audio=False,
        ai_policy_kind="patrol_only",
        tick_hz=0.5,
        relative_compute_cost=0.05,
    ),
}


def get_profile(tier: MobTempoTier) -> TierProfile:
    return TIER_PROFILES[tier]


# ----------------------------------------------------------------------
# Tuning constants
# ----------------------------------------------------------------------

# 80m active radius — the doc's 'Active radius: only mobs within
# 80m of any player get full position broadcasts'.
ACTIVE_RADIUS_METERS: float = 80.0

# Active-tier crowd cap. Doc: '2-15 in combat radius'. We use 15
# as the upper bound; over that we keep the tier=Active assignment
# but the orchestrator can opt to throttle further.
ACTIVE_TIER_PARTY_BOUNDS: tuple[int, int] = (2, 15)


# ----------------------------------------------------------------------
# Promotion / demotion
# ----------------------------------------------------------------------

@dataclasses.dataclass
class MobTierState:
    """Per-mob runtime state for the tempo classifier."""
    mob_id: str
    current_tier: MobTempoTier = MobTempoTier.AMBIENT
    is_current_target_of: t.Optional[str] = None    # actor_id of target lock

    def __post_init__(self) -> None:
        if self.is_current_target_of is not None:
            self.current_tier = MobTempoTier.HERO


def classify_tier(*,
                    is_current_target: bool,
                    closest_player_distance_m: float) -> MobTempoTier:
    """Classify a mob given two inputs. Pure function for testability.

    The two-input contract:
        - is_current_target  -> True if any player has it lock-targeted
        - closest_player_distance_m -> nearest player distance, meters

    The ladder is exclusive: HERO if targeted, else ACTIVE if within
    ACTIVE_RADIUS_METERS, else AMBIENT.
    """
    if closest_player_distance_m < 0:
        raise ValueError("distance must be non-negative")
    if is_current_target:
        return MobTempoTier.HERO
    if closest_player_distance_m <= ACTIVE_RADIUS_METERS:
        return MobTempoTier.ACTIVE
    return MobTempoTier.AMBIENT


def update_state(state: MobTierState,
                   *,
                   is_current_target: bool,
                   closest_player_distance_m: float) -> tuple[bool, MobTempoTier]:
    """Update one mob's tier and return (changed?, new_tier)."""
    new = classify_tier(
        is_current_target=is_current_target,
        closest_player_distance_m=closest_player_distance_m,
    )
    changed = new != state.current_tier
    state.current_tier = new
    state.is_current_target_of = (state.is_current_target_of
                                       if is_current_target
                                       else None)
    return changed, new


# ----------------------------------------------------------------------
# Compute-budget aggregation
# ----------------------------------------------------------------------

def total_compute_cost(states: t.Iterable[MobTierState]) -> float:
    """Sum of relative_compute_cost over a mob set.

    Used by the per-zone orchestrator to budget itself: 'better to
    ship a zone at 800 mobs that runs smoothly than 2000 that lags'.
    """
    cost = 0.0
    for s in states:
        cost += get_profile(s.current_tier).relative_compute_cost
    return cost


def count_by_tier(states: t.Iterable[MobTierState]) -> dict[MobTempoTier, int]:
    out: dict[MobTempoTier, int] = {t: 0 for t in MobTempoTier}
    for s in states:
        out[s.current_tier] += 1
    return out
