"""Mog House display mannequins.

Cosmetic display dummies that wear a full equipment set in the
player's Mog House. Used to:
* show off favorite gear sets
* preserve a memorable kill/event loadout
* photograph for screenshots / community sharing

Each mannequin has 8 equipment slots matching player gear:
    main_hand, sub_hand (or shield), ranged, ammo,
    head, body, hands, legs, feet
plus accessories: neck, waist, back, ear1, ear2, ring1, ring2

Mannequins themselves come in 5 races (matching playable races).
A player can install up to 5 mannequins in their Mog House.

Public surface
--------------
    MannequinRace enum
    EquipSlot enum
    Mannequin dataclass (one display dummy)
    PlayerMannequinCollection
        .install(race) / .remove(mannequin_id)
        .equip(mannequin_id, slot, item_id) -> bool
        .clear_slot(mannequin_id, slot)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_MANNEQUINS_PER_PLAYER = 5


class MannequinRace(str, enum.Enum):
    HUME_M = "hume_male"
    HUME_F = "hume_female"
    ELVAAN_M = "elvaan_male"
    ELVAAN_F = "elvaan_female"
    TARUTARU_M = "tarutaru_male"
    TARUTARU_F = "tarutaru_female"
    MITHRA = "mithra"
    GALKA = "galka"


class EquipSlot(str, enum.Enum):
    MAIN_HAND = "main_hand"
    SUB_HAND = "sub_hand"
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


ALL_SLOTS: tuple[EquipSlot, ...] = tuple(EquipSlot)


@dataclasses.dataclass
class Mannequin:
    mannequin_id: str
    race: MannequinRace
    label: str = ""
    equipment: dict[EquipSlot, str] = dataclasses.field(default_factory=dict)

    def equipped_count(self) -> int:
        return len(self.equipment)


@dataclasses.dataclass(frozen=True)
class InstallResult:
    accepted: bool
    mannequin: t.Optional[Mannequin] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class EquipResult:
    accepted: bool
    slot: t.Optional[EquipSlot] = None
    item_id: t.Optional[str] = None
    replaced_item_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerMannequinCollection:
    player_id: str
    mannequins: dict[str, Mannequin] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def install(self, *, race: MannequinRace,
                  label: str = "") -> InstallResult:
        if len(self.mannequins) >= MAX_MANNEQUINS_PER_PLAYER:
            return InstallResult(False, reason="mannequin slot full")
        mid = f"mannequin_{self._next_id}"
        self._next_id += 1
        m = Mannequin(mannequin_id=mid, race=race, label=label)
        self.mannequins[mid] = m
        return InstallResult(True, mannequin=m)

    def remove(self, *, mannequin_id: str) -> bool:
        return self.mannequins.pop(mannequin_id, None) is not None

    def equip(
        self, *, mannequin_id: str, slot: EquipSlot, item_id: str,
    ) -> EquipResult:
        m = self.mannequins.get(mannequin_id)
        if m is None:
            return EquipResult(False, reason="unknown mannequin")
        if not item_id:
            return EquipResult(False, reason="item_id required")
        prev = m.equipment.get(slot)
        m.equipment[slot] = item_id
        return EquipResult(
            True, slot=slot, item_id=item_id,
            replaced_item_id=prev,
        )

    def clear_slot(self, *, mannequin_id: str,
                     slot: EquipSlot) -> EquipResult:
        m = self.mannequins.get(mannequin_id)
        if m is None:
            return EquipResult(False, reason="unknown mannequin")
        prev = m.equipment.pop(slot, None)
        return EquipResult(
            True, slot=slot, item_id=None, replaced_item_id=prev,
        )


__all__ = [
    "MAX_MANNEQUINS_PER_PLAYER",
    "MannequinRace", "EquipSlot", "ALL_SLOTS",
    "Mannequin", "InstallResult", "EquipResult",
    "PlayerMannequinCollection",
]
