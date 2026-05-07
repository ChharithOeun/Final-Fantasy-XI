"""Recipe adoption — players pin a recipe to their
crafting log.

A player who adopts a published recipe gets it pinned in
their synthesis UI: when they walk up to the workbench
and select the discipline, the adopted recipes are at
the top with live cost projection from recipe_economics
(so you see "best margin RIGHT NOW" not just "best
margin when chharith published").

Modes:
    SHOW_IN_LOG       guide pinned in the recipe browser
                      panel; quick-craft button enabled
    PROJECT_COST_TOO  also runs recipe_economics.report()
                      every time it renders, so the
                      profit-margin updates every visit

Per-recipe per-player one adoption record (re-adopting
just refreshes the pin's mode/timestamp).

Public surface
--------------
    PinMode enum
    AdoptionRecord dataclass (frozen)
    RecipeAdoption
        .adopt(player_id, recipe_id, mode, adopted_at)
            -> Optional[AdoptionRecord]
        .un_adopt(player_id, recipe_id) -> bool
        .pinned_for(player_id) -> list[AdoptionRecord]
        .has_adopted(player_id, recipe_id) -> bool
        .adopters_count(recipe_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.recipe_publisher import (
    RecipePublisher, RecipeStatus,
)


class PinMode(str, enum.Enum):
    SHOW_IN_LOG = "show_in_log"
    PROJECT_COST_TOO = "project_cost_too"


@dataclasses.dataclass(frozen=True)
class AdoptionRecord:
    player_id: str
    recipe_id: str
    mode: PinMode
    adopted_at: int


@dataclasses.dataclass
class RecipeAdoption:
    _publisher: RecipePublisher
    # (player_id, recipe_id) -> record
    _records: dict[
        tuple[str, str], AdoptionRecord,
    ] = dataclasses.field(default_factory=dict)

    def adopt(
        self, *, player_id: str, recipe_id: str,
        mode: PinMode, adopted_at: int,
    ) -> t.Optional[AdoptionRecord]:
        if not player_id:
            return None
        recipe = self._publisher.lookup(recipe_id=recipe_id)
        if recipe is None:
            return None
        if recipe.status != RecipeStatus.PUBLISHED:
            return None
        rec = AdoptionRecord(
            player_id=player_id, recipe_id=recipe_id,
            mode=mode, adopted_at=adopted_at,
        )
        # Re-adopting refreshes (mode/timestamp can change)
        self._records[(player_id, recipe_id)] = rec
        return rec

    def un_adopt(
        self, *, player_id: str, recipe_id: str,
    ) -> bool:
        key = (player_id, recipe_id)
        if key not in self._records:
            return False
        del self._records[key]
        return True

    def has_adopted(
        self, *, player_id: str, recipe_id: str,
    ) -> bool:
        return (player_id, recipe_id) in self._records

    def pinned_for(
        self, *, player_id: str,
    ) -> list[AdoptionRecord]:
        out = [
            r for (pid, _), r in self._records.items()
            if pid == player_id
        ]
        out.sort(key=lambda r: r.adopted_at)
        return out

    def adopters_count(self, *, recipe_id: str) -> int:
        return sum(
            1 for (_pid, rid) in self._records
            if rid == recipe_id
        )

    def total_adoptions(self) -> int:
        return len(self._records)


__all__ = [
    "PinMode", "AdoptionRecord", "RecipeAdoption",
]
