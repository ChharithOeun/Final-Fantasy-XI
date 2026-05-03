"""Rhapsody key items — fast-travel bundles + bonus stack.

Canonical FFXI introduced a series of "Rhapsody" key items
that ease quality-of-life across multiple legacy systems. Each
Rhapsody granted at a specific Rhapsody-quest milestone unlocks
faster home-point recall, free travel, EXP/skill bonuses, etc.

Six tiers (canonical color order):
    WHITE     — base Rhapsody, +5% EXP/skill, faster Home Point
    MAUVE     — +10% EXP/skill, free Cavernous Maw warps
    CRIMSON   — +15% EXP/skill, free Survival Guide warps
    AZURE     — +20%, free Mog Garden tablet
    VERDIGRIS — +25%, no Mog Wardrobe restrictions
    OCHRE     — +30%, free Outpost Warp from anywhere

Higher tiers SUPERSEDE lower (they roll up the bonuses), so a
player with OCHRE has the full stack of perks. Bonuses are
read-only for callers (RoE, conquest, etc.); this module is
the registry + lookup.

Public surface
--------------
    Rhapsody enum (6 tiers in order)
    BonusBundle dataclass — what each tier unlocks
    RHAPSODY_BONUSES
    PlayerRhapsodyState
        .grant(rhapsody) -> bool
        .holds(rhapsody) -> bool
        .highest_held() -> Optional[Rhapsody]
        .effective_bonuses() -> BonusBundle
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Rhapsody(str, enum.Enum):
    WHITE = "rhapsody_in_white"
    MAUVE = "rhapsody_in_mauve"
    CRIMSON = "rhapsody_in_crimson"
    AZURE = "rhapsody_in_azure"
    VERDIGRIS = "rhapsody_in_verdigris"
    OCHRE = "rhapsody_in_ochre"


_TIER_ORDER: tuple[Rhapsody, ...] = (
    Rhapsody.WHITE, Rhapsody.MAUVE, Rhapsody.CRIMSON,
    Rhapsody.AZURE, Rhapsody.VERDIGRIS, Rhapsody.OCHRE,
)


@dataclasses.dataclass(frozen=True)
class BonusBundle:
    exp_bonus_pct: int = 0
    skill_bonus_pct: int = 0
    free_home_point: bool = False
    free_maw_warps: bool = False
    free_survival_guide: bool = False
    free_mog_garden_tablet: bool = False
    wardrobe_unrestricted: bool = False
    free_outpost_warp: bool = False


# Per-tier bundle (cumulative — each tier is a SUPERSET of the prior)
RHAPSODY_BONUSES: dict[Rhapsody, BonusBundle] = {
    Rhapsody.WHITE: BonusBundle(
        exp_bonus_pct=5, skill_bonus_pct=5,
        free_home_point=True,
    ),
    Rhapsody.MAUVE: BonusBundle(
        exp_bonus_pct=10, skill_bonus_pct=10,
        free_home_point=True, free_maw_warps=True,
    ),
    Rhapsody.CRIMSON: BonusBundle(
        exp_bonus_pct=15, skill_bonus_pct=15,
        free_home_point=True, free_maw_warps=True,
        free_survival_guide=True,
    ),
    Rhapsody.AZURE: BonusBundle(
        exp_bonus_pct=20, skill_bonus_pct=20,
        free_home_point=True, free_maw_warps=True,
        free_survival_guide=True,
        free_mog_garden_tablet=True,
    ),
    Rhapsody.VERDIGRIS: BonusBundle(
        exp_bonus_pct=25, skill_bonus_pct=25,
        free_home_point=True, free_maw_warps=True,
        free_survival_guide=True,
        free_mog_garden_tablet=True,
        wardrobe_unrestricted=True,
    ),
    Rhapsody.OCHRE: BonusBundle(
        exp_bonus_pct=30, skill_bonus_pct=30,
        free_home_point=True, free_maw_warps=True,
        free_survival_guide=True,
        free_mog_garden_tablet=True,
        wardrobe_unrestricted=True,
        free_outpost_warp=True,
    ),
}


def is_higher_tier(*, a: Rhapsody, b: Rhapsody) -> bool:
    """True if a is a higher Rhapsody tier than b."""
    return _TIER_ORDER.index(a) > _TIER_ORDER.index(b)


@dataclasses.dataclass
class PlayerRhapsodyState:
    player_id: str
    held: set[Rhapsody] = dataclasses.field(default_factory=set)

    def grant(self, *, rhapsody: Rhapsody) -> bool:
        if rhapsody in self.held:
            return False
        self.held.add(rhapsody)
        return True

    def holds(self, rhapsody: Rhapsody) -> bool:
        return rhapsody in self.held

    def highest_held(self) -> t.Optional[Rhapsody]:
        for r in reversed(_TIER_ORDER):
            if r in self.held:
                return r
        return None

    def effective_bonuses(self) -> BonusBundle:
        """Bonuses are sourced from the HIGHEST tier held, since
        each tier is a superset of the lower tiers."""
        top = self.highest_held()
        if top is None:
            return BonusBundle()
        return RHAPSODY_BONUSES[top]


__all__ = [
    "Rhapsody", "BonusBundle", "RHAPSODY_BONUSES",
    "is_higher_tier", "PlayerRhapsodyState",
]
