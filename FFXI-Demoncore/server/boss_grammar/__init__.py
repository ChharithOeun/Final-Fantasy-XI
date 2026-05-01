"""Boss grammar — the 5-layer recipe DSL.

Per BOSS_GRAMMAR.md: 'A boss in Demoncore is not a monster with a
big HP pool. A boss is a performance.' Five layers — Body, Repertoire,
Phases, Mind, Cinematic — compose into one BossRecipe.

Module layout:
    layers.py     - 5-layer dataclasses + BossRecipe + validate
    repertoire.py - 7-12 attack rule + AOE size bands
    phases.py     - 6 phases mapped to visible-health stages
    cinematic.py  - Entrance / Intro / Defeat / Aftermath beats
"""
from .cinematic import (
    AftermathBeat,
    BossCinematic,
    DefeatBeat,
    EntranceBeat,
    IntroBeat,
)
from .layers import (
    BodyLayer,
    BossRecipe,
    MindLayer,
    validate_recipe,
)
from .phases import (
    BOSS_PHASE_ORDER,
    BossPhase,
    PhaseRule,
    PhaseTransitionEvent,
    phase_for_hp_fraction,
)
from .repertoire import (
    AOE_SIZE_BANDS,
    BossAttack,
    Repertoire,
    classify_attack_size,
    validate_repertoire,
)

__all__ = [
    "BossRecipe", "BodyLayer", "MindLayer", "validate_recipe",
    "Repertoire", "BossAttack", "AOE_SIZE_BANDS",
    "classify_attack_size", "validate_repertoire",
    "BossPhase", "BOSS_PHASE_ORDER", "PhaseRule",
    "PhaseTransitionEvent", "phase_for_hp_fraction",
    "BossCinematic", "EntranceBeat", "IntroBeat",
    "DefeatBeat", "AftermathBeat",
]
