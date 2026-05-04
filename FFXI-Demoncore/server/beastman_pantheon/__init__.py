"""Beastman pantheon — god + hero + goblin neutrality.

The four playable beastman races worship a single shared god,
SHATHAR THE OUTCAST, who was cast out of Altana's pantheon
before the Crystal War. He's the patron of the broken, the
remembered, the unclaimed. Worship is mediated through a
SHRINE PILGRIMAGE quest chain.

Beastmen also collectively venerate a HERO — the one who led
the assault on the Tavnazian Stronghold during the Great War
and held the line until the Crystal Marshals broke. They do
not say his name lightly. Within game text he is referenced
as THE TAVNAZIAN HERO; players uncover his actual name only
after specific lore quests.

GOBLINS are explicitly NEUTRAL beastmen — they trade with
every nation, every race, even outlaws. The goblin merchant
caste is unaffiliated with Shathar's worship, and never enters
a pilgrimage. Goblins are, in effect, the cosmopolitan side of
the beastmen world.

Public surface
--------------
    DeityKind enum    SHATHAR / GOBLIN_NEUTRAL
    HeroKind enum     THE_TAVNAZIAN_HERO
    PilgrimageStage enum
    DeityProfile dataclass
    BeastmanPantheon
        .pledge_to_shathar(player_id, race)
        .advance_pilgrimage_stage(player_id, stage)
        .praise_tavnazian_hero(player_id) -> int (count)
        .mark_goblin_neutral_trade(buyer_id, seller_id)
        .is_goblin_neutral(npc_id) -> bool
        .declare_goblin(npc_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class DeityKind(str, enum.Enum):
    SHATHAR = "shathar"
    GOBLIN_NEUTRAL = "goblin_neutral"


class HeroKind(str, enum.Enum):
    THE_TAVNAZIAN_HERO = "the_tavnazian_hero"


class PilgrimageStage(str, enum.Enum):
    OUTCAST_TEMPLE = "outcast_temple"
    HOLLOW_THRONE = "hollow_throne"
    BROKEN_VEIL = "broken_veil"
    SHATHAR_VOICE = "shathar_voice"


_PILGRIMAGE_ORDER: tuple[PilgrimageStage, ...] = tuple(
    PilgrimageStage,
)


@dataclasses.dataclass
class _Devotion:
    player_id: str
    race: BeastmanRace
    deity: DeityKind = DeityKind.SHATHAR
    pilgrimage_progress: list[PilgrimageStage] = (
        dataclasses.field(default_factory=list)
    )
    times_praised_hero: int = 0


@dataclasses.dataclass(frozen=True)
class PilgrimageResult:
    accepted: bool
    stage: PilgrimageStage
    is_complete: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BeastmanPantheon:
    _devotions: dict[str, _Devotion] = dataclasses.field(
        default_factory=dict,
    )
    _goblin_npcs: set[str] = dataclasses.field(
        default_factory=set,
    )
    # buyer_id -> set of goblin merchant ids dealt with
    _goblin_trades: dict[
        str, set[str],
    ] = dataclasses.field(default_factory=dict)

    def pledge_to_shathar(
        self, *, player_id: str,
        race: BeastmanRace,
    ) -> bool:
        if player_id in self._devotions:
            return False
        self._devotions[player_id] = _Devotion(
            player_id=player_id, race=race,
            deity=DeityKind.SHATHAR,
        )
        return True

    def is_devotee(
        self, *, player_id: str,
    ) -> bool:
        return player_id in self._devotions

    def advance_pilgrimage_stage(
        self, *, player_id: str,
        stage: PilgrimageStage,
    ) -> PilgrimageResult:
        d = self._devotions.get(player_id)
        if d is None:
            return PilgrimageResult(
                False, stage=stage, is_complete=False,
                reason="no devotion",
            )
        order = _PILGRIMAGE_ORDER
        next_idx = len(d.pilgrimage_progress)
        if next_idx >= len(order):
            return PilgrimageResult(
                False, stage=stage, is_complete=True,
                reason="already complete",
            )
        expected = order[next_idx]
        if stage != expected:
            return PilgrimageResult(
                False, stage=stage, is_complete=False,
                reason=f"out of order; expected {expected.value}",
            )
        d.pilgrimage_progress.append(stage)
        is_done = (
            len(d.pilgrimage_progress) == len(order)
        )
        return PilgrimageResult(
            accepted=True, stage=stage,
            is_complete=is_done,
        )

    def pilgrimage_complete(
        self, *, player_id: str,
    ) -> bool:
        d = self._devotions.get(player_id)
        if d is None:
            return False
        return (
            len(d.pilgrimage_progress)
            == len(_PILGRIMAGE_ORDER)
        )

    def praise_tavnazian_hero(
        self, *, player_id: str,
    ) -> t.Optional[int]:
        d = self._devotions.get(player_id)
        if d is None:
            return None
        d.times_praised_hero += 1
        return d.times_praised_hero

    def times_hero_praised(
        self, *, player_id: str,
    ) -> int:
        d = self._devotions.get(player_id)
        return d.times_praised_hero if d else 0

    def declare_goblin(
        self, *, npc_id: str,
    ) -> bool:
        if not npc_id:
            return False
        if npc_id in self._goblin_npcs:
            return False
        self._goblin_npcs.add(npc_id)
        return True

    def is_goblin_neutral(
        self, *, npc_id: str,
    ) -> bool:
        return npc_id in self._goblin_npcs

    def mark_goblin_neutral_trade(
        self, *, buyer_id: str,
        seller_id: str,
    ) -> bool:
        if seller_id not in self._goblin_npcs:
            return False
        if buyer_id == seller_id:
            return False
        s = self._goblin_trades.setdefault(
            buyer_id, set(),
        )
        if seller_id in s:
            return False
        s.add(seller_id)
        return True

    def goblin_partners_for(
        self, *, buyer_id: str,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(self._goblin_trades.get(buyer_id, set()))
        )

    def total_devotees(self) -> int:
        return len(self._devotions)

    def total_goblin_npcs(self) -> int:
        return len(self._goblin_npcs)


__all__ = [
    "DeityKind", "HeroKind", "PilgrimageStage",
    "PilgrimageResult",
    "BeastmanPantheon",
]
