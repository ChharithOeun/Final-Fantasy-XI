"""Water-skin — refillable container for thirst restoration.

A leather pouch carrying water. The wayfarer's standard
travel kit. 4 quality tiers determine capacity (in
"sips") and refill rate when at a SPRING. Each sip
restores 10 thirst.

Tiers:
    BASIC_LEATHER     6 sips, 1 sip per refill-second
    OILED_LEATHER    10 sips, 1 sip/sec
    BEEHIVE_BLADDER  16 sips, 2 sips/sec
    DRAGONHIDE       24 sips, 3 sips/sec  (kept-warm in cold,
                                           kept-cool in heat)

A water-skin can be filled only at a SPRING node (or any
"clean_water" source ref). Drinking is one sip, restoring
the configured thirst amount.

Public surface
--------------
    SkinTier enum
    WaterSkin dataclass (mutable)
    WaterSkinRegistry
        .craft(skin_id, owner_id, tier, crafted_at) -> bool
        .refill(skin_id, source_kind, dt_seconds) -> int
        .drink(skin_id) -> int    (thirst restored)
        .level(skin_id) -> int
        .capacity(skin_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SkinTier(str, enum.Enum):
    BASIC_LEATHER = "basic_leather"
    OILED_LEATHER = "oiled_leather"
    BEEHIVE_BLADDER = "beehive_bladder"
    DRAGONHIDE = "dragonhide"


_TIER_PROFILE = {
    SkinTier.BASIC_LEATHER: (6, 1),
    SkinTier.OILED_LEATHER: (10, 1),
    SkinTier.BEEHIVE_BLADDER: (16, 2),
    SkinTier.DRAGONHIDE: (24, 3),
}


_THIRST_PER_SIP = 10
_VALID_SOURCES = {"spring", "clean_water"}


@dataclasses.dataclass
class WaterSkin:
    skin_id: str
    owner_id: str
    tier: SkinTier
    sips_remaining: int
    crafted_at: int


@dataclasses.dataclass
class WaterSkinRegistry:
    _skins: dict[str, WaterSkin] = dataclasses.field(
        default_factory=dict,
    )

    def craft(
        self, *, skin_id: str, owner_id: str,
        tier: SkinTier, crafted_at: int,
    ) -> bool:
        if not skin_id or not owner_id:
            return False
        if skin_id in self._skins:
            return False
        cap, _ = _TIER_PROFILE[tier]
        self._skins[skin_id] = WaterSkin(
            skin_id=skin_id, owner_id=owner_id, tier=tier,
            sips_remaining=cap, crafted_at=crafted_at,
        )
        return True

    def refill(
        self, *, skin_id: str, source_kind: str,
        dt_seconds: int,
    ) -> int:
        s = self._skins.get(skin_id)
        if s is None:
            return 0
        if source_kind not in _VALID_SOURCES:
            return s.sips_remaining
        if dt_seconds <= 0:
            return s.sips_remaining
        cap, rate = _TIER_PROFILE[s.tier]
        added = rate * dt_seconds
        s.sips_remaining = min(cap, s.sips_remaining + added)
        return s.sips_remaining

    def drink(self, *, skin_id: str) -> int:
        s = self._skins.get(skin_id)
        if s is None:
            return 0
        if s.sips_remaining <= 0:
            return 0
        s.sips_remaining -= 1
        return _THIRST_PER_SIP

    def level(self, *, skin_id: str) -> int:
        s = self._skins.get(skin_id)
        return s.sips_remaining if s else 0

    def capacity(self, *, skin_id: str) -> int:
        s = self._skins.get(skin_id)
        if s is None:
            return 0
        cap, _ = _TIER_PROFILE[s.tier]
        return cap

    def total_skins(self) -> int:
        return len(self._skins)


__all__ = ["SkinTier", "WaterSkin", "WaterSkinRegistry"]
