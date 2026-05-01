"""7 Sequencer template assets per CINEMATIC_GRAMMAR.md.

Templates live at /Game/Demoncore/Cinematics/Templates/. Each template
holds keyframed camera tracks (per the 5-shot grammar), audio bus,
music cue track, particle/post-process tracks, trigger event tracks.

To author a new boss cinematic: clone the template, swap the camera
target actor, swap the voice-cloned audio file, swap the music cue.
~30 minutes per boss. ~50 cinematics across the world = ~25 hours
of cinematic authoring after the templates exist.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .shot_grammar import ShotType


class TemplateId(str, enum.Enum):
    ENTRANCE_ESTABLISHING = "ST_Entrance_Establishing"
    ENTRANCE_DIRECT_REVEAL = "ST_Entrance_DirectReveal"
    PHASE_TRANSITION = "ST_PhaseTransition"
    DEFEAT_PLAYER_WON = "ST_Defeat_PlayerWon"
    DEFEAT_PLAYER_LOST = "ST_Defeat_PlayerLost"
    AFTERMATH_BOSS_IMPRESSED = "ST_Aftermath_BossImpressed"
    AFTERMATH_LORE = "ST_Aftermath_Lore"


@dataclasses.dataclass(frozen=True)
class SequencerTemplate:
    """One reusable cinematic template."""
    template_id: TemplateId
    asset_path: str
    shot_sequence: tuple[ShotType, ...]
    total_seconds: float
    has_voice_track: bool
    has_music_cue: bool
    has_particle_track: bool
    has_post_process: bool
    notes: str = ""


# Doc-named 7 templates. shot_sequence reflects the doc's 5-shot
# grammar — entrance combos pair establishing + hero_entry; defeat
# uses aftermath; phase transition is a quick CHAOS pulse.
TEMPLATES: dict[TemplateId, SequencerTemplate] = {
    TemplateId.ENTRANCE_ESTABLISHING: SequencerTemplate(
        template_id=TemplateId.ENTRANCE_ESTABLISHING,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Entrance_Establishing",
        shot_sequence=(ShotType.ESTABLISHING, ShotType.HERO_ENTRY),
        total_seconds=10.0,        # 5s establishing + 5s hero entry
        has_voice_track=True,
        has_music_cue=True,
        has_particle_track=True,
        has_post_process=True,
        notes="establishing + hero-entry combo per doc",
    ),
    TemplateId.ENTRANCE_DIRECT_REVEAL: SequencerTemplate(
        template_id=TemplateId.ENTRANCE_DIRECT_REVEAL,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Entrance_DirectReveal",
        shot_sequence=(ShotType.HERO_ENTRY,),
        total_seconds=4.0,
        has_voice_track=False,     # quick reveal; mid-tier bosses
        has_music_cue=True,
        has_particle_track=True,
        has_post_process=False,
        notes="quick boss reveal for mid-tier",
    ),
    TemplateId.PHASE_TRANSITION: SequencerTemplate(
        template_id=TemplateId.PHASE_TRANSITION,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_PhaseTransition",
        shot_sequence=(ShotType.CHAOS,),
        total_seconds=1.0,         # 1-second slow-mo + tilt
        has_voice_track=True,      # phase line
        has_music_cue=False,
        has_particle_track=True,   # armor drop
        has_post_process=False,
        notes="short cut for visible armor-drop",
    ),
    TemplateId.DEFEAT_PLAYER_WON: SequencerTemplate(
        template_id=TemplateId.DEFEAT_PLAYER_WON,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Defeat_PlayerWon",
        shot_sequence=(ShotType.AFTERMATH,),
        total_seconds=10.0,
        has_voice_track=True,
        has_music_cue=True,
        has_particle_track=True,
        has_post_process=True,
        notes="slow-clap aftermath template",
    ),
    TemplateId.DEFEAT_PLAYER_LOST: SequencerTemplate(
        template_id=TemplateId.DEFEAT_PLAYER_LOST,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Defeat_PlayerLost",
        shot_sequence=(ShotType.EXCHANGE, ShotType.AFTERMATH),
        total_seconds=8.0,
        has_voice_track=True,
        has_music_cue=True,
        has_particle_track=False,
        has_post_process=True,
        notes="boss head-shake / sit-back-down",
    ),
    TemplateId.AFTERMATH_BOSS_IMPRESSED: SequencerTemplate(
        template_id=TemplateId.AFTERMATH_BOSS_IMPRESSED,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Aftermath_BossImpressed",
        shot_sequence=(ShotType.AFTERMATH, ShotType.EXCHANGE),
        total_seconds=12.0,
        has_voice_track=True,
        has_music_cue=True,
        has_particle_track=False,
        has_post_process=True,
        notes="Maat-style 'I haven't seen Light in years' beat",
    ),
    TemplateId.AFTERMATH_LORE: SequencerTemplate(
        template_id=TemplateId.AFTERMATH_LORE,
        asset_path="/Game/Demoncore/Cinematics/Templates/ST_Aftermath_Lore",
        shot_sequence=(ShotType.AFTERMATH, ShotType.EXCHANGE,
                          ShotType.AFTERMATH),
        total_seconds=20.0,        # multi-line soliloquy
        has_voice_track=True,
        has_music_cue=True,
        has_particle_track=False,
        has_post_process=True,
        notes="multi-line soliloquy template",
    ),
}


@dataclasses.dataclass(frozen=True)
class ClonedCinematic:
    """A template instantiated for a specific boss / story moment."""
    instance_id: str
    template_id: TemplateId
    target_actor_id: str
    voice_clip_id: str
    music_cue_id: str
    output_asset_path: str         # /Game/Demoncore/Cinematics/<nation>/<id>


def get_template(template_id: TemplateId) -> SequencerTemplate:
    return TEMPLATES[template_id]


def clone_for_boss(*,
                       template_id: TemplateId,
                       boss_id: str,
                       voice_clip_id: str,
                       music_cue_id: str,
                       nation: str = "global"
                       ) -> ClonedCinematic:
    """Doc workflow: clone template, swap camera target, voice, music.

    The output_asset_path follows the doc's filesystem convention.
    """
    if template_id not in TEMPLATES:
        raise ValueError(f"unknown template {template_id}")
    instance_id = f"{boss_id}_{template_id.value}"
    output = (f"/Game/Demoncore/Cinematics/{nation}/"
                f"{boss_id}_{template_id.name.lower()}")
    return ClonedCinematic(
        instance_id=instance_id, template_id=template_id,
        target_actor_id=boss_id,
        voice_clip_id=voice_clip_id,
        music_cue_id=music_cue_id,
        output_asset_path=output,
    )


def estimate_total_authoring_hours(boss_count: int,
                                        *,
                                        per_boss_minutes: int = 30
                                        ) -> float:
    """Doc: '~30 minutes per boss. ~50 cinematics = ~25 hours.'"""
    if boss_count < 0:
        raise ValueError("boss_count must be non-negative")
    return (boss_count * per_boss_minutes) / 60.0
