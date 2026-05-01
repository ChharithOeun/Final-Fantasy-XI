"""Spell → seal-sequence catalog.

Per NIN_HAND_SIGNS.md the 13 canonical Ninjutsu sequences. Designer-
authored, balanced for combat tempo:
    Ichi-tier:  2-3 seals (~0.45s)
    Ni-tier:    3-4 seals (~0.6s)
    San-tier:   4-7 seals (~0.9-1.1s)

Spell families:
    utsusemi   - shadow images, defensive
    katon      - fire offense
    hyoton     - ice offense
    doton      - earth (root / utility)
    suiton     - water offense / escape
    huton      - wind / movement
    raiton     - lightning offense
    tonko      - escape utility
    aisha      - debuff stack
"""
from __future__ import annotations

import typing as t

from .seals import Seal


DEFAULT_SEAL_TIME_SECONDS = 0.15


# Master spell-to-sequence map (the 13 canonical sequences from the doc).
NINJUTSU_SEQUENCES: dict[str, list[Seal]] = {
    # Utsusemi family (shadow images)
    "utsusemi_ichi": [Seal.TIGER, Seal.BOAR],
    "utsusemi_ni":   [Seal.TIGER, Seal.BOAR, Seal.SNAKE],
    "utsusemi_san":  [Seal.TIGER, Seal.BOAR, Seal.SNAKE, Seal.RAM],

    # Katon family (fire)
    "katon_ichi":    [Seal.SNAKE, Seal.TIGER],
    "katon_ni":      [Seal.SNAKE, Seal.TIGER, Seal.HORSE],
    "katon_san":     [Seal.SNAKE, Seal.TIGER, Seal.HORSE, Seal.MONKEY, Seal.TIGER],

    # Hyoton (ice) — single-tier in the doc
    "hyoton_ichi":   [Seal.BIRD, Seal.SNAKE, Seal.RAM, Seal.BOAR, Seal.OX, Seal.TIGER],

    # Doton (earth root)
    "doton_ichi":    [Seal.BOAR, Seal.DRAGON, Seal.RABBIT],

    # Suiton (water)
    "suiton_ichi":   [Seal.DOG, Seal.BOAR],

    # Huton (wind)
    "huton_ichi":    [Seal.BIRD, Seal.DOG],

    # Raiton (lightning)
    "raiton_ichi":   [Seal.OX, Seal.RABBIT, Seal.MONKEY],

    # Tonko (escape)
    "tonko_ni":      [Seal.TIGER, Seal.SNAKE, Seal.RAT],

    # Aisha (debuff)
    "aisha":         [Seal.SNAKE, Seal.BOAR, Seal.TIGER],
}


SPELL_FAMILY_PREFIXES: tuple[str, ...] = (
    "utsusemi", "katon", "hyoton", "doton", "suiton",
    "huton", "raiton", "tonko", "aisha",
)


def sequence_for(spell: str) -> t.Optional[list[Seal]]:
    """Look up the seal sequence. Case-insensitive; returns None if
    unknown."""
    return NINJUTSU_SEQUENCES.get(spell.lower())


def spell_family(spell: str) -> str:
    """Map a spell id to its family ('katon_san' -> 'katon').

    Returns the matched family prefix, or 'unknown' if no canonical
    family applies."""
    s = spell.lower()
    for family in SPELL_FAMILY_PREFIXES:
        if s.startswith(family):
            return family
    return "unknown"


def expected_total_time(sequence: list[Seal],
                          *,
                          per_seal: float = DEFAULT_SEAL_TIME_SECONDS,
                          ) -> float:
    """How long the full sign-sequence takes at base seal speed."""
    return len(sequence) * per_seal
