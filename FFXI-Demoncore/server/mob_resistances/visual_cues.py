"""Element → visible cue lookup.

Per the design doc table:
    Reddish glow on attack       -> fire
    Cyan steam-breath            -> ice
    Yellow crackle around limbs  -> lightning
    Earthen-brown dust trail     -> earth
    Pale-green leaf swirl        -> wind
    Deep-blue water droplets     -> water
    White-gold radiance          -> light
    Desaturated purple aura      -> dark

These are the strings the visual layer (Niagara emitters in UE5)
keys off when picking which glow effect to spawn. Subtle in the
'pristine' health stage; brighten as the mob moves into 'bloodied'
+ 'critical' (per VISUAL_HEALTH_SYSTEM).
"""
from __future__ import annotations

import dataclasses

from .elements import Element


@dataclasses.dataclass(frozen=True)
class VisualCue:
    """One rendering cue for an elemental affinity."""
    element: Element
    description: str             # narration: "reddish glow on attack"
    niagara_emitter: str         # asset id for the UE5 Niagara emitter
    audio_loop: str              # SFX loop key (subtle ambient)


VISUAL_CUE_TABLE: dict[Element, VisualCue] = {
    Element.FIRE: VisualCue(
        Element.FIRE,
        description="reddish glow on attack",
        niagara_emitter="NS_AffinityGlow_Fire",
        audio_loop="affinity_loop_fire",
    ),
    Element.ICE: VisualCue(
        Element.ICE,
        description="cyan steam-breath",
        niagara_emitter="NS_AffinityGlow_Ice",
        audio_loop="affinity_loop_ice",
    ),
    Element.LIGHTNING: VisualCue(
        Element.LIGHTNING,
        description="yellow crackle around limbs",
        niagara_emitter="NS_AffinityGlow_Lightning",
        audio_loop="affinity_loop_lightning",
    ),
    Element.EARTH: VisualCue(
        Element.EARTH,
        description="earthen-brown dust trail",
        niagara_emitter="NS_AffinityGlow_Earth",
        audio_loop="affinity_loop_earth",
    ),
    Element.WIND: VisualCue(
        Element.WIND,
        description="pale-green leaf swirl",
        niagara_emitter="NS_AffinityGlow_Wind",
        audio_loop="affinity_loop_wind",
    ),
    Element.WATER: VisualCue(
        Element.WATER,
        description="deep-blue water droplets",
        niagara_emitter="NS_AffinityGlow_Water",
        audio_loop="affinity_loop_water",
    ),
    Element.LIGHT: VisualCue(
        Element.LIGHT,
        description="white-gold radiance",
        niagara_emitter="NS_AffinityGlow_Light",
        audio_loop="affinity_loop_light",
    ),
    Element.DARK: VisualCue(
        Element.DARK,
        description="desaturated purple aura",
        niagara_emitter="NS_AffinityGlow_Dark",
        audio_loop="affinity_loop_dark",
    ),
}


def visual_cue_for(element: Element) -> VisualCue:
    """Look up the rendering cue. NONE returns a sentinel cue."""
    if element == Element.NONE:
        return VisualCue(
            element=Element.NONE,
            description="no elemental aura",
            niagara_emitter="",
            audio_loop="",
        )
    return VISUAL_CUE_TABLE[element]
