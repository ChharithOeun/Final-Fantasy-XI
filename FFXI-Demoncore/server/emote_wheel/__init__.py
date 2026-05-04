"""Emote wheel — radial emote selector with favorites.

Players /wave, /salute, /sit, /cheer. The emote wheel is a
radial picker (12 slots, like the macro palette) holding the
player's FAVORITE emotes. Slot binding is per-player and
persistent. Some emotes are CUSTOM (player-authored short clip
or pose). Some are GATED behind achievements (e.g. /maatlevel
unlocks after defeating Maat).

The wheel uses the same controller logic as macro_palette_radial:
L/R cycle slots, point-with-stick to land on a slot.

Public surface
--------------
    EmoteKind enum
    EmoteSlot dataclass
    EmoteWheel dataclass
    EmoteUseResult dataclass
    EmoteWheelSystem
        .register_emote(emote_id, kind, label, gated_by)
        .unlock(player_id, emote_id) — for gated emotes
        .bind(player_id, slot_index, emote_id)
        .clear_slot(player_id, slot_index)
        .point(player_id, slot_index)
        .activate(player_id) -> EmoteUseResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# 12 slots like the macro palette ring.
SLOTS_PER_WHEEL = 12


class EmoteKind(str, enum.Enum):
    DEFAULT = "default"        # built-in (always available)
    CUSTOM = "custom"           # player-authored
    GATED = "gated"             # unlock-required


@dataclasses.dataclass(frozen=True)
class EmoteDef:
    emote_id: str
    label: str
    kind: EmoteKind
    gated_by: t.Optional[str] = None    # achievement_id


@dataclasses.dataclass
class EmoteSlot:
    slot_index: int
    emote_id: t.Optional[str] = None


@dataclasses.dataclass
class EmoteWheel:
    player_id: str
    slots: list[EmoteSlot] = dataclasses.field(
        default_factory=lambda: [
            EmoteSlot(slot_index=i)
            for i in range(SLOTS_PER_WHEEL)
        ],
    )
    highlighted_index: int = 0


@dataclasses.dataclass(frozen=True)
class EmoteUseResult:
    accepted: bool
    emote_id: t.Optional[str] = None
    label: str = ""
    reason: t.Optional[str] = None


@dataclasses.dataclass
class EmoteWheelSystem:
    _emotes: dict[str, EmoteDef] = dataclasses.field(
        default_factory=dict,
    )
    _wheels: dict[str, EmoteWheel] = dataclasses.field(
        default_factory=dict,
    )
    _unlocks: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def register_emote(
        self, *, emote_id: str, label: str,
        kind: EmoteKind = EmoteKind.DEFAULT,
        gated_by: t.Optional[str] = None,
    ) -> t.Optional[EmoteDef]:
        if emote_id in self._emotes:
            return None
        e = EmoteDef(
            emote_id=emote_id, label=label,
            kind=kind, gated_by=gated_by,
        )
        self._emotes[emote_id] = e
        return e

    def unlock(
        self, *, player_id: str, emote_id: str,
    ) -> bool:
        if emote_id not in self._emotes:
            return False
        self._unlocks.setdefault(
            player_id, set(),
        ).add(emote_id)
        return True

    def is_unlocked(
        self, *, player_id: str, emote_id: str,
    ) -> bool:
        e = self._emotes.get(emote_id)
        if e is None:
            return False
        if e.kind != EmoteKind.GATED:
            return True
        return emote_id in self._unlocks.get(
            player_id, set(),
        )

    def _wheel(self, player_id: str) -> EmoteWheel:
        w = self._wheels.get(player_id)
        if w is None:
            w = EmoteWheel(player_id=player_id)
            self._wheels[player_id] = w
        return w

    def bind(
        self, *, player_id: str, slot_index: int,
        emote_id: str,
    ) -> bool:
        if not (0 <= slot_index < SLOTS_PER_WHEEL):
            return False
        if emote_id not in self._emotes:
            return False
        if not self.is_unlocked(
            player_id=player_id, emote_id=emote_id,
        ):
            return False
        w = self._wheel(player_id)
        w.slots[slot_index] = EmoteSlot(
            slot_index=slot_index, emote_id=emote_id,
        )
        return True

    def clear_slot(
        self, *, player_id: str, slot_index: int,
    ) -> bool:
        w = self._wheels.get(player_id)
        if w is None:
            return False
        if not (0 <= slot_index < SLOTS_PER_WHEEL):
            return False
        if w.slots[slot_index].emote_id is None:
            return False
        w.slots[slot_index] = EmoteSlot(
            slot_index=slot_index,
        )
        return True

    def point(
        self, *, player_id: str, slot_index: int,
    ) -> bool:
        if not (0 <= slot_index < SLOTS_PER_WHEEL):
            return False
        w = self._wheel(player_id)
        w.highlighted_index = slot_index
        return True

    def cycle_next(
        self, *, player_id: str,
    ) -> int:
        w = self._wheel(player_id)
        w.highlighted_index = (
            w.highlighted_index + 1
        ) % SLOTS_PER_WHEEL
        return w.highlighted_index

    def cycle_prev(
        self, *, player_id: str,
    ) -> int:
        w = self._wheel(player_id)
        w.highlighted_index = (
            w.highlighted_index - 1
        ) % SLOTS_PER_WHEEL
        return w.highlighted_index

    def activate(
        self, *, player_id: str,
    ) -> EmoteUseResult:
        w = self._wheels.get(player_id)
        if w is None:
            return EmoteUseResult(
                False, reason="no wheel",
            )
        slot = w.slots[w.highlighted_index]
        if slot.emote_id is None:
            return EmoteUseResult(
                False, reason="empty slot",
            )
        emote = self._emotes.get(slot.emote_id)
        if emote is None:
            return EmoteUseResult(
                False, reason="emote unregistered",
            )
        if not self.is_unlocked(
            player_id=player_id, emote_id=slot.emote_id,
        ):
            return EmoteUseResult(
                False, reason="emote locked",
            )
        return EmoteUseResult(
            accepted=True,
            emote_id=emote.emote_id,
            label=emote.label,
        )

    def wheel(
        self, *, player_id: str,
    ) -> EmoteWheel:
        return self._wheel(player_id)

    def total_emotes(self) -> int:
        return len(self._emotes)


__all__ = [
    "SLOTS_PER_WHEEL",
    "EmoteKind",
    "EmoteDef", "EmoteSlot",
    "EmoteWheel", "EmoteUseResult",
    "EmoteWheelSystem",
]
