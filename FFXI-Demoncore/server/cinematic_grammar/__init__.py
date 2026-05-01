"""Cinematic grammar — Mandalorian StageCraft adapted to UE5.

Per CINEMATIC_GRAMMAR.md: every cutscene shot on the StageCraft
principles, real-time lighting, virtual camera operated by phone,
shots composed for the screen.

Module layout:
    shot_grammar.py        - 5-shot table (ESTABLISHING/HERO_ENTRY/
                                EXCHANGE/CHAOS/AFTERMATH)
    sequencer_templates.py - 7 reusable templates + clone_for_boss
    chaos_camera.py        - 6 ChaosMode reactions for combat
    post_process.py        - 5 PPV presets + stack composer
"""
from .chaos_camera import (
    REACTIONS,
    CameraEvent,
    CameraTimeline,
    ChaosReaction,
    get_reaction,
    total_reaction_seconds,
)
from .post_process import (
    PPV_PRESETS,
    PostProcessVolume,
    PpvPreset,
    get_preset,
    stack_presets,
)
from .sequencer_templates import (
    TEMPLATES,
    ClonedCinematic,
    SequencerTemplate,
    TemplateId,
    clone_for_boss,
    estimate_total_authoring_hours,
    get_template,
)
from .shot_grammar import (
    SHOT_PROFILES,
    ShotProfile,
    ShotType,
    get_profile,
    is_within_band,
    midpoint_duration,
    shots_with_use_case,
)

__all__ = [
    # shot_grammar
    "ShotType", "ShotProfile", "SHOT_PROFILES",
    "get_profile", "is_within_band", "shots_with_use_case",
    "midpoint_duration",
    # sequencer_templates
    "TemplateId", "SequencerTemplate", "TEMPLATES",
    "ClonedCinematic", "get_template", "clone_for_boss",
    "estimate_total_authoring_hours",
    # chaos_camera
    "CameraEvent", "ChaosReaction", "REACTIONS",
    "CameraTimeline", "get_reaction", "total_reaction_seconds",
    # post_process
    "PpvPreset", "PostProcessVolume", "PPV_PRESETS",
    "get_preset", "stack_presets",
]
