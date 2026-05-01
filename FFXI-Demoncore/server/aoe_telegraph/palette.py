"""Element / damage type color palette.

Per AOE_TELEGRAPH.md table — each element/damage type maps to a hex
color so the battlefield reads at a glance. The renderer keys off
this string to pick the decal material parameter.

Saturation + border thickness convey friend/foe:
    high saturation + thick border  = enemy AOE (panic)
    lower saturation + thin border  = ally AOE (be aware)

This module only owns the hex strings; saturation tweaks happen at
the material layer. Downstream code resolves the right hex via
color_for_element() and the renderer applies the friend/foe modifier.
"""
from __future__ import annotations


# Hex strings exactly as authored in the design doc.
ELEMENT_COLOR_HEX: dict[str, str] = {
    # Elemental
    "fire":       "#ff6633",
    "ice":        "#66ccff",
    "lightning":  "#ffd633",   # animated stripe with #cc66ff (yellow-violet)
    "earth":      "#996633",
    "wind":       "#99ff99",
    "water":      "#3366cc",
    "light":      "#fff5cc",
    "dark":       "#663366",
    # Damage type / category
    "physical":   "#ff9999",
    "healing":    "#99ffcc",
    "buff_zone":  "#ffe699",
    "debuff_zone":"#cc6666",
}

# Lightning gets a second stripe color for the animated effect
LIGHTNING_STRIPE_HEX = "#cc66ff"


def color_for_element(element: str) -> str:
    """Look up the primary color hex for an element / damage type.

    Returns "#cccccc" (neutral grey) for unknown types so renderers
    don't crash on unusual spell tags. The caller can choose to log
    or surface that as a warning."""
    return ELEMENT_COLOR_HEX.get(element.lower(), "#cccccc")
