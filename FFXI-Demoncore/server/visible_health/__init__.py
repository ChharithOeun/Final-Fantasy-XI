"""Visible health — no HP/MP bars; read the world physically.

Per VISUAL_HEALTH_SYSTEM.md the highest skill-ceiling lift in
Demoncore. HP and MP are server-side; the client renders posture,
blood, limp, cough, ear-flatten, wing-droop. Players who learn
this read encounters with sub-second precision; veterans recruit
'a bard with Glee Tango' for the visual-reveal advantage.

Module layout:
    damage_stages.py       - 7-stage entity HP grammar + cues
    status_ailments.py     - 17 ailment cues (particle + tint +
                                anim + audio + UI gating)
    race_overrides.py      - 5-race blood/voice/posture overrides
    mob_class_overrides.py - 6 mob-class cue overrides
                                (dragon/slime/goblin/quadav/yagudo/worm)
    reveal_skills.py       - 13-row reveal-skill catalog
                                (/check, Scan, Drain, Aspir, Mug,
                                 Glee Tango, Cure-peek, Cura, MB,
                                 Indicolure, Stoneskin, /pol)
    reveal_handle.py       - RevealHandle lifecycle + RevealManager
    check_descriptor.py    - /check level + mood + damage descriptors
    party_summary.py       - /pol command reducer

Public surface:
    DamageStage, StageBand, STAGE_BANDS, STAGE_TO_BAND,
        get_band, resolve_stage, cues_for, attack_speed_multiplier,
        audible_cue, stage_for_check_descriptor
    Ailment, AilmentCue, AILMENT_CUES, get_cue,
        is_visible_to_others, visible_ailments_for_observer,
        render_layers_for
    Race, RaceCueOverride, RACE_OVERRIDES, get_race_override,
        voice_pitch_multiplier, blood_visibility_multiplier
    MobClass, MobCueOverride, MOB_CLASS_OVERRIDES,
        get_mob_class_override, has_mob_class_override
    RevealKind, RevealScope, RevealSkill, REVEAL_SKILLS,
        MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD,
        get_skill, is_reveal_skill,
        magic_burst_grants_reveal, mug_reveal_proc
    RevealHandle, RevealReadout, RevealManager
    LevelDescriptor, level_descriptor_for, MOOD_DESCRIPTOR,
        mood_descriptor_for, CheckResult, perform_check
    PartyStageSummary, summarize_party
"""
from .check_descriptor import (
    MOOD_DESCRIPTOR,
    CheckResult,
    LevelDescriptor,
    level_descriptor_for,
    mood_descriptor_for,
    perform_check,
)
from .damage_stages import (
    STAGE_BANDS,
    STAGE_TO_BAND,
    DamageStage,
    StageBand,
    attack_speed_multiplier,
    audible_cue,
    cues_for,
    resolve_stage,
    stage_for_check_descriptor,
)
from .damage_stages import get_band as get_stage_band
from .mob_class_overrides import (
    MOB_CLASS_OVERRIDES,
    MobClass,
    MobCueOverride,
    has_override as has_mob_class_override,
)
from .mob_class_overrides import get_override as get_mob_class_override
from .party_summary import PartyStageSummary, summarize_party
from .race_overrides import (
    RACE_OVERRIDES,
    Race,
    RaceCueOverride,
    blood_visibility_multiplier,
    voice_pitch_multiplier,
)
from .race_overrides import get_override as get_race_override
from .reveal_handle import RevealHandle, RevealManager, RevealReadout
from .reveal_skills import (
    MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD,
    REVEAL_SKILLS,
    RevealKind,
    RevealScope,
    RevealSkill,
    get_skill,
    is_reveal_skill,
    magic_burst_grants_reveal,
    mug_reveal_proc,
)
from .status_ailments import (
    AILMENT_CUES,
    Ailment,
    AilmentCue,
    get_cue,
    is_visible_to_others,
    render_layers_for,
    visible_ailments_for_observer,
)

__all__ = [
    # damage_stages
    "DamageStage", "StageBand", "STAGE_BANDS", "STAGE_TO_BAND",
    "get_stage_band", "resolve_stage", "cues_for",
    "attack_speed_multiplier", "audible_cue",
    "stage_for_check_descriptor",
    # status_ailments
    "Ailment", "AilmentCue", "AILMENT_CUES", "get_cue",
    "is_visible_to_others", "visible_ailments_for_observer",
    "render_layers_for",
    # race_overrides
    "Race", "RaceCueOverride", "RACE_OVERRIDES",
    "get_race_override",
    "voice_pitch_multiplier", "blood_visibility_multiplier",
    # mob_class_overrides
    "MobClass", "MobCueOverride", "MOB_CLASS_OVERRIDES",
    "get_mob_class_override", "has_mob_class_override",
    # reveal_skills
    "RevealKind", "RevealScope", "RevealSkill", "REVEAL_SKILLS",
    "MAGIC_BURST_REVEAL_DAMAGE_THRESHOLD",
    "get_skill", "is_reveal_skill",
    "magic_burst_grants_reveal", "mug_reveal_proc",
    # reveal_handle
    "RevealHandle", "RevealReadout", "RevealManager",
    # check_descriptor
    "LevelDescriptor", "level_descriptor_for", "MOOD_DESCRIPTOR",
    "mood_descriptor_for", "CheckResult", "perform_check",
    # party_summary
    "PartyStageSummary", "summarize_party",
]
