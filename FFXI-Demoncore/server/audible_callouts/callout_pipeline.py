"""CalloutPipeline — emit + spatial-audio mixer.

Per AUDIBLE_CALLOUTS.md callouts are spatially located to the
speaker's actor position. UE5 places them via spatial audio so
'a WAR shouting "Skillchain open!" from across the arena is
positionally audible to the rest of the party'.

This module collects emission events and exposes them to the
voice pipeline + UE5 audio renderer. Backends are stubbed.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .mood_voice import apply_mood_tone


@dataclasses.dataclass(frozen=True)
class SpatialAudio:
    """Where the line plays from."""
    actor_id: str
    position: tuple[float, float, float]
    volume_multiplier: float = 1.0


@dataclasses.dataclass(frozen=True)
class CalloutEmission:
    """One emitted callout, ready for the voice pipeline."""
    line: str
    speaker: SpatialAudio
    mood_label: str
    at_time: float
    is_combat: bool = True
    synthesizer_input: t.Mapping[str, t.Any] = dataclasses.field(
        default_factory=dict)


def emit_callout(*,
                    line: str,
                    speaker: SpatialAudio,
                    mood_label: str,
                    now: float,
                    is_combat: bool = True
                    ) -> CalloutEmission:
    """Build an emission record for the voice pipeline to render."""
    synth = dict(apply_mood_tone(line=line, mood_label=mood_label))
    synth["speaker"] = speaker.actor_id
    synth["spatial"] = list(speaker.position)
    return CalloutEmission(
        line=line, speaker=speaker, mood_label=mood_label,
        at_time=now, is_combat=is_combat,
        synthesizer_input=synth,
    )


class CalloutPipeline:
    """Per-zone collector. Tests use this to inspect what was emitted."""

    def __init__(self) -> None:
        self._emissions: list[CalloutEmission] = []

    def emit(self,
                *,
                line: str,
                speaker: SpatialAudio,
                mood_label: str,
                now: float,
                is_combat: bool = True
                ) -> CalloutEmission:
        em = emit_callout(line=line, speaker=speaker,
                              mood_label=mood_label, now=now,
                              is_combat=is_combat)
        self._emissions.append(em)
        return em

    def emissions(self) -> list[CalloutEmission]:
        return list(self._emissions)

    def __len__(self) -> int:
        return len(self._emissions)

    def lines_in_window(self, *, start: float, end: float) -> list[str]:
        return [e.line for e in self._emissions
                  if start <= e.at_time <= end]

    def emissions_by_speaker(self, actor_id: str) -> list[CalloutEmission]:
        return [e for e in self._emissions
                  if e.speaker.actor_id == actor_id]

    def clear(self) -> None:
        self._emissions.clear()
