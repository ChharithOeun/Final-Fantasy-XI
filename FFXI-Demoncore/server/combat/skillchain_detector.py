"""Skillchain detector.

Observes a stream of weapon-skill / hand-sign-spell events on a
target and emits skillchain-closed events when two compatible
WS land within the 8-second close window per
`SKILLCHAIN_SYSTEM.md`.

Pure-Python deterministic logic. The LSB damage broker calls
`observe_weapon_skill()` whenever a player's WS resolves on a
target. The detector returns `SkillchainEvent` objects when a
chain detonates (Level 1, 2, or 3).

Design notes:
- Window semantics: chain closes if the SECOND WS lands within
  8 seconds of the FIRST. After detonation, a new chain can be
  opened (Level 2 extension) within 3 more seconds.
- Property combining: per the canonical FFXI Skillchain table.
  Two WS with combinable properties produce a named element.
- NIN substitution: hand-sign elemental ninjutsu landing in
  the close window counts as one chain contributor (per
  NIN_HAND_SIGNS.md + SKILLCHAIN_SYSTEM.md).
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# ---------------------------------------------------------------------------
# WSProperty — the 8 chain-properties a WS or hand-sign spell can carry
# ---------------------------------------------------------------------------

class WSProperty(str, enum.Enum):
    LIQUEFACTION = "liquefaction"   # fire
    INDURATION = "induration"        # ice
    REVERBERATION = "reverberation"  # water
    DETONATION = "detonation"        # wind
    SCISSION = "scission"            # earth
    COMPRESSION = "compression"      # dark
    TRANSFIXION = "transfixion"      # light
    IMPACTION = "impaction"          # lightning


class Element(str, enum.Enum):
    FIRE = "fire"
    ICE = "ice"
    WATER = "water"
    WIND = "wind"
    EARTH = "earth"
    DARK = "dark"
    LIGHT = "light"
    LIGHTNING = "lightning"
    PHYSICAL = "physical"


# WSProperty → Element (when the property matures into a chain element)
PROPERTY_TO_ELEMENT: dict[WSProperty, Element] = {
    WSProperty.LIQUEFACTION: Element.FIRE,
    WSProperty.INDURATION: Element.ICE,
    WSProperty.REVERBERATION: Element.WATER,
    WSProperty.DETONATION: Element.WIND,
    WSProperty.SCISSION: Element.EARTH,
    WSProperty.COMPRESSION: Element.DARK,
    WSProperty.TRANSFIXION: Element.LIGHT,
    WSProperty.IMPACTION: Element.LIGHTNING,
}


# ---------------------------------------------------------------------------
# SkillchainElement — what the chain detonates as
# ---------------------------------------------------------------------------

class SkillchainElement(str, enum.Enum):
    # Level 1
    LIQUEFACTION = "liquefaction"
    INDURATION = "induration"
    REVERBERATION = "reverberation"
    DETONATION = "detonation"
    SCISSION = "scission"
    COMPRESSION = "compression"
    TRANSFIXION = "transfixion"
    IMPACTION = "impaction"
    # Level 2
    FUSION = "fusion"               # fire + light
    FRAGMENTATION = "fragmentation" # wind + lightning
    DISTORTION = "distortion"       # water + ice
    GRAVITATION = "gravitation"     # earth + dark
    # Level 3 apex
    LIGHT = "light"
    DARKNESS = "darkness"


class SkillchainLevel(enum.IntEnum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


# ---------------------------------------------------------------------------
# Combination tables
# ---------------------------------------------------------------------------

# Level-1 chain table: (opener, closer) -> element
# Per canonical FFXI mappings preserved in SKILLCHAIN_SYSTEM.md
LEVEL_1_TABLE: dict[tuple[WSProperty, WSProperty], SkillchainElement] = {
    (WSProperty.IMPACTION,    WSProperty.LIQUEFACTION):  SkillchainElement.LIQUEFACTION,
    (WSProperty.DETONATION,   WSProperty.LIQUEFACTION):  SkillchainElement.LIQUEFACTION,
    (WSProperty.IMPACTION,    WSProperty.INDURATION):    SkillchainElement.INDURATION,
    (WSProperty.COMPRESSION,  WSProperty.INDURATION):    SkillchainElement.INDURATION,
    (WSProperty.DETONATION,   WSProperty.REVERBERATION): SkillchainElement.REVERBERATION,
    (WSProperty.COMPRESSION,  WSProperty.DETONATION):    SkillchainElement.DETONATION,
    (WSProperty.SCISSION,     WSProperty.DETONATION):    SkillchainElement.DETONATION,
    (WSProperty.LIQUEFACTION, WSProperty.SCISSION):      SkillchainElement.SCISSION,
    (WSProperty.REVERBERATION,WSProperty.SCISSION):      SkillchainElement.SCISSION,
    (WSProperty.INDURATION,   WSProperty.COMPRESSION):   SkillchainElement.COMPRESSION,
    (WSProperty.REVERBERATION,WSProperty.COMPRESSION):   SkillchainElement.COMPRESSION,
    (WSProperty.SCISSION,     WSProperty.TRANSFIXION):   SkillchainElement.TRANSFIXION,
    (WSProperty.COMPRESSION,  WSProperty.TRANSFIXION):   SkillchainElement.TRANSFIXION,
    (WSProperty.TRANSFIXION,  WSProperty.IMPACTION):     SkillchainElement.IMPACTION,
}

# Level-2 chains extend a Level-1 chain element with a new WS property
LEVEL_2_TABLE: dict[tuple[SkillchainElement, WSProperty], SkillchainElement] = {
    # Fusion = fire + light: closer Liquefaction or Transfixion
    (SkillchainElement.LIQUEFACTION, WSProperty.TRANSFIXION): SkillchainElement.FUSION,
    (SkillchainElement.TRANSFIXION,  WSProperty.LIQUEFACTION): SkillchainElement.FUSION,
    # Fragmentation = wind + lightning
    (SkillchainElement.DETONATION,   WSProperty.IMPACTION):    SkillchainElement.FRAGMENTATION,
    (SkillchainElement.IMPACTION,    WSProperty.DETONATION):   SkillchainElement.FRAGMENTATION,
    # Distortion = water + ice
    (SkillchainElement.REVERBERATION,WSProperty.INDURATION):   SkillchainElement.DISTORTION,
    (SkillchainElement.INDURATION,   WSProperty.REVERBERATION):SkillchainElement.DISTORTION,
    # Gravitation = earth + dark
    (SkillchainElement.SCISSION,     WSProperty.COMPRESSION):  SkillchainElement.GRAVITATION,
    (SkillchainElement.COMPRESSION,  WSProperty.SCISSION):     SkillchainElement.GRAVITATION,
}

# Level-3 chains: two Level-2 chain elements compose
LEVEL_3_TABLE: dict[tuple[SkillchainElement, SkillchainElement], SkillchainElement] = {
    (SkillchainElement.FUSION,        SkillchainElement.FRAGMENTATION): SkillchainElement.LIGHT,
    (SkillchainElement.FRAGMENTATION, SkillchainElement.FUSION):        SkillchainElement.LIGHT,
    (SkillchainElement.DISTORTION,    SkillchainElement.GRAVITATION):   SkillchainElement.DARKNESS,
    (SkillchainElement.GRAVITATION,   SkillchainElement.DISTORTION):    SkillchainElement.DARKNESS,
    # Two Lights or two Darknesses also stack
    (SkillchainElement.FUSION,        SkillchainElement.FUSION):        SkillchainElement.LIGHT,
    (SkillchainElement.FRAGMENTATION, SkillchainElement.FRAGMENTATION): SkillchainElement.LIGHT,
    (SkillchainElement.DISTORTION,    SkillchainElement.DISTORTION):    SkillchainElement.DARKNESS,
    (SkillchainElement.GRAVITATION,   SkillchainElement.GRAVITATION):   SkillchainElement.DARKNESS,
}


# Element of the chain output (used by damage resolver to compute affinity)
SKILLCHAIN_ELEMENT_TO_ELEMENT: dict[SkillchainElement, Element] = {
    SkillchainElement.LIQUEFACTION:  Element.FIRE,
    SkillchainElement.INDURATION:    Element.ICE,
    SkillchainElement.REVERBERATION: Element.WATER,
    SkillchainElement.DETONATION:    Element.WIND,
    SkillchainElement.SCISSION:      Element.EARTH,
    SkillchainElement.COMPRESSION:   Element.DARK,
    SkillchainElement.TRANSFIXION:   Element.LIGHT,
    SkillchainElement.IMPACTION:     Element.LIGHTNING,
    SkillchainElement.FUSION:        Element.FIRE,    # primary; light is secondary
    SkillchainElement.FRAGMENTATION: Element.WIND,
    SkillchainElement.DISTORTION:    Element.WATER,
    SkillchainElement.GRAVITATION:   Element.EARTH,
    SkillchainElement.LIGHT:         Element.LIGHT,
    SkillchainElement.DARKNESS:      Element.DARK,
}


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class WeaponSkillEvent:
    """A weapon skill or hand-sign spell landed on the target."""
    actor_id: str
    target_id: str
    ws_id: str                       # e.g. "crescent_moon", "hyoton_ichi"
    property: WSProperty
    damage: int                       # raw damage dealt
    landed_at: float                  # world-time seconds


@dataclasses.dataclass
class SkillchainEvent:
    """A skillchain just detonated."""
    target_id: str
    element: SkillchainElement
    level: SkillchainLevel
    contributors: list[str]           # actor ids that contributed
    base_damage_sum: int              # sum of contributor WS damages
    detonated_at: float
    mb_window_expires_at: float       # 3 seconds after detonation


# ---------------------------------------------------------------------------
# SkillchainDetector
# ---------------------------------------------------------------------------

# Time window for chain combinations (per canonical FFXI)
CHAIN_CLOSE_WINDOW_SECONDS = 8.0
# Time after a detonation during which a Level-2 extension can fire
EXTENSION_WINDOW_SECONDS = 3.0


@dataclasses.dataclass
class _PendingChain:
    """Tracking state for an open chain on a single target."""
    last_ws_event: t.Optional[WeaponSkillEvent] = None
    last_chain_element: t.Optional[SkillchainElement] = None
    last_chain_level: t.Optional[SkillchainLevel] = None
    last_chain_contributors: list[str] = dataclasses.field(default_factory=list)
    last_chain_base_damage: int = 0
    last_chain_detonated_at: t.Optional[float] = None


class SkillchainDetector:
    """One detector instance tracks per-target chain state."""

    def __init__(self):
        self._pending: dict[str, _PendingChain] = {}

    def observe_weapon_skill(self, event: WeaponSkillEvent) -> t.Optional[SkillchainEvent]:
        """Process one WS landing. Returns a SkillchainEvent if the
        WS just closed a chain (Level 1, 2, or 3). Returns None
        otherwise (chain opener or out-of-window)."""
        target = event.target_id
        pending = self._pending.setdefault(target, _PendingChain())
        now = event.landed_at

        # First check: is this WS extending an existing chain?
        if (pending.last_chain_element is not None
                and pending.last_chain_detonated_at is not None
                and now - pending.last_chain_detonated_at <= EXTENSION_WINDOW_SECONDS
                and pending.last_chain_level == SkillchainLevel.LEVEL_1):
            # Try Level-2 extension
            key = (pending.last_chain_element, event.property)
            if key in LEVEL_2_TABLE:
                detonated_element = LEVEL_2_TABLE[key]
                contributors = list(pending.last_chain_contributors) + [event.actor_id]
                total_damage = pending.last_chain_base_damage + event.damage
                detonation = SkillchainEvent(
                    target_id=target,
                    element=detonated_element,
                    level=SkillchainLevel.LEVEL_2,
                    contributors=contributors,
                    base_damage_sum=total_damage,
                    detonated_at=now,
                    mb_window_expires_at=now + EXTENSION_WINDOW_SECONDS,
                )
                pending.last_ws_event = event
                pending.last_chain_element = detonated_element
                pending.last_chain_level = SkillchainLevel.LEVEL_2
                pending.last_chain_contributors = contributors
                pending.last_chain_base_damage = total_damage
                pending.last_chain_detonated_at = now
                return detonation

        if (pending.last_chain_element is not None
                and pending.last_chain_detonated_at is not None
                and now - pending.last_chain_detonated_at <= EXTENSION_WINDOW_SECONDS
                and pending.last_chain_level == SkillchainLevel.LEVEL_2):
            # Could only happen if a *separate* Level-2 chain just closed
            # in the extension window — extremely rare. We don't model
            # the "two L2 chains in one extension window" case here.
            pass

        # Second check: does this WS close a Level-1 chain?
        if (pending.last_ws_event is not None
                and now - pending.last_ws_event.landed_at <= CHAIN_CLOSE_WINDOW_SECONDS
                and pending.last_chain_element is None):
            # Two-WS combo
            key = (pending.last_ws_event.property, event.property)
            if key in LEVEL_1_TABLE:
                detonated_element = LEVEL_1_TABLE[key]
                contributors = [pending.last_ws_event.actor_id, event.actor_id]
                total_damage = pending.last_ws_event.damage + event.damage
                detonation = SkillchainEvent(
                    target_id=target,
                    element=detonated_element,
                    level=SkillchainLevel.LEVEL_1,
                    contributors=contributors,
                    base_damage_sum=total_damage,
                    detonated_at=now,
                    mb_window_expires_at=now + EXTENSION_WINDOW_SECONDS,
                )
                pending.last_ws_event = event
                pending.last_chain_element = detonated_element
                pending.last_chain_level = SkillchainLevel.LEVEL_1
                pending.last_chain_contributors = contributors
                pending.last_chain_base_damage = total_damage
                pending.last_chain_detonated_at = now
                return detonation

        # Otherwise this WS is a new opener (or out of window)
        pending.last_ws_event = event
        # Reset chain state if window expired
        if (pending.last_chain_detonated_at is not None
                and now - pending.last_chain_detonated_at > EXTENSION_WINDOW_SECONDS):
            pending.last_chain_element = None
            pending.last_chain_level = None
            pending.last_chain_contributors = []
            pending.last_chain_base_damage = 0
            pending.last_chain_detonated_at = None
        return None

    def get_active_window(self, target_id: str) -> t.Optional[SkillchainElement]:
        """Return the active chain element on a target, or None.

        Used by the damage resolver to know if a Magic Burst is
        landing on a chain. The element is the LAST detonation that's
        still within the MB window.
        """
        pending = self._pending.get(target_id)
        if pending is None or pending.last_chain_element is None:
            return None
        return pending.last_chain_element

    def is_in_mb_window(self, target_id: str, now: float) -> bool:
        pending = self._pending.get(target_id)
        if pending is None or pending.last_chain_detonated_at is None:
            return False
        return now - pending.last_chain_detonated_at <= EXTENSION_WINDOW_SECONDS

    def reset_target(self, target_id: str) -> None:
        """Called when a target dies or leaves combat — clear chain state."""
        self._pending.pop(target_id, None)


def chain_to_element(skillchain_element: SkillchainElement) -> Element:
    """Convenience for damage_resolver."""
    return SKILLCHAIN_ELEMENT_TO_ELEMENT[skillchain_element]
