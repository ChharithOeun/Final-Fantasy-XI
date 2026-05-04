"""Beastman fellowship NPC — pre-Trust solo adventuring companion.

The beastman analog to FFXI's Adventuring Fellow — a single
named NPC companion bound to your character. Unlike Trusts
(temporary instanced spirits), a fellowship NPC PERSISTS, has
its own job, gear, name, level, and bond points that grow with
shared experience. Only ONE fellowship NPC per player.

Each fellowship has a personality archetype (BERSERKER /
HEALER / TRICKSTER / SCHOLAR), a cap-tier level (FAITHFUL /
TRUSTED / STAUNCH / SWORN) gated by BOND POINTS earned alongside
the player. Higher tiers unlock JA-level commands (e.g. trigger
a heal on demand, request a focus-fire callout).

Public surface
--------------
    PersonalityArchetype enum
    FellowshipTier enum   FAITHFUL / TRUSTED / STAUNCH / SWORN
    Fellowship dataclass
    BeastmanFellowshipNpc
        .summon_fellow(player_id, name, archetype)
        .grant_bond(player_id, points)
        .promote_if_eligible(player_id)
        .dismiss(player_id)
        .fellow_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PersonalityArchetype(str, enum.Enum):
    BERSERKER = "berserker"
    HEALER = "healer"
    TRICKSTER = "trickster"
    SCHOLAR = "scholar"


class FellowshipTier(str, enum.Enum):
    FAITHFUL = "faithful"
    TRUSTED = "trusted"
    STAUNCH = "staunch"
    SWORN = "sworn"


_TIER_ORDER: list[FellowshipTier] = [
    FellowshipTier.FAITHFUL,
    FellowshipTier.TRUSTED,
    FellowshipTier.STAUNCH,
    FellowshipTier.SWORN,
]


_TIER_BOND_FLOOR: dict[FellowshipTier, int] = {
    FellowshipTier.FAITHFUL: 0,
    FellowshipTier.TRUSTED: 500,
    FellowshipTier.STAUNCH: 2_000,
    FellowshipTier.SWORN: 8_000,
}


@dataclasses.dataclass
class Fellowship:
    player_id: str
    name: str
    archetype: PersonalityArchetype
    bond_points: int = 0
    tier: FellowshipTier = FellowshipTier.FAITHFUL


@dataclasses.dataclass(frozen=True)
class SummonResult:
    accepted: bool
    name: str = ""
    archetype: t.Optional[PersonalityArchetype] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class BondResult:
    accepted: bool
    bond_points: int = 0
    new_tier: FellowshipTier = FellowshipTier.FAITHFUL
    promoted: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanFellowshipNpc:
    _fellows: dict[str, Fellowship] = dataclasses.field(
        default_factory=dict,
    )

    def summon_fellow(
        self, *, player_id: str,
        name: str,
        archetype: PersonalityArchetype,
    ) -> SummonResult:
        if not name:
            return SummonResult(False, reason="empty name")
        if player_id in self._fellows:
            return SummonResult(
                False, reason="fellow already summoned",
            )
        self._fellows[player_id] = Fellowship(
            player_id=player_id,
            name=name,
            archetype=archetype,
        )
        return SummonResult(
            accepted=True, name=name, archetype=archetype,
        )

    def grant_bond(
        self, *, player_id: str, points: int,
    ) -> BondResult:
        f = self._fellows.get(player_id)
        if f is None:
            return BondResult(
                False, reason="no fellow",
            )
        if points <= 0:
            return BondResult(
                False, bond_points=f.bond_points,
                new_tier=f.tier,
                reason="non-positive points",
            )
        f.bond_points += points
        return BondResult(
            accepted=True,
            bond_points=f.bond_points,
            new_tier=f.tier,
            promoted=False,
        )

    def promote_if_eligible(
        self, *, player_id: str,
    ) -> BondResult:
        f = self._fellows.get(player_id)
        if f is None:
            return BondResult(
                False, reason="no fellow",
            )
        idx = _TIER_ORDER.index(f.tier)
        promoted = False
        while idx < len(_TIER_ORDER) - 1:
            next_tier = _TIER_ORDER[idx + 1]
            if f.bond_points >= _TIER_BOND_FLOOR[next_tier]:
                f.tier = next_tier
                idx += 1
                promoted = True
            else:
                break
        return BondResult(
            accepted=True,
            bond_points=f.bond_points,
            new_tier=f.tier,
            promoted=promoted,
        )

    def dismiss(
        self, *, player_id: str,
    ) -> bool:
        if player_id not in self._fellows:
            return False
        del self._fellows[player_id]
        return True

    def fellow_for(
        self, *, player_id: str,
    ) -> t.Optional[Fellowship]:
        return self._fellows.get(player_id)

    def total_fellows(self) -> int:
        return len(self._fellows)


__all__ = [
    "PersonalityArchetype", "FellowshipTier",
    "Fellowship", "SummonResult", "BondResult",
    "BeastmanFellowshipNpc",
]
