"""Insulation clothing — gear that mitigates exposure.

Each equipped piece (head/body/hands/legs/feet/cloak) has
an insulation_rating measured in two channels:
    cold_rating    fights HP drain in cold zones
    heat_rating    fights MP drain in hot zones

The aggregate insulation feeds exposure_damage. Ratings
stack additively across equipped slots.

Some pieces are SEASONAL (winter-only or summer-only) —
wearing the wrong one in the wrong climate gives you
a small comfort penalty (-5 effective rating) representing
discomfort and sweat.

Public surface
--------------
    GarmentSlot enum
    GarmentProfile dataclass (frozen)
    InsulationLoadout dataclass (mutable)
    InsulationCalculator
        .define_garment(garment_id, slot, cold, heat,
                        seasonal=None) -> bool
        .equip(player_id, garment_id) -> bool
        .unequip(player_id, slot) -> bool
        .total_cold(player_id, current_climate=None) -> int
        .total_heat(player_id, current_climate=None) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GarmentSlot(str, enum.Enum):
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    CLOAK = "cloak"


@dataclasses.dataclass(frozen=True)
class GarmentProfile:
    garment_id: str
    slot: GarmentSlot
    cold_rating: int
    heat_rating: int
    seasonal: t.Optional[str] = None    # "winter" / "summer" / None


@dataclasses.dataclass
class InsulationLoadout:
    player_id: str
    equipped: dict[GarmentSlot, str] = dataclasses.field(
        default_factory=dict,
    )


_DISCOMFORT_PENALTY = 5


@dataclasses.dataclass
class InsulationCalculator:
    _garments: dict[str, GarmentProfile] = dataclasses.field(
        default_factory=dict,
    )
    _loadouts: dict[str, InsulationLoadout] = dataclasses.field(
        default_factory=dict,
    )

    def define_garment(
        self, *, garment_id: str, slot: GarmentSlot,
        cold_rating: int = 0, heat_rating: int = 0,
        seasonal: t.Optional[str] = None,
    ) -> bool:
        if not garment_id:
            return False
        if cold_rating < 0 or heat_rating < 0:
            return False
        if garment_id in self._garments:
            return False
        self._garments[garment_id] = GarmentProfile(
            garment_id=garment_id, slot=slot,
            cold_rating=cold_rating, heat_rating=heat_rating,
            seasonal=seasonal,
        )
        return True

    def equip(
        self, *, player_id: str, garment_id: str,
    ) -> bool:
        if not player_id:
            return False
        g = self._garments.get(garment_id)
        if g is None:
            return False
        lo = self._loadouts.setdefault(
            player_id, InsulationLoadout(player_id=player_id),
        )
        lo.equipped[g.slot] = garment_id
        return True

    def unequip(
        self, *, player_id: str, slot: GarmentSlot,
    ) -> bool:
        lo = self._loadouts.get(player_id)
        if lo is None:
            return False
        if slot not in lo.equipped:
            return False
        del lo.equipped[slot]
        return True

    def _aggregate(
        self, *, player_id: str,
        current_climate: t.Optional[str],
        channel: str,
    ) -> int:
        lo = self._loadouts.get(player_id)
        if lo is None:
            return 0
        total = 0
        for slot, gid in lo.equipped.items():
            g = self._garments.get(gid)
            if g is None:
                continue
            base = g.cold_rating if channel == "cold" else g.heat_rating
            # discomfort penalty if wrong-season garment
            if (g.seasonal is not None
                    and current_climate is not None):
                if g.seasonal != current_climate:
                    base = max(0, base - _DISCOMFORT_PENALTY)
            total += base
        return total

    def total_cold(
        self, *, player_id: str,
        current_climate: t.Optional[str] = None,
    ) -> int:
        return self._aggregate(
            player_id=player_id,
            current_climate=current_climate,
            channel="cold",
        )

    def total_heat(
        self, *, player_id: str,
        current_climate: t.Optional[str] = None,
    ) -> int:
        return self._aggregate(
            player_id=player_id,
            current_climate=current_climate,
            channel="heat",
        )

    def equipped_in_slot(
        self, *, player_id: str, slot: GarmentSlot,
    ) -> t.Optional[str]:
        lo = self._loadouts.get(player_id)
        if lo is None:
            return None
        return lo.equipped.get(slot)

    def total_garments_defined(self) -> int:
        return len(self._garments)


__all__ = [
    "GarmentSlot", "GarmentProfile", "InsulationLoadout",
    "InsulationCalculator",
]
