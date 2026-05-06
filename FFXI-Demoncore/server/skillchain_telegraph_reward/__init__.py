"""Skillchain telegraph reward — closing a chain reveals the boss.

When the alliance closes a SKILLCHAIN (the canonical
two-WS combo system), the boss is staggered for a heart-
beat. During that staggered moment, every chain
participant gets a brief window of free telegraph
visibility — they can SEE the boss's next wind-up clearly.

This is intentional. It rewards good chain timing AND
incentivizes the chain even when nobody's casting MBs.
And it's free — you don't need a GEO or BRD up — but
it's transient: 8 seconds, and only for those who closed
the chain together.

A KEY DESIGN POINT: Higher-tier skillchains (Light/Darkness)
grant longer visibility (12s); LV-1 chains grant the
default 8s. Magic Burst kills extend further: if the
chain is finished off by an MB, all MB casters AND the
chain participants get the visibility.

Public surface
--------------
    SkillchainTier enum
    RewardGrant dataclass (frozen)
    SkillchainTelegraphReward
        .on_chain_closed(chain_id, participant_ids,
                         tier, mb_caster_ids, gate,
                         now_seconds) -> RewardGrant
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


class SkillchainTier(str, enum.Enum):
    LV1 = "lv1"           # 2-step LV1 (Liquefaction, etc.)
    LV2 = "lv2"           # 2-step LV2 (Distortion, Fragmentation, etc.)
    LV3 = "lv3"           # 3-step closer (Detonation, Compression, etc.)
    LIGHT = "light"        # 4+ step Light
    DARKNESS = "darkness"  # 4+ step Darkness


# Per-tier visibility window (seconds)
TIER_VISIBILITY_SECONDS: dict[SkillchainTier, int] = {
    SkillchainTier.LV1: 8,
    SkillchainTier.LV2: 9,
    SkillchainTier.LV3: 10,
    SkillchainTier.LIGHT: 12,
    SkillchainTier.DARKNESS: 12,
}


@dataclasses.dataclass(frozen=True)
class RewardGrant:
    accepted: bool
    chain_id: str = ""
    tier: t.Optional[SkillchainTier] = None
    visibility_seconds: int = 0
    granted_player_ids: tuple[str, ...] = ()
    expires_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SkillchainTelegraphReward:
    # Track chain_id -> already-rewarded so we don't double-grant
    _rewarded_chains: set[str] = dataclasses.field(default_factory=set)

    def on_chain_closed(
        self, *, chain_id: str, participant_ids: t.Iterable[str],
        tier: SkillchainTier,
        gate: TelegraphVisibilityGate,
        now_seconds: int,
        mb_caster_ids: t.Iterable[str] = (),
    ) -> RewardGrant:
        if not chain_id:
            return RewardGrant(False, reason="blank chain id")
        if chain_id in self._rewarded_chains:
            return RewardGrant(
                False, chain_id=chain_id,
                reason="already rewarded",
            )
        seconds = TIER_VISIBILITY_SECONDS[tier]
        # Aggregate: chain participants + MB casters (deduped)
        recipients: list[str] = []
        seen: set[str] = set()
        for pid in participant_ids:
            if pid and pid not in seen:
                seen.add(pid)
                recipients.append(pid)
        for pid in mb_caster_ids:
            if pid and pid not in seen:
                seen.add(pid)
                recipients.append(pid)
        if not recipients:
            return RewardGrant(
                False, chain_id=chain_id, tier=tier,
                reason="no recipients",
            )
        granted: list[str] = []
        expires_at = now_seconds + seconds
        for pid in recipients:
            ok = gate.grant_visibility(
                player_id=pid,
                source=VisibilitySource.SKILLCHAIN_BONUS,
                granted_at=now_seconds,
                expires_at=expires_at,
                granted_by=chain_id,
            )
            if ok:
                granted.append(pid)
        self._rewarded_chains.add(chain_id)
        return RewardGrant(
            accepted=True, chain_id=chain_id, tier=tier,
            visibility_seconds=seconds,
            granted_player_ids=tuple(granted),
            expires_at=expires_at,
        )

    def has_been_rewarded(self, *, chain_id: str) -> bool:
        return chain_id in self._rewarded_chains


__all__ = [
    "SkillchainTier", "RewardGrant",
    "SkillchainTelegraphReward",
    "TIER_VISIBILITY_SECONDS",
]
