"""Crafting breakthrough — random discoveries that unlock new recipes.

A crafter at high skill occasionally has a "moment" — they
add an unusual ingredient, the synth glows, and they
DISCOVER a new recipe variant that wasn't previously
known to anyone on the server. They earn a permanent
recipe slot (added to recipe_book_ui), can teach it to
others, and the masterwork_synthesis system recognizes
they have a breakthrough_active flag for the next 60
seconds.

A breakthrough is rolled per-synthesis with chance:
    base_chance = (skill_level - recipe_level) / 100
    daily_attempt_decay: each attempt this day reduces
                         the chance by 0.5%
    capped at 8%

Once a breakthrough hits, three things happen:
    1. The crafter gets a 60-sec window where
       breakthrough_active=True (used by
       masterwork_synthesis attempt)
    2. A new recipe variant is added to their
       discovered_recipes set; the variant_id is derived
       from base_recipe + some glyph
    3. A server-wide announcement fires (if the recipe
       is novel server-wide; else just personal)

Breakthroughs decay: if the crafter doesn't use them
within 60 seconds, the active flag expires.

Public surface
--------------
    BreakthroughResult dataclass (frozen)
    DiscoveredRecipe dataclass (frozen)
    CraftingBreakthrough
        .roll_breakthrough(crafter, recipe_id, skill,
                           recipe_level, attempts_today,
                           rng_seed) -> BreakthroughResult
        .is_active(crafter, now_ms) -> bool
        .consume(crafter) -> bool
        .discovered_recipes(crafter) -> list[DiscoveredRecipe]
        .first_discoverer(variant_id) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import typing as t


_BREAKTHROUGH_CAP_PCT = 8.0
_PER_ATTEMPT_DECAY_PCT = 0.5
_ACTIVE_WINDOW_MS = 60_000


@dataclasses.dataclass(frozen=True)
class BreakthroughResult:
    crafter_id: str
    recipe_id: str
    breakthrough_fired: bool
    variant_id: t.Optional[str]
    chance_pct: float
    is_server_first: bool


@dataclasses.dataclass(frozen=True)
class DiscoveredRecipe:
    variant_id: str
    base_recipe_id: str
    discovered_at_ms: int


@dataclasses.dataclass
class _CrafterState:
    discovered: dict[str, DiscoveredRecipe] = dataclasses.field(
        default_factory=dict,
    )
    active_until_ms: int = 0


@dataclasses.dataclass
class CraftingBreakthrough:
    _crafters: dict[str, _CrafterState] = dataclasses.field(
        default_factory=dict,
    )
    _server_first: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def _state(self, crafter_id: str) -> _CrafterState:
        if crafter_id not in self._crafters:
            self._crafters[crafter_id] = _CrafterState()
        return self._crafters[crafter_id]

    def roll_breakthrough(
        self, *, crafter_id: str, recipe_id: str,
        skill_level: int, recipe_level: int,
        attempts_today: int, rng_seed: int,
        now_ms: int,
    ) -> BreakthroughResult:
        if not crafter_id or not recipe_id:
            return BreakthroughResult(
                crafter_id=crafter_id, recipe_id=recipe_id,
                breakthrough_fired=False,
                variant_id=None, chance_pct=0.0,
                is_server_first=False,
            )
        margin = max(0, skill_level - recipe_level)
        base = margin / 100.0 * 100.0  # margin*0.01 -> %
        # Cap base first, THEN apply per-attempt decay,
        # so a high-margin crafter doesn't get protected
        # from decay by an enormous uncapped base.
        capped_base = min(_BREAKTHROUGH_CAP_PCT, base)
        chance = max(
            0.0,
            capped_base
            - attempts_today * _PER_ATTEMPT_DECAY_PCT,
        )
        # Deterministic RNG for tests: we use rng_seed % 10000
        # against chance * 100.
        roll = rng_seed % 10000
        threshold = int(chance * 100)
        fired = roll < threshold
        variant_id: t.Optional[str] = None
        is_first = False
        if fired:
            variant_id = f"{recipe_id}::v{rng_seed % 1000}"
            st = self._state(crafter_id)
            st.discovered[variant_id] = DiscoveredRecipe(
                variant_id=variant_id,
                base_recipe_id=recipe_id,
                discovered_at_ms=now_ms,
            )
            st.active_until_ms = now_ms + _ACTIVE_WINDOW_MS
            if variant_id not in self._server_first:
                self._server_first[variant_id] = crafter_id
                is_first = True
        return BreakthroughResult(
            crafter_id=crafter_id, recipe_id=recipe_id,
            breakthrough_fired=fired,
            variant_id=variant_id,
            chance_pct=round(chance, 2),
            is_server_first=is_first,
        )

    def is_active(
        self, *, crafter_id: str, now_ms: int,
    ) -> bool:
        if crafter_id not in self._crafters:
            return False
        return now_ms < self._crafters[
            crafter_id
        ].active_until_ms

    def consume(
        self, *, crafter_id: str, now_ms: int,
    ) -> bool:
        if not self.is_active(
            crafter_id=crafter_id, now_ms=now_ms,
        ):
            return False
        self._crafters[crafter_id].active_until_ms = 0
        return True

    def discovered_recipes(
        self, *, crafter_id: str,
    ) -> list[DiscoveredRecipe]:
        if crafter_id not in self._crafters:
            return []
        return sorted(
            self._crafters[crafter_id].discovered.values(),
            key=lambda r: r.discovered_at_ms,
        )

    def first_discoverer(
        self, *, variant_id: str,
    ) -> t.Optional[str]:
        return self._server_first.get(variant_id)


__all__ = [
    "BreakthroughResult", "DiscoveredRecipe",
    "CraftingBreakthrough",
]
