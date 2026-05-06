"""Duel arena — physical platforms where Trial by Combat plays out.

When two players accept a Trial by Combat challenge, the
fight has to happen *somewhere*. The arena is the physical
component: a real platform in a real zone, with seats for
witnesses, ringside lighting, and a small staff that
announces winner, escorts loser, and records who showed up.

Arena kinds
-----------
    NATION_PLATFORM    one in each of the 3 nations.
                       Always available, low spectacle.
    OUTLAW_PIT         shadow venue in Bastok mines.
                       No witnesses required, anything goes.
    GRAND_COLISEUM     the marquee venue, only used for
                       LEGENDARY-tier stakes. Auto-records
                       a LEGENDARY_DUEL history entry.
    CIRCLE_OF_SHADOWS  Adoulin-style honor arena. Best-of-3
                       format unique to this venue.

Lifecycle:
    register_arena -> assign_duel -> seat_witnesses ->
    start_match -> conclude_match (winner_id) -> arena freed

Public surface
--------------
    ArenaKind enum
    Arena dataclass (mutable)
    DuelArenaRegistry
        .register_arena(arena_id, kind, capacity, region_id)
        .assign_duel(arena_id, challenge_id, scheduled_at)
            -> bool
        .seat_witness(arena_id, witness_id) -> bool
        .start_match(arena_id, started_at) -> bool
        .conclude_match(arena_id, winner_id, ended_at) -> bool
        .arena_for(challenge_id) -> Optional[Arena]
        .available_arenas(kind) -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ArenaKind(str, enum.Enum):
    NATION_PLATFORM = "nation_platform"
    OUTLAW_PIT = "outlaw_pit"
    GRAND_COLISEUM = "grand_coliseum"
    CIRCLE_OF_SHADOWS = "circle_of_shadows"


class ArenaState(str, enum.Enum):
    IDLE = "idle"
    ASSIGNED = "assigned"      # duel scheduled, waiting
    LIVE = "live"              # match underway
    CONCLUDED = "concluded"    # awaiting reset to IDLE


@dataclasses.dataclass
class Arena:
    arena_id: str
    kind: ArenaKind
    capacity: int
    region_id: str
    state: ArenaState = ArenaState.IDLE
    current_challenge_id: t.Optional[str] = None
    witnesses: tuple[str, ...] = ()
    scheduled_at: t.Optional[int] = None
    started_at: t.Optional[int] = None
    ended_at: t.Optional[int] = None
    winner_id: t.Optional[str] = None


@dataclasses.dataclass
class DuelArenaRegistry:
    _arenas: dict[str, Arena] = dataclasses.field(
        default_factory=dict,
    )
    _challenge_to_arena: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_arena(
        self, *, arena_id: str, kind: ArenaKind,
        capacity: int, region_id: str,
    ) -> bool:
        if not arena_id or capacity < 0:
            return False
        if arena_id in self._arenas:
            return False
        self._arenas[arena_id] = Arena(
            arena_id=arena_id, kind=kind,
            capacity=capacity, region_id=region_id,
        )
        return True

    def get(self, *, arena_id: str) -> t.Optional[Arena]:
        return self._arenas.get(arena_id)

    def assign_duel(
        self, *, arena_id: str, challenge_id: str,
        scheduled_at: int,
    ) -> bool:
        a = self._arenas.get(arena_id)
        if a is None:
            return False
        if a.state != ArenaState.IDLE:
            return False
        if not challenge_id:
            return False
        if challenge_id in self._challenge_to_arena:
            return False
        a.state = ArenaState.ASSIGNED
        a.current_challenge_id = challenge_id
        a.scheduled_at = scheduled_at
        a.witnesses = ()
        self._challenge_to_arena[challenge_id] = arena_id
        return True

    def seat_witness(
        self, *, arena_id: str, witness_id: str,
    ) -> bool:
        a = self._arenas.get(arena_id)
        if a is None or not witness_id:
            return False
        if a.state not in (ArenaState.ASSIGNED, ArenaState.LIVE):
            return False
        # outlaw pit doesn't need witnesses, but they can show up
        if witness_id in a.witnesses:
            return False
        if len(a.witnesses) >= a.capacity:
            return False
        a.witnesses = a.witnesses + (witness_id,)
        return True

    def start_match(
        self, *, arena_id: str, started_at: int,
    ) -> bool:
        a = self._arenas.get(arena_id)
        if a is None:
            return False
        if a.state != ArenaState.ASSIGNED:
            return False
        a.state = ArenaState.LIVE
        a.started_at = started_at
        return True

    def conclude_match(
        self, *, arena_id: str, winner_id: str, ended_at: int,
    ) -> bool:
        a = self._arenas.get(arena_id)
        if a is None or not winner_id:
            return False
        if a.state != ArenaState.LIVE:
            return False
        a.state = ArenaState.CONCLUDED
        a.winner_id = winner_id
        a.ended_at = ended_at
        return True

    def reset_arena(self, *, arena_id: str) -> bool:
        a = self._arenas.get(arena_id)
        if a is None:
            return False
        if a.state != ArenaState.CONCLUDED:
            return False
        if a.current_challenge_id:
            self._challenge_to_arena.pop(
                a.current_challenge_id, None,
            )
        a.state = ArenaState.IDLE
        a.current_challenge_id = None
        a.witnesses = ()
        a.scheduled_at = None
        a.started_at = None
        a.ended_at = None
        a.winner_id = None
        return True

    def arena_for(
        self, *, challenge_id: str,
    ) -> t.Optional[Arena]:
        aid = self._challenge_to_arena.get(challenge_id)
        if aid is None:
            return None
        return self._arenas.get(aid)

    def available_arenas(
        self, *, kind: t.Optional[ArenaKind] = None,
    ) -> tuple[str, ...]:
        out = [
            a.arena_id for a in self._arenas.values()
            if a.state == ArenaState.IDLE
            and (kind is None or a.kind == kind)
        ]
        return tuple(sorted(out))


__all__ = [
    "ArenaKind", "ArenaState", "Arena", "DuelArenaRegistry",
]
