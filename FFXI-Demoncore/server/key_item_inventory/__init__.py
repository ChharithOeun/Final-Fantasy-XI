"""Key item inventory — global registry + per-player holdings.

Key items aren't regular items. They:
* don't take an inventory slot
* can't be traded, dropped, or stored
* are usually quest/mission gates or zone passes
* are unique per player (you have it or you don't — no stacks)

Public surface
--------------
    KeyItemCategory enum (MISSION / ZONE_KEY / QUEST / EVENT)
    KeyItem dataclass / KEY_ITEM_CATALOG
    PlayerKeyItems
        .grant(ki_id) / .revoke(ki_id) / .has(ki_id)
        .has_all(*ids) / .holdings property
    can_enter_zone(zone_id, ki) -> bool
    can_start_quest(quest_id, ki) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class KeyItemCategory(str, enum.Enum):
    MISSION = "mission"
    ZONE_KEY = "zone_key"
    QUEST = "quest"
    EVENT = "event"
    EXPANSION = "expansion"


@dataclasses.dataclass(frozen=True)
class KeyItem:
    ki_id: str
    label: str
    category: KeyItemCategory
    description: str = ""


# Sample catalog — covers the major use cases
KEY_ITEM_CATALOG: dict[str, KeyItem] = {
    # Mission gates
    "airship_pass": KeyItem(
        "airship_pass", "Airship Pass",
        KeyItemCategory.MISSION,
        "Granted upon completing nation rank 5",
    ),
    "rank_10_glory": KeyItem(
        "rank_10_glory", "Glory of the Nation",
        KeyItemCategory.MISSION,
    ),
    # Zone keys
    "ancient_lockbox_key": KeyItem(
        "ancient_lockbox_key", "Ancient Lockbox Key",
        KeyItemCategory.ZONE_KEY,
    ),
    "sky_orb": KeyItem(
        "sky_orb", "Eyes of the Believer",
        KeyItemCategory.ZONE_KEY,
        "Required to enter Tu'Lia",
    ),
    "sea_orb": KeyItem(
        "sea_orb", "Whisper of the Sea",
        KeyItemCategory.ZONE_KEY,
        "Required to enter Al'Taieu",
    ),
    "dynamis_token": KeyItem(
        "dynamis_token", "Dynamis Token",
        KeyItemCategory.ZONE_KEY,
    ),
    # Quest items
    "moogle_kupowers": KeyItem(
        "moogle_kupowers", "Moogle's Kupowers",
        KeyItemCategory.QUEST,
    ),
    "kingmakers_seal": KeyItem(
        "kingmakers_seal", "Kingmaker's Seal",
        KeyItemCategory.QUEST,
    ),
    # Events
    "vana_fete_pin": KeyItem(
        "vana_fete_pin", "Vana'fete Pin",
        KeyItemCategory.EVENT,
    ),
    # Expansion-tier
    "rhapsodies_progress": KeyItem(
        "rhapsodies_progress", "Rhapsody in White",
        KeyItemCategory.EXPANSION,
    ),
}


# Zone gates — which KI is required for which zone
_ZONE_GATES: dict[str, str] = {
    "tu_lia": "sky_orb",
    "al_taieu": "sea_orb",
    "dynamis_jeuno": "dynamis_token",
    "dynamis_bastok": "dynamis_token",
}


# Quest gates
_QUEST_GATES: dict[str, str] = {
    "starter_kupowers_quest": "moogle_kupowers",
    "kingmaker_quest": "kingmakers_seal",
}


@dataclasses.dataclass
class PlayerKeyItems:
    player_id: str
    _holdings: set[str] = dataclasses.field(default_factory=set)

    @property
    def holdings(self) -> frozenset[str]:
        return frozenset(self._holdings)

    def has(self, ki_id: str) -> bool:
        return ki_id in self._holdings

    def has_all(self, *ki_ids: str) -> bool:
        return all(k in self._holdings for k in ki_ids)

    def grant(self, *, ki_id: str) -> bool:
        if ki_id not in KEY_ITEM_CATALOG:
            return False
        if ki_id in self._holdings:
            return False
        self._holdings.add(ki_id)
        return True

    def revoke(self, *, ki_id: str) -> bool:
        if ki_id not in self._holdings:
            return False
        self._holdings.remove(ki_id)
        return True


def can_enter_zone(*, zone_id: str,
                    player_ki: PlayerKeyItems) -> bool:
    required = _ZONE_GATES.get(zone_id)
    if required is None:
        return True   # no key item gate
    return player_ki.has(required)


def can_start_quest(*, quest_id: str,
                     player_ki: PlayerKeyItems) -> bool:
    required = _QUEST_GATES.get(quest_id)
    if required is None:
        return True
    return player_ki.has(required)


__all__ = [
    "KeyItemCategory", "KeyItem", "KEY_ITEM_CATALOG",
    "PlayerKeyItems",
    "can_enter_zone", "can_start_quest",
]
