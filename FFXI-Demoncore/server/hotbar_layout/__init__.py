"""Hotbar layout — N customizable bars × M slots, keybind storage.

Macro books exist (server/macro_system) for the canonical
ctrl/alt-numbered macro lines. Hotbars are the modern
LUA-addon-style augmentation: free-floating bars on
screen, each holding 12 slots, each slot bound to a
command_id resolvable by turn_command_resolver.

A player can have up to 8 hotbars, each with 12 slots.
Each slot stores a (command_id, label, icon_hint). The
keybind is opaque to this module — the addon decides
"slot 3 of bar 2 = ctrl+3 of bar 2."

Bars are saved per-player and per-job: a White Mage and
a Black Mage want different bars. Switch jobs → switch
bars. The active layout is the (player, job) pair.

Public surface
--------------
    HotbarSlot dataclass (mutable)
    HotbarBar dataclass (mutable)
    HotbarLayout dataclass (mutable)
    HotbarLayoutRegistry
        .ensure_layout(player_id, job) -> bool
        .set_slot(player_id, job, bar_index, slot_index,
                  command_id, label, icon_hint) -> bool
        .clear_slot(player_id, job, bar_index, slot_index)
            -> bool
        .get_slot(player_id, job, bar_index, slot_index)
            -> Optional[HotbarSlot]
        .copy_layout(player_id, from_job, to_job) -> bool
"""
from __future__ import annotations

import dataclasses
import typing as t


_NUM_BARS = 8
_SLOTS_PER_BAR = 12


@dataclasses.dataclass
class HotbarSlot:
    command_id: str
    label: str
    icon_hint: str


_EMPTY_SLOT = HotbarSlot(command_id="", label="", icon_hint="")


@dataclasses.dataclass
class HotbarBar:
    bar_index: int
    slots: list[HotbarSlot]


@dataclasses.dataclass
class HotbarLayout:
    player_id: str
    job: str
    bars: list[HotbarBar]


def _empty_bar(idx: int) -> HotbarBar:
    return HotbarBar(
        bar_index=idx,
        slots=[
            HotbarSlot(command_id="", label="", icon_hint="")
            for _ in range(_SLOTS_PER_BAR)
        ],
    )


def _empty_layout(player_id: str, job: str) -> HotbarLayout:
    return HotbarLayout(
        player_id=player_id, job=job,
        bars=[_empty_bar(i) for i in range(_NUM_BARS)],
    )


@dataclasses.dataclass
class HotbarLayoutRegistry:
    _layouts: dict[tuple[str, str], HotbarLayout] = \
        dataclasses.field(default_factory=dict)

    def ensure_layout(
        self, *, player_id: str, job: str,
    ) -> bool:
        if not player_id or not job:
            return False
        key = (player_id, job)
        if key in self._layouts:
            return False  # already exists
        self._layouts[key] = _empty_layout(player_id, job)
        return True

    def _get_layout(
        self, player_id: str, job: str,
    ) -> t.Optional[HotbarLayout]:
        return self._layouts.get((player_id, job))

    def set_slot(
        self, *, player_id: str, job: str,
        bar_index: int, slot_index: int,
        command_id: str, label: str = "",
        icon_hint: str = "",
    ) -> bool:
        if not command_id:
            return False
        layout = self._layouts.get((player_id, job))
        if layout is None:
            return False
        if bar_index < 0 or bar_index >= _NUM_BARS:
            return False
        if slot_index < 0 or slot_index >= _SLOTS_PER_BAR:
            return False
        layout.bars[bar_index].slots[slot_index] = HotbarSlot(
            command_id=command_id, label=label,
            icon_hint=icon_hint,
        )
        return True

    def clear_slot(
        self, *, player_id: str, job: str,
        bar_index: int, slot_index: int,
    ) -> bool:
        layout = self._layouts.get((player_id, job))
        if layout is None:
            return False
        if bar_index < 0 or bar_index >= _NUM_BARS:
            return False
        if slot_index < 0 or slot_index >= _SLOTS_PER_BAR:
            return False
        layout.bars[bar_index].slots[slot_index] = HotbarSlot(
            command_id="", label="", icon_hint="",
        )
        return True

    def get_slot(
        self, *, player_id: str, job: str,
        bar_index: int, slot_index: int,
    ) -> t.Optional[HotbarSlot]:
        layout = self._layouts.get((player_id, job))
        if layout is None:
            return None
        if bar_index < 0 or bar_index >= _NUM_BARS:
            return None
        if slot_index < 0 or slot_index >= _SLOTS_PER_BAR:
            return None
        return layout.bars[bar_index].slots[slot_index]

    def copy_layout(
        self, *, player_id: str,
        from_job: str, to_job: str,
    ) -> bool:
        src = self._layouts.get((player_id, from_job))
        if src is None:
            return False
        if from_job == to_job:
            return False
        # copy by value
        new_bars: list[HotbarBar] = []
        for bar in src.bars:
            new_bars.append(HotbarBar(
                bar_index=bar.bar_index,
                slots=[
                    HotbarSlot(
                        command_id=s.command_id,
                        label=s.label,
                        icon_hint=s.icon_hint,
                    ) for s in bar.slots
                ],
            ))
        self._layouts[(player_id, to_job)] = HotbarLayout(
            player_id=player_id, job=to_job, bars=new_bars,
        )
        return True

    def num_bars(self) -> int:
        return _NUM_BARS

    def slots_per_bar(self) -> int:
        return _SLOTS_PER_BAR

    def total_layouts(self) -> int:
        return len(self._layouts)


__all__ = [
    "HotbarSlot", "HotbarBar", "HotbarLayout",
    "HotbarLayoutRegistry",
]
