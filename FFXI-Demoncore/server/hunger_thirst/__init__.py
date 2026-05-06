"""Hunger & thirst — gauges that decay over time.

Both gauges run 0..100 (100 = sated, 0 = starving / parched).
Each tick, both decay at base rates that scale with player
activity (combat doubles thirst). At low levels, debuffs
apply:

   level >= 60     no penalty
   30 <= level < 60   PECKISH / PARCHED   (-5% regen)
   10 <= level < 30   HUNGRY / DRY        (-15% regen, -5% combat)
   level < 10         STARVING / DEHYDRATED (HP drain over time,
                       no regen)

Eat / drink calls add to the gauge, capped at 100.

Public surface
--------------
    NeedTier enum
    NeedState dataclass (mutable)
    HungerThirstEngine
        .register(player_id, started_at)
        .tick(player_id, dt_seconds, in_combat=False) -> NeedTier
        .eat(player_id, restore) -> int
        .drink(player_id, restore) -> int
        .hunger_for(player_id) -> int
        .thirst_for(player_id) -> int
        .tier_for(player_id) -> NeedTier
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NeedTier(str, enum.Enum):
    SATED = "sated"
    PECKISH = "peckish"
    HUNGRY = "hungry"
    STARVING = "starving"
    PARCHED = "parched"
    DRY = "dry"
    DEHYDRATED = "dehydrated"


# decay per second
_HUNGER_PER_SEC = 1   # full bar = 100 seconds
_THIRST_PER_SEC = 2   # thirst goes faster
_COMBAT_THIRST_MULT = 2


@dataclasses.dataclass
class NeedState:
    player_id: str
    hunger: int = 100
    thirst: int = 100


@dataclasses.dataclass
class HungerThirstEngine:
    _states: dict[str, NeedState] = dataclasses.field(
        default_factory=dict,
    )

    def register(
        self, *, player_id: str, started_at: int = 0,
    ) -> bool:
        if not player_id:
            return False
        if player_id in self._states:
            return False
        self._states[player_id] = NeedState(player_id=player_id)
        return True

    def tick(
        self, *, player_id: str, dt_seconds: int,
        in_combat: bool = False,
    ) -> NeedTier:
        s = self._states.get(player_id)
        if s is None:
            return NeedTier.SATED
        s.hunger = max(0, s.hunger - _HUNGER_PER_SEC * dt_seconds)
        thirst_rate = _THIRST_PER_SEC
        if in_combat:
            thirst_rate *= _COMBAT_THIRST_MULT
        s.thirst = max(0, s.thirst - thirst_rate * dt_seconds)
        return self.tier_for(player_id=player_id)

    def eat(
        self, *, player_id: str, restore: int,
    ) -> int:
        s = self._states.get(player_id)
        if s is None:
            return 0
        if restore < 0:
            return s.hunger
        s.hunger = min(100, s.hunger + restore)
        return s.hunger

    def drink(
        self, *, player_id: str, restore: int,
    ) -> int:
        s = self._states.get(player_id)
        if s is None:
            return 0
        if restore < 0:
            return s.thirst
        s.thirst = min(100, s.thirst + restore)
        return s.thirst

    def hunger_for(self, *, player_id: str) -> int:
        s = self._states.get(player_id)
        return s.hunger if s else 0

    def thirst_for(self, *, player_id: str) -> int:
        s = self._states.get(player_id)
        return s.thirst if s else 0

    def tier_for(self, *, player_id: str) -> NeedTier:
        s = self._states.get(player_id)
        if s is None:
            return NeedTier.SATED
        # thirst is more dangerous than hunger; report the worst
        thirst_tier = self._thirst_tier(s.thirst)
        hunger_tier = self._hunger_tier(s.hunger)
        # rank: lower number = more concerning
        order = {
            NeedTier.SATED: 0,
            NeedTier.PECKISH: 1, NeedTier.PARCHED: 1,
            NeedTier.HUNGRY: 2, NeedTier.DRY: 2,
            NeedTier.STARVING: 3, NeedTier.DEHYDRATED: 3,
        }
        if order[thirst_tier] >= order[hunger_tier]:
            return thirst_tier
        return hunger_tier

    def _hunger_tier(self, hunger: int) -> NeedTier:
        if hunger >= 60:
            return NeedTier.SATED
        if hunger >= 30:
            return NeedTier.PECKISH
        if hunger >= 10:
            return NeedTier.HUNGRY
        return NeedTier.STARVING

    def _thirst_tier(self, thirst: int) -> NeedTier:
        if thirst >= 60:
            return NeedTier.SATED
        if thirst >= 30:
            return NeedTier.PARCHED
        if thirst >= 10:
            return NeedTier.DRY
        return NeedTier.DEHYDRATED


__all__ = [
    "NeedTier", "NeedState", "HungerThirstEngine",
]
