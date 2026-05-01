"""Mount equipment — barding / saddle / headgear / saddlebags.

Per the user direction: 'add equipment with stats to the mounts
with weight and extra storage space'. Each piece occupies one of
four slots; total weight feeds the rider's effective weight pool
(via weight_physics integration) and storage slots stack.

Stats vocabulary (sample):
    defense, evasion, fire_resist / ice_resist / etc.
    attack_power, accuracy
    aggro_reduction (percentage)
    stamina_recovery_per_minute (ambient regen)
    storage_slots (saddlebags primary; saddle minor)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class MountEquipmentSlot(str, enum.Enum):
    BARDING = "barding"            # body armor for the mount
    SADDLE = "saddle"              # control + minor storage
    HEADGEAR = "headgear"          # head protection / aggro reduction
    SADDLEBAGS = "saddlebags"      # primary storage


@dataclasses.dataclass(frozen=True)
class MountEquipment:
    """A single equippable piece of mount gear."""
    slot: MountEquipmentSlot
    item_id: str
    name: str
    weight: float
    stats: dict[str, float] = dataclasses.field(default_factory=dict)
    storage_slots: int = 0
    notes: str = ""


# ----------------------------------------------------------------------
# Sample equipment catalog (tier-spread)
# ----------------------------------------------------------------------

SAMPLE_BARDINGS: dict[str, MountEquipment] = {
    "leather_barding": MountEquipment(
        slot=MountEquipmentSlot.BARDING,
        item_id="leather_barding", name="Leather Barding",
        weight=8.0,
        stats={"defense": 30, "evasion": 5},
    ),
    "scale_barding": MountEquipment(
        slot=MountEquipmentSlot.BARDING,
        item_id="scale_barding", name="Scale Barding",
        weight=18.0,
        stats={"defense": 60, "fire_resist": 5},
    ),
    "adaman_barding": MountEquipment(
        slot=MountEquipmentSlot.BARDING,
        item_id="adaman_barding", name="Adaman Barding",
        weight=44.0,
        stats={"defense": 120, "fire_resist": 10, "ice_resist": 10},
        notes="grandmaster-tier; heavy",
    ),
}


SAMPLE_SADDLES: dict[str, MountEquipment] = {
    "common_saddle": MountEquipment(
        slot=MountEquipmentSlot.SADDLE,
        item_id="common_saddle", name="Common Saddle",
        weight=4.0,
        stats={"control": 5},
        storage_slots=2,
    ),
    "ranger_saddle": MountEquipment(
        slot=MountEquipmentSlot.SADDLE,
        item_id="ranger_saddle", name="Ranger Saddle",
        weight=6.0,
        stats={"control": 10, "accuracy": 5},
        storage_slots=4,
        notes="favored by mounted archers",
    ),
    "knight_saddle": MountEquipment(
        slot=MountEquipmentSlot.SADDLE,
        item_id="knight_saddle", name="Knight's Saddle",
        weight=10.0,
        stats={"control": 15, "attack_power": 10},
        storage_slots=2,
        notes="heavy; best for cavalry stance",
    ),
}


SAMPLE_HEADGEAR: dict[str, MountEquipment] = {
    "felt_caparison": MountEquipment(
        slot=MountEquipmentSlot.HEADGEAR,
        item_id="felt_caparison", name="Felt Caparison",
        weight=2.0,
        stats={"defense": 10, "aggro_reduction": 0.05},
    ),
    "iron_chamfron": MountEquipment(
        slot=MountEquipmentSlot.HEADGEAR,
        item_id="iron_chamfron", name="Iron Chamfron",
        weight=8.0,
        stats={"defense": 30, "aggro_reduction": 0.10},
    ),
    "wisp_charm_caparison": MountEquipment(
        slot=MountEquipmentSlot.HEADGEAR,
        item_id="wisp_charm_caparison", name="Wisp-Charm Caparison",
        weight=3.0,
        stats={"stamina_recovery_per_minute": 4,
                "aggro_reduction": 0.03},
        notes="reduces sound-aggro proc",
    ),
}


SAMPLE_SADDLEBAGS: dict[str, MountEquipment] = {
    "small_saddlebag": MountEquipment(
        slot=MountEquipmentSlot.SADDLEBAGS,
        item_id="small_saddlebag", name="Small Saddlebag",
        weight=2.0,
        storage_slots=8,
    ),
    "trader_saddlebag": MountEquipment(
        slot=MountEquipmentSlot.SADDLEBAGS,
        item_id="trader_saddlebag", name="Trader's Saddlebag",
        weight=5.0,
        storage_slots=20,
    ),
    "expedition_saddlebag": MountEquipment(
        slot=MountEquipmentSlot.SADDLEBAGS,
        item_id="expedition_saddlebag", name="Expedition Saddlebag",
        weight=8.0,
        storage_slots=32,
        notes="bulky; max storage; weight-aware traders only",
    ),
}


# ----------------------------------------------------------------------
# Loadout
# ----------------------------------------------------------------------

class MountEquipmentLoadout:
    """Per-mount equipped-loadout. One slot per slot type."""

    def __init__(self) -> None:
        self.slots: dict[MountEquipmentSlot, t.Optional[MountEquipment]] = {
            slot: None for slot in MountEquipmentSlot
        }

    def equip(self, item: MountEquipment) -> t.Optional[MountEquipment]:
        """Equip an item; returns the previous occupant of the slot
        (or None)."""
        prev = self.slots[item.slot]
        self.slots[item.slot] = item
        return prev

    def unequip(self,
                  slot: MountEquipmentSlot) -> t.Optional[MountEquipment]:
        prev = self.slots[slot]
        self.slots[slot] = None
        return prev

    def total_weight(self) -> float:
        return sum(item.weight for item in self.slots.values()
                     if item is not None)

    def total_storage_slots(self) -> int:
        return sum(item.storage_slots for item in self.slots.values()
                     if item is not None)

    def aggregated_stats(self) -> dict[str, float]:
        """Sum each numeric stat across all equipped pieces."""
        out: dict[str, float] = {}
        for item in self.slots.values():
            if item is None:
                continue
            for stat, value in item.stats.items():
                out[stat] = out.get(stat, 0.0) + value
        return out

    def equipped_items(self) -> list[MountEquipment]:
        return [item for item in self.slots.values() if item is not None]
