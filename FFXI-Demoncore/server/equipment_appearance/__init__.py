"""Equipment appearance — glamour / transmog system.

Lets a player overlay one item's appearance on another's stats.
You wear Excalibur for stats but show Mythril Sword visually. The
overlay is a per-slot setting on the equipped item; appearance must
be from items you've owned (or have a "appearance unlock" for).

Public surface
--------------
    Slot enum (head/body/hands/legs/feet/main_hand/off_hand/...)
    AppearanceUnlocks per player
        .unlock_appearance(item_id)
        .has_appearance(item_id)
    GlamourSet per player
        .set(slot, target_item_id, appearance_item_id)
        .clear(slot)
        .effective_appearance(slot, currently_equipped_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Slot(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    NECK = "neck"
    EARRING_LEFT = "earring_left"
    EARRING_RIGHT = "earring_right"
    RING_LEFT = "ring_left"
    RING_RIGHT = "ring_right"
    BACK = "back"
    WAIST = "waist"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    RANGED = "ranged"
    AMMO = "ammo"


# Slots that the glamour system can re-skin. Some retail systems
# limit it to visual armor slots only.
GLAMOURABLE_SLOTS: frozenset[Slot] = frozenset({
    Slot.HEAD, Slot.BODY, Slot.HANDS, Slot.LEGS, Slot.FEET,
    Slot.MAIN_HAND, Slot.OFF_HAND, Slot.RANGED, Slot.BACK,
})


@dataclasses.dataclass
class AppearanceUnlocks:
    """Items the player has the right to display, even if no
    longer in inventory."""
    player_id: str
    unlocks: set[str] = dataclasses.field(default_factory=set)

    def unlock_appearance(self, *, item_id: str) -> bool:
        if item_id in self.unlocks:
            return False
        self.unlocks.add(item_id)
        return True

    def has_appearance(self, item_id: str) -> bool:
        return item_id in self.unlocks


@dataclasses.dataclass
class GlamourSet:
    """Per-slot mapping from real item -> appearance item."""
    player_id: str
    overlays: dict[Slot, str] = dataclasses.field(default_factory=dict)

    def set(
        self, *,
        slot: Slot,
        appearance_item_id: str,
        unlocks: AppearanceUnlocks,
    ) -> bool:
        if slot not in GLAMOURABLE_SLOTS:
            return False
        if not unlocks.has_appearance(appearance_item_id):
            return False
        self.overlays[slot] = appearance_item_id
        return True

    def clear(self, *, slot: Slot) -> bool:
        if slot not in self.overlays:
            return False
        del self.overlays[slot]
        return True

    def effective_appearance(
        self, *, slot: Slot, equipped_item_id: t.Optional[str],
    ) -> t.Optional[str]:
        """What item appearance should render in this slot?
        Override if set; else the equipped item itself."""
        return self.overlays.get(slot, equipped_item_id)

    def is_overridden(self, slot: Slot) -> bool:
        return slot in self.overlays

    def overlay_count(self) -> int:
        return len(self.overlays)


__all__ = [
    "Slot", "GLAMOURABLE_SLOTS",
    "AppearanceUnlocks", "GlamourSet",
]
