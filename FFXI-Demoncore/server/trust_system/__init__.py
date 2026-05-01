"""Trust system — expanded roster, smarter AI, PvP-despawn.

Per the user direction: revamp the OG FFXI trust system.
- Expand the roster: more nation NPCs + Tenshodo + beastman allies
- Better AI: real party-sync (heal thresholds that read party HP,
  skillchain coordination, intervention MB awareness, target-follow
  on the player's target)
- No PvP: trusts cannot be used in PvP. The moment the owner
  attacks another player while trusts are summoned, all trusts
  despawn.

This module owns:
    catalog.py    — TrustSpec dataclass + 18-entry roster spanning
                     all 5 nations + outlaw-allied trusts
    party.py      — TrustParty manager (5-slot cap; summon/despawn)
    ai_brain.py   — Tick-based action selector with priority ladder
                     (self-preservation -> party heal -> SC/MB ->
                     debuff -> default action)
    pvp_guard.py  — TrustPvpGuard: despawn on owner_attacked_player

Public surface:
    TrustRole, TrustSpec, TrustSnapshot
    TRUST_CATALOG, trust_for(trust_id)
    TrustParty, MAX_TRUST_SLOTS
    TrustAIBrain, AIDecision, AIPriority
    DEFAULT_HEAL_THRESHOLDS
    TrustPvpGuard, DespawnReason
"""
from .ai_brain import (
    AIDecision,
    AIPriority,
    DEFAULT_HEAL_THRESHOLDS,
    PartyMemberState,
    TrustAIBrain,
)
from .catalog import (
    TRUST_CATALOG,
    TrustRole,
    TrustSpec,
    trust_for,
)
from .companions import (
    COMPANION_CATALOG,
    CompanionAttachment,
    CompanionManager,
    CompanionRole,
    CompanionSpec,
    CompanionType,
    companion_for,
    companions_by_type,
)
from .party import (
    DespawnReason,
    MAX_TRUST_SLOTS,
    TrustParty,
    TrustSnapshot,
)
from .pvp_guard import (
    TrustPvpGuard,
)

__all__ = [
    "TrustRole",
    "TrustSpec",
    "TrustSnapshot",
    "TRUST_CATALOG",
    "trust_for",
    "TrustParty",
    "MAX_TRUST_SLOTS",
    "DespawnReason",
    "TrustAIBrain",
    "AIDecision",
    "AIPriority",
    "DEFAULT_HEAL_THRESHOLDS",
    "PartyMemberState",
    "TrustPvpGuard",
]
