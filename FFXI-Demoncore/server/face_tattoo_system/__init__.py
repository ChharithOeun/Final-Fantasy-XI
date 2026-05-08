"""Face tattoo system — applied body markings.

In retail FFXI everyone of a given race-face combo looks
identical. Demoncore lets a player visit a tattoo NPC
and APPLY markings — clan tattoos, achievement marks,
faction sigils, decorative work. Each marking is
tracked per-player and rendered on the model.

Markings are SLOTTED — a face has a fixed set of slots
(forehead, left_cheek, right_cheek, chin, left_eye,
right_eye, nose, neck) and only one marking per slot.
Removing a marking takes a separate ritual (and a fee).

Some markings are GATED:
    Clan tattoos require linkshell rank or fame
    Faction sigils require nation rank
    Trial marks require completing a specific event
    Decorative is freely available

Public surface
--------------
    Slot enum
    MarkingKind enum
    Marking dataclass (frozen)
    AppliedMarking dataclass (frozen)
    FaceTattooSystem
        .register_marking(marking) -> bool
        .apply(player_id, marking_id, slot, gates_met)
            -> bool
        .remove(player_id, slot) -> bool
        .markings_for(player_id) -> list[AppliedMarking]
        .marking_in_slot(player_id, slot)
            -> Optional[AppliedMarking]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Slot(str, enum.Enum):
    FOREHEAD = "forehead"
    LEFT_CHEEK = "left_cheek"
    RIGHT_CHEEK = "right_cheek"
    CHIN = "chin"
    LEFT_EYE = "left_eye"
    RIGHT_EYE = "right_eye"
    NOSE = "nose"
    NECK = "neck"


class MarkingKind(str, enum.Enum):
    CLAN_TATTOO = "clan_tattoo"
    FACTION_SIGIL = "faction_sigil"
    TRIAL_MARK = "trial_mark"
    DECORATIVE = "decorative"


@dataclasses.dataclass(frozen=True)
class Marking:
    marking_id: str
    kind: MarkingKind
    name: str
    description: str
    valid_slots: tuple[Slot, ...]
    gate_token: t.Optional[str] = None  # what gates_met must include


@dataclasses.dataclass(frozen=True)
class AppliedMarking:
    player_id: str
    marking_id: str
    slot: Slot
    applied_day: int


@dataclasses.dataclass
class FaceTattooSystem:
    _markings: dict[str, Marking] = dataclasses.field(
        default_factory=dict,
    )
    # (player, slot) -> AppliedMarking
    _applied: dict[
        tuple[str, Slot], AppliedMarking,
    ] = dataclasses.field(default_factory=dict)

    def register_marking(self, marking: Marking) -> bool:
        if not marking.marking_id or not marking.name:
            return False
        if not marking.valid_slots:
            return False
        if marking.marking_id in self._markings:
            return False
        self._markings[marking.marking_id] = marking
        return True

    def apply(
        self, *, player_id: str, marking_id: str,
        slot: Slot, applied_day: int,
        gates_met: t.Optional[set[str]] = None,
    ) -> bool:
        if not player_id:
            return False
        if marking_id not in self._markings:
            return False
        m = self._markings[marking_id]
        if slot not in m.valid_slots:
            return False
        if m.gate_token is not None:
            if not gates_met or m.gate_token not in gates_met:
                return False
        key = (player_id, slot)
        if key in self._applied:
            return False  # remove first
        self._applied[key] = AppliedMarking(
            player_id=player_id, marking_id=marking_id,
            slot=slot, applied_day=applied_day,
        )
        return True

    def remove(
        self, *, player_id: str, slot: Slot,
    ) -> bool:
        key = (player_id, slot)
        if key not in self._applied:
            return False
        del self._applied[key]
        return True

    def markings_for(
        self, *, player_id: str,
    ) -> list[AppliedMarking]:
        return sorted(
            (am for (pid, _), am in self._applied.items()
             if pid == player_id),
            key=lambda am: am.slot.value,
        )

    def marking_in_slot(
        self, *, player_id: str, slot: Slot,
    ) -> t.Optional[AppliedMarking]:
        return self._applied.get((player_id, slot))


__all__ = [
    "Slot", "MarkingKind", "Marking", "AppliedMarking",
    "FaceTattooSystem",
]
