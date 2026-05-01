"""Blue Magic — spell catalog, learning, set-point budget.

Blue Mage uses a unique spell system: defeat the source mob with
a fighting BLU and you have a chance to learn a spell. Spells
must be SET into a limited slot budget; setting spells also
grants stat traits per the canonical FFXI BLU job.

Public surface
--------------
    BlueSpellCategory enum
    BlueSpell immutable spec (id, name, set_cost, source_mob,
                              learn_chance)
    BLUE_SPELL_CATALOG sample spells
    BlueSpellbook per-player learned + equipped sets
        .attempt_learn(spell_id, rng_pool) -> bool
        .equip(spell_id) -> EquipResult
        .unequip(spell_id)
        .set_point_used / .set_point_cap
    set_point_cap_for_level(level)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_LOOT_DROPS


class BlueSpellCategory(str, enum.Enum):
    PHYSICAL = "physical"
    MAGICAL = "magical"
    HEALING = "healing"
    UTILITY = "utility"
    BREATH = "breath"


@dataclasses.dataclass(frozen=True)
class BlueSpell:
    spell_id: str
    name: str
    category: BlueSpellCategory
    set_cost: int                   # points consumed when equipped
    learn_level: int                # min job level to learn
    source_mob: str                 # mob_class_id where you learn it
    learn_chance: float = 0.50      # per-kill chance


# Sample catalog
BLUE_SPELL_CATALOG: tuple[BlueSpell, ...] = (
    BlueSpell("pollen", "Pollen", BlueSpellCategory.HEALING,
              set_cost=2, learn_level=4, source_mob="bee_soldier"),
    BlueSpell("wild_carrot", "Wild Carrot",
              BlueSpellCategory.HEALING,
              set_cost=2, learn_level=10, source_mob="rabbit"),
    BlueSpell("cocoon", "Cocoon", BlueSpellCategory.UTILITY,
              set_cost=1, learn_level=8, source_mob="caterpillar"),
    BlueSpell("sandspin", "Sandspin", BlueSpellCategory.MAGICAL,
              set_cost=2, learn_level=8, source_mob="goblin_smithy"),
    BlueSpell("bludgeon", "Bludgeon", BlueSpellCategory.PHYSICAL,
              set_cost=3, learn_level=14,
              source_mob="goblin_pathfinder"),
    BlueSpell("flying_hip_press", "Flying Hip Press",
              BlueSpellCategory.PHYSICAL,
              set_cost=4, learn_level=20, source_mob="quadav"),
    BlueSpell("mind_blast", "Mind Blast",
              BlueSpellCategory.MAGICAL,
              set_cost=4, learn_level=30, source_mob="hieracosphinx"),
    BlueSpell("self_destruct", "Self-Destruct",
              BlueSpellCategory.BREATH,
              set_cost=5, learn_level=24, source_mob="bomb"),
    BlueSpell("magic_fruit", "Magic Fruit",
              BlueSpellCategory.HEALING,
              set_cost=4, learn_level=42, source_mob="treant"),
    BlueSpell("hysteric_barrage", "Hysteric Barrage",
              BlueSpellCategory.PHYSICAL,
              set_cost=5, learn_level=68,
              source_mob="naga_swordsman"),
)

SPELL_BY_ID: dict[str, BlueSpell] = {
    s.spell_id: s for s in BLUE_SPELL_CATALOG
}


def set_point_cap_for_level(level: int) -> int:
    """Set-point budget grows with BLU job level.
       1 -> 4 points
       30 -> 25 points
       60 -> 45 points
       75 -> 50 points
       99 -> 60 points
    """
    if level < 1:
        return 0
    if level <= 30:
        return 4 + (level * 21) // 30
    if level <= 60:
        return 25 + ((level - 30) * 20) // 30
    if level <= 75:
        return 45 + ((level - 60) * 5) // 15
    if level <= 99:
        return 50 + ((level - 75) * 10) // 24
    return 60


@dataclasses.dataclass(frozen=True)
class EquipResult:
    accepted: bool
    spell_id: str
    set_points_after: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class BlueSpellbook:
    player_id: str
    job_level: int
    learned: set[str] = dataclasses.field(default_factory=set)
    equipped: list[str] = dataclasses.field(default_factory=list)

    def attempt_learn(
        self, *, spell_id: str, rng_pool: RngPool,
        stream_name: str = STREAM_LOOT_DROPS,
    ) -> bool:
        spell = SPELL_BY_ID.get(spell_id)
        if spell is None:
            return False
        if spell_id in self.learned:
            return False
        if self.job_level < spell.learn_level:
            return False
        rng = rng_pool.stream(stream_name)
        if rng.random() < spell.learn_chance:
            self.learned.add(spell_id)
            return True
        return False

    @property
    def set_point_cap(self) -> int:
        return set_point_cap_for_level(self.job_level)

    @property
    def set_point_used(self) -> int:
        return sum(SPELL_BY_ID[s].set_cost for s in self.equipped)

    @property
    def set_point_available(self) -> int:
        return self.set_point_cap - self.set_point_used

    def equip(self, *, spell_id: str) -> EquipResult:
        spell = SPELL_BY_ID.get(spell_id)
        if spell is None:
            return EquipResult(False, spell_id, reason="unknown")
        if spell_id not in self.learned:
            return EquipResult(False, spell_id, reason="not learned")
        if spell_id in self.equipped:
            return EquipResult(
                False, spell_id, reason="already equipped",
            )
        if self.set_point_available < spell.set_cost:
            return EquipResult(
                False, spell_id,
                reason=(
                    f"not enough set points "
                    f"(need {spell.set_cost}, have "
                    f"{self.set_point_available})"
                ),
            )
        self.equipped.append(spell_id)
        return EquipResult(
            True, spell_id, set_points_after=self.set_point_used,
        )

    def unequip(self, *, spell_id: str) -> bool:
        if spell_id not in self.equipped:
            return False
        self.equipped.remove(spell_id)
        return True


__all__ = [
    "BlueSpellCategory", "BlueSpell",
    "BLUE_SPELL_CATALOG", "SPELL_BY_ID",
    "set_point_cap_for_level",
    "EquipResult", "BlueSpellbook",
]
