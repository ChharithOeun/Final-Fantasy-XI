"""Elemental affinity + mob resistance engine.

Per MOB_RESISTANCES.md: every mob/NM/boss has a visible elemental
affinity. Players read it through fur color, equipment color,
breath effect, mood-glow, and voice — the same "look at the world"
language as VISUAL_HEALTH_SYSTEM. Picking the right element matters
more than picking the biggest spell.

Per-mob aligned_element + weak_to + strong_vs:
    matching        ->  0.50x damage
    weak_to (hit)   ->  1.25x
    strong_vs (hit) ->  0.75x
    neutral         ->  1.00x

Boss-grade encounters can hide affinity during pristine phase and
shift affinity per phase (Maat opens dark, shifts to light, can
flip neutral during Hundred Fists).

Public surface:
    Element (enum)
    MobAffinity
    damage_multiplier(attacker_element, defender) -> float
    MOB_CLASS_AFFINITIES
    affinity_for(mob_class)
    visual_cue_for(element)
    VISUAL_CUE_TABLE
    BossAffinityPhase, BossPhaseShifter
    apply_chain_x_affinity(chain_dmg_base, affinity_mult, stationary)
    apply_ailment_x_affinity(base_ailment_strength, affinity_mult)
"""
from .affinity import (
    MOB_CLASS_AFFINITIES,
    MobAffinity,
    affinity_for,
    apply_ailment_x_affinity,
    apply_chain_x_affinity,
    damage_multiplier,
)
from .elements import (
    ELEMENT_OPPOSITES,
    Element,
)
from .phase_shifter import (
    BossAffinityPhase,
    BossPhaseShifter,
)
from .visual_cues import (
    VISUAL_CUE_TABLE,
    visual_cue_for,
)

__all__ = [
    # Elements
    "Element",
    "ELEMENT_OPPOSITES",
    # Affinity
    "MobAffinity",
    "MOB_CLASS_AFFINITIES",
    "affinity_for",
    "damage_multiplier",
    "apply_chain_x_affinity",
    "apply_ailment_x_affinity",
    # Visual
    "visual_cue_for",
    "VISUAL_CUE_TABLE",
    # Phases
    "BossAffinityPhase",
    "BossPhaseShifter",
]
