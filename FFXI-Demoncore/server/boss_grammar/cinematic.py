"""Layer 5: cinematic — Entrance / Intro / Defeat / Aftermath beats.

Per BOSS_GRAMMAR.md every boss has Sequencer-driven cutscenes.
Beat durations are tuning anchors; voice line is the mood-tinted
script for the voice pipeline.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class EntranceBeat:
    """~10s reveal — slow dolly in, signature pose, music swells."""
    duration_seconds: float = 10.0
    camera_path: str = "slow_dolly_in"
    pose: str = "signature"
    music_cue: str = "boss_swell"


@dataclasses.dataclass(frozen=True)
class IntroBeat:
    """~8s voice-cloned bark in personality."""
    duration_seconds: float = 8.0
    voice_line: str = ""
    voice_anchor_id: str = ""
    mood_label: str = "alert"


@dataclasses.dataclass(frozen=True)
class DefeatBeat:
    """~8s collapse + final voice line."""
    duration_seconds: float = 8.0
    collapse_anim: str = "knee_then_topple"
    voice_line: str = ""
    drops_loot: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class AftermathBeat:
    """~5s scene reset — music outro, party reaction."""
    duration_seconds: float = 5.0
    music_outro: str = "boss_outro"
    enables_reaction_callouts: bool = True


@dataclasses.dataclass(frozen=True)
class BossCinematic:
    """Full cinematic pipeline."""
    entrance: EntranceBeat
    intro: IntroBeat
    defeat: DefeatBeat
    aftermath: AftermathBeat

    @property
    def total_seconds(self) -> float:
        return (self.entrance.duration_seconds
                  + self.intro.duration_seconds
                  + self.defeat.duration_seconds
                  + self.aftermath.duration_seconds)
