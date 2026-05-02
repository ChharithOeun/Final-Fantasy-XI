"""Mob respawn — per-mob respawn timer + variance + ToD gates.

Each mob has a base respawn time after death, with a +/- variance
window so packs don't pop on a perfect cadence. Some mobs only
spawn during NIGHT or DAY ToD windows.

Public surface
--------------
    RespawnRule (base, variance, tod_gate)
    RespawnTracker
        .record_kill(mob_id, now_tick, rng_pool)
        .due_for_respawn(mob_id, now_tick, vanadiel_hour)
        .is_alive(mob_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.rng_pool import RngPool, STREAM_ENCOUNTER_GEN


class ToDGate(str, enum.Enum):
    ANY = "any"
    NIGHT = "night"      # Vana 20:00 - 5:59
    DAY = "day"          # Vana 6:00 - 19:59


@dataclasses.dataclass(frozen=True)
class RespawnRule:
    base_seconds: int
    variance_seconds: int = 0
    tod_gate: ToDGate = ToDGate.ANY


def _is_night(hour: int) -> bool:
    return hour >= 20 or hour < 6


def _tod_open(gate: ToDGate, hour: int) -> bool:
    if gate == ToDGate.ANY:
        return True
    if gate == ToDGate.NIGHT:
        return _is_night(hour)
    if gate == ToDGate.DAY:
        return not _is_night(hour)
    return False


@dataclasses.dataclass
class _MobState:
    alive: bool = True
    last_kill_tick: t.Optional[int] = None
    next_respawn_tick: t.Optional[int] = None


@dataclasses.dataclass
class RespawnTracker:
    rules: dict[str, RespawnRule] = dataclasses.field(
        default_factory=dict,
    )
    states: dict[str, _MobState] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def register_mob(
        self, *, mob_id: str, rule: RespawnRule,
    ) -> None:
        if rule.base_seconds <= 0:
            raise ValueError("base_seconds must be > 0")
        if rule.variance_seconds < 0:
            raise ValueError("variance must be >= 0")
        self.rules[mob_id] = rule
        self.states[mob_id] = _MobState()

    def record_kill(
        self, *,
        mob_id: str, now_tick: int,
        rng_pool: t.Optional[RngPool] = None,
        stream_name: str = STREAM_ENCOUNTER_GEN,
    ) -> bool:
        if mob_id not in self.rules:
            return False
        rule = self.rules[mob_id]
        state = self.states[mob_id]
        if not state.alive:
            return False
        state.alive = False
        state.last_kill_tick = now_tick
        # Compute next respawn with variance
        offset = rule.base_seconds
        if rule.variance_seconds > 0 and rng_pool is not None:
            rng = rng_pool.stream(stream_name)
            jitter = rng.randint(
                -rule.variance_seconds, rule.variance_seconds,
            )
            offset = max(1, offset + jitter)
        state.next_respawn_tick = now_tick + offset
        return True

    def is_alive(self, mob_id: str) -> bool:
        state = self.states.get(mob_id)
        return state is not None and state.alive

    def due_for_respawn(
        self, *,
        mob_id: str, now_tick: int, vanadiel_hour: int,
    ) -> bool:
        if mob_id not in self.rules:
            return False
        state = self.states[mob_id]
        if state.alive:
            return False
        if state.next_respawn_tick is None:
            return False
        if now_tick < state.next_respawn_tick:
            return False
        rule = self.rules[mob_id]
        if not _tod_open(rule.tod_gate, vanadiel_hour):
            return False
        return True

    def respawn(self, *, mob_id: str) -> bool:
        if mob_id not in self.states:
            return False
        state = self.states[mob_id]
        if state.alive:
            return False
        state.alive = True
        state.next_respawn_tick = None
        return True


__all__ = [
    "ToDGate", "RespawnRule",
    "RespawnTracker",
]
