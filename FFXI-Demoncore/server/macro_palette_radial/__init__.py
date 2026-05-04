"""Macro palette radial — circular controller-friendly macros.

Retail FFXI puts the macro palette as a strip at the top of the
screen. Demoncore makes it a CIRCLE around the player toon —
better for controllers and for keeping eyes on the action.

Each player has multiple SETS (rings). A set is one ring of up
to 12 SLOTS evenly distributed around the toon. The active ring
is rendered; unused rings are buffered behind it.

Controller mapping
------------------
* L1/R1 cycle to the previous/next RING
* L2/R2 cycle SLOT step-by-step (left or right)
* hold L1/R1 + flick the right analog stick — pointer mode,
  lands on the slot under the stick angle
* tap a face button = activate the highlighted slot

Each slot binds to a MACRO_LINE (existing macro_system) or a
SHORTCUT_KIND (item / spell / job ability / weapon skill / pet
command). The mapping holds the activation payload.

Public surface
--------------
    SlotKind enum
    InputAction enum
    RadialSet dataclass
    RadialSlot dataclass
    PaletteSelection dataclass
    MacroPaletteRadial
        .create_set(player_id, set_id, label) -> RadialSet
        .bind(player_id, set_id, slot_index, kind, payload)
        .switch_set(player_id, set_id) -> active set
        .cycle(player_id, direction) -> new highlighted slot
        .point(player_id, angle_radians) -> highlighted slot
        .activate(player_id) -> bound payload
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


# 12 evenly-spaced slots per ring (every 30 degrees).
SLOTS_PER_RING = 12


class SlotKind(str, enum.Enum):
    EMPTY = "empty"
    MACRO_LINE = "macro_line"        # body of macro_system
    ITEM = "item"
    SPELL = "spell"
    JOB_ABILITY = "job_ability"
    WEAPONSKILL = "weaponskill"
    PET_COMMAND = "pet_command"


class InputAction(str, enum.Enum):
    NEXT_SLOT = "next_slot"
    PREV_SLOT = "prev_slot"
    NEXT_RING = "next_ring"
    PREV_RING = "prev_ring"


@dataclasses.dataclass
class RadialSlot:
    slot_index: int
    kind: SlotKind = SlotKind.EMPTY
    payload: str = ""           # opaque ID to the runtime
    label: str = ""


@dataclasses.dataclass
class RadialSet:
    set_id: str
    label: str
    slots: list[RadialSlot] = dataclasses.field(
        default_factory=lambda: [
            RadialSlot(slot_index=i)
            for i in range(SLOTS_PER_RING)
        ],
    )


@dataclasses.dataclass
class _PlayerPalette:
    player_id: str
    sets: dict[str, RadialSet] = dataclasses.field(
        default_factory=dict,
    )
    active_set_id: t.Optional[str] = None
    highlighted_index: int = 0


@dataclasses.dataclass(frozen=True)
class PaletteSelection:
    player_id: str
    set_id: str
    slot_index: int
    kind: SlotKind
    payload: str
    label: str


@dataclasses.dataclass
class MacroPaletteRadial:
    _palettes: dict[str, _PlayerPalette] = dataclasses.field(
        default_factory=dict,
    )

    def _palette_for(
        self, player_id: str,
    ) -> _PlayerPalette:
        p = self._palettes.get(player_id)
        if p is None:
            p = _PlayerPalette(player_id=player_id)
            self._palettes[player_id] = p
        return p

    def create_set(
        self, *, player_id: str, set_id: str,
        label: str = "",
    ) -> t.Optional[RadialSet]:
        pal = self._palette_for(player_id)
        if set_id in pal.sets:
            return None
        rs = RadialSet(set_id=set_id, label=label or set_id)
        pal.sets[set_id] = rs
        if pal.active_set_id is None:
            pal.active_set_id = set_id
        return rs

    def remove_set(
        self, *, player_id: str, set_id: str,
    ) -> bool:
        pal = self._palettes.get(player_id)
        if pal is None or set_id not in pal.sets:
            return False
        del pal.sets[set_id]
        if pal.active_set_id == set_id:
            # Pick another active set or None
            pal.active_set_id = next(
                iter(pal.sets), None,
            )
            pal.highlighted_index = 0
        return True

    def bind(
        self, *, player_id: str, set_id: str,
        slot_index: int, kind: SlotKind,
        payload: str = "", label: str = "",
    ) -> bool:
        pal = self._palettes.get(player_id)
        if pal is None:
            return False
        rs = pal.sets.get(set_id)
        if rs is None:
            return False
        if not (0 <= slot_index < SLOTS_PER_RING):
            return False
        rs.slots[slot_index] = RadialSlot(
            slot_index=slot_index,
            kind=kind, payload=payload, label=label,
        )
        return True

    def switch_set(
        self, *, player_id: str, set_id: str,
    ) -> bool:
        pal = self._palettes.get(player_id)
        if pal is None or set_id not in pal.sets:
            return False
        pal.active_set_id = set_id
        pal.highlighted_index = 0
        return True

    def cycle(
        self, *, player_id: str, action: InputAction,
    ) -> t.Optional[int]:
        pal = self._palettes.get(player_id)
        if pal is None:
            return None
        if action in (InputAction.NEXT_SLOT, InputAction.PREV_SLOT):
            if pal.active_set_id is None:
                return None
            step = 1 if action == InputAction.NEXT_SLOT else -1
            pal.highlighted_index = (
                pal.highlighted_index + step
            ) % SLOTS_PER_RING
            return pal.highlighted_index
        if action in (InputAction.NEXT_RING, InputAction.PREV_RING):
            if not pal.sets:
                return None
            ids = list(pal.sets.keys())
            idx = (
                ids.index(pal.active_set_id)
                if pal.active_set_id in ids else 0
            )
            step = 1 if action == InputAction.NEXT_RING else -1
            new_idx = (idx + step) % len(ids)
            pal.active_set_id = ids[new_idx]
            pal.highlighted_index = 0
            return pal.highlighted_index
        return None

    def point(
        self, *, player_id: str, angle_radians: float,
    ) -> t.Optional[int]:
        """Map a 0..2pi angle into the nearest slot index.
        0 rad = slot 0 (north), increasing clockwise."""
        pal = self._palettes.get(player_id)
        if pal is None or pal.active_set_id is None:
            return None
        # Normalize to [0, 2pi)
        normalized = angle_radians % (2 * math.pi)
        slot = int(
            round(
                normalized
                / (2 * math.pi / SLOTS_PER_RING)
            )
        ) % SLOTS_PER_RING
        pal.highlighted_index = slot
        return slot

    def activate(
        self, *, player_id: str,
    ) -> t.Optional[PaletteSelection]:
        pal = self._palettes.get(player_id)
        if pal is None or pal.active_set_id is None:
            return None
        rs = pal.sets[pal.active_set_id]
        slot = rs.slots[pal.highlighted_index]
        if slot.kind == SlotKind.EMPTY:
            return None
        return PaletteSelection(
            player_id=player_id,
            set_id=pal.active_set_id,
            slot_index=slot.slot_index,
            kind=slot.kind,
            payload=slot.payload,
            label=slot.label,
        )

    def active_set(
        self, *, player_id: str,
    ) -> t.Optional[RadialSet]:
        pal = self._palettes.get(player_id)
        if pal is None or pal.active_set_id is None:
            return None
        return pal.sets.get(pal.active_set_id)

    def total_sets(
        self, *, player_id: str,
    ) -> int:
        pal = self._palettes.get(player_id)
        return len(pal.sets) if pal else 0


__all__ = [
    "SLOTS_PER_RING",
    "SlotKind", "InputAction",
    "RadialSlot", "RadialSet",
    "PaletteSelection",
    "MacroPaletteRadial",
]
