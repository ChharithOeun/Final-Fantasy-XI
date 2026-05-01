"""Ninja hand-sign engine.

Per NIN_HAND_SIGNS.md: NIN doesn't chant — they form hand seals in
sequence, chakra-flow visible between fingers, while moving at full
sprint. Other observers can READ the sequence and predict which
spell is coming. The skill-ceiling principle from VISUAL_HEALTH +
AOE_TELEGRAPH applies here too.

Twelve seals (canonical Naruto zodiac vocabulary, freely available
across martial-arts and anime canon — animations authored from
reference, no IP issues): Tiger, Boar, Dog, Dragon, Snake, Bird,
Ram, Horse, Monkey, Rabbit, Ox, Rat.

This module owns:
    - The 12 seals + their element biases (seals.py)
    - 13 canonical Ninjutsu spell sequences (sequences.py)
    - Active sign-session lifecycle with pause-on-damage + 1.5s
      resume window (sign_session.py)
    - Spell predictor: 'given the seals seen so far, what spells could
      this become?' — the basis for the visible-reading principle
      (spell_predictor.py)
    - Chakra-flow brightness + elemental tint helper for the renderer
      (visual_chakra.py)

Public surface:
    Seal, SealSpec, SEAL_SPECS
    NINJUTSU_SEQUENCES, sequence_for(spell)
    NinSignSession, NinSignManager, SignState
    SpellPredictor, candidate_spells, is_uniquely_identified
    chakra_brightness, chakra_tint, ELEMENTAL_TINTS
"""
from .seals import (
    SEAL_SPECS,
    Seal,
    SealSpec,
)
from .sequences import (
    DEFAULT_SEAL_TIME_SECONDS,
    NINJUTSU_SEQUENCES,
    sequence_for,
    spell_family,
)
from .sign_session import (
    DAMAGE_INTERRUPT_CHANCE,
    NinSignManager,
    NinSignSession,
    RESUME_WINDOW_SECONDS,
    SignState,
    SignTick,
)
from .spell_predictor import (
    SpellPredictor,
    candidate_spells,
    is_uniquely_identified,
)
from .visual_chakra import (
    ELEMENTAL_TINTS,
    chakra_brightness,
    chakra_tint,
)

__all__ = [
    "Seal",
    "SealSpec",
    "SEAL_SPECS",
    "NINJUTSU_SEQUENCES",
    "sequence_for",
    "spell_family",
    "DEFAULT_SEAL_TIME_SECONDS",
    "NinSignSession",
    "NinSignManager",
    "SignState",
    "SignTick",
    "DAMAGE_INTERRUPT_CHANCE",
    "RESUME_WINDOW_SECONDS",
    "SpellPredictor",
    "candidate_spells",
    "is_uniquely_identified",
    "chakra_brightness",
    "chakra_tint",
    "ELEMENTAL_TINTS",
]
