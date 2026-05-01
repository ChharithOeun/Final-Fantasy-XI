"""Global PvP + Outlaw bounty system.

Per PVP_GLOBAL_OUTLAWS.md: cross-race kills are XP for everyone (the
daytime XP route for fomors / mobs / NMs). Same-race kills brand the
killer as an outlaw — flagged, bounty-bearing, kill-on-sight in the
nation cities, refuge available only in Norg / Selbina / Mhaura.

This module owns the flagging logic + bounty arithmetic + aggro
gating. It composes with honor_reputation (outlaw flag is a separate
axis from honor/rep, but apply_act(BECAME_OUTLAW) usually fires here)
and player_state (outlaw permadeath produces an outlaw fomor).

Public surface:
    BountyTracker
    BountySnapshot
    KillResult
    OutlawStatus (enum)
    FactionRace (enum)
    OutlawAggroRules
    OUTLAW_SAFE_HAVENS
"""
from .aggro_rules import OutlawAggroRules
from .bounty import (
    BOUNTY_BASE_PER_LEVEL,
    BOUNTY_PAYOFF_MULTIPLIER,
    BountySnapshot,
    BountyTracker,
    FactionRace,
    KillResult,
    MONASTIC_SECLUSION_SECONDS,
    NATION_WIPE_THRESHOLD,
    OUTLAW_SAFE_HAVENS,
    OutlawStatus,
    REJOINDER_KILL_THRESHOLD,
    REJOINDER_WINDOW_SECONDS,
)

__all__ = [
    "BountyTracker",
    "BountySnapshot",
    "KillResult",
    "OutlawStatus",
    "FactionRace",
    "OutlawAggroRules",
    "OUTLAW_SAFE_HAVENS",
    "BOUNTY_BASE_PER_LEVEL",
    "BOUNTY_PAYOFF_MULTIPLIER",
    "MONASTIC_SECLUSION_SECONDS",
    "NATION_WIPE_THRESHOLD",
    "REJOINDER_KILL_THRESHOLD",
    "REJOINDER_WINDOW_SECONDS",
]
