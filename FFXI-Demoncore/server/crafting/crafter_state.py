"""Per-character craft levels + XP curve + titles + LB cooldown tracking.

XP curve from the doc:
    1.0 XP per same-level synth
    0.5 XP per below-level synth
    2.0 XP per above-level synth (harder = bigger reward)

Each level requires `level * 100` XP into that level — apprentice
levels are quick, grandmaster levels are an investment. This is a
deliberately less-grindy curve than retail FFXI's; in Demoncore
everyone needs to actually reach grandmaster occasionally for the
crafter community to function.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .crafts import Craft, CraftTier, GAME_DAY_SECONDS, tier_for_level


XP_PER_SAME_LEVEL = 1.0
XP_PER_BELOW_LEVEL = 0.5
XP_PER_ABOVE_LEVEL = 2.0


@dataclasses.dataclass
class CraftLevels:
    """Per-character craft state. The `last_master_synthesis` field
    tracks per-craft cooldowns for the LB; one entry per craft the
    character has ever used the LB on.

    `nation` colors the grandmaster title ('Bastok Master Smith')."""
    actor_id: str
    nation: str = "bastok"
    levels: dict[Craft, int] = dataclasses.field(default_factory=dict)
    xp_into_level: dict[Craft, float] = dataclasses.field(default_factory=dict)
    last_master_synthesis: dict[Craft, t.Optional[float]] = dataclasses.field(
        default_factory=dict)
    titles_earned: set[str] = dataclasses.field(default_factory=set)

    def __post_init__(self) -> None:
        # Normalize: every craft has a level entry (defaulting to 0)
        for craft in Craft:
            self.levels.setdefault(craft, 0)
            self.xp_into_level.setdefault(craft, 0.0)
            self.last_master_synthesis.setdefault(craft, None)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def level(self, craft: Craft) -> int:
        return self.levels.get(craft, 0)

    def tier(self, craft: Craft) -> CraftTier:
        return tier_for_level(self.level(craft))

    def is_grandmaster(self, craft: Craft) -> bool:
        return self.level(craft) >= 90

    def grandmaster_count(self) -> int:
        return sum(1 for c in Craft if self.is_grandmaster(c))


def xp_for_synth(*,
                  recipe_level: int,
                  crafter_level: int) -> float:
    """How much XP a successful synth grants.

    Same-level: 1.0
    Below-level (recipe < crafter): 0.5
    Above-level (recipe > crafter): 2.0
    """
    if recipe_level == crafter_level:
        return XP_PER_SAME_LEVEL
    if recipe_level < crafter_level:
        return XP_PER_BELOW_LEVEL
    return XP_PER_ABOVE_LEVEL


def xp_required_for_level(level: int) -> float:
    """Cumulative XP required to enter `level`. The curve is per-level
    progressive: level n requires n*100 XP into level (n-1)."""
    if level <= 0:
        return 0.0
    return level * 100.0


def grant_xp(state: CraftLevels,
             craft: Craft,
             *,
             xp: float) -> tuple[int, int]:
    """Add `xp` to the craft and roll over levels as thresholds are
    crossed. Returns (level_before, level_after).

    Tier-change side effects (titles, rep cap raise) are read by the
    caller via tier_for_level/is_grandmaster after this call.
    """
    if xp <= 0:
        return state.level(craft), state.level(craft)

    level_before = state.level(craft)
    accumulated = state.xp_into_level.get(craft, 0.0) + xp

    new_level = level_before
    while new_level < 99:
        threshold = xp_required_for_level(new_level + 1)
        if accumulated < threshold:
            break
        accumulated -= threshold
        new_level += 1

    state.levels[craft] = new_level
    state.xp_into_level[craft] = accumulated

    # Award the grandmaster title if crossed into 90
    if new_level >= 90 and level_before < 90:
        title = title_for_grandmaster(craft, state.nation)
        state.titles_earned.add(title)

    return level_before, new_level


def title_for_grandmaster(craft: Craft, nation: str) -> str:
    """The visible title above a grandmaster crafter's name.

    Example: 'Bastok Master Smith' / 'Windy Master Loomweaver'.
    """
    nation_pretty = nation.capitalize().replace("_", " ")
    craft_label = {
        Craft.SMITHING: "Smith",
        Craft.GOLDSMITHING: "Goldsmith",
        Craft.LEATHERWORKING: "Tanner",
        Craft.WOODWORKING: "Carpenter",
        Craft.CLOTH: "Loomweaver",
        Craft.ALCHEMY: "Alchemist",
        Craft.BONECRAFT: "Bonecrafter",
        Craft.COOKING: "Chef",
        Craft.FISHING: "Master Angler",
    }[craft]
    return f"{nation_pretty} Master {craft_label}"


def reputation_cap_raise(state: CraftLevels) -> int:
    """+1000 nation reputation cap per grandmaster craft, per the doc.
    Used by honor_reputation when computing the cap."""
    return state.grandmaster_count() * 1000


def stable_hands_active(state: CraftLevels, craft: Craft) -> bool:
    """Mastery 5 (level >= 5 in this craft) grants 'stable hands' —
    the mini-game timing is more forgiving. Caller passes this into
    SynthesisResolver to relax the skill_score requirement."""
    return state.level(craft) >= 5


def can_use_master_synthesis(state: CraftLevels,
                                craft: Craft,
                                *,
                                now: float) -> bool:
    """Master Synthesis LB: grandmaster + once-per-game-day per craft."""
    if not state.is_grandmaster(craft):
        return False
    last = state.last_master_synthesis.get(craft)
    if last is None:
        return True
    return (now - last) >= GAME_DAY_SECONDS
