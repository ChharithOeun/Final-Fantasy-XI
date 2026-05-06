"""Target cycle — F8/F1-F6/Tab keybinds in turn-based combat.

Menu-driven combat needs fast target selection. The
canonical bindings:

    F1..F6      cycle to party member 1-6 (yourself + allies)
    F7          previous target you had
    F8          nearest hostile mob
    Tab         cycle through visible mobs
    Esc         clear target

This module is the per-player target state machine. UI
calls one of the cycle helpers; the resulting target_id
becomes the default for the next turn_command_resolver
call.

The "candidate sets" — the list of party members, the
list of nearby hostiles — are passed in by the caller
(typically zone state). This module doesn't try to
discover entities itself; it just chooses among the
ones it's told about.

Public surface
--------------
    TargetState dataclass (mutable)
    TargetCycler
        .set_party_roster(player_id, party) -> bool
        .set_nearby_hostiles(player_id, ordered) -> bool
        .target_party_slot(player_id, slot) -> Optional[str]
        .target_nearest_hostile(player_id) -> Optional[str]
        .cycle_hostile(player_id, direction) -> Optional[str]
        .recall_previous(player_id) -> Optional[str]
        .clear(player_id) -> bool
        .current(player_id) -> str   ("" if no target)
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class TargetState:
    player_id: str
    current_target: str
    previous_target: str
    party: list[str]                 # ordered, 6 slots max
    hostiles: list[str]              # ordered by distance ascending
    hostile_cursor: int              # index into hostiles


_PARTY_MAX = 6


@dataclasses.dataclass
class TargetCycler:
    _states: dict[str, TargetState] = dataclasses.field(
        default_factory=dict,
    )

    def _get_or_create(self, player_id: str) -> TargetState:
        s = self._states.get(player_id)
        if s is None:
            s = TargetState(
                player_id=player_id, current_target="",
                previous_target="", party=[], hostiles=[],
                hostile_cursor=-1,
            )
            self._states[player_id] = s
        return s

    def set_party_roster(
        self, *, player_id: str, party: list[str],
    ) -> bool:
        if not player_id:
            return False
        if len(party) > _PARTY_MAX:
            return False
        s = self._get_or_create(player_id)
        s.party = list(party)
        return True

    def set_nearby_hostiles(
        self, *, player_id: str, ordered: list[str],
    ) -> bool:
        if not player_id:
            return False
        s = self._get_or_create(player_id)
        s.hostiles = list(ordered)
        # reset cursor — the caller-supplied list is fresh
        s.hostile_cursor = -1
        return True

    def _set_target(self, s: TargetState, new_target: str) -> None:
        if s.current_target and s.current_target != new_target:
            s.previous_target = s.current_target
        s.current_target = new_target

    def target_party_slot(
        self, *, player_id: str, slot: int,
    ) -> t.Optional[str]:
        s = self._states.get(player_id)
        if s is None:
            return None
        # slot is 1-indexed (F1 = slot 1)
        if slot < 1 or slot > len(s.party):
            return None
        new = s.party[slot - 1]
        self._set_target(s, new)
        return new

    def target_nearest_hostile(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        s = self._states.get(player_id)
        if s is None or not s.hostiles:
            return None
        new = s.hostiles[0]
        s.hostile_cursor = 0
        self._set_target(s, new)
        return new

    def cycle_hostile(
        self, *, player_id: str, direction: int = 1,
    ) -> t.Optional[str]:
        """Tab forward (1) or back (-1) through the hostile list."""
        s = self._states.get(player_id)
        if s is None or not s.hostiles:
            return None
        n = len(s.hostiles)
        # if no current cursor, start at 0; otherwise step
        if s.hostile_cursor < 0:
            s.hostile_cursor = 0
        else:
            s.hostile_cursor = (
                s.hostile_cursor + direction
            ) % n
        new = s.hostiles[s.hostile_cursor]
        self._set_target(s, new)
        return new

    def recall_previous(
        self, *, player_id: str,
    ) -> t.Optional[str]:
        s = self._states.get(player_id)
        if s is None or not s.previous_target:
            return None
        # swap current and previous
        cur = s.current_target
        s.current_target = s.previous_target
        s.previous_target = cur
        return s.current_target

    def clear(self, *, player_id: str) -> bool:
        s = self._states.get(player_id)
        if s is None:
            return False
        if not s.current_target:
            return False
        s.previous_target = s.current_target
        s.current_target = ""
        s.hostile_cursor = -1
        return True

    def current(self, *, player_id: str) -> str:
        s = self._states.get(player_id)
        if s is None:
            return ""
        return s.current_target

    def total_tracked(self) -> int:
        return len(self._states)


__all__ = [
    "TargetState", "TargetCycler",
]
