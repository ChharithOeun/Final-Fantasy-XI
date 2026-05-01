"""Per-mob affinity table + damage multiplier resolver.

Per MOB_RESISTANCES.md damage formula:

    chain_dmg_final = chain_dmg_base × affinity_multiplier × stationary_bonus

    affinity_multiplier:
      weak-to:        1.25
      neutral:        1.00
      strong-against: 0.75
      matching:       0.50

The 3x ailment amplification (per SKILLCHAIN_SYSTEM.md) is multiplied
by the affinity bonus too: a 3x Slow on a wind-weak target during
an Earth-element chain = 3.75x effective Slow strength.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .elements import Element


# Multipliers per the doc
MATCHING_MULTIPLIER = 0.50
WEAK_TO_MULTIPLIER = 1.25
STRONG_VS_MULTIPLIER = 0.75
NEUTRAL_MULTIPLIER = 1.00


@dataclasses.dataclass(frozen=True)
class MobAffinity:
    """Per-mob (or per-class default) affinity profile.

    aligned_element  - the element the mob *is*. Casting this
                        element on it is half-damage.
    weak_to          - the element that hits this mob hard (+25%).
    strong_vs        - the element this mob shrugs off (-25%).
    resists_all      - special flag (e.g. Demon NM): every spell
                        does -25% except their weak_to.
    """
    aligned_element: Element
    weak_to: t.Optional[Element] = None
    strong_vs: t.Optional[Element] = None
    resists_all: bool = False


def damage_multiplier(*,
                       attacker_element: Element,
                       defender: MobAffinity) -> float:
    """Return the multiplier for `attacker_element` hitting a mob
    with the given affinity."""
    # Non-elemental damage (NONE) is unaffected by elemental affinity
    if attacker_element == Element.NONE:
        return NEUTRAL_MULTIPLIER

    # Matching trumps everything: same element as the mob = half.
    if attacker_element == defender.aligned_element:
        return MATCHING_MULTIPLIER

    # Weak-to overrides resists_all (you found the chink)
    if defender.weak_to is not None and attacker_element == defender.weak_to:
        return WEAK_TO_MULTIPLIER

    # Strong-vs is a per-element resistance line item
    if defender.strong_vs is not None and attacker_element == defender.strong_vs:
        return STRONG_VS_MULTIPLIER

    # Demon-style "resists everything"
    if defender.resists_all:
        return STRONG_VS_MULTIPLIER

    return NEUTRAL_MULTIPLIER


def apply_chain_x_affinity(*,
                            chain_dmg_base: float,
                            affinity_multiplier: float,
                            stationary_bonus: float = 1.0) -> float:
    """Compose the chain damage formula. stationary_bonus comes from
    weight_physics (e.g. 1.10 for fully-still attacker + still target
    times the weapon-weight scale — passed in)."""
    return chain_dmg_base * affinity_multiplier * stationary_bonus


def apply_ailment_x_affinity(*,
                              base_ailment_strength: float,
                              affinity_multiplier: float,
                              ailment_amp: float = 3.0) -> float:
    """Per the doc: 3x Slow on a wind-weak target during an Earth
    chain = 3.75x effective.

    base_ailment_strength × ailment_amp × affinity_multiplier.
    """
    return base_ailment_strength * ailment_amp * affinity_multiplier


# ----------------------------------------------------------------------
# Per-mob-class table (populated from the doc)
# ----------------------------------------------------------------------

MOB_CLASS_AFFINITIES: dict[str, MobAffinity] = {
    "quadav": MobAffinity(Element.LIGHTNING, Element.WATER, Element.WIND),
    "yagudo": MobAffinity(Element.WATER, Element.LIGHTNING, Element.FIRE),
    "orc":    MobAffinity(Element.FIRE, Element.ICE, Element.WIND),
    "goblin": MobAffinity(Element.EARTH, Element.WIND, Element.LIGHTNING),
    "tonberry": MobAffinity(Element.DARK, Element.LIGHT, None),
    "naga":   MobAffinity(Element.WATER, Element.LIGHTNING, Element.FIRE),
    "bee":    MobAffinity(Element.WIND, Element.EARTH, Element.WATER),
    "skeleton": MobAffinity(Element.DARK, Element.LIGHT, None),
    "sahagin":  MobAffinity(Element.WATER, Element.LIGHTNING, Element.FIRE),
    "bug":      MobAffinity(Element.EARTH, Element.WIND, Element.WATER),
    "demon_nm": MobAffinity(Element.DARK, Element.LIGHT, None,
                              resists_all=True),
    # Slime + Dragon are intentionally NOT in this table — they
    # vary per-zone or per-individual; the caller supplies the
    # affinity at mob-spawn time.
}


def affinity_for(mob_class: str) -> t.Optional[MobAffinity]:
    """Lookup helper. Returns None for variable-affinity classes
    (slimes, dragons) — caller must supply the spawned individual's
    affinity directly."""
    return MOB_CLASS_AFFINITIES.get(mob_class.lower())
