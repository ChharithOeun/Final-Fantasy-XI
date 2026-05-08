"""VR haptic feedback — controller rumble for game events.

In flat-screen play the only feedback is visual + audio.
In VR the controller can buzz, kick, pulse — and that
makes a real difference. A spell finishing tick-tick-tick
in your casting hand, a heavy hit slamming both controllers,
your weapon hand jumping when a weaponskill procs — these
are the things that make VR feel "real" rather than "a 3D
display attached to my head."

This module is the catalog + dispatcher:

    EventKind   what happened in-game (DAMAGE_TAKEN,
                SPELL_CAST_TICK, WEAPONSKILL_PROC ...)
    HapticHand  which hand to buzz (LEFT, RIGHT, BOTH)
    HapticPattern (frequency_hz, amplitude, duration_ms,
                   hand) — a default-tunable rumble shape
    HapticPulse the actual emitted "play this on the
                controller now" record

A built-in default table maps every EventKind to a
sensible pattern. set_pattern() lets a player customize
any individual pattern; reset_pattern() returns to default.

emit(player_id, event_kind) does three things:
    1. Looks up the player's pattern (custom > default).
    2. Scales amplitude by the player's user_intensity
       (0.0..1.0, default 1.0). 0 = muted entirely.
    3. Applies the global mute toggle if set; muted
       players get nothing at all.
    4. Records a HapticPulse.

Pulses are buffered. The VR runtime calls pulses_for()
each frame to drain pending haptic commands and forward
them to the OpenXR/SteamVR/Oculus side.

Why we expose intensity as a separate axis instead of
re-baking patterns: accessibility. A player with sensory
sensitivities turns intensity to 0.3 and KEEPS the texture
of every event — DAMAGE_TAKEN still feels heavier than
ITEM_PICKUP — just at lower absolute force. Re-baking
every pattern to a "low" preset would erase that texture.

Public surface
--------------
    EventKind enum
    HapticHand enum
    HapticPattern dataclass (frozen)
    HapticPulse dataclass (frozen)
    VrHapticFeedback
        .set_pattern(event_kind, pattern) -> bool
        .reset_pattern(event_kind) -> bool
        .resolve_pattern(event_kind) -> HapticPattern
        .set_intensity(player_id, intensity) -> bool
        .mute(player_id) -> bool
        .unmute(player_id) -> bool
        .is_muted(player_id) -> bool
        .emit(player_id, event_kind) -> Optional[HapticPulse]
        .pulses_for(player_id) -> list[HapticPulse]
        .clear_pulses(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EventKind(str, enum.Enum):
    DAMAGE_TAKEN = "damage_taken"
    DAMAGE_DEALT = "damage_dealt"
    SPELL_CAST_TICK = "spell_cast_tick"
    SPELL_CAST_COMPLETE = "spell_cast_complete"
    WEAPONSKILL_PROC = "weaponskill_proc"
    SKILLCHAIN_LIGHT = "skillchain_light"
    ITEM_PICKUP = "item_pickup"
    AGGRO_DETECTED = "aggro_detected"
    COUNTDOWN_PULSE = "countdown_pulse"
    HEAL_RECEIVED = "heal_received"
    DEATH = "death"
    LEVEL_UP = "level_up"


class HapticHand(str, enum.Enum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


@dataclasses.dataclass(frozen=True)
class HapticPattern:
    frequency_hz: float
    amplitude: float        # 0.0..1.0
    duration_ms: int
    hand: HapticHand


@dataclasses.dataclass(frozen=True)
class HapticPulse:
    player_id: str
    event_kind: EventKind
    frequency_hz: float
    amplitude: float
    duration_ms: int
    hand: HapticHand


_DEFAULT_PATTERNS: dict[EventKind, HapticPattern] = {
    EventKind.DAMAGE_TAKEN: HapticPattern(
        frequency_hz=80.0, amplitude=0.8,
        duration_ms=200, hand=HapticHand.BOTH,
    ),
    EventKind.DAMAGE_DEALT: HapticPattern(
        frequency_hz=60.0, amplitude=0.4,
        duration_ms=80, hand=HapticHand.RIGHT,
    ),
    EventKind.SPELL_CAST_TICK: HapticPattern(
        frequency_hz=30.0, amplitude=0.3,
        duration_ms=50, hand=HapticHand.LEFT,
    ),
    EventKind.SPELL_CAST_COMPLETE: HapticPattern(
        frequency_hz=50.0, amplitude=0.6,
        duration_ms=300, hand=HapticHand.LEFT,
    ),
    EventKind.WEAPONSKILL_PROC: HapticPattern(
        frequency_hz=100.0, amplitude=0.9,
        duration_ms=150, hand=HapticHand.RIGHT,
    ),
    EventKind.SKILLCHAIN_LIGHT: HapticPattern(
        frequency_hz=70.0, amplitude=0.7,
        duration_ms=250, hand=HapticHand.BOTH,
    ),
    EventKind.ITEM_PICKUP: HapticPattern(
        frequency_hz=40.0, amplitude=0.3,
        duration_ms=60, hand=HapticHand.RIGHT,
    ),
    EventKind.AGGRO_DETECTED: HapticPattern(
        frequency_hz=90.0, amplitude=0.5,
        duration_ms=100, hand=HapticHand.BOTH,
    ),
    EventKind.COUNTDOWN_PULSE: HapticPattern(
        frequency_hz=50.0, amplitude=0.3,
        duration_ms=80, hand=HapticHand.BOTH,
    ),
    EventKind.HEAL_RECEIVED: HapticPattern(
        frequency_hz=35.0, amplitude=0.4,
        duration_ms=200, hand=HapticHand.LEFT,
    ),
    EventKind.DEATH: HapticPattern(
        frequency_hz=30.0, amplitude=1.0,
        duration_ms=1000, hand=HapticHand.BOTH,
    ),
    EventKind.LEVEL_UP: HapticPattern(
        frequency_hz=55.0, amplitude=0.7,
        duration_ms=400, hand=HapticHand.BOTH,
    ),
}


@dataclasses.dataclass
class VrHapticFeedback:
    _custom: dict[
        EventKind, HapticPattern,
    ] = dataclasses.field(default_factory=dict)
    _intensity: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    _muted: set[str] = dataclasses.field(
        default_factory=set,
    )
    _pulses: list[HapticPulse] = dataclasses.field(
        default_factory=list,
    )

    def set_pattern(
        self, *, event_kind: EventKind,
        pattern: HapticPattern,
    ) -> bool:
        if pattern.amplitude < 0 or pattern.amplitude > 1:
            return False
        if pattern.duration_ms <= 0:
            return False
        if pattern.frequency_hz <= 0:
            return False
        self._custom[event_kind] = pattern
        return True

    def reset_pattern(self, *, event_kind: EventKind) -> bool:
        if event_kind not in self._custom:
            return False
        del self._custom[event_kind]
        return True

    def resolve_pattern(
        self, *, event_kind: EventKind,
    ) -> HapticPattern:
        if event_kind in self._custom:
            return self._custom[event_kind]
        return _DEFAULT_PATTERNS[event_kind]

    def set_intensity(
        self, *, player_id: str, intensity: float,
    ) -> bool:
        if not player_id:
            return False
        if intensity < 0.0 or intensity > 1.0:
            return False
        self._intensity[player_id] = intensity
        return True

    def mute(self, *, player_id: str) -> bool:
        if not player_id:
            return False
        if player_id in self._muted:
            return False
        self._muted.add(player_id)
        return True

    def unmute(self, *, player_id: str) -> bool:
        if player_id not in self._muted:
            return False
        self._muted.discard(player_id)
        return True

    def is_muted(self, *, player_id: str) -> bool:
        return player_id in self._muted

    def emit(
        self, *, player_id: str, event_kind: EventKind,
    ) -> t.Optional[HapticPulse]:
        if not player_id:
            return None
        if player_id in self._muted:
            return None
        pat = self.resolve_pattern(event_kind=event_kind)
        scale = self._intensity.get(player_id, 1.0)
        if scale <= 0.0:
            return None
        amp = max(0.0, min(1.0, pat.amplitude * scale))
        if amp <= 0.0:
            return None
        pulse = HapticPulse(
            player_id=player_id, event_kind=event_kind,
            frequency_hz=pat.frequency_hz,
            amplitude=round(amp, 3),
            duration_ms=pat.duration_ms,
            hand=pat.hand,
        )
        self._pulses.append(pulse)
        return pulse

    def pulses_for(
        self, *, player_id: str,
    ) -> list[HapticPulse]:
        return [
            p for p in self._pulses
            if p.player_id == player_id
        ]

    def clear_pulses(self, *, player_id: str) -> bool:
        before = len(self._pulses)
        self._pulses = [
            p for p in self._pulses
            if p.player_id != player_id
        ]
        return before != len(self._pulses)


__all__ = [
    "EventKind", "HapticHand", "HapticPattern",
    "HapticPulse", "VrHapticFeedback",
]
