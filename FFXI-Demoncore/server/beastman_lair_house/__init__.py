"""Beastman lair house — beastman-side Mog House equivalent.

Each beastman PLAYER gets a LAIR, instanced to them. Lairs come
in TIERS (BURROW → DEN → STRONGHOLD → FORTRESS) that gate
storage capacity, trophy slots, and crafting bench unlock.

A lair has a RACE THEME baked in at creation (matches the
player's race), which tints décor and unlocks race-specific
furniture sets:
  Yagudo - feathered nests, eggshell shrines
  Quadav - mineral plinths, slate altars
  Lamia  - tidepool basins, coral arches
  Orc    - bone-piles, banner walls

Players can:
  - place_furniture (counts vs decor_capacity)
  - mount_trophy (NM kills, raid loot - counts vs trophy_slots)
  - upgrade_tier (one tier at a time, gold + reputation cost)
  - garden (per-tier plot count; harvest ticks)

Public surface
--------------
    LairTier enum     BURROW / DEN / STRONGHOLD / FORTRESS
    LairTheme enum    YAGUDO / QUADAV / LAMIA / ORC
    Furniture dataclass
    Trophy dataclass
    Lair dataclass
    UpgradeResult / PlaceResult / MountResult dataclasses
    BeastmanLairHouse
        .open_lair(player_id, race)
        .place_furniture(player_id, item_id, slots_used)
        .mount_trophy(player_id, trophy_id, source)
        .upgrade_tier(player_id, gold_paid, rep_paid)
        .lair_summary(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class LairTier(str, enum.Enum):
    BURROW = "burrow"
    DEN = "den"
    STRONGHOLD = "stronghold"
    FORTRESS = "fortress"


class LairTheme(str, enum.Enum):
    YAGUDO = "yagudo_feather"
    QUADAV = "quadav_stone"
    LAMIA = "lamia_tidepool"
    ORC = "orc_bone"


_TIER_ORDER: list[LairTier] = [
    LairTier.BURROW,
    LairTier.DEN,
    LairTier.STRONGHOLD,
    LairTier.FORTRESS,
]


_TIER_DECOR_CAPACITY: dict[LairTier, int] = {
    LairTier.BURROW: 6,
    LairTier.DEN: 12,
    LairTier.STRONGHOLD: 24,
    LairTier.FORTRESS: 40,
}


_TIER_TROPHY_SLOTS: dict[LairTier, int] = {
    LairTier.BURROW: 1,
    LairTier.DEN: 3,
    LairTier.STRONGHOLD: 6,
    LairTier.FORTRESS: 10,
}


_TIER_GARDEN_PLOTS: dict[LairTier, int] = {
    LairTier.BURROW: 0,
    LairTier.DEN: 2,
    LairTier.STRONGHOLD: 4,
    LairTier.FORTRESS: 8,
}


_UPGRADE_COSTS: dict[LairTier, tuple[int, int]] = {
    # next_tier: (gold, reputation)
    LairTier.DEN: (5_000, 200),
    LairTier.STRONGHOLD: (50_000, 1_000),
    LairTier.FORTRESS: (300_000, 5_000),
}


_THEME_FOR_RACE: dict[BeastmanRace, LairTheme] = {
    BeastmanRace.YAGUDO: LairTheme.YAGUDO,
    BeastmanRace.QUADAV: LairTheme.QUADAV,
    BeastmanRace.LAMIA: LairTheme.LAMIA,
    BeastmanRace.ORC: LairTheme.ORC,
}


@dataclasses.dataclass(frozen=True)
class Furniture:
    item_id: str
    slots_used: int


@dataclasses.dataclass(frozen=True)
class Trophy:
    trophy_id: str
    source: str


@dataclasses.dataclass
class Lair:
    player_id: str
    race: BeastmanRace
    theme: LairTheme
    tier: LairTier = LairTier.BURROW
    furniture: list[Furniture] = dataclasses.field(default_factory=list)
    trophies: list[Trophy] = dataclasses.field(default_factory=list)
    decor_used: int = 0


@dataclasses.dataclass(frozen=True)
class PlaceResult:
    accepted: bool
    decor_used_total: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class MountResult:
    accepted: bool
    trophies_total: int
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class UpgradeResult:
    accepted: bool
    new_tier: LairTier
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class LairSummary:
    player_id: str
    tier: LairTier
    theme: LairTheme
    decor_used: int
    decor_capacity: int
    trophies: int
    trophy_slots: int
    garden_plots: int


@dataclasses.dataclass
class BeastmanLairHouse:
    _lairs: dict[str, Lair] = dataclasses.field(default_factory=dict)

    def open_lair(
        self, *, player_id: str, race: BeastmanRace,
    ) -> t.Optional[Lair]:
        if player_id in self._lairs:
            return None
        if race not in _THEME_FOR_RACE:
            return None
        lair = Lair(
            player_id=player_id, race=race,
            theme=_THEME_FOR_RACE[race],
        )
        self._lairs[player_id] = lair
        return lair

    def get_lair(self, player_id: str) -> t.Optional[Lair]:
        return self._lairs.get(player_id)

    def place_furniture(
        self, *, player_id: str,
        item_id: str, slots_used: int,
    ) -> PlaceResult:
        lair = self._lairs.get(player_id)
        if lair is None:
            return PlaceResult(False, 0, reason="no lair")
        if slots_used <= 0:
            return PlaceResult(
                False, lair.decor_used,
                reason="non-positive slot count",
            )
        cap = _TIER_DECOR_CAPACITY[lair.tier]
        if lair.decor_used + slots_used > cap:
            return PlaceResult(
                False, lair.decor_used,
                reason="decor capacity exceeded",
            )
        if any(f.item_id == item_id for f in lair.furniture):
            return PlaceResult(
                False, lair.decor_used,
                reason="furniture already placed",
            )
        lair.furniture.append(
            Furniture(item_id=item_id, slots_used=slots_used),
        )
        lair.decor_used += slots_used
        return PlaceResult(
            accepted=True, decor_used_total=lair.decor_used,
        )

    def mount_trophy(
        self, *, player_id: str,
        trophy_id: str, source: str,
    ) -> MountResult:
        lair = self._lairs.get(player_id)
        if lair is None:
            return MountResult(False, 0, reason="no lair")
        slots = _TIER_TROPHY_SLOTS[lair.tier]
        if len(lair.trophies) >= slots:
            return MountResult(
                False, len(lair.trophies),
                reason="trophy slots full",
            )
        if any(tr.trophy_id == trophy_id for tr in lair.trophies):
            return MountResult(
                False, len(lair.trophies),
                reason="trophy already mounted",
            )
        lair.trophies.append(
            Trophy(trophy_id=trophy_id, source=source),
        )
        return MountResult(
            accepted=True, trophies_total=len(lair.trophies),
        )

    def upgrade_tier(
        self, *, player_id: str,
        gold_paid: int, rep_paid: int,
    ) -> UpgradeResult:
        lair = self._lairs.get(player_id)
        if lair is None:
            return UpgradeResult(
                False, LairTier.BURROW, reason="no lair",
            )
        idx = _TIER_ORDER.index(lair.tier)
        if idx >= len(_TIER_ORDER) - 1:
            return UpgradeResult(
                False, lair.tier, reason="already at max tier",
            )
        next_tier = _TIER_ORDER[idx + 1]
        gold_req, rep_req = _UPGRADE_COSTS[next_tier]
        if gold_paid < gold_req:
            return UpgradeResult(
                False, lair.tier, reason="insufficient gold",
            )
        if rep_paid < rep_req:
            return UpgradeResult(
                False, lair.tier, reason="insufficient reputation",
            )
        lair.tier = next_tier
        return UpgradeResult(accepted=True, new_tier=next_tier)

    def lair_summary(
        self, *, player_id: str,
    ) -> t.Optional[LairSummary]:
        lair = self._lairs.get(player_id)
        if lair is None:
            return None
        return LairSummary(
            player_id=player_id,
            tier=lair.tier,
            theme=lair.theme,
            decor_used=lair.decor_used,
            decor_capacity=_TIER_DECOR_CAPACITY[lair.tier],
            trophies=len(lair.trophies),
            trophy_slots=_TIER_TROPHY_SLOTS[lair.tier],
            garden_plots=_TIER_GARDEN_PLOTS[lair.tier],
        )

    def total_lairs(self) -> int:
        return len(self._lairs)


__all__ = [
    "LairTier", "LairTheme",
    "Furniture", "Trophy", "Lair",
    "PlaceResult", "MountResult", "UpgradeResult",
    "LairSummary", "BeastmanLairHouse",
]
