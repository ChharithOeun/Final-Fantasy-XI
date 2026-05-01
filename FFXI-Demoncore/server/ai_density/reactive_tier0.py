"""Tier-0 reactive primitives — pure reflex behaviors.

Per AI_WORLD_DENSITY.md: 'Pure reflex behaviors. No memory. No plan.
Trigger -> response.' Cost ~0 per agent because the entire population
runs on UE5 native Behavior Trees + simple state machines client-side.

This module is the *catalog* — caller maps a (entity, trigger) pair
to the named ReactiveBehavior and the UE5 client plays the matching
state machine. The Python side just publishes the catalog.
"""
from __future__ import annotations

import dataclasses
import enum


class ReactiveTrigger(str, enum.Enum):
    """Stimulus kinds a Tier-0 entity can respond to."""
    FOOTSTEP_SOUND = "footstep_sound"
    SWORD_DRAWN_NEARBY = "sword_drawn_nearby"
    AOE_DETONATION = "aoe_detonation"
    PLAYER_BASIC_ATTACK_ON_OBJECT = "player_basic_attack_on_object"
    MOUNTED_PLAYER_NEARBY = "mounted_player_nearby"
    LOUD_NOISE = "loud_noise"
    SHADOW_PASSING_OVERHEAD = "shadow_passing_overhead"
    FIRE_NEARBY = "fire_nearby"


@dataclasses.dataclass(frozen=True)
class ReactiveBehavior:
    """A single reflex behavior."""
    behavior_id: str
    archetype: str           # which entities can run it
    trigger: ReactiveTrigger
    response: str            # named UE5 BT branch / state machine
    radius_cm: float         # detection radius
    cooldown_seconds: float = 0.0
    notes: str = ""


# Catalog of reflex behaviors — 8 canonical examples from the doc.
REACTIVE_PRIMITIVES: dict[str, ReactiveBehavior] = {
    "fish_school_avoidance": ReactiveBehavior(
        behavior_id="fish_school_avoidance",
        archetype="fish_school",
        trigger=ReactiveTrigger.FOOTSTEP_SOUND,
        response="boids_steer_away",
        radius_cm=300,
        notes="boids-style swerve from approaching footsteps",
    ),
    "bird_startle": ReactiveBehavior(
        behavior_id="bird_startle",
        archetype="bird",
        trigger=ReactiveTrigger.SWORD_DRAWN_NEARBY,
        response="flap_takeoff",
        radius_cm=800,
    ),
    "rat_flee": ReactiveBehavior(
        behavior_id="rat_flee",
        archetype="rat",
        trigger=ReactiveTrigger.FOOTSTEP_SOUND,
        response="dart_to_nearest_hide_spot",
        radius_cm=200,
    ),
    "banner_flap": ReactiveBehavior(
        behavior_id="banner_flap",
        archetype="banner",
        trigger=ReactiveTrigger.AOE_DETONATION,
        response="flap_animation_loop",
        radius_cm=1500,
    ),
    "lantern_flicker": ReactiveBehavior(
        behavior_id="lantern_flicker",
        archetype="lantern",
        trigger=ReactiveTrigger.PLAYER_BASIC_ATTACK_ON_OBJECT,
        response="flicker_2s",
        radius_cm=50,
        cooldown_seconds=4.0,
    ),
    "wildlife_hop": ReactiveBehavior(
        behavior_id="wildlife_hop",
        archetype="wildlife",
        trigger=ReactiveTrigger.MOUNTED_PLAYER_NEARBY,
        response="sidestep_path",
        radius_cm=400,
    ),
    "small_animal_freeze": ReactiveBehavior(
        behavior_id="small_animal_freeze",
        archetype="small_animal",
        trigger=ReactiveTrigger.LOUD_NOISE,
        response="freeze_then_dart",
        radius_cm=600,
    ),
    "scared_bystander_duck": ReactiveBehavior(
        behavior_id="scared_bystander_duck",
        archetype="ambient_townfolk",
        trigger=ReactiveTrigger.SWORD_DRAWN_NEARBY,
        response="duck_and_cover",
        radius_cm=500,
        cooldown_seconds=10.0,
        notes="even Tier-1 NPCs play this Tier-0 reflex when threatened",
    ),
}


def react_to(*,
              archetype: str,
              trigger: ReactiveTrigger) -> list[ReactiveBehavior]:
    """Return the reflex behaviors that fire for this (archetype,
    trigger) pair. Most Tier-0 entities have one matching reflex;
    bystanders may have several."""
    out = []
    for bh in REACTIVE_PRIMITIVES.values():
        if bh.archetype == archetype.lower() and bh.trigger == trigger:
            out.append(bh)
    return out
