"""Bedroll quality — what you sleep on shapes how you wake.

A traveler dropping a bedroll on cold tundra wants down or
fur, not the cheap straw mat that suits a balmy meadow.
Each bedroll has a base sleep_quality_pct (used by
sleep_dream's reward roll) plus a climate fit profile so
the *same* bedroll behaves differently in the wrong place.

Continuing the gear↔weather pattern from insulation_clothing:
sleeping in fur on a hot desert night actually *hurts*
quality (the player overheats), so picking gear for the
biome matters.

Bedroll tiers
-------------
    STRAW  base 30  — disposable, fine in mild climates
    WOOL   base 55  — warm-leaning all-rounder
    DOWN   base 70  — soft and warm, fragile in damp
    FUR    base 80  — luxurious, miserable in heat

Each tier carries a list of preferred climates and a list
of ill-suited climates. A match adds +10 quality, a
mismatch subtracts 20. The climate values match the keys
used by seasonal_clock / weather modules ("temperate",
"arctic", "desert", "rainforest", "alpine").

Each bedroll has finite durability (uses_remaining). Sleeping
on it consumes one use; once exhausted it can't be slept on
again until repaired.

Public surface
--------------
    BedrollTier enum
    BedrollProfile dataclass (frozen) — base + climate prefs
    Bedroll dataclass (mutable) — runtime instance
    BedrollRegistry
        .craft(bedroll_id, owner_id, tier, crafted_at) -> bool
        .effective_quality(bedroll_id, climate) -> int
        .use(bedroll_id) -> bool      (consumes 1 durability)
        .repair(bedroll_id, units) -> int
        .uses_remaining(bedroll_id) -> int
        .profile_for(tier) -> BedrollProfile
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class BedrollTier(str, enum.Enum):
    STRAW = "straw"
    WOOL = "wool"
    DOWN = "down"
    FUR = "fur"


@dataclasses.dataclass(frozen=True)
class BedrollProfile:
    tier: BedrollTier
    base_quality_pct: int
    max_uses: int
    preferred_climates: tuple[str, ...]
    poor_climates: tuple[str, ...]


# Tuned so DOWN and FUR shine where they should, suffer
# where they shouldn't. STRAW is the cheap-and-cheerful
# fallback you toss when you need a bed and don't have one.
_PROFILES: dict[BedrollTier, BedrollProfile] = {
    BedrollTier.STRAW: BedrollProfile(
        tier=BedrollTier.STRAW,
        base_quality_pct=30,
        max_uses=3,
        preferred_climates=("temperate",),
        poor_climates=("arctic",),
    ),
    BedrollTier.WOOL: BedrollProfile(
        tier=BedrollTier.WOOL,
        base_quality_pct=55,
        max_uses=10,
        preferred_climates=("alpine", "temperate"),
        poor_climates=("desert",),
    ),
    BedrollTier.DOWN: BedrollProfile(
        tier=BedrollTier.DOWN,
        base_quality_pct=70,
        max_uses=12,
        preferred_climates=("temperate", "alpine"),
        poor_climates=("rainforest",),
    ),
    BedrollTier.FUR: BedrollProfile(
        tier=BedrollTier.FUR,
        base_quality_pct=80,
        max_uses=20,
        preferred_climates=("arctic", "alpine"),
        poor_climates=("desert", "rainforest"),
    ),
}

_PREFERRED_BONUS = 10
_POOR_PENALTY = 20
_MAX_QUALITY = 100
_MIN_QUALITY = 0


@dataclasses.dataclass
class Bedroll:
    bedroll_id: str
    owner_id: str
    tier: BedrollTier
    crafted_at: int
    uses_remaining: int


@dataclasses.dataclass
class BedrollRegistry:
    _bedrolls: dict[str, Bedroll] = dataclasses.field(
        default_factory=dict,
    )

    def craft(
        self, *, bedroll_id: str, owner_id: str,
        tier: BedrollTier, crafted_at: int,
    ) -> bool:
        if not bedroll_id or not owner_id:
            return False
        if bedroll_id in self._bedrolls:
            return False
        prof = _PROFILES[tier]
        self._bedrolls[bedroll_id] = Bedroll(
            bedroll_id=bedroll_id, owner_id=owner_id,
            tier=tier, crafted_at=crafted_at,
            uses_remaining=prof.max_uses,
        )
        return True

    def profile_for(self, *, tier: BedrollTier) -> BedrollProfile:
        return _PROFILES[tier]

    def effective_quality(
        self, *, bedroll_id: str, climate: str,
    ) -> int:
        b = self._bedrolls.get(bedroll_id)
        if b is None:
            return 0
        # exhausted bedrolls give nothing — you can't sleep on
        # a torn-up mat, so quality should reflect that.
        if b.uses_remaining <= 0:
            return 0
        prof = _PROFILES[b.tier]
        q = prof.base_quality_pct
        c = climate.lower()
        if c in prof.preferred_climates:
            q += _PREFERRED_BONUS
        if c in prof.poor_climates:
            q -= _POOR_PENALTY
        if q > _MAX_QUALITY:
            q = _MAX_QUALITY
        if q < _MIN_QUALITY:
            q = _MIN_QUALITY
        return q

    def use(self, *, bedroll_id: str) -> bool:
        b = self._bedrolls.get(bedroll_id)
        if b is None:
            return False
        if b.uses_remaining <= 0:
            return False
        b.uses_remaining -= 1
        return True

    def repair(self, *, bedroll_id: str, units: int) -> int:
        b = self._bedrolls.get(bedroll_id)
        if b is None:
            return 0
        if units <= 0:
            return b.uses_remaining
        prof = _PROFILES[b.tier]
        new_val = b.uses_remaining + units
        if new_val > prof.max_uses:
            new_val = prof.max_uses
        b.uses_remaining = new_val
        return b.uses_remaining

    def uses_remaining(self, *, bedroll_id: str) -> int:
        b = self._bedrolls.get(bedroll_id)
        if b is None:
            return 0
        return b.uses_remaining

    def total_bedrolls(self) -> int:
        return len(self._bedrolls)


__all__ = [
    "BedrollTier", "BedrollProfile", "Bedroll",
    "BedrollRegistry",
]
