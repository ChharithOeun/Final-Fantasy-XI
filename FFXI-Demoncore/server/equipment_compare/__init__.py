"""Equipment compare — hover-to-compare with stat deltas.

When the player hovers a candidate item in the inventory or
auction house, this module produces a side-by-side stat
DELTA against whatever's currently equipped in that slot.
Positive deltas render green, negatives render red, zero is
neutral.

The stat schema covers the seven core stats + skills. Skill
deltas surface separately so the renderer can show a "+5 Sword,
-3 Evasion" line beneath the main grid.

Public surface
--------------
    EquipSlot enum
    StatKind enum
    SkillKind enum
    ItemDef dataclass
    StatDelta dataclass
    CompareResult dataclass
    EquipmentCompare
        .register_item(item_id, slot, stats, skills)
        .equip(player_id, slot, item_id)
        .compare(player_id, candidate_item_id) -> CompareResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EquipSlot(str, enum.Enum):
    MAIN = "main"
    SUB = "sub"
    RANGED = "ranged"
    AMMO = "ammo"
    HEAD = "head"
    NECK = "neck"
    EAR_1 = "ear_1"
    EAR_2 = "ear_2"
    BODY = "body"
    HANDS = "hands"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    BACK = "back"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"


class StatKind(str, enum.Enum):
    STR = "str"
    DEX = "dex"
    VIT = "vit"
    AGI = "agi"
    INT = "int"
    MND = "mnd"
    CHR = "chr"
    HP = "hp"
    MP = "mp"
    ACCURACY = "accuracy"
    ATTACK = "attack"
    DEFENSE = "defense"
    EVASION = "evasion"
    MAGIC_ACCURACY = "magic_accuracy"
    MAGIC_DEFENSE = "magic_defense"


class SkillKind(str, enum.Enum):
    SWORD = "sword"
    AXE = "axe"
    POLEARM = "polearm"
    DAGGER = "dagger"
    HAND_TO_HAND = "hand_to_hand"
    ARCHERY = "archery"
    HEALING_MAGIC = "healing_magic"
    ENFEEBLING = "enfeebling"
    ELEMENTAL = "elemental"
    DARK = "dark"
    DIVINE = "divine"
    NINJUTSU = "ninjutsu"
    SUMMONING = "summoning"


@dataclasses.dataclass(frozen=True)
class ItemDef:
    item_id: str
    label: str
    slot: EquipSlot
    stats: t.Mapping[StatKind, int] = dataclasses.field(
        default_factory=dict,
    )
    skills: t.Mapping[SkillKind, int] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass(frozen=True)
class StatDelta:
    stat: StatKind
    old_value: int
    new_value: int
    delta: int


@dataclasses.dataclass(frozen=True)
class SkillDelta:
    skill: SkillKind
    old_value: int
    new_value: int
    delta: int


@dataclasses.dataclass(frozen=True)
class CompareResult:
    candidate_item_id: str
    candidate_label: str
    slot: EquipSlot
    currently_equipped_item_id: t.Optional[str]
    stat_deltas: tuple[StatDelta, ...]
    skill_deltas: tuple[SkillDelta, ...]
    net_score: int


@dataclasses.dataclass
class EquipmentCompare:
    _items: dict[str, ItemDef] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> slot -> item_id
    _equipped: dict[
        str, dict[EquipSlot, str],
    ] = dataclasses.field(default_factory=dict)

    def register_item(
        self, *, item_id: str, label: str,
        slot: EquipSlot,
        stats: t.Mapping[StatKind, int] = (),
        skills: t.Mapping[SkillKind, int] = (),
    ) -> t.Optional[ItemDef]:
        if item_id in self._items:
            return None
        item = ItemDef(
            item_id=item_id, label=label, slot=slot,
            stats=dict(stats), skills=dict(skills),
        )
        self._items[item_id] = item
        return item

    def equip(
        self, *, player_id: str, item_id: str,
    ) -> bool:
        item = self._items.get(item_id)
        if item is None:
            return False
        self._equipped.setdefault(
            player_id, {},
        )[item.slot] = item_id
        return True

    def equipped_in_slot(
        self, *, player_id: str, slot: EquipSlot,
    ) -> t.Optional[str]:
        return self._equipped.get(
            player_id, {},
        ).get(slot)

    def compare(
        self, *, player_id: str,
        candidate_item_id: str,
    ) -> t.Optional[CompareResult]:
        candidate = self._items.get(candidate_item_id)
        if candidate is None:
            return None
        currently = self.equipped_in_slot(
            player_id=player_id, slot=candidate.slot,
        )
        equipped = (
            self._items.get(currently)
            if currently is not None
            else None
        )
        old_stats = (
            dict(equipped.stats) if equipped else {}
        )
        old_skills = (
            dict(equipped.skills) if equipped else {}
        )
        # Stat deltas — union of keys
        all_stats = (
            set(old_stats) | set(candidate.stats)
        )
        stat_deltas: list[StatDelta] = []
        net_score = 0
        for s in all_stats:
            old_v = old_stats.get(s, 0)
            new_v = candidate.stats.get(s, 0)
            delta = new_v - old_v
            stat_deltas.append(StatDelta(
                stat=s, old_value=old_v,
                new_value=new_v, delta=delta,
            ))
            net_score += delta
        all_skills = (
            set(old_skills) | set(candidate.skills)
        )
        skill_deltas: list[SkillDelta] = []
        for k in all_skills:
            old_v = old_skills.get(k, 0)
            new_v = candidate.skills.get(k, 0)
            delta = new_v - old_v
            skill_deltas.append(SkillDelta(
                skill=k, old_value=old_v,
                new_value=new_v, delta=delta,
            ))
            net_score += delta
        # Sort deltas: positive first, then by absolute size
        stat_deltas.sort(
            key=lambda d: (-d.delta, d.stat.value),
        )
        skill_deltas.sort(
            key=lambda d: (-d.delta, d.skill.value),
        )
        return CompareResult(
            candidate_item_id=candidate_item_id,
            candidate_label=candidate.label,
            slot=candidate.slot,
            currently_equipped_item_id=currently,
            stat_deltas=tuple(stat_deltas),
            skill_deltas=tuple(skill_deltas),
            net_score=net_score,
        )

    def total_items(self) -> int:
        return len(self._items)


__all__ = [
    "EquipSlot", "StatKind", "SkillKind",
    "ItemDef", "StatDelta", "SkillDelta",
    "CompareResult",
    "EquipmentCompare",
]
