"""Banquet hall — town-scale public feasts.

feast_table is for parties (small, intimate, host-driven).
A banquet is a town-scale event hosted by an NPC chef
during festivals or anniversaries. Players walk into
the hall, the buff is applied passively by proximity,
and the feast runs on a server clock — show up while
it's open and you're fed.

Banquets stack a *small* aura on top of any meal/drink
buff a player already has — the magnitude is just enough
to be a "free hot meal in the city" benefit, not a
combat-defining stack. The intent is encouraging players
to gather in town during events.

Lifecycle
---------
    SCHEDULED   declared, not started
    SERVING     buff aura active to entrants
    ENDED       no more buffs, hall closes

A player who enters during SERVING and leaves before
ENDED keeps the buff for its remaining duration. New
entrants after ENDED get nothing.

Public surface
--------------
    BanquetState enum
    BanquetEvent dataclass (mutable)
    BanquetHall
        .schedule(banquet_id, host_npc_id, town_id,
                  payload, scheduled_at) -> bool
        .open_serving(banquet_id, opened_at) -> bool
        .end_serving(banquet_id, ended_at) -> bool
        .enter(banquet_id, player_id) -> Optional[BuffPayload]
        .state(banquet_id) -> Optional[BanquetState]
        .attendees(banquet_id) -> list[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.cookpot_recipes import BuffPayload


class BanquetState(str, enum.Enum):
    SCHEDULED = "scheduled"
    SERVING = "serving"
    ENDED = "ended"


# Banquet aura is small — NOT a power feast. The intent
# is community gathering, not stacking damage.
_BANQUET_BUFF_PCT = 30


@dataclasses.dataclass
class BanquetEvent:
    banquet_id: str
    host_npc_id: str
    town_id: str
    payload: BuffPayload
    state: BanquetState
    scheduled_at: int
    opened_at: int
    ended_at: int
    attendees: list[str]


@dataclasses.dataclass
class BanquetHall:
    _banquets: dict[str, BanquetEvent] = dataclasses.field(
        default_factory=dict,
    )

    def schedule(
        self, *, banquet_id: str, host_npc_id: str,
        town_id: str, payload: BuffPayload,
        scheduled_at: int,
    ) -> bool:
        if not banquet_id or not host_npc_id or not town_id:
            return False
        if banquet_id in self._banquets:
            return False
        self._banquets[banquet_id] = BanquetEvent(
            banquet_id=banquet_id, host_npc_id=host_npc_id,
            town_id=town_id, payload=payload,
            state=BanquetState.SCHEDULED,
            scheduled_at=scheduled_at, opened_at=0,
            ended_at=0, attendees=[],
        )
        return True

    def open_serving(
        self, *, banquet_id: str, opened_at: int,
    ) -> bool:
        b = self._banquets.get(banquet_id)
        if b is None:
            return False
        if b.state != BanquetState.SCHEDULED:
            return False
        b.state = BanquetState.SERVING
        b.opened_at = opened_at
        return True

    def end_serving(
        self, *, banquet_id: str, ended_at: int,
    ) -> bool:
        b = self._banquets.get(banquet_id)
        if b is None:
            return False
        if b.state != BanquetState.SERVING:
            return False
        b.state = BanquetState.ENDED
        b.ended_at = ended_at
        return True

    def enter(
        self, *, banquet_id: str, player_id: str,
    ) -> t.Optional[BuffPayload]:
        b = self._banquets.get(banquet_id)
        if b is None:
            return None
        if not player_id:
            return None
        if b.state != BanquetState.SERVING:
            return None
        if player_id in b.attendees:
            # already buffed; second entry no-ops
            return None
        b.attendees.append(player_id)
        # Build the small aura payload
        p = b.payload
        pct = _BANQUET_BUFF_PCT / 100
        return BuffPayload(
            str_bonus=int(p.str_bonus * pct),
            dex_bonus=int(p.dex_bonus * pct),
            vit_bonus=int(p.vit_bonus * pct),
            regen_per_tick=int(p.regen_per_tick * pct),
            refresh_per_tick=int(p.refresh_per_tick * pct),
            hp_max_pct=int(p.hp_max_pct * pct),
            mp_max_pct=int(p.mp_max_pct * pct),
            cold_resist=int(p.cold_resist * pct),
            heat_resist=int(p.heat_resist * pct),
            duration_seconds=p.duration_seconds,
        )

    def state(
        self, *, banquet_id: str,
    ) -> t.Optional[BanquetState]:
        b = self._banquets.get(banquet_id)
        if b is None:
            return None
        return b.state

    def attendees(self, *, banquet_id: str) -> list[str]:
        b = self._banquets.get(banquet_id)
        if b is None:
            return []
        return list(b.attendees)

    def total_banquets(self) -> int:
        return len(self._banquets)


__all__ = [
    "BanquetState", "BanquetEvent", "BanquetHall",
]
