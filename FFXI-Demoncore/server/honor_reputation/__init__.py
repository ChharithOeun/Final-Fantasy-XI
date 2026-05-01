"""Honor + Reputation dual-gauge morality engine.

Per HONOR_REPUTATION.md: every character (player and NPC) has an
internal Honor gauge (private, moves on major moral acts) and a public
Reputation gauge (per-nation + global, moves on visible deeds).

Together the two gauges gate city entry, teleports, vendor disposition,
quest acceptance, mog-house access, and most NPC interactions. They
are also the connective tissue to the Outlaw / Reactive World systems.

Public surface:
    HonorRepTracker
    MoralityGauges
    MoralAct (enum)
    QuestDisposition (enum)
    ReputationTier (enum)
    SAFE_HAVEN_TOWNS
"""
from .tracker import (
    HonorRepTracker,
    MoralAct,
    MoralityGauges,
    QuestDisposition,
    ReputationTier,
    SAFE_HAVEN_TOWNS,
    GLOBAL_NATION_KEY,
)

__all__ = [
    "HonorRepTracker",
    "MoralityGauges",
    "MoralAct",
    "QuestDisposition",
    "ReputationTier",
    "SAFE_HAVEN_TOWNS",
    "GLOBAL_NATION_KEY",
]
