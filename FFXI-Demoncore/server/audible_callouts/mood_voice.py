"""Mood-aware voice tone — the line is the same, the delivery changes.

Per AUDIBLE_CALLOUTS.md the same callout 'Skillchain open!' sounds
different at content vs furious mood. The line is canonical; the
voice tone (pitch + pace + intensity) is mood-modulated.

The voice pipeline (Higgs Audio v2) consumes a MoodVoiceProfile
and synthesizes the line accordingly.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class MoodVoiceProfile:
    mood: str
    pitch_multiplier: float
    pace_multiplier: float
    intensity_multiplier: float
    description: str


# Tuning anchors keyed to the mood vocabulary used elsewhere
# (mood_propagation event_deltas etc).
MOOD_VOICE_PROFILES: dict[str, MoodVoiceProfile] = {
    "content": MoodVoiceProfile(
        mood="content", pitch_multiplier=1.0,
        pace_multiplier=1.0, intensity_multiplier=1.0,
        description="baseline calm",
    ),
    "alert": MoodVoiceProfile(
        mood="alert", pitch_multiplier=1.05,
        pace_multiplier=1.10, intensity_multiplier=1.10,
        description="taut focus",
    ),
    "agitated": MoodVoiceProfile(
        mood="agitated", pitch_multiplier=1.10,
        pace_multiplier=1.20, intensity_multiplier=1.15,
        description="strained",
    ),
    "furious": MoodVoiceProfile(
        mood="furious", pitch_multiplier=1.15,
        pace_multiplier=1.30, intensity_multiplier=1.40,
        description="full-throated shout",
    ),
    "fearful": MoodVoiceProfile(
        mood="fearful", pitch_multiplier=1.20,
        pace_multiplier=1.25, intensity_multiplier=0.85,
        description="strained higher pitch, strangled",
    ),
    "weary": MoodVoiceProfile(
        mood="weary", pitch_multiplier=0.92,
        pace_multiplier=0.85, intensity_multiplier=0.75,
        description="flat exhaustion",
    ),
    "mischievous": MoodVoiceProfile(
        mood="mischievous", pitch_multiplier=1.05,
        pace_multiplier=1.10, intensity_multiplier=1.05,
        description="playful lift",
    ),
    "contemplative": MoodVoiceProfile(
        mood="contemplative", pitch_multiplier=0.98,
        pace_multiplier=0.90, intensity_multiplier=0.90,
        description="measured, thoughtful",
    ),
}


# Default for unknown moods.
_DEFAULT_PROFILE = MOOD_VOICE_PROFILES["content"]


def profile_for_mood(mood_label: str) -> MoodVoiceProfile:
    return MOOD_VOICE_PROFILES.get(mood_label, _DEFAULT_PROFILE)


def apply_mood_tone(*,
                       line: str,
                       mood_label: str
                       ) -> dict[str, float | str]:
    """Build the synthesizer input for a mood-tinted line.

    The voice pipeline reads this dict.
    """
    profile = profile_for_mood(mood_label)
    return {
        "line": line,
        "mood": profile.mood,
        "pitch_multiplier": profile.pitch_multiplier,
        "pace_multiplier": profile.pace_multiplier,
        "intensity_multiplier": profile.intensity_multiplier,
    }
