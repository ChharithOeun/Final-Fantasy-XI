"""Chakra-flow VFX descriptor.

Per NIN_HAND_SIGNS.md:
    Persistent Niagara emitter binds to NIN's hand sockets.
    On seal-sequence start, emitter spins up:
      - Faint blue chakra-light wrapping each hand
      - Thin chakra-line tracing between hands at hand-touching seals
      - Brightness ramps with each completed seal in the sequence —
        mid-sequence the NIN is visibly glowing
      - Element of the spell tints the chakra in the LAST 30%
      - On final seal, a bright burst as the spell completes

This module is a small descriptor: given a seal_index + total +
spell_id, return the brightness ramp + (optional) elemental tint
for the renderer.
"""
from __future__ import annotations

import typing as t

from .sequences import spell_family


# Per-family final-30% tint hex values.
ELEMENTAL_TINTS: dict[str, str] = {
    "katon":     "#ff6633",   # red-orange (fire)
    "hyoton":    "#66ccff",   # cyan (ice)
    "raiton":    "#ffd633",   # yellow (lightning, with flicker)
    "suiton":    "#3366cc",   # deep blue (water)
    "doton":     "#996633",   # brown-amber (earth)
    "huton":     "#99ff99",   # pale green (wind)
    "tonko":     "#cccccc",   # silver-flash (escape)
    "utsusemi":  "#aac8ff",   # faint blue (illusion / shadow)
    "aisha":     "#cc6666",   # desaturated red (debuff)
}

# Default 'pre-tint' chakra color — faint blue for everyone
BASE_CHAKRA_HEX = "#7aaaff"

# Last fraction of the sequence where elemental tint replaces the base.
TINT_RAMP_THRESHOLD = 0.7


def chakra_brightness(seal_index: int, total_seals: int) -> float:
    """0..1 brightness as the sequence progresses.

    seal_index = 0 -> 0.20 (faint glow on hands at start)
    seal_index = total -> 1.00 (peak brightness; spell about to release)
    """
    if total_seals <= 0:
        return 0.0
    progress = min(1.0, seal_index / total_seals)
    # Range: 0.20 (faint) to 1.00 (peak)
    return 0.20 + 0.80 * progress


def chakra_tint(spell: str,
                 *,
                 seal_index: int,
                 total_seals: int) -> str:
    """Renderer-keyed hex color. Returns BASE_CHAKRA_HEX until the
    sequence crosses the tint-ramp threshold (last 30%); after that,
    returns the spell-family elemental tint.

    A spell with no known family or no canonical tint stays on the
    base color throughout."""
    if total_seals <= 0:
        return BASE_CHAKRA_HEX
    progress = seal_index / total_seals
    if progress < TINT_RAMP_THRESHOLD:
        return BASE_CHAKRA_HEX
    family = spell_family(spell)
    return ELEMENTAL_TINTS.get(family, BASE_CHAKRA_HEX)
