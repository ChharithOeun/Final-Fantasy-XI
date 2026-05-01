"""AiTier enum + classification helpers.

Tier assignment is the orchestrator's per-entity decision. Helpers
here let the caller derive a default tier from the entity's archetype
(player / hero NPC / vendor NPC / mob / wildlife).
"""
from __future__ import annotations

import enum
import typing as t


class AiTier(int, enum.Enum):
    """5 tiers from cheapest to most-expensive AI."""
    REACTIVE = 0           # boids, reflex, no memory
    SCRIPTED_BARK = 1      # schedule + bark library
    REFLECTION = 2         # hourly LLM reflection on memory_summary
    HERO = 3               # full generative agent (daily plans + relationships)
    RL_POLICY = 4          # per-mob-class ONNX combat policy


# Default tier per archetype hint
_DEFAULT_TIER_BY_ARCHETYPE: dict[str, AiTier] = {
    "wildlife": AiTier.REACTIVE,
    "fish_school": AiTier.REACTIVE,
    "bird": AiTier.REACTIVE,
    "rat": AiTier.REACTIVE,
    "ambient_townfolk": AiTier.SCRIPTED_BARK,
    "patrol_guard": AiTier.SCRIPTED_BARK,
    "performer": AiTier.SCRIPTED_BARK,
    "vendor": AiTier.REFLECTION,
    "questgiver": AiTier.REFLECTION,
    "tavern_regular": AiTier.REFLECTION,
    "guild_master": AiTier.REFLECTION,
    "hero_npc": AiTier.HERO,
    "named_storyteller": AiTier.HERO,
    "mob": AiTier.RL_POLICY,
    "nm": AiTier.RL_POLICY,
    "boss": AiTier.RL_POLICY,
}


def classify_tier(*,
                    archetype: str,
                    is_hero: bool = False,
                    has_named_role: bool = False,
                    is_combat_entity: bool = False,
                    ) -> AiTier:
    """Resolve the default tier for a new entity.

    `archetype` is the primary hint (e.g. 'vendor', 'wildlife',
    'hero_npc'). Caller can override with the boolean hints when the
    archetype is ambiguous.

    Returns AiTier.SCRIPTED_BARK for unknown archetypes (safe default).
    """
    if is_hero:
        return AiTier.HERO
    if is_combat_entity:
        return AiTier.RL_POLICY
    if has_named_role:
        return AiTier.REFLECTION
    return _DEFAULT_TIER_BY_ARCHETYPE.get(archetype.lower(),
                                            AiTier.SCRIPTED_BARK)
