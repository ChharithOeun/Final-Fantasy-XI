"""Character creation — the 90-second guided cinematic.

Per CHARACTER_CREATION.md: 'Make them count.' Layout: Nation -> Race
-> sub-race/face/hair/eyes/skin -> Gear -> Voice -> Name -> Begin.

Module layout:
    creation_steps.py - 7-step state machine + commit gate
    nations_races.py  - Nation/Race tables + per-race overrides
    voice_bank.py     - Higgs Audio voice anchor catalog + Custom rec
    presets.py        - re-roll memory + JSON preset import/export
"""
from .creation_steps import (
    CREATION_STEP_ORDER,
    CharacterDraft,
    CreationSession,
    CreationStep,
)
from .nations_races import (
    NATIONS,
    NATION_OPENING_LINES,
    RACES,
    Nation,
    NationProfile,
    Race,
    RaceProfile,
    galka_tail_removed,
    nation_unlocked_for,
    opening_line_for,
)
from .presets import (
    CharacterPreset,
    export_preset,
    import_preset,
)
from .voice_bank import (
    VOICE_ANCHORS,
    CustomVoiceRecording,
    VoiceAnchor,
    register_custom_voice,
    voice_anchors_for_race,
)

__all__ = [
    # creation_steps
    "CreationStep", "CREATION_STEP_ORDER",
    "CreationSession", "CharacterDraft",
    # nations_races
    "Nation", "NationProfile", "Race", "RaceProfile",
    "NATIONS", "RACES",
    "NATION_OPENING_LINES", "opening_line_for",
    "nation_unlocked_for", "galka_tail_removed",
    # voice_bank
    "VoiceAnchor", "CustomVoiceRecording", "VOICE_ANCHORS",
    "voice_anchors_for_race", "register_custom_voice",
    # presets
    "CharacterPreset", "export_preset", "import_preset",
]
