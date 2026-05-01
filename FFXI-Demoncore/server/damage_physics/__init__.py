"""Damage physics + healing — destructible structures with HoT.

Per DAMAGE_PHYSICS_HEALING.md: 'The world has weight. Spells crater
earth, swords splinter wood, beastman sieges punch holes in city
walls. And then - over time - it heals.'

This module is the server-authoritative spine for that system.
The UE5 client plays the spectacle (Chaos Geometry Collection +
Niagara VFX); we own HP, state, healing math, repair NPC quotes,
and PvP rules.

Module layout:
    structure_kinds.py  - presets table + MaterialClass + VFX presets
    structure_state.py  - HealingStructure + VisibleState bands
    damage_resolver.py  - apply_damage + AOE + permanent-threshold
    heal_tick.py        - heal_delay_s aware regen + broadcast filter
    repair_npc.py       - 3-NPC roster + quote_repair + apply_repair
    pvp_rules.py        - own/foreign/iconic strike classification
    registry.py         - per-zone store + tick_all + snapshot/restore

Public surface:
    MaterialClass, StructurePreset, STRUCTURE_PRESETS, VFX_PRESETS,
    DEFAULT_HEAL_DELAY_S, get_preset, is_iconic
    VisibleState, HealingStructure, resolve_visible_state
    DamageEvent, apply_damage, aoe_damage, linear_falloff
    HealEvent, can_heal, heal_tick, heal_tick_many,
        filter_broadcastable
    RepairNpc, RepairQuote, REPAIR_NPC_ROSTER,
        get_repair_npc, quote_repair, apply_repair
    StrikeOutcome, StrikeRuling, StrikeContext, classify_strike,
        OWN_NATION_HONOR_PENALTY, OWN_NATION_FINE_GIL,
        ICONIC_HONOR_PENALTY, ICONIC_FINE_GIL
    StructureRegistry, StructureSnapshot, global_registry,
        reset_global_registry
"""
from .damage_resolver import (
    DamageEvent,
    aoe_damage,
    apply_damage,
    linear_falloff,
)
from .heal_tick import (
    HealEvent,
    can_heal,
    filter_broadcastable,
    heal_tick,
    heal_tick_many,
)
from .pvp_rules import (
    ICONIC_FINE_GIL,
    ICONIC_HONOR_PENALTY,
    OWN_NATION_FINE_GIL,
    OWN_NATION_HONOR_PENALTY,
    StrikeContext,
    StrikeOutcome,
    StrikeRuling,
    classify_strike,
)
from .registry import (
    StructureRegistry,
    StructureSnapshot,
    global_registry,
    reset_global_registry,
)
from .repair_npc import (
    REPAIR_NPC_ROSTER,
    RepairNpc,
    RepairQuote,
    apply_repair,
    get_repair_npc,
    quote_repair,
)
from .structure_kinds import (
    DEFAULT_HEAL_DELAY_S,
    STRUCTURE_PRESETS,
    VFX_PRESETS,
    MaterialClass,
    StructurePreset,
    VfxPreset,
    get_preset,
    is_iconic,
)
from .structure_state import (
    HealingStructure,
    VisibleState,
    resolve_visible_state,
)

__all__ = [
    # structure_kinds
    "MaterialClass", "StructurePreset", "VfxPreset",
    "STRUCTURE_PRESETS", "VFX_PRESETS", "DEFAULT_HEAL_DELAY_S",
    "get_preset", "is_iconic",
    # structure_state
    "VisibleState", "HealingStructure", "resolve_visible_state",
    # damage_resolver
    "DamageEvent", "apply_damage", "aoe_damage", "linear_falloff",
    # heal_tick
    "HealEvent", "can_heal", "heal_tick", "heal_tick_many",
    "filter_broadcastable",
    # repair_npc
    "RepairNpc", "RepairQuote", "REPAIR_NPC_ROSTER",
    "get_repair_npc", "quote_repair", "apply_repair",
    # pvp_rules
    "StrikeOutcome", "StrikeRuling", "StrikeContext",
    "classify_strike",
    "OWN_NATION_HONOR_PENALTY", "OWN_NATION_FINE_GIL",
    "ICONIC_HONOR_PENALTY", "ICONIC_FINE_GIL",
    # registry
    "StructureRegistry", "StructureSnapshot",
    "global_registry", "reset_global_registry",
]
