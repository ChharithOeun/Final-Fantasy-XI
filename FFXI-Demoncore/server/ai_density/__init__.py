"""AI world density — 4-tier brain budget for the whole world.

Per AI_WORLD_DENSITY.md doctrine: 'the world is full of brains. By
ship date, every entity bigger than a particle has some degree of
autonomous behavior'. We tier by importance so we can run a 70B
LLM-level brain on Cid but a free reflex behavior on a chicken.

Five tiers:
    Tier 0 - REACTIVE        millions, ~free per agent (boids, reflex)
    Tier 1 - SCRIPTED_BARK   thousands, ~$0 (schedule + bark library)
    Tier 2 - REFLECTION      hundreds, $0.0001 (Llama 3 8B hourly reflect)
    Tier 3 - HERO            dozens, $0.001/turn (full generative agent)
    Tier 4 - RL_POLICY       per-mob-class (combat-only ONNX policies)

Module layout:
    tier_classifier.py  - AiTier enum + assignment helpers
    reactive_tier0.py   - Tier-0 reflex primitives
    scripted_bark.py    - Tier-1 schedule + bark library
    reflection_agent.py - Tier-2 hourly memory_summary + bark tuning
    hero_agent.py       - Tier-3 daily plans + relationships + goals
    density_budget.py   - per-zone density targets + admission control

Public surface:
    AiTier, classify_tier, ZONE_DENSITY_TARGETS
    ReactiveBehavior, REACTIVE_PRIMITIVES, react_to
    BarkAgent, ScheduleEntry, pick_bark
    ReflectionAgent, reflect_on_events, MEMORY_SUMMARY_MAX_CHARS
    HeroAgent, DailyScheduleEntry, Relationship
    DensityBudget, admit_entity, current_density
"""
from .density_budget import (
    DensityBudget,
    DensitySnapshot,
    ZONE_DENSITY_TARGETS,
    admit_entity,
    current_density,
)
from .hero_agent import (
    DailyScheduleEntry,
    HeroAgent,
    Relationship,
)
from .reactive_tier0 import (
    REACTIVE_PRIMITIVES,
    ReactiveBehavior,
    ReactiveTrigger,
    react_to,
)
from .reflection_agent import (
    MEMORY_SUMMARY_MAX_CHARS,
    REFLECTION_INTERVAL_SECONDS,
    ReflectionAgent,
    reflect_on_events,
)
from .scripted_bark import (
    BarkAgent,
    ScheduleEntry,
    pick_bark,
)
from .tier_classifier import (
    AiTier,
    classify_tier,
)

__all__ = [
    "AiTier",
    "classify_tier",
    "ZONE_DENSITY_TARGETS",
    "DensityBudget",
    "DensitySnapshot",
    "admit_entity",
    "current_density",
    "ReactiveBehavior",
    "ReactiveTrigger",
    "REACTIVE_PRIMITIVES",
    "react_to",
    "BarkAgent",
    "ScheduleEntry",
    "pick_bark",
    "ReflectionAgent",
    "reflect_on_events",
    "MEMORY_SUMMARY_MAX_CHARS",
    "REFLECTION_INTERVAL_SECONDS",
    "HeroAgent",
    "DailyScheduleEntry",
    "Relationship",
]
