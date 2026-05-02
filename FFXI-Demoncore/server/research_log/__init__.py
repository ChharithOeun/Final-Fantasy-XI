"""Research log — bestiary that reveals info as you kill mobs.

Each mob family has tiered info gates:
    1 kill   -> name + portrait
    5 kills  -> base stats (HP, MP, weakness)
    20 kills -> full drop table
    50 kills -> lore / story tab unlocks

Public surface
--------------
    BestiaryEntry catalog
    PlayerResearchLog
        .record_kill(family_id) -> tier_just_unlocked or None
        .visible_info(family_id)
        .total_unique_families()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ResearchTier(int, enum.Enum):
    LOCKED = 0
    SIGHTED = 1          # 1 kill: name + portrait
    KNOWN = 2            # 5 kills: stats + weakness
    DOCUMENTED = 3       # 20 kills: full drop table
    MASTERED = 4         # 50 kills: lore unlocked


# Kill thresholds
TIER_KILL_THRESHOLDS: dict[ResearchTier, int] = {
    ResearchTier.SIGHTED: 1,
    ResearchTier.KNOWN: 5,
    ResearchTier.DOCUMENTED: 20,
    ResearchTier.MASTERED: 50,
}


@dataclasses.dataclass(frozen=True)
class BestiaryEntry:
    family_id: str
    label: str
    portrait_id: str
    base_hp: int
    base_mp: int
    weakness: str            # element name
    drops: tuple[str, ...]
    lore: str = ""


# Sample bestiary
BESTIARY_CATALOG: tuple[BestiaryEntry, ...] = (
    BestiaryEntry(
        family_id="orc", label="Orcish Footsoldier",
        portrait_id="orc_portrait",
        base_hp=180, base_mp=0, weakness="ice",
        drops=("orcish_axe", "shabby_belt", "rusty_helm"),
        lore="Aggressive humanoid scavengers; central to Davoi.",
    ),
    BestiaryEntry(
        family_id="quadav", label="Quadav Sentinel",
        portrait_id="quadav_portrait",
        base_hp=420, base_mp=80, weakness="lightning",
        drops=("zinc_ore", "shabby_shield"),
        lore="Beadeaux's lightning-aligned beastman tribe.",
    ),
    BestiaryEntry(
        family_id="yagudo", label="Yagudo Theologist",
        portrait_id="yagudo_portrait",
        base_hp=200, base_mp=120, weakness="fire",
        drops=("yagudo_necklace", "yagudo_cherry"),
        lore="Castle Oztroja's avian theocracy.",
    ),
    BestiaryEntry(
        family_id="goblin", label="Goblin Pathfinder",
        portrait_id="goblin_portrait",
        base_hp=140, base_mp=0, weakness="water",
        drops=("goblin_mask", "torn_hat"),
        lore="Self-styled freelance traders.",
    ),
    BestiaryEntry(
        family_id="tonberry", label="Tonberry",
        portrait_id="tonberry_portrait",
        base_hp=2400, base_mp=0, weakness="dark",
        drops=("tonberry_lantern", "yhoator_jungle_seed"),
        lore="Carriers of perpetual grudges.",
    ),
)

ENTRY_BY_ID: dict[str, BestiaryEntry] = {
    e.family_id: e for e in BESTIARY_CATALOG
}


@dataclasses.dataclass
class _ResearchProgress:
    kills: int = 0
    tier: ResearchTier = ResearchTier.LOCKED


def _tier_for_kills(kills: int) -> ResearchTier:
    """Map a kill count to the highest tier achieved."""
    achieved = ResearchTier.LOCKED
    for tier, threshold in TIER_KILL_THRESHOLDS.items():
        if kills >= threshold:
            if tier.value > achieved.value:
                achieved = tier
    return achieved


@dataclasses.dataclass
class PlayerResearchLog:
    player_id: str
    _progress: dict[str, _ResearchProgress] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def record_kill(
        self, *, family_id: str,
    ) -> t.Optional[ResearchTier]:
        """Tally one kill. Returns the tier just unlocked, if any."""
        if family_id not in ENTRY_BY_ID:
            return None
        prog = self._progress.setdefault(
            family_id, _ResearchProgress(),
        )
        prev_tier = prog.tier
        prog.kills += 1
        prog.tier = _tier_for_kills(prog.kills)
        if prog.tier.value > prev_tier.value:
            return prog.tier
        return None

    def tier_for(self, family_id: str) -> ResearchTier:
        prog = self._progress.get(family_id)
        if prog is None:
            return ResearchTier.LOCKED
        return prog.tier

    def kill_count(self, family_id: str) -> int:
        prog = self._progress.get(family_id)
        return prog.kills if prog else 0

    def visible_info(
        self, family_id: str,
    ) -> dict[str, t.Any]:
        """What the bestiary UI should reveal at the player's
        current tier."""
        entry = ENTRY_BY_ID.get(family_id)
        if entry is None:
            return {}
        tier = self.tier_for(family_id)
        info: dict[str, t.Any] = {}
        if tier.value >= ResearchTier.SIGHTED.value:
            info["label"] = entry.label
            info["portrait_id"] = entry.portrait_id
        if tier.value >= ResearchTier.KNOWN.value:
            info["base_hp"] = entry.base_hp
            info["base_mp"] = entry.base_mp
            info["weakness"] = entry.weakness
        if tier.value >= ResearchTier.DOCUMENTED.value:
            info["drops"] = entry.drops
        if tier.value >= ResearchTier.MASTERED.value:
            info["lore"] = entry.lore
        return info

    def total_unique_families(self) -> int:
        return sum(
            1 for p in self._progress.values()
            if p.kills > 0
        )

    def total_mastered(self) -> int:
        return sum(
            1 for p in self._progress.values()
            if p.tier == ResearchTier.MASTERED
        )


__all__ = [
    "ResearchTier", "TIER_KILL_THRESHOLDS",
    "BestiaryEntry", "BESTIARY_CATALOG", "ENTRY_BY_ID",
    "PlayerResearchLog",
]
