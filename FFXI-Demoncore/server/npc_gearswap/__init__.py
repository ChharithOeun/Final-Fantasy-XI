"""NPC gearswap — bosses and NMs swap gear sets like players do.

The marquee Windower/Ashita addon is GearSwap: equip the
right armor for the moment — precast haste set for cast
time, midcast MAB set for damage, idle refresh set for
downtime, TP set for engaged auto-attacks, WS set for the
weaponskill, magic burst set for the burst window.

This module makes that capability available to NPCs as
well. A boss with a gearswap profile cycles through gear
sets on the same triggers a player would: PRECAST when
casting starts, MIDCAST mid-cast, ENGAGED when in melee
range, MAGIC_BURST when riding a skillchain, IDLE when
disengaged, WS when launching a weaponskill.

Why this matters: the same toolbox players use against
bosses, bosses can use back. A WHM avatar swapping into
a Cure Potency set mid-cast is the same code path as a
Maat NM swapping into his Hundred Fists TP set.

Public surface
--------------
    GearTrigger enum (PRECAST/MIDCAST/ENGAGED/MAGIC_BURST/
                      IDLE/WEAPONSKILL)
    GearSet dataclass (frozen)
    NpcGearswapRegistry
        .define_profile(npc_id, sets) -> bool
        .swap_for(npc_id, trigger) -> Optional[GearSet]
        .current_set(npc_id) -> Optional[GearSet]
        .reset(npc_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GearTrigger(str, enum.Enum):
    PRECAST = "precast"
    MIDCAST = "midcast"
    ENGAGED = "engaged"
    MAGIC_BURST = "magic_burst"
    IDLE = "idle"
    WEAPONSKILL = "weaponskill"


@dataclasses.dataclass(frozen=True)
class GearSet:
    set_name: str
    # slot → item_id; slots match equipment_stats convention
    # ("main", "sub", "ranged", "head", "neck", "ear1", "ear2",
    #  "body", "hands", "ring1", "ring2", "back", "waist",
    #  "legs", "feet")
    items: dict[str, str]


@dataclasses.dataclass
class _NpcProfile:
    npc_id: str
    sets: dict[GearTrigger, GearSet]
    current_trigger: t.Optional[GearTrigger]


@dataclasses.dataclass
class NpcGearswapRegistry:
    _profiles: dict[str, _NpcProfile] = dataclasses.field(
        default_factory=dict,
    )

    def define_profile(
        self, *, npc_id: str,
        sets: dict[GearTrigger, GearSet],
    ) -> bool:
        if not npc_id:
            return False
        if npc_id in self._profiles:
            return False
        if not sets:
            return False
        # validate that every set has at least one item slot
        for trig, gs in sets.items():
            if not gs.items:
                return False
        self._profiles[npc_id] = _NpcProfile(
            npc_id=npc_id, sets=dict(sets),
            current_trigger=None,
        )
        return True

    def swap_for(
        self, *, npc_id: str, trigger: GearTrigger,
    ) -> t.Optional[GearSet]:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return None
        gs = prof.sets.get(trigger)
        if gs is None:
            # No set defined for this trigger; current stays.
            return None
        prof.current_trigger = trigger
        return gs

    def current_set(
        self, *, npc_id: str,
    ) -> t.Optional[GearSet]:
        prof = self._profiles.get(npc_id)
        if prof is None or prof.current_trigger is None:
            return None
        return prof.sets.get(prof.current_trigger)

    def has_set_for(
        self, *, npc_id: str, trigger: GearTrigger,
    ) -> bool:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return False
        return trigger in prof.sets

    def reset(self, *, npc_id: str) -> bool:
        prof = self._profiles.get(npc_id)
        if prof is None:
            return False
        prof.current_trigger = None
        return True

    def total_profiles(self) -> int:
        return len(self._profiles)


__all__ = [
    "GearTrigger", "GearSet", "NpcGearswapRegistry",
]
