"""Audible callouts — voice as combat UI per AUDIBLE_CALLOUTS.md.

The chatbox is silent during combat. The information lives in
voice: 'Skillchain open!' / 'Closing — Fusion!' / 'LIGHT!' /
'Magic Burst — Slow!' Plus universal grunts. Plus mood-tinted
voice tone.

Module layout:
    callout_grammar.py - canonical doc-exact callout strings
    grunt_vocab.py     - universal grunt taxonomy (8 categories)
    mood_voice.py      - 8-mood per-line tone modifier
    callout_pipeline.py - emit + spatial-audio pipeline
"""
from .callout_grammar import (
    CALLOUT_TEMPLATES,
    CalloutKind,
    chain_close_callout,
    light_or_darkness_callout,
    mb_ailment_callout,
    mb_callout,
    setup_callout,
    skillchain_open_callout,
)
from .callout_pipeline import (
    CalloutEmission,
    CalloutPipeline,
    SpatialAudio,
    emit_callout,
)
from .grunt_vocab import (
    GRUNT_VOCAB,
    GruntCategory,
    GruntEntry,
    grunt_for_event,
)
from .mood_voice import (
    MOOD_VOICE_PROFILES,
    MoodVoiceProfile,
    apply_mood_tone,
    profile_for_mood,
)

__all__ = [
    # callout_grammar
    "CalloutKind", "CALLOUT_TEMPLATES",
    "skillchain_open_callout", "chain_close_callout",
    "light_or_darkness_callout", "mb_callout",
    "mb_ailment_callout", "setup_callout",
    # grunt_vocab
    "GruntCategory", "GruntEntry", "GRUNT_VOCAB", "grunt_for_event",
    # mood_voice
    "MoodVoiceProfile", "MOOD_VOICE_PROFILES",
    "profile_for_mood", "apply_mood_tone",
    # callout_pipeline
    "SpatialAudio", "CalloutEmission",
    "CalloutPipeline", "emit_callout",
]
