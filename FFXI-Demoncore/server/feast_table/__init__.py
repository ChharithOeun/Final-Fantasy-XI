"""Feast table — one big dish, the whole party eats.

A solo cook makes a Hunter's Stew for one player. A
*feast* takes more ingredients and cooks ONE big pot for
the whole party. Every member gets the buff (slightly
reduced — one stew can't fully nourish six people), and
crucially everyone gets it on the same timer, which
synchronizes party rotations.

The mechanic encourages parties to eat together before
a big fight: you trade some peak power for shared
buffs and a moment of camaraderie.

Lifecycle
---------
1. host opens a feast (declares dish, invites party)
2. members can join (must be in the party already)
3. host commits — feast becomes ACTIVE, buff applied
   to all current members; latecomers can no longer join
4. feast expires after duration; buffs drop on schedule

A member who joined late and missed commit gets nothing.

Public surface
--------------
    FeastState enum
    FeastSession dataclass (mutable)
    FeastTable
        .open(feast_id, host_id, dish_token, ingredient_pot,
              opened_at) -> bool
        .join(feast_id, joiner_id) -> bool
        .commit(feast_id, payload) -> Optional[list[str]]
            (returns participant ids who got buffed; None if bad)
        .members(feast_id) -> list[str]
        .state(feast_id) -> Optional[FeastState]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload


class FeastState(str, enum.Enum):
    OPEN = "open"           # accepting joiners
    ACTIVE = "active"       # buffed, joiners locked
    EXPIRED = "expired"     # timer ran out


# Feast applies buffs at this fraction of the original
# magnitude — one pot fed to N people. Tuned so a feast
# is desirable (synced timer + zero per-person ingredient
# cost) without making solo cooking obsolete.
_FEAST_BUFF_PCT = 75


@dataclasses.dataclass
class FeastSession:
    feast_id: str
    host_id: str
    dish_token: str
    members: list[str]
    state: FeastState
    opened_at: int
    committed_at: int


@dataclasses.dataclass
class FeastTable:
    _feasts: dict[str, FeastSession] = dataclasses.field(
        default_factory=dict,
    )

    def open(
        self, *, feast_id: str, host_id: str,
        dish_token: str, opened_at: int,
    ) -> bool:
        if not feast_id or not host_id or not dish_token:
            return False
        if feast_id in self._feasts:
            return False
        self._feasts[feast_id] = FeastSession(
            feast_id=feast_id, host_id=host_id,
            dish_token=dish_token, members=[host_id],
            state=FeastState.OPEN, opened_at=opened_at,
            committed_at=0,
        )
        return True

    def join(
        self, *, feast_id: str, joiner_id: str,
    ) -> bool:
        f = self._feasts.get(feast_id)
        if f is None:
            return False
        if f.state != FeastState.OPEN:
            return False
        if not joiner_id:
            return False
        if joiner_id in f.members:
            return False
        f.members.append(joiner_id)
        return True

    def commit(
        self, *, feast_id: str, payload: BuffPayload,
        committed_at: int,
    ) -> t.Optional[tuple[list[str], BuffPayload]]:
        f = self._feasts.get(feast_id)
        if f is None:
            return None
        if f.state != FeastState.OPEN:
            return None
        f.state = FeastState.ACTIVE
        f.committed_at = committed_at
        # Build the per-person reduced payload. Duration
        # is unchanged — feast still lasts the full time.
        feast_payload = BuffPayload(
            str_bonus=int(payload.str_bonus * _FEAST_BUFF_PCT / 100),
            dex_bonus=int(payload.dex_bonus * _FEAST_BUFF_PCT / 100),
            vit_bonus=int(payload.vit_bonus * _FEAST_BUFF_PCT / 100),
            regen_per_tick=int(
                payload.regen_per_tick * _FEAST_BUFF_PCT / 100,
            ),
            refresh_per_tick=int(
                payload.refresh_per_tick * _FEAST_BUFF_PCT / 100,
            ),
            hp_max_pct=int(payload.hp_max_pct * _FEAST_BUFF_PCT / 100),
            mp_max_pct=int(payload.mp_max_pct * _FEAST_BUFF_PCT / 100),
            cold_resist=int(payload.cold_resist * _FEAST_BUFF_PCT / 100),
            heat_resist=int(payload.heat_resist * _FEAST_BUFF_PCT / 100),
            duration_seconds=payload.duration_seconds,
        )
        return (list(f.members), feast_payload)

    def expire(self, *, feast_id: str) -> bool:
        f = self._feasts.get(feast_id)
        if f is None:
            return False
        if f.state == FeastState.EXPIRED:
            return False
        f.state = FeastState.EXPIRED
        return True

    def members(self, *, feast_id: str) -> list[str]:
        f = self._feasts.get(feast_id)
        if f is None:
            return []
        return list(f.members)

    def state(
        self, *, feast_id: str,
    ) -> t.Optional[FeastState]:
        f = self._feasts.get(feast_id)
        if f is None:
            return None
        return f.state

    def total_feasts(self) -> int:
        return len(self._feasts)


__all__ = [
    "FeastState", "FeastSession", "FeastTable",
]
