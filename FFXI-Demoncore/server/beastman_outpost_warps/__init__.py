"""Beastman outpost warps — outpost teleport network for shadow zones.

Beastman cities project OUTPOSTS into nearby contested zones; once
a player has UNLOCKED an outpost (via questline + standing
threshold), they can warp there from any major beastman city for
a small gil + standing fee.

Network shape:
  - 4 home cities (Oztroja / Palborough / Halvung / Arrapago)
  - Each city has a roster of outposts in adjacent zones
  - Warp prices scale by ZONE_DISTANCE (1-5 hops) and shrink with
    higher REPUTATION_TIER (NEUTRAL / FRIENDLY / TRUSTED / KIN)

Public surface
--------------
    HomeCity enum
    ReputationTier enum
    Outpost dataclass
    BeastmanOutpostWarps
        .register_outpost(outpost_id, zone_id, home_city,
                          distance, base_price)
        .unlock(player_id, outpost_id)
        .warp(player_id, outpost_id, gil_held, reputation)
        .price_for(outpost_id, reputation)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HomeCity(str, enum.Enum):
    OZTROJA = "oztroja"
    PALBOROUGH = "palborough"
    HALVUNG = "halvung"
    ARRAPAGO = "arrapago"


class ReputationTier(str, enum.Enum):
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    TRUSTED = "trusted"
    KIN = "kin"


# Discount applied to base price per reputation tier
_TIER_DISCOUNT_PCT: dict[ReputationTier, int] = {
    ReputationTier.NEUTRAL: 0,
    ReputationTier.FRIENDLY: 10,
    ReputationTier.TRUSTED: 25,
    ReputationTier.KIN: 50,
}


@dataclasses.dataclass(frozen=True)
class Outpost:
    outpost_id: str
    zone_id: str
    home_city: HomeCity
    distance: int          # 1..5 hops
    base_price: int


@dataclasses.dataclass(frozen=True)
class WarpResult:
    accepted: bool
    outpost_id: str
    gil_charged: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanOutpostWarps:
    _outposts: dict[str, Outpost] = dataclasses.field(
        default_factory=dict,
    )
    _unlocked: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)

    def register_outpost(
        self, *, outpost_id: str,
        zone_id: str,
        home_city: HomeCity,
        distance: int,
        base_price: int,
    ) -> t.Optional[Outpost]:
        if outpost_id in self._outposts:
            return None
        if not (1 <= distance <= 5):
            return None
        if base_price < 0:
            return None
        if not zone_id:
            return None
        op = Outpost(
            outpost_id=outpost_id, zone_id=zone_id,
            home_city=home_city,
            distance=distance,
            base_price=base_price,
        )
        self._outposts[outpost_id] = op
        return op

    def unlock(
        self, *, player_id: str, outpost_id: str,
    ) -> bool:
        if outpost_id not in self._outposts:
            return False
        unlocked = self._unlocked.setdefault(player_id, set())
        if outpost_id in unlocked:
            return False
        unlocked.add(outpost_id)
        return True

    def is_unlocked(
        self, *, player_id: str, outpost_id: str,
    ) -> bool:
        return outpost_id in self._unlocked.get(player_id, set())

    def price_for(
        self, *, outpost_id: str,
        reputation: ReputationTier,
    ) -> t.Optional[int]:
        op = self._outposts.get(outpost_id)
        if op is None:
            return None
        # Distance compounds the base price
        gross = op.base_price * op.distance
        discount = _TIER_DISCOUNT_PCT[reputation]
        # discount is whole percent off
        return gross - (gross * discount) // 100

    def warp(
        self, *, player_id: str,
        outpost_id: str,
        gil_held: int,
        reputation: ReputationTier,
    ) -> WarpResult:
        op = self._outposts.get(outpost_id)
        if op is None:
            return WarpResult(
                False, outpost_id, reason="unknown outpost",
            )
        if not self.is_unlocked(
            player_id=player_id, outpost_id=outpost_id,
        ):
            return WarpResult(
                False, outpost_id, reason="not unlocked",
            )
        price = self.price_for(
            outpost_id=outpost_id, reputation=reputation,
        )
        if price is None:
            return WarpResult(
                False, outpost_id, reason="no price",
            )
        if gil_held < price:
            return WarpResult(
                False, outpost_id, gil_charged=price,
                reason="insufficient gil",
            )
        return WarpResult(
            accepted=True, outpost_id=outpost_id,
            gil_charged=price,
        )

    def total_outposts(self) -> int:
        return len(self._outposts)


__all__ = [
    "HomeCity", "ReputationTier",
    "Outpost", "WarpResult",
    "BeastmanOutpostWarps",
]
