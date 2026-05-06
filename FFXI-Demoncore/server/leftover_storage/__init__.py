"""Leftover storage — yesterday's stew is half as good.

A cooked meal isn't always eaten on the spot. Save a
portion in your pack and eat it later — but the buff
will be reduced and the food won't keep forever.
After the spoil window, leftovers go inedible.

The pattern: store a portion + payload, the registry
keeps it for `shelf_life_seconds`. consume() returns a
diminished payload while the leftover is still fresh;
returns None if expired or unknown.

Two diminishment levers:
  - **age**:   linear decay from 100% (fresh) to 50%
               (just before spoiling)
  - **reheat**: each reheat further trims duration

The diminishment is *deliberately steep* — leftovers
are a backup, not a replacement for cooking fresh.

Public surface
--------------
    LeftoverState enum (FRESH/STALE/SPOILED)
    Leftover dataclass (mutable)
    LeftoverStorage
        .stash(leftover_id, owner_id, dish, payload,
               shelf_life_seconds, stashed_at) -> bool
        .age_all(dt_seconds) -> int (count of new spoils)
        .consume(leftover_id, consumer_id, now)
            -> Optional[BuffPayload]
        .state_of(leftover_id, now) -> LeftoverState
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload, DishKind


class LeftoverState(str, enum.Enum):
    FRESH = "fresh"
    STALE = "stale"      # past 50% shelf life, still edible
    SPOILED = "spoiled"  # cannot consume


# Reheating reduces buff DURATION (you used some food
# energy to warm the rest). Magnitude stays linear with
# age — that's the freshness penalty.
_REHEAT_DURATION_PCT = 80


@dataclasses.dataclass
class Leftover:
    leftover_id: str
    owner_id: str
    dish: DishKind
    payload: BuffPayload
    shelf_life_seconds: int
    stashed_at: int
    age_seconds: int
    reheats: int


def _state_for(age: int, shelf: int) -> LeftoverState:
    if shelf <= 0:
        return LeftoverState.SPOILED
    if age >= shelf:
        return LeftoverState.SPOILED
    if age >= shelf // 2:
        return LeftoverState.STALE
    return LeftoverState.FRESH


def _diminished(
    payload: BuffPayload, age: int, shelf: int, reheats: int,
) -> BuffPayload:
    # magnitude factor: 1.0 at age=0, 0.5 just before spoil
    if shelf <= 0:
        mag = 0.0
    else:
        ratio = age / shelf
        if ratio < 0:
            ratio = 0.0
        if ratio > 1:
            ratio = 1.0
        mag = 1.0 - 0.5 * ratio
    # duration factor stacks reheats
    dur_factor = 1.0
    for _ in range(reheats):
        dur_factor *= _REHEAT_DURATION_PCT / 100
    return BuffPayload(
        str_bonus=int(payload.str_bonus * mag),
        dex_bonus=int(payload.dex_bonus * mag),
        vit_bonus=int(payload.vit_bonus * mag),
        regen_per_tick=int(payload.regen_per_tick * mag),
        refresh_per_tick=int(payload.refresh_per_tick * mag),
        hp_max_pct=int(payload.hp_max_pct * mag),
        mp_max_pct=int(payload.mp_max_pct * mag),
        cold_resist=int(payload.cold_resist * mag),
        heat_resist=int(payload.heat_resist * mag),
        duration_seconds=max(
            1, int(payload.duration_seconds * dur_factor),
        ),
    )


@dataclasses.dataclass
class LeftoverStorage:
    _leftovers: dict[str, Leftover] = dataclasses.field(
        default_factory=dict,
    )

    def stash(
        self, *, leftover_id: str, owner_id: str,
        dish: DishKind, payload: BuffPayload,
        shelf_life_seconds: int, stashed_at: int,
    ) -> bool:
        if not leftover_id or not owner_id:
            return False
        if leftover_id in self._leftovers:
            return False
        if shelf_life_seconds <= 0:
            return False
        self._leftovers[leftover_id] = Leftover(
            leftover_id=leftover_id, owner_id=owner_id,
            dish=dish, payload=payload,
            shelf_life_seconds=shelf_life_seconds,
            stashed_at=stashed_at, age_seconds=0,
            reheats=0,
        )
        return True

    def age_all(self, *, dt_seconds: int) -> int:
        if dt_seconds <= 0:
            return 0
        new_spoils: list[str] = []
        for lo in self._leftovers.values():
            was_edible = lo.age_seconds < lo.shelf_life_seconds
            lo.age_seconds += dt_seconds
            if was_edible and \
                    lo.age_seconds >= lo.shelf_life_seconds:
                new_spoils.append(lo.leftover_id)
        return len(new_spoils)

    def consume(
        self, *, leftover_id: str, consumer_id: str,
    ) -> t.Optional[BuffPayload]:
        lo = self._leftovers.get(leftover_id)
        if lo is None:
            return None
        if lo.owner_id != consumer_id:
            return None
        if lo.age_seconds >= lo.shelf_life_seconds:
            return None
        out = _diminished(
            lo.payload, lo.age_seconds,
            lo.shelf_life_seconds, lo.reheats,
        )
        del self._leftovers[leftover_id]
        return out

    def reheat(self, *, leftover_id: str) -> bool:
        lo = self._leftovers.get(leftover_id)
        if lo is None:
            return False
        if lo.age_seconds >= lo.shelf_life_seconds:
            return False
        lo.reheats += 1
        return True

    def state_of(
        self, *, leftover_id: str,
    ) -> t.Optional[LeftoverState]:
        lo = self._leftovers.get(leftover_id)
        if lo is None:
            return None
        return _state_for(lo.age_seconds, lo.shelf_life_seconds)

    def total_leftovers(self) -> int:
        return len(self._leftovers)


__all__ = [
    "LeftoverState", "Leftover", "LeftoverStorage",
]
