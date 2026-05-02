"""Title system — earnable titles with optional stat bonuses.

Players earn titles for milestones (kill the AV, finish CoP, master
WAR, etc.). Earned titles go into the player's collection. One title
can be equipped at a time and may grant a small stat bonus while
worn.

Public surface
--------------
    Title catalog with stat bonuses
    PlayerTitleCollection
        .earn(title_id) -> bool (True if newly earned)
        .equip(title_id) -> bool
        .currently_equipped
        .has(title_id)
        .stat_bonuses() -> dict with current equipped's bonuses
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Title:
    title_id: str
    label: str
    description: str = ""
    stat_bonuses: tuple[tuple[str, int], ...] = ()


# Sample title catalog
TITLE_CATALOG: tuple[Title, ...] = (
    Title("orc_pillager", "Orc Pillager",
          stat_bonuses=()),
    Title("dragon_slayer", "Dragon Slayer",
          description="Killed Fafnir.",
          stat_bonuses=(("str", 1),)),
    Title("avian_assassin", "Avian Assassin",
          stat_bonuses=()),
    Title("master_of_warriors", "Master of Warriors",
          description="WAR mastery.",
          stat_bonuses=(("str", 2), ("vit", 2))),
    Title("hero_of_vana", "Hero of Vana'diel",
          description="Cleared Chains of Promathia.",
          stat_bonuses=(("hp", 30), ("mp", 20))),
    Title("savior_of_aht_urhgan", "Savior of Aht Urhgan",
          description="Cleared Treasures of Aht Urhgan.",
          stat_bonuses=(("attack", 5),)),
    Title("knight_of_the_round", "Knight of the Round",
          description="Defeated 100 Dynamis lords.",
          stat_bonuses=(("hp", 50), ("defense", 10))),
)

TITLE_BY_ID: dict[str, Title] = {t.title_id: t for t in TITLE_CATALOG}


@dataclasses.dataclass
class PlayerTitleCollection:
    player_id: str
    earned: set[str] = dataclasses.field(default_factory=set)
    equipped: t.Optional[str] = None

    def earn(self, *, title_id: str) -> bool:
        """Add a title to the player. Returns True if newly earned."""
        if title_id not in TITLE_BY_ID:
            return False
        if title_id in self.earned:
            return False
        self.earned.add(title_id)
        return True

    def has(self, title_id: str) -> bool:
        return title_id in self.earned

    def equip(self, *, title_id: str) -> bool:
        """Wear an earned title. Returns True on success."""
        if title_id not in self.earned:
            return False
        self.equipped = title_id
        return True

    def unequip(self) -> bool:
        if self.equipped is None:
            return False
        self.equipped = None
        return True

    @property
    def currently_equipped(self) -> t.Optional[Title]:
        if self.equipped is None:
            return None
        return TITLE_BY_ID.get(self.equipped)

    def stat_bonuses(self) -> dict[str, int]:
        title = self.currently_equipped
        if title is None:
            return {}
        return dict(title.stat_bonuses)

    def collection_size(self) -> int:
        return len(self.earned)


__all__ = [
    "Title", "TITLE_CATALOG", "TITLE_BY_ID",
    "PlayerTitleCollection",
]
