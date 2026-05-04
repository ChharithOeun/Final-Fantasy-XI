"""Beastman seal collection — seal trade-in for beastman AF gear.

The beastman analog to FFXI's AF seal grouping. Each piece of
beastman ARTIFACT GEAR is unlocked by trading in a count of
SEALS (head/body/hands/legs/feet) earned from kills against the
opposite faction.

Seals come in two ranks:
  CRESTED   - drop from regular hume army units
  ASCENDED  - drop from named hume officers

Each AF piece has a recipe: e.g., "5 crested head seals + 1
ascended head seal" → unlocks the head AF piece.

Public surface
--------------
    SealSlot enum     HEAD / BODY / HANDS / LEGS / FEET
    SealRank enum     CRESTED / ASCENDED
    AfRecipe dataclass
    BeastmanSealCollection
        .grant_seal(player_id, slot, rank, count)
        .balance(player_id, slot, rank)
        .register_recipe(piece_id, slot, crested_cost, ascended_cost)
        .redeem(player_id, piece_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SealSlot(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"


class SealRank(str, enum.Enum):
    CRESTED = "crested"
    ASCENDED = "ascended"


@dataclasses.dataclass(frozen=True)
class AfRecipe:
    piece_id: str
    slot: SealSlot
    crested_cost: int
    ascended_cost: int


@dataclasses.dataclass(frozen=True)
class GrantResult:
    accepted: bool
    new_balance: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class RedeemResult:
    accepted: bool
    piece_id: str
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanSealCollection:
    _balances: dict[
        tuple[str, SealSlot, SealRank], int,
    ] = dataclasses.field(default_factory=dict)
    _recipes: dict[str, AfRecipe] = dataclasses.field(
        default_factory=dict,
    )
    _redeemed: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def grant_seal(
        self, *, player_id: str,
        slot: SealSlot, rank: SealRank,
        count: int,
    ) -> GrantResult:
        if count <= 0:
            return GrantResult(
                False, reason="non-positive count",
            )
        key = (player_id, slot, rank)
        new = self._balances.get(key, 0) + count
        self._balances[key] = new
        return GrantResult(accepted=True, new_balance=new)

    def balance(
        self, *, player_id: str,
        slot: SealSlot, rank: SealRank,
    ) -> int:
        return self._balances.get((player_id, slot, rank), 0)

    def register_recipe(
        self, *, piece_id: str,
        slot: SealSlot,
        crested_cost: int,
        ascended_cost: int,
    ) -> t.Optional[AfRecipe]:
        if piece_id in self._recipes:
            return None
        if crested_cost < 0 or ascended_cost < 0:
            return None
        if crested_cost == 0 and ascended_cost == 0:
            return None
        r = AfRecipe(
            piece_id=piece_id,
            slot=slot,
            crested_cost=crested_cost,
            ascended_cost=ascended_cost,
        )
        self._recipes[piece_id] = r
        return r

    def redeem(
        self, *, player_id: str, piece_id: str,
    ) -> RedeemResult:
        r = self._recipes.get(piece_id)
        if r is None:
            return RedeemResult(
                False, piece_id, reason="unknown recipe",
            )
        already = self._redeemed.get(player_id, set())
        if piece_id in already:
            return RedeemResult(
                False, piece_id, reason="already redeemed",
            )
        crested = self.balance(
            player_id=player_id, slot=r.slot,
            rank=SealRank.CRESTED,
        )
        ascended = self.balance(
            player_id=player_id, slot=r.slot,
            rank=SealRank.ASCENDED,
        )
        if crested < r.crested_cost:
            return RedeemResult(
                False, piece_id, reason="not enough crested seals",
            )
        if ascended < r.ascended_cost:
            return RedeemResult(
                False, piece_id, reason="not enough ascended seals",
            )
        # Consume seals
        self._balances[(player_id, r.slot, SealRank.CRESTED)] = (
            crested - r.crested_cost
        )
        self._balances[(player_id, r.slot, SealRank.ASCENDED)] = (
            ascended - r.ascended_cost
        )
        self._redeemed.setdefault(player_id, set()).add(piece_id)
        return RedeemResult(accepted=True, piece_id=piece_id)

    def has_redeemed(
        self, *, player_id: str, piece_id: str,
    ) -> bool:
        return piece_id in self._redeemed.get(player_id, set())

    def total_recipes(self) -> int:
        return len(self._recipes)


__all__ = [
    "SealSlot", "SealRank",
    "AfRecipe", "GrantResult", "RedeemResult",
    "BeastmanSealCollection",
]
