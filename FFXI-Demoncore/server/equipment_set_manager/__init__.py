"""Equipment set manager — saved gear sets with hot swap.

A player saves NAMED SETS of gear across the 16 equipment slots
(matching equipment_compare). Examples: "WAR/NIN melee", "BLM
nuke", "RDM heal". A SET is a frozen mapping of slot -> item_id.
The manager swaps the player's current loadout to a saved set
on demand, item by item.

Public surface
--------------
    SetKind enum
    EquipmentSet dataclass
    SwapPlan dataclass
    EquipmentSetManager
        .save_set(player_id, name, kind, slot_map)
        .delete_set(player_id, name)
        .rename_set(player_id, old_name, new_name)
        .sets_for(player_id)
        .build_swap_plan(player_id, currently_equipped, name)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

# We borrow EquipSlot from equipment_compare so set entries
# share the same slot vocabulary.
from server.equipment_compare import EquipSlot


# Bounds.
MAX_SETS_PER_PLAYER = 30


class SetKind(str, enum.Enum):
    GENERIC = "generic"
    JOB_RECOMMENDED = "job_recommended"   # the suggested base
    PRECAST = "precast"
    MIDCAST = "midcast"
    POSTCAST = "postcast"
    ENGAGED_MELEE = "engaged_melee"
    IDLE = "idle"
    TP_SET = "tp_set"
    WS_SET = "ws_set"
    NUKE = "nuke"
    HEAL = "heal"


@dataclasses.dataclass(frozen=True)
class EquipmentSet:
    name: str
    kind: SetKind
    slot_map: t.Mapping[EquipSlot, str]


@dataclasses.dataclass(frozen=True)
class SlotSwap:
    slot: EquipSlot
    from_item_id: t.Optional[str]
    to_item_id: t.Optional[str]


@dataclasses.dataclass(frozen=True)
class SwapPlan:
    player_id: str
    set_name: str
    swaps: tuple[SlotSwap, ...]
    no_change_count: int


@dataclasses.dataclass
class EquipmentSetManager:
    max_sets_per_player: int = MAX_SETS_PER_PLAYER
    # player_id -> name -> set
    _sets: dict[
        str, dict[str, EquipmentSet],
    ] = dataclasses.field(default_factory=dict)

    def save_set(
        self, *, player_id: str, name: str,
        kind: SetKind = SetKind.GENERIC,
        slot_map: t.Mapping[EquipSlot, str] = (),
    ) -> t.Optional[EquipmentSet]:
        if not name:
            return None
        player_sets = self._sets.setdefault(
            player_id, {},
        )
        if (
            name not in player_sets
            and len(player_sets) >= self.max_sets_per_player
        ):
            return None
        if not slot_map:
            return None
        # Deduplicate keys in case caller passed a dict-like with
        # weirdness; build a clean dict.
        clean: dict[EquipSlot, str] = {}
        for slot, item_id in dict(slot_map).items():
            if not item_id:
                continue
            clean[slot] = item_id
        if not clean:
            return None
        s = EquipmentSet(
            name=name, kind=kind,
            slot_map=clean,
        )
        player_sets[name] = s
        return s

    def delete_set(
        self, *, player_id: str, name: str,
    ) -> bool:
        sets = self._sets.get(player_id)
        if sets is None or name not in sets:
            return False
        del sets[name]
        return True

    def rename_set(
        self, *, player_id: str,
        old_name: str, new_name: str,
    ) -> bool:
        sets = self._sets.get(player_id)
        if sets is None:
            return False
        if old_name not in sets:
            return False
        if new_name in sets:
            return False
        if not new_name:
            return False
        s = sets.pop(old_name)
        sets[new_name] = EquipmentSet(
            name=new_name, kind=s.kind,
            slot_map=s.slot_map,
        )
        return True

    def get_set(
        self, *, player_id: str, name: str,
    ) -> t.Optional[EquipmentSet]:
        sets = self._sets.get(player_id)
        if sets is None:
            return None
        return sets.get(name)

    def sets_for(
        self, *, player_id: str,
    ) -> tuple[EquipmentSet, ...]:
        sets = self._sets.get(player_id)
        if sets is None:
            return ()
        out = list(sets.values())
        out.sort(key=lambda s: s.name)
        return tuple(out)

    def build_swap_plan(
        self, *, player_id: str, set_name: str,
        currently_equipped: t.Mapping[EquipSlot, str] = (),
    ) -> t.Optional[SwapPlan]:
        s = self.get_set(player_id=player_id, name=set_name)
        if s is None:
            return None
        current = dict(currently_equipped)
        swaps: list[SlotSwap] = []
        unchanged = 0
        # All slots that the saved set OR current loadout
        # touches need consideration.
        all_slots = (
            set(current.keys()) | set(s.slot_map.keys())
        )
        for slot in all_slots:
            cur = current.get(slot)
            target = s.slot_map.get(slot)
            if cur == target:
                unchanged += 1
                continue
            swaps.append(SlotSwap(
                slot=slot,
                from_item_id=cur,
                to_item_id=target,
            ))
        # Deterministic order
        swaps.sort(key=lambda x: x.slot.value)
        return SwapPlan(
            player_id=player_id, set_name=set_name,
            swaps=tuple(swaps),
            no_change_count=unchanged,
        )

    def total_sets(
        self, *, player_id: str,
    ) -> int:
        return len(self._sets.get(player_id, {}))


__all__ = [
    "MAX_SETS_PER_PLAYER",
    "SetKind",
    "EquipmentSet", "SlotSwap", "SwapPlan",
    "EquipmentSetManager",
]
