"""Meal buff engine — apply cooked-dish buffs to players.

Once a player eats a cooked dish, the BuffPayload that
came out of cookpot_recipes needs to do something. This
module is the runtime that holds active buffs and ticks
them down, with three rules baked in:

1. **One meal at a time.** A player has at most ONE
   active meal buff. Eating again *replaces* the prior
   buff — the body can only digest so much. (Snacks /
   drinks live in a separate slot and stack with meals.)
2. **A drink stacks alongside a meal.** Warming tea +
   hunter's stew can both be active. The per-stat result
   is the additive sum.
3. **Time consumes the buff.** tick(dt_seconds) reduces
   each buff's remaining time; expired ones drop off.

The engine doesn't know how to apply str_bonus to combat
math — that's the caller's job. This module's
responsibility is just "what's currently active for
player X" and "tell me their summed bonuses".

Public surface
--------------
    BuffSlot enum (MEAL/DRINK)
    ActiveBuff dataclass (mutable)
    AggregateBonus dataclass (frozen) — summed across slots
    MealBuffEngine
        .apply(player_id, slot, payload, applied_at) -> bool
        .tick(dt_seconds) -> int  (count of expired)
        .aggregate_for(player_id) -> AggregateBonus
        .clear(player_id) -> int  (count cleared)
        .has_buff(player_id, slot) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload


class BuffSlot(str, enum.Enum):
    MEAL = "meal"     # main dish, one at a time
    DRINK = "drink"   # tea/draught, stacks with meal


@dataclasses.dataclass
class ActiveBuff:
    player_id: str
    slot: BuffSlot
    payload: BuffPayload
    applied_at: int
    seconds_remaining: int


@dataclasses.dataclass(frozen=True)
class AggregateBonus:
    str_bonus: int
    dex_bonus: int
    vit_bonus: int
    regen_per_tick: int
    refresh_per_tick: int
    hp_max_pct: int
    mp_max_pct: int
    cold_resist: int
    heat_resist: int


_ZERO_AGG = AggregateBonus(
    str_bonus=0, dex_bonus=0, vit_bonus=0,
    regen_per_tick=0, refresh_per_tick=0,
    hp_max_pct=0, mp_max_pct=0,
    cold_resist=0, heat_resist=0,
)


@dataclasses.dataclass
class MealBuffEngine:
    # keyed by (player_id, slot) — at most one per slot
    _active: dict[tuple[str, BuffSlot], ActiveBuff] = \
        dataclasses.field(default_factory=dict)

    def apply(
        self, *, player_id: str, slot: BuffSlot,
        payload: BuffPayload, applied_at: int,
    ) -> bool:
        if not player_id:
            return False
        if payload.duration_seconds <= 0:
            return False
        # replace any existing buff in the same slot —
        # the body can only digest one meal at a time
        self._active[(player_id, slot)] = ActiveBuff(
            player_id=player_id, slot=slot,
            payload=payload, applied_at=applied_at,
            seconds_remaining=payload.duration_seconds,
        )
        return True

    def tick(self, *, dt_seconds: int) -> int:
        if dt_seconds <= 0:
            return 0
        expired: list[tuple[str, BuffSlot]] = []
        for k, buff in self._active.items():
            buff.seconds_remaining -= dt_seconds
            if buff.seconds_remaining <= 0:
                expired.append(k)
        for k in expired:
            del self._active[k]
        return len(expired)

    def aggregate_for(
        self, *, player_id: str,
    ) -> AggregateBonus:
        if not player_id:
            return _ZERO_AGG
        # sum across all slots for this player
        s_str = s_dex = s_vit = 0
        s_regen = s_refresh = 0
        s_hp = s_mp = 0
        s_cold = s_heat = 0
        any_found = False
        for (pid, _slot), buff in self._active.items():
            if pid != player_id:
                continue
            any_found = True
            p = buff.payload
            s_str += p.str_bonus
            s_dex += p.dex_bonus
            s_vit += p.vit_bonus
            s_regen += p.regen_per_tick
            s_refresh += p.refresh_per_tick
            s_hp += p.hp_max_pct
            s_mp += p.mp_max_pct
            s_cold += p.cold_resist
            s_heat += p.heat_resist
        if not any_found:
            return _ZERO_AGG
        return AggregateBonus(
            str_bonus=s_str, dex_bonus=s_dex, vit_bonus=s_vit,
            regen_per_tick=s_regen, refresh_per_tick=s_refresh,
            hp_max_pct=s_hp, mp_max_pct=s_mp,
            cold_resist=s_cold, heat_resist=s_heat,
        )

    def clear(self, *, player_id: str) -> int:
        keys = [k for k in self._active if k[0] == player_id]
        for k in keys:
            del self._active[k]
        return len(keys)

    def has_buff(
        self, *, player_id: str, slot: BuffSlot,
    ) -> bool:
        return (player_id, slot) in self._active

    def total_active(self) -> int:
        return len(self._active)


__all__ = [
    "BuffSlot", "ActiveBuff", "AggregateBonus",
    "MealBuffEngine",
]
