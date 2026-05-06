"""Leftover storage — yesterday's stew is half as good.

A cooked meal isn't always eaten on the spot. Save a
portion in your pack and eat it later — but the buff
will be reduced and the food won't keep forever.
After the spoil window, leftovers go inedible.

Tuning notes (set by design):
    Food shelf life:   7 full days
    Drink shelf life:  ~3 months (90 days)

These are intentionally generous so a player who cooks
a stack on the weekend can use it through the week. The
diminishing magnitude (100% → 50%) keeps a "fresh is
better" pressure even with the long window.

Provision provenance:
    PLAYER_MADE  — ages immediately on stash()
    NPC_STOCKED  — does NOT age until first sale; once
                   transfer_to_player() flips it to
                   PLAYER_MADE, normal aging applies.
                   This prevents a player cook from
                   buying out NPC stocks to corner the
                   market on a slow-decaying drink.

Two diminishment levers:
  - **age**:   linear decay from 100% (fresh) to 50%
               (just before spoiling)
  - **reheat**: each reheat further trims duration

Public surface
--------------
    LeftoverState enum (FRESH/STALE/SPOILED)
    ProvisionKind enum (FOOD/DRINK)
    Provenance enum (PLAYER_MADE/NPC_STOCKED)
    Leftover dataclass (mutable)
    LeftoverStorage
        .stash(...) — shelf_life optional; default by kind
        .age_all(dt_seconds)
        .consume(leftover_id, consumer_id) -> Optional[BuffPayload]
        .reheat(leftover_id) -> bool
        .state_of(leftover_id) -> Optional[LeftoverState]
        .transfer_to_player(leftover_id, new_owner)
            (NPC_STOCKED → PLAYER_MADE; aging starts here)
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


class ProvisionKind(str, enum.Enum):
    FOOD = "food"
    DRINK = "drink"


class Provenance(str, enum.Enum):
    PLAYER_MADE = "player_made"     # ages on every age_all()
    NPC_STOCKED = "npc_stocked"     # frozen until purchased


# Default shelf life by kind (real-time seconds).
# Set by design — generous so a weekend cook can use stock
# through the week, drinks travel-stable for months.
_DEFAULT_SHELF_FOOD = 7 * 24 * 3600          # 7 days
_DEFAULT_SHELF_DRINK = 90 * 24 * 3600        # ~3 months

_DEFAULT_SHELF: dict[ProvisionKind, int] = {
    ProvisionKind.FOOD: _DEFAULT_SHELF_FOOD,
    ProvisionKind.DRINK: _DEFAULT_SHELF_DRINK,
}

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
    kind: ProvisionKind = ProvisionKind.FOOD
    provenance: Provenance = Provenance.PLAYER_MADE


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
        stashed_at: int,
        shelf_life_seconds: t.Optional[int] = None,
        kind: ProvisionKind = ProvisionKind.FOOD,
        provenance: Provenance = Provenance.PLAYER_MADE,
    ) -> bool:
        if not leftover_id or not owner_id:
            return False
        if leftover_id in self._leftovers:
            return False
        # Default shelf life from kind unless caller overrode.
        if shelf_life_seconds is None:
            shelf_life_seconds = _DEFAULT_SHELF[kind]
        if shelf_life_seconds <= 0:
            return False
        self._leftovers[leftover_id] = Leftover(
            leftover_id=leftover_id, owner_id=owner_id,
            dish=dish, payload=payload,
            shelf_life_seconds=shelf_life_seconds,
            stashed_at=stashed_at, age_seconds=0,
            reheats=0, kind=kind, provenance=provenance,
        )
        return True

    def transfer_to_player(
        self, *, leftover_id: str, new_owner_id: str,
    ) -> bool:
        """Sale/handoff from NPC to player.

        Flips provenance from NPC_STOCKED → PLAYER_MADE so
        aging starts. Refuses if the item is already
        player-owned (caller should use a different path
        for player-to-player trades, which preserve aging).
        """
        lo = self._leftovers.get(leftover_id)
        if lo is None:
            return False
        if not new_owner_id:
            return False
        if lo.provenance != Provenance.NPC_STOCKED:
            return False
        lo.owner_id = new_owner_id
        lo.provenance = Provenance.PLAYER_MADE
        return True

    def age_all(self, *, dt_seconds: int) -> int:
        if dt_seconds <= 0:
            return 0
        new_spoils: list[str] = []
        for lo in self._leftovers.values():
            # NPC-stocked provisions are frozen until sold.
            # This prevents player cooks from buying out
            # NPC stocks and waiting for them to spoil.
            if lo.provenance == Provenance.NPC_STOCKED:
                continue
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
    "LeftoverState", "ProvisionKind", "Provenance",
    "Leftover", "LeftoverStorage",
]
