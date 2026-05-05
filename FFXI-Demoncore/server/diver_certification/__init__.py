"""Diver certification — depth-tier permits.

Going deep is dangerous. Even with underwater_swim's pressure
mechanics, the world doesn't let you descend below the
shallows without proof you can survive it. This module is
the LICENSING system: each depth tier requires a CERT earned
by completing trial dives or job-trial milestones.

Cert tiers (each is a requirement for descending deeper):
  SHALLOWS_PERMIT     - 0..50 yalms      (free, granted at MSQ start)
  MID_DEPTH_PERMIT    - 50..150 yalms    (TIDEMAGE-1 trial OR
                                           SPEAR_DIVER-1 trial)
  DEEP_PERMIT         - 150..300 yalms   (any underwater job lvl 30
                                           + Brine Lozenge x10)
  ABYSS_PERMIT        - 300+ yalms       (any underwater job at
                                           Genkai 50 + 5 Sunken
                                           Crown sigils)

Without the right cert, the world spawner refuses to admit
the player past the depth gate. (We don't enforce gameplay
here — we just record certs and answer can_descend_to().)

Public surface
--------------
    DiverTier enum
    CertGrant dataclass
    DiverCertification
        .grant(player_id, tier, source)
        .has_cert(player_id, tier)
        .can_descend_to(player_id, depth_yalms)
        .max_certified_depth(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DiverTier(str, enum.Enum):
    SHALLOWS_PERMIT = "shallows_permit"
    MID_DEPTH_PERMIT = "mid_depth_permit"
    DEEP_PERMIT = "deep_permit"
    ABYSS_PERMIT = "abyss_permit"


# tier -> max allowed depth (yalms)
_TIER_DEPTH_CEILING: dict[DiverTier, int] = {
    DiverTier.SHALLOWS_PERMIT: 50,
    DiverTier.MID_DEPTH_PERMIT: 150,
    DiverTier.DEEP_PERMIT: 300,
    DiverTier.ABYSS_PERMIT: 10_000,    # effectively unlimited
}

# tier ordering (deeper tiers imply shallower)
_TIER_ORDER: tuple[DiverTier, ...] = (
    DiverTier.SHALLOWS_PERMIT,
    DiverTier.MID_DEPTH_PERMIT,
    DiverTier.DEEP_PERMIT,
    DiverTier.ABYSS_PERMIT,
)


@dataclasses.dataclass(frozen=True)
class CertGrant:
    accepted: bool
    tier: t.Optional[DiverTier] = None
    source: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerCerts:
    player_id: str
    tiers: set[DiverTier] = dataclasses.field(default_factory=set)
    granted_at: dict[DiverTier, int] = dataclasses.field(
        default_factory=dict,
    )
    granted_via: dict[DiverTier, str] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class DiverCertification:
    _certs: dict[str, _PlayerCerts] = dataclasses.field(
        default_factory=dict,
    )

    def _ensure(self, player_id: str) -> _PlayerCerts:
        rec = self._certs.get(player_id)
        if rec is None:
            rec = _PlayerCerts(player_id=player_id)
            self._certs[player_id] = rec
        return rec

    def grant(
        self, *, player_id: str,
        tier: DiverTier,
        source: str,
        now_seconds: int,
    ) -> CertGrant:
        if not player_id or not source:
            return CertGrant(False, reason="bad ids")
        if tier not in _TIER_DEPTH_CEILING:
            return CertGrant(False, reason="unknown tier")
        rec = self._ensure(player_id)
        if tier in rec.tiers:
            return CertGrant(False, reason="already granted")
        rec.tiers.add(tier)
        rec.granted_at[tier] = now_seconds
        rec.granted_via[tier] = source
        return CertGrant(accepted=True, tier=tier, source=source)

    def has_cert(
        self, *, player_id: str, tier: DiverTier,
    ) -> bool:
        rec = self._certs.get(player_id)
        if rec is None:
            return False
        return tier in rec.tiers

    def max_certified_depth(self, *, player_id: str) -> int:
        rec = self._certs.get(player_id)
        if rec is None:
            return 0
        if not rec.tiers:
            return 0
        return max(_TIER_DEPTH_CEILING[t] for t in rec.tiers)

    def can_descend_to(
        self, *, player_id: str, depth_yalms: int,
    ) -> bool:
        if depth_yalms < 0:
            return False
        return depth_yalms <= self.max_certified_depth(
            player_id=player_id,
        )

    def required_tier_for(
        self, *, depth_yalms: int,
    ) -> t.Optional[DiverTier]:
        if depth_yalms < 0:
            return None
        for tier in _TIER_ORDER:
            if depth_yalms <= _TIER_DEPTH_CEILING[tier]:
                return tier
        return DiverTier.ABYSS_PERMIT


__all__ = [
    "DiverTier", "CertGrant", "DiverCertification",
]
