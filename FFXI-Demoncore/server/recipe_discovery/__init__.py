"""Recipe discovery — first-cook moments and player cookbooks.

The first time a player successfully cooks a dish, the
game says "you discovered Hunter's Stew" with a small
flourish — a name added to their personal cookbook, an
ROE-style objective ticked, maybe a fame nudge with the
Cooking guild.

Subsequent cooks of the same dish are silent. This makes
exploring the cookpot menu meaningful — every novel
recipe is a moment of pride.

The discovery flag is per-player, so two friends who both
cook Hunter's Stew for the first time both get the moment.

Public surface
--------------
    DiscoveryEvent dataclass (frozen)
    RecipeDiscoveryRegistry
        .record_cook(player_id, dish, cooked_at)
            -> Optional[DiscoveryEvent]
            (returns event on FIRST cook only; None thereafter)
        .has_discovered(player_id, dish) -> bool
        .cookbook_of(player_id) -> list[DishKind]
        .total_discoveries(player_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.cookpot_recipes import DishKind


@dataclasses.dataclass(frozen=True)
class DiscoveryEvent:
    player_id: str
    dish: DishKind
    discovered_at: int
    sequence_number: int   # 1 = first dish ever discovered


@dataclasses.dataclass
class RecipeDiscoveryRegistry:
    # player_id -> {dish: DiscoveryEvent}
    _by_player: dict[str, dict[DishKind, DiscoveryEvent]] = \
        dataclasses.field(default_factory=dict)

    def record_cook(
        self, *, player_id: str, dish: DishKind,
        cooked_at: int,
    ) -> t.Optional[DiscoveryEvent]:
        if not player_id:
            return None
        cookbook = self._by_player.setdefault(player_id, {})
        if dish in cookbook:
            return None    # not a discovery, already known
        seq = len(cookbook) + 1
        event = DiscoveryEvent(
            player_id=player_id, dish=dish,
            discovered_at=cooked_at, sequence_number=seq,
        )
        cookbook[dish] = event
        return event

    def has_discovered(
        self, *, player_id: str, dish: DishKind,
    ) -> bool:
        cookbook = self._by_player.get(player_id, {})
        return dish in cookbook

    def cookbook_of(
        self, *, player_id: str,
    ) -> list[DishKind]:
        cookbook = self._by_player.get(player_id, {})
        # ordered by discovery time
        return sorted(
            cookbook.keys(),
            key=lambda d: cookbook[d].sequence_number,
        )

    def total_discoveries(
        self, *, player_id: str,
    ) -> int:
        return len(self._by_player.get(player_id, {}))

    def get_discovery(
        self, *, player_id: str, dish: DishKind,
    ) -> t.Optional[DiscoveryEvent]:
        cookbook = self._by_player.get(player_id, {})
        return cookbook.get(dish)


__all__ = [
    "DiscoveryEvent", "RecipeDiscoveryRegistry",
]
