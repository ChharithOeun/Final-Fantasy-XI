"""Genkai (level cap quest) chain — 50/55/60/65/70/75.

Canonical FFXI level cap progression:
* 50 -> Genkai I "An Invitation to the Past"
* 55 -> Genkai II "Atop the Highest Mountains"
* 60 -> Genkai III "Whence Blows the Wind"
* 65 -> Genkai IV "The Beast Within"
* 70 -> Genkai V "The Beast Without"
* 75 -> Genkai VI "Maat" (the celebrated 1v1 fight)

Each Genkai must be completed in order; the next can't be
attempted until the previous unlocks. Once Genkai N is complete,
the player's max level is raised to (45 + 5 * N).

Public surface
--------------
    GenkaiTier enum
    GENKAI_QUESTS  (catalog with cap-after value)
    PlayerGenkaiState
        .available_genkai(main_level) -> Optional[next tier]
        .complete(tier, main_level) -> bool
        .level_cap property
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


@dataclasses.dataclass(frozen=True)
class GenkaiQuest:
    tier: int
    quest_id: str
    label: str
    starts_at_level: int
    raises_cap_to: int


GENKAI_QUESTS: tuple[GenkaiQuest, ...] = (
    GenkaiQuest(1, "genkai_1_invitation", "An Invitation to the Past",
                 starts_at_level=50, raises_cap_to=55),
    GenkaiQuest(2, "genkai_2_highest_mountains",
                 "Atop the Highest Mountains",
                 starts_at_level=55, raises_cap_to=60),
    GenkaiQuest(3, "genkai_3_whence_blows_wind",
                 "Whence Blows the Wind",
                 starts_at_level=60, raises_cap_to=65),
    GenkaiQuest(4, "genkai_4_beast_within",
                 "The Beast Within",
                 starts_at_level=65, raises_cap_to=70),
    GenkaiQuest(5, "genkai_5_beast_without",
                 "The Beast Without",
                 starts_at_level=70, raises_cap_to=75),
    GenkaiQuest(6, "genkai_6_maat",
                 "In the Presence of Maat",
                 starts_at_level=75, raises_cap_to=80),
)


GENKAI_BY_TIER: dict[int, GenkaiQuest] = {q.tier: q for q in GENKAI_QUESTS}


DEFAULT_INITIAL_CAP = 50


@dataclasses.dataclass
class PlayerGenkaiState:
    player_id: str
    completed_tiers: set[int] = dataclasses.field(default_factory=set)

    @property
    def highest_completed(self) -> int:
        return max(self.completed_tiers, default=0)

    @property
    def level_cap(self) -> int:
        if not self.completed_tiers:
            return DEFAULT_INITIAL_CAP
        return GENKAI_BY_TIER[self.highest_completed].raises_cap_to

    def available_genkai(self, *, main_level: int
                          ) -> t.Optional[GenkaiQuest]:
        """Next genkai the player is eligible to attempt, or None."""
        next_tier = self.highest_completed + 1
        q = GENKAI_BY_TIER.get(next_tier)
        if q is None:
            return None
        if main_level < q.starts_at_level:
            return None
        return q

    def complete(self, *, tier: int, main_level: int) -> bool:
        q = GENKAI_BY_TIER.get(tier)
        if q is None:
            return False
        if tier in self.completed_tiers:
            return False
        # Must be next-in-sequence
        if tier != self.highest_completed + 1:
            return False
        if main_level < q.starts_at_level:
            return False
        self.completed_tiers.add(tier)
        return True


__all__ = [
    "DEFAULT_INITIAL_CAP",
    "GenkaiQuest", "GENKAI_QUESTS", "GENKAI_BY_TIER",
    "PlayerGenkaiState",
]
