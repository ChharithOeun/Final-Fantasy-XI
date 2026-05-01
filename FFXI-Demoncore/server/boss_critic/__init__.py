"""Boss Critic LLM — apex AI brain that adapts hero-boss strategy mid-fight.

Per BOSS_GRAMMAR.md Layer 4 + AI_WORLD_DENSITY.md Tier 3.
Watches the encounter every ~30 seconds, reads skillchain history +
party mood + damage events, outputs strategy hints (which attack
priority, which player to silence, whether to pop ultimate, whether
to yield) the boss combat AI consumes.

Public surface:
    BossCritic                — owns one boss instance's critic loop
    EncounterSnapshot         — input data
    StrategyHint              — output
"""
from .critic import (
    BossCritic,
    EncounterSnapshot,
    StrategyHint,
)

__all__ = [
    "BossCritic",
    "EncounterSnapshot",
    "StrategyHint",
]
