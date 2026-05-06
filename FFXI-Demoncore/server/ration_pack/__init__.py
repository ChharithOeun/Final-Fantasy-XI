"""Ration pack — pre-portioned travel food.

A ration pack is a compressed, pre-portioned meal sealed
for travel. It trades flavor and magnitude for shelf life
and convenience: you can't reheat a ration (no fire
needed), the buff is modest, but it keeps for 30 days
and consumes in a single menu click — perfect for the
turn-based combat menu, where opening Item > Use > Pack
is a single in-fight action.

Soldiers, expedition leaders, and lazy adventurers all
carry ration packs. Crafted from cooked-meal output
(the cook compresses a meal into pack form, sacrificing
50% of the buff magnitude for portability).

Three contents:
    TRAVEL_RATION   modest str+vit
    SCOUT_BISCUIT   modest dex+regen
    HEALER_TONIC    modest mp_max + refresh

Public surface
--------------
    PackKind enum
    RationPack dataclass (mutable)
    RationPackRegistry
        .pack_from_meal(pack_id, owner_id, kind,
                        source_payload, packed_at) -> bool
        .age_all(dt_seconds) -> int
        .consume(pack_id, consumer_id) -> Optional[BuffPayload]
        .available(pack_id) -> bool
        .total_packs() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload


class PackKind(str, enum.Enum):
    TRAVEL_RATION = "travel_ration"
    SCOUT_BISCUIT = "scout_biscuit"
    HEALER_TONIC = "healer_tonic"


# 30 days real time; the longest in-pack provision shelf
# life so soldiers can stockpile before campaigns.
_RATION_SHELF_SECONDS = 30 * 24 * 3600

# Ration packs sacrifice magnitude for portability.
_PACK_MAGNITUDE_PCT = 50


@dataclasses.dataclass
class RationPack:
    pack_id: str
    owner_id: str
    kind: PackKind
    payload: BuffPayload
    age_seconds: int


def _diminish(payload: BuffPayload) -> BuffPayload:
    """Compress a fresh meal payload into pack form."""
    p = _PACK_MAGNITUDE_PCT / 100
    return BuffPayload(
        str_bonus=int(payload.str_bonus * p),
        dex_bonus=int(payload.dex_bonus * p),
        vit_bonus=int(payload.vit_bonus * p),
        regen_per_tick=int(payload.regen_per_tick * p),
        refresh_per_tick=int(payload.refresh_per_tick * p),
        hp_max_pct=int(payload.hp_max_pct * p),
        mp_max_pct=int(payload.mp_max_pct * p),
        cold_resist=int(payload.cold_resist * p),
        heat_resist=int(payload.heat_resist * p),
        # ration buffs are short — pack is a quick boost,
        # not a feast — half the original duration too.
        duration_seconds=max(1, int(payload.duration_seconds * p)),
    )


@dataclasses.dataclass
class RationPackRegistry:
    _packs: dict[str, RationPack] = dataclasses.field(
        default_factory=dict,
    )

    def pack_from_meal(
        self, *, pack_id: str, owner_id: str,
        kind: PackKind, source_payload: BuffPayload,
        packed_at: int,
    ) -> bool:
        if not pack_id or not owner_id:
            return False
        if pack_id in self._packs:
            return False
        self._packs[pack_id] = RationPack(
            pack_id=pack_id, owner_id=owner_id,
            kind=kind, payload=_diminish(source_payload),
            age_seconds=0,
        )
        return True

    def age_all(self, *, dt_seconds: int) -> int:
        if dt_seconds <= 0:
            return 0
        new_spoils: list[str] = []
        for p in self._packs.values():
            was_edible = p.age_seconds < _RATION_SHELF_SECONDS
            p.age_seconds += dt_seconds
            if was_edible and p.age_seconds >= _RATION_SHELF_SECONDS:
                new_spoils.append(p.pack_id)
        return len(new_spoils)

    def available(self, *, pack_id: str) -> bool:
        p = self._packs.get(pack_id)
        if p is None:
            return False
        return p.age_seconds < _RATION_SHELF_SECONDS

    def consume(
        self, *, pack_id: str, consumer_id: str,
    ) -> t.Optional[BuffPayload]:
        p = self._packs.get(pack_id)
        if p is None:
            return None
        if p.owner_id != consumer_id:
            return None
        if p.age_seconds >= _RATION_SHELF_SECONDS:
            return None
        out = p.payload
        del self._packs[pack_id]
        return out

    def total_packs(self) -> int:
        return len(self._packs)

    def shelf_seconds(self) -> int:
        return _RATION_SHELF_SECONDS


__all__ = [
    "PackKind", "RationPack", "RationPackRegistry",
]
