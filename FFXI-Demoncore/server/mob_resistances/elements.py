"""Element wheel + opposition map.

Canonical FFXI 8-element scheme:
    Fire <-> Ice
    Water <-> Lightning
    Earth <-> Wind
    Light <-> Dark

Each element has a single bidirectional opposite. The visual wheel
in MOB_RESISTANCES.md positions Light/Dark on the vertical axis,
Earth/Wind+Lightning/Water on the horizontal cross, Fire/Ice as
the explicit opposition pair.

Note: the per-mob affinity object (MobAffinity) explicitly lists
weak_to + strong_vs because mobs often have an affinity that's NOT
their opposite — an Orc is fire-aligned but its weak_to is Ice (its
opposite) AND its strong_vs is Wind (a different relationship the
mob class chose). The wheel governs the *general* case; per-mob
overrides handle the specific.
"""
from __future__ import annotations

import enum


class Element(str, enum.Enum):
    """8-element scheme + non-elemental NONE."""
    FIRE = "fire"
    ICE = "ice"
    WATER = "water"
    LIGHTNING = "lightning"
    EARTH = "earth"
    WIND = "wind"
    LIGHT = "light"
    DARK = "dark"
    NONE = "none"          # non-elemental physical / fixed dmg


ELEMENT_OPPOSITES: dict[Element, Element] = {
    Element.FIRE: Element.ICE,
    Element.ICE: Element.FIRE,
    Element.WATER: Element.LIGHTNING,
    Element.LIGHTNING: Element.WATER,
    Element.EARTH: Element.WIND,
    Element.WIND: Element.EARTH,
    Element.LIGHT: Element.DARK,
    Element.DARK: Element.LIGHT,
}


def opposite_of(element: Element) -> Element:
    """Return the canonical wheel opposite. NONE has no opposite."""
    return ELEMENT_OPPOSITES.get(element, Element.NONE)
