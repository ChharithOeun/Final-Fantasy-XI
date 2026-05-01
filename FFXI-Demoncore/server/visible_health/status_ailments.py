"""Status-ailment visible cues — 17 entries, integrated into bodies.

Per VISUAL_HEALTH_SYSTEM.md:
    'These are NOT iconified above the head. They are integrated
     into the character's visible body. A player with three
     ailments looks genuinely sick — green tinge, pustules, jerky
     walk all at once.'

Each ailment binds to:
    - particle emitter (Niagara)
    - material parameter (skin tone tint, opacity)
    - anim layer override (jerky animation, posture lurch)
    - audio override (silenced cast SFX)
    - extra UI gating (e.g. disease can't eat food)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Ailment(str, enum.Enum):
    """The 17 ailments the doc names."""
    POISON = "poison"
    SLEEP = "sleep"
    PARALYZE = "paralyze"
    SILENCE = "silence"
    BIND = "bind"
    STUN = "stun"
    CURSE = "curse"
    DISEASE = "disease"
    PLAGUE = "plague"
    CONFUSE = "confuse"
    CHARM = "charm"
    PETRIFY = "petrify"
    DOOM = "doom"
    WEAKNESS = "weakness"
    AMNESIA = "amnesia"
    TERROR = "terror"
    EN_AURA = "en_aura"


@dataclasses.dataclass(frozen=True)
class AilmentCue:
    """How an ailment renders on a body."""
    ailment: Ailment
    particle: str           # Niagara emitter id
    material_tint: t.Optional[str] = None       # color or None
    anim_override: t.Optional[str] = None
    audio_override: t.Optional[str] = None
    visible_to_others: bool = True              # doom is self-only
    ui_gating: t.Optional[str] = None
    notes: str = ""


AILMENT_CUES: dict[Ailment, AilmentCue] = {
    Ailment.POISON: AilmentCue(
        ailment=Ailment.POISON,
        particle="green_sweat_drift",
        material_tint="poison_green",
        audio_override="occasional_cough",
        notes="green particle sweat; occasional cough; skin tints green",
    ),
    Ailment.SLEEP: AilmentCue(
        ailment=Ailment.SLEEP,
        particle="z_drift",
        anim_override="slumped_eyes_closed",
        notes="eyes closed; Z-particle drifts up; slumped posture; "
                "can't move",
    ),
    Ailment.PARALYZE: AilmentCue(
        ailment=Ailment.PARALYZE,
        particle="paralyze_arc",
        anim_override="jerky_swings_with_stagger",
        notes="jerky animation; staggers mid-action; weapon swings wobble",
    ),
    Ailment.SILENCE: AilmentCue(
        ailment=Ailment.SILENCE,
        particle="silence_throat",
        anim_override="hand_to_throat_reflex",
        audio_override="mute_cast_sfx",
        notes="cast animation plays but no audio",
    ),
    Ailment.BIND: AilmentCue(
        ailment=Ailment.BIND,
        particle="bind_root",
        anim_override="feet_rooted_torso_twists",
        notes="feet rooted to ground; body can twist",
    ),
    Ailment.STUN: AilmentCue(
        ailment=Ailment.STUN,
        particle="stars_dazed",
        anim_override="posture_lurch",
        notes="stars/dazed particles around head; posture lurches",
    ),
    Ailment.CURSE: AilmentCue(
        ailment=Ailment.CURSE,
        particle="dark_wisps",
        material_tint="eye_darken_periodic",
        notes="dark wisps trail off the body; eyes occasionally darken",
    ),
    Ailment.DISEASE: AilmentCue(
        ailment=Ailment.DISEASE,
        particle="disease_haze",
        material_tint="pale_skin",
        anim_override="lethargic_movement_with_cough",
        ui_gating="cannot_eat_food",
        notes="pale skin; lethargic; coughs; can't eat food",
    ),
    Ailment.PLAGUE: AilmentCue(
        ailment=Ailment.PLAGUE,
        particle="mp_drain_aspir_visible",
        material_tint="pustule_decals",
        notes="pustule decals on skin; faster MP drain (visible)",
    ),
    Ailment.CONFUSE: AilmentCue(
        ailment=Ailment.CONFUSE,
        particle="confuse_swirl",
        anim_override="random_walk_swivel_head",
        notes="walks in random directions; head swivels; mis-targets",
    ),
    Ailment.CHARM: AilmentCue(
        ailment=Ailment.CHARM,
        particle="charm_pink_gaze",
        material_tint="pink_eye_tint",
        anim_override="follow_charmer",
        notes="pink-tinged gaze locked on charmer; follows obediently",
    ),
    Ailment.PETRIFY: AilmentCue(
        ailment=Ailment.PETRIFY,
        particle="stone_creep",
        material_tint="stone_progressive",
        anim_override="freeze_progressive_full_statue",
        notes="stone slowly creeps up from feet; full statue at end",
    ),
    Ailment.DOOM: AilmentCue(
        ailment=Ailment.DOOM,
        particle="doom_countdown_aura",
        audio_override="doom_clock_tick",
        visible_to_others=False,         # 'visible ONLY to the afflicted'
        notes="dark countdown aura; clock ticks",
    ),
    Ailment.WEAKNESS: AilmentCue(
        ailment=Ailment.WEAKNESS,
        particle="weakness_translucent",
        material_tint="translucent_body",
        notes="post-death; translucent body for the duration",
    ),
    Ailment.AMNESIA: AilmentCue(
        ailment=Ailment.AMNESIA,
        particle="amnesia_question",
        ui_gating="no_special_abilities",
        notes="no special abilities used; small ? particle when attempted",
    ),
    Ailment.TERROR: AilmentCue(
        ailment=Ailment.TERROR,
        particle="terror_shake",
        anim_override="full_body_shake_eyes_wide_no_act",
        notes="full-body shaking; can't act; eyes wide",
    ),
    Ailment.EN_AURA: AilmentCue(
        ailment=Ailment.EN_AURA,
        particle="en_element_glow",
        material_tint="weapon_element_glow",
        notes="weapon glows the element's color (player-applied buff)",
    ),
}


def get_cue(ailment: Ailment) -> AilmentCue:
    return AILMENT_CUES[ailment]


def is_visible_to_others(ailment: Ailment) -> bool:
    return AILMENT_CUES[ailment].visible_to_others


def visible_ailments_for_observer(active: t.Iterable[Ailment]
                                       ) -> tuple[Ailment, ...]:
    """Filter to only ailments other players see on this entity.

    Doom is visible only to the afflicted; everyone else sees nothing
    special. Used by the BPC pipeline when rendering an observer's
    view of another character's body.
    """
    return tuple(a for a in active if is_visible_to_others(a))


def render_layers_for(ailments: t.Iterable[Ailment]) -> dict[str, list[str]]:
    """Compose a multi-ailment render — three ailments at once look
    'genuinely sick — green tinge, pustules, jerky walk all at once'.

    Returns a dict of layer_kind -> ordered list of overrides, in
    arrival order. The BPC stacks them.
    """
    out: dict[str, list[str]] = {
        "particles": [],
        "material_tints": [],
        "anim_overrides": [],
        "audio_overrides": [],
        "ui_gating": [],
    }
    for a in ailments:
        cue = get_cue(a)
        if cue.particle:
            out["particles"].append(cue.particle)
        if cue.material_tint:
            out["material_tints"].append(cue.material_tint)
        if cue.anim_override:
            out["anim_overrides"].append(cue.anim_override)
        if cue.audio_override:
            out["audio_overrides"].append(cue.audio_override)
        if cue.ui_gating:
            out["ui_gating"].append(cue.ui_gating)
    return out
