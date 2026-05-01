"""Per-race humanoid cue overrides.

Per VISUAL_HEALTH_SYSTEM.md the doc names 5 races and how their
visible-damage cues differ from the 'Hume reference':

    Galka       blood is harder to see on dark hide; visibly tense /
                clench more, breathing becomes a low growl
    Tarutaru    blood is more visible (smaller body, larger relative
                wounds); voice gets higher and faster at low HP
    Mithra      ears flatten progressively; tail gets twitchy at <30%
    Elvaan      proud-stance erodes into hunched shoulders by `wounded`
    Hume        standard reference — no overrides
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .damage_stages import DamageStage


class Race(str, enum.Enum):
    HUME = "hume"
    GALKA = "galka"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    ELVAAN = "elvaan"


@dataclasses.dataclass(frozen=True)
class RaceCueOverride:
    """Per-(race, stage) override appended to the standard cue list."""
    race: Race
    stage: DamageStage
    extra_cues: tuple[str, ...]
    voice_pitch_multiplier: float = 1.0
    voice_pace_multiplier: float = 1.0
    blood_visibility_multiplier: float = 1.0   # 0.5 dark hide; 1.5 small body


# Race table — only stages where the override differs are listed.
# Empty stages mean 'use standard humanoid cues'.
RACE_OVERRIDES: dict[Race, dict[DamageStage, RaceCueOverride]] = {
    Race.GALKA: {
        DamageStage.BLOODIED: RaceCueOverride(
            race=Race.GALKA, stage=DamageStage.BLOODIED,
            extra_cues=("visibly tense", "clenched fists"),
            voice_pitch_multiplier=0.95,
            blood_visibility_multiplier=0.5,
        ),
        DamageStage.WOUNDED: RaceCueOverride(
            race=Race.GALKA, stage=DamageStage.WOUNDED,
            extra_cues=("low growl breathing", "tense shoulders"),
            voice_pitch_multiplier=0.90,
            blood_visibility_multiplier=0.5,
        ),
        DamageStage.GRIEVOUS: RaceCueOverride(
            race=Race.GALKA, stage=DamageStage.GRIEVOUS,
            extra_cues=("growl deepens", "knuckles white"),
            voice_pitch_multiplier=0.85,
            blood_visibility_multiplier=0.5,
        ),
        DamageStage.BROKEN: RaceCueOverride(
            race=Race.GALKA, stage=DamageStage.BROKEN,
            extra_cues=("growl rumbles continuously",),
            voice_pitch_multiplier=0.80,
            blood_visibility_multiplier=0.5,
        ),
    },
    Race.TARUTARU: {
        DamageStage.BLOODIED: RaceCueOverride(
            race=Race.TARUTARU, stage=DamageStage.BLOODIED,
            extra_cues=("relatively-large blood smears",),
            blood_visibility_multiplier=1.5,
        ),
        DamageStage.WOUNDED: RaceCueOverride(
            race=Race.TARUTARU, stage=DamageStage.WOUNDED,
            extra_cues=("voice climbs higher",),
            voice_pitch_multiplier=1.10,
            voice_pace_multiplier=1.10,
            blood_visibility_multiplier=1.5,
        ),
        DamageStage.GRIEVOUS: RaceCueOverride(
            race=Race.TARUTARU, stage=DamageStage.GRIEVOUS,
            extra_cues=("voice high and fast", "frantic chattering"),
            voice_pitch_multiplier=1.20,
            voice_pace_multiplier=1.25,
            blood_visibility_multiplier=1.5,
        ),
        DamageStage.BROKEN: RaceCueOverride(
            race=Race.TARUTARU, stage=DamageStage.BROKEN,
            extra_cues=("voice frantic high-pitched",),
            voice_pitch_multiplier=1.30,
            voice_pace_multiplier=1.40,
            blood_visibility_multiplier=1.5,
        ),
    },
    Race.MITHRA: {
        DamageStage.SCUFFED: RaceCueOverride(
            race=Race.MITHRA, stage=DamageStage.SCUFFED,
            extra_cues=("ears flatten slightly",),
        ),
        DamageStage.BLOODIED: RaceCueOverride(
            race=Race.MITHRA, stage=DamageStage.BLOODIED,
            extra_cues=("ears flattened",),
        ),
        DamageStage.WOUNDED: RaceCueOverride(
            race=Race.MITHRA, stage=DamageStage.WOUNDED,
            extra_cues=("ears flat against skull",),
        ),
        # Doc: 'tail gets twitchy at <30%'
        DamageStage.GRIEVOUS: RaceCueOverride(
            race=Race.MITHRA, stage=DamageStage.GRIEVOUS,
            extra_cues=("ears pinned", "tail twitching erratically"),
        ),
        DamageStage.BROKEN: RaceCueOverride(
            race=Race.MITHRA, stage=DamageStage.BROKEN,
            extra_cues=("ears pinned flat", "tail thrashing"),
        ),
    },
    Race.ELVAAN: {
        DamageStage.WOUNDED: RaceCueOverride(
            race=Race.ELVAAN, stage=DamageStage.WOUNDED,
            extra_cues=("hunched shoulders",),
        ),
        DamageStage.GRIEVOUS: RaceCueOverride(
            race=Race.ELVAAN, stage=DamageStage.GRIEVOUS,
            extra_cues=("posture collapses; head down",),
        ),
        DamageStage.BROKEN: RaceCueOverride(
            race=Race.ELVAAN, stage=DamageStage.BROKEN,
            extra_cues=("can barely stand upright",),
        ),
    },
    Race.HUME: {},      # standard reference
}


def get_override(race: Race, stage: DamageStage
                  ) -> t.Optional[RaceCueOverride]:
    """Return the override (if any) for the given race+stage combo."""
    return RACE_OVERRIDES.get(race, {}).get(stage)


def voice_pitch_multiplier(race: Race, stage: DamageStage) -> float:
    """Doc: Tarutaru voice climbs at low HP; Galka growl deepens.

    Returns 1.0 for any race+stage without an override.
    """
    o = get_override(race, stage)
    if o is None:
        return 1.0
    return o.voice_pitch_multiplier


def blood_visibility_multiplier(race: Race, stage: DamageStage) -> float:
    """Galka 0.5 (dark hide); Tarutaru 1.5 (small body); rest 1.0."""
    o = get_override(race, stage)
    if o is None:
        return 1.0
    return o.blood_visibility_multiplier
