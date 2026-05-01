"""Demoncore combat resolver + skillchain detector.

Per SKILLCHAIN_SYSTEM.md, INTERVENTION_MB.md, WEIGHT_PHYSICS.md,
and MOB_RESISTANCES.md. The math made executable: feed in a stream
of weapon-skill / spell / damage events, get back resolved damage
numbers + skillchain detonation events + magic-burst windows.

Public surface:
    SkillchainDetector  — observes WS events, emits chain detonations
    DamageResolver       — computes damage given all the modifiers
    Element             — canonical FFXI element enum
    SkillchainElement   — Level-1 / Level-2 / Level-3 chain elements
    WSProperty          — the chain-property (Liquefaction etc) a WS carries
    DamageContext       — input to the resolver
    DamageResult        — output of the resolver
"""
from .skillchain_detector import (
    Element,
    SkillchainDetector,
    SkillchainElement,
    SkillchainEvent,
    SkillchainLevel,
    WSProperty,
    WeaponSkillEvent,
)
from .damage_resolver import (
    DamageContext,
    DamageResolver,
    DamageResult,
    SpellType,
)

__all__ = [
    "Element",
    "SkillchainDetector",
    "SkillchainElement",
    "SkillchainEvent",
    "SkillchainLevel",
    "WSProperty",
    "WeaponSkillEvent",
    "DamageContext",
    "DamageResolver",
    "DamageResult",
    "SpellType",
]
